from starlette.datastructures import Headers
from fastapi import UploadFile
from fastapi.datastructures import UploadFile as UploadFileDatastructure
from qdrant_client.http.models import VectorParams, Distance
from tempfile import SpooledTemporaryFile
from typing import List, BinaryIO, cast
from pathlib import Path
from config.config import settings
from app.clients.qdrant_client import QuadrantClient
from app.clients.redis_client import RedisClient
from app.utils.file_processing_pipeline import FileProcessingPipeline
from app.models.uploading import ChunkedUploadMetadata, ChunkDataInfo
from app.utils.CustomHTTPException import CustomHTTPException
import uuid
import asyncio
import aiofiles
import math
import os


class UploadController:
    def __init__(self) -> None:
        self.__qdrant_client = QuadrantClient().client
        self.__redis_client = RedisClient().client
        self.__file_processing_pipeline = FileProcessingPipeline()
        self.__processable_file_types = [".txt"]
        self.__upload_locks: dict[str, asyncio.Lock] = {}
        self.__upload_locks_lock = asyncio.Lock()
        self.__chunks_location = Path("/tmp/upload")
        
    def _scan_for_non_uploaded_chunks(self, metadata: ChunkedUploadMetadata):
        missing_chunk_indexs = []
        for i, cm in enumerate(metadata.chunk_metadata):
            if cm.chunk_index != i:
                missing_chunk_indexs.append(i)
                
        return missing_chunk_indexs
        
    def _merge_chunks(self, file_extention: str, chunks_dir: str, merged_file_name = None, block_size: int = settings.MERGING_CHUNK_SIZE):
        if merged_file_name is None:
            merged_file_name = Path(chunks_dir).name
        
        all_files = os.listdir(chunks_dir)
        chunk_files = [f for f in all_files if f.startswith('chunk_')]
        if len(chunk_files) == 0:
            raise ValueError("No chunk files found in directory")
        
        sorted_chunk_files = sorted(chunk_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        merged_path = os.path.join(chunks_dir, merged_file_name) + f".{file_extention}"
        
        # Delete existing merged if present (cleanup leftovers)
        if os.path.exists(merged_path):
            os.remove(merged_path)
        
        with open(merged_path, "wb") as merged_file:
            for file in sorted_chunk_files:
                chunk_path = os.path.join(chunks_dir, file)
                with open(chunk_path, "rb") as f:
                    while True:
                        block = f.read(block_size)
                        if not block:
                            break
                        merged_file.write(block)
        return merged_path
        
    async def _get_upload_lock(self, upload_id) -> asyncio.Lock:
        async with self.__upload_locks_lock:
            if upload_id not in self.__upload_locks:
                self.__upload_locks[upload_id] = asyncio.Lock()
            return self.__upload_locks[upload_id]
        
    def _existing_collection(self, collection_name: str, redis_uuid: str):
        collection_exists = self.__qdrant_client.collection_exists(collection_name + "_" + redis_uuid)
        if collection_exists:
            self.__redis_client.delete(redis_uuid)
        return collection_exists
        
    def _create_upload_file(self, file_path: str) -> UploadFileDatastructure:
        with open(file_path, 'rb') as file:
            file_content = file.read()
        
        spooled_file = SpooledTemporaryFile()
        spooled_file.write(file_content)
        spooled_file.seek(0)
        
        upload_file = UploadFileDatastructure(
            filename=file_path.split('/')[-1],
            file=cast(BinaryIO, spooled_file),
            headers=Headers({"content-type": "text/plain"}),
        )
    
        return upload_file
    
    async def upload_files_to_qdrant(self, files: List[UploadFile]):
        for f in files:
            await self.upload_file_to_qdrant(f)
    
    async def upload_file_to_qdrant(self, file: UploadFile):
        if file.filename is None:
            raise ValueError("Uploaded file must have a filename")
        if Path(file.filename).suffix not in self.__processable_file_types:
            raise ValueError("Filetype currently not processable")
        file_collection_name = Path(file.filename).stem
        
        try:
            vec_points = await self.__file_processing_pipeline.process_txt_file(file)
        except Exception as e:
            raise ValueError(f"error occured wile processing file: {e}")
        
        embedding_model = self.__file_processing_pipeline.embedding_model
        dimension = embedding_model.get_sentence_embedding_dimension()
        
        if dimension is None:
            raise ValueError("Model embedding dimension is None.")
        
        self.__qdrant_client.create_collection(
            collection_name=file_collection_name,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE,
            ),
        )
        
        self.__qdrant_client.upsert(
            collection_name=file_collection_name,
            points=vec_points
        )

    async def chunked_upload_init(self, file_name: str, file_size: int, chunk_size: int, total_chunks: int, content_type: str):
        
        metadata = ChunkedUploadMetadata(
            file_name=file_name,
            file_size=file_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            content_type=content_type,
            chunk_metadata=[],
        )
        
        if file_size > settings.MAX_FILESIZE:
            raise ValueError(f"File size exceeds the limit. {file_size} > {settings.MAX_FILESIZE}")

        if chunk_size > settings.MAX_CHUNK_SIZE:
            raise ValueError(f"Chunk size exceeds the limit.")

        try:
            session_id = str(uuid.uuid4())
            await self.__redis_client.set(session_id, metadata.json(), ex=settings.CHUNK_TTL)
        except Exception as e:
            raise ValueError(f"Redis Error: {str(e)}")

        return {
                "metadata": metadata.dict(), 
                "redis_uuid": session_id
        }
    
    async def process_chunk(self, chunk_data: bytes, chunk_index: int, redis_uuid: str):
        
        upload_lock = await self._get_upload_lock(chunk_index)
        
        async with upload_lock:

            redis_data = await self.__redis_client.get(redis_uuid)
            metadata = ChunkedUploadMetadata.parse_raw(redis_data)
            
            collection_name = Path(metadata.file_name).stem
            if self._existing_collection(collection_name, redis_uuid):
                raise ValueError(f"Existing collection {collection_name}")

            try:
                upload_dir = self.__chunks_location / f"{collection_name}_{redis_uuid}"
                upload_dir.mkdir(parents=True, exist_ok=True)

                chunk_path = upload_dir / f"chunk_{chunk_index}.txt"
                async with aiofiles.open(chunk_path, "wb") as f:
                    await f.write(chunk_data)

            except Exception as e:
                raise ValueError(f"Error saving chunk: {str(e)}")

            if any(cm.chunk_index == chunk_index for cm in metadata.chunk_metadata):
                return {
                    "message": f"Chunk {chunk_index} already uploaded.",
                    "payload": {"ignore": True}
                }

            metadata.chunk_metadata.append(
                ChunkDataInfo(chunk_index=chunk_index, file_path=str(chunk_path))
            )

            try:
                await self.__redis_client.set(redis_uuid, metadata.json(), ex=settings.CHUNK_TTL)
            except Exception as e:
                raise ValueError(f"Redis Error: {str(e)}")
    
    async def chunked_chunking_status(self, redis_uuid: str):
        
        try: 
            redis_data = await self.__redis_client.get(redis_uuid)
            metadata = ChunkedUploadMetadata.parse_raw(redis_data)

            is_complete = len(metadata.chunk_metadata) == metadata.total_chunks
            
        except Exception as e:
            raise ValueError(f"Redis Error: {str(e)}")
        
        return {
                "metadata": metadata.dict(), 
                "progress_percentage": len(metadata.chunk_metadata) / metadata.total_chunks,
                "is_complete": is_complete
        }    
    
    async def complete_chunked_upload(self, redis_uuid: str):
        retries = 0

        redis_data = await self.__redis_client.get(redis_uuid)
        if not redis_data:
            raise ValueError("Upload session not found")

        metadata = ChunkedUploadMetadata.parse_raw(redis_data)

        while len(metadata.chunk_metadata) != metadata.total_chunks:
            if retries > settings.MAX_RETRIES:
                raise ValueError("all retries failed, data not fully uploaded")
            missing_indexs = self._scan_for_non_uploaded_chunks(metadata)
            retries += 1
            try:
                delay = math.factorial(retries)
                await asyncio.sleep(delay)
                redis_data = await self.__redis_client.get(redis_uuid)
                metadata = ChunkedUploadMetadata.parse_raw(redis_data)
            except Exception as e:
                return {
                    "message": f"Error during retry {retries}: {str(e)}",
                    "payload": {"missing_indexes": missing_indexs}
                }
        
            try:
                chunks_dir = str(self.__chunks_location / f"{Path(metadata.file_name).stem}_{redis_uuid}")
                ext = metadata.file_name.split(".")[-1]
                merged_chunks_file_path = self._merge_chunks(file_extention=ext, chunks_dir=chunks_dir)
                result = await self.upload_file_to_qdrant(self._create_upload_file(merged_chunks_file_path))

                for chunk in metadata.chunk_metadata:
                    os.remove(chunk.file_path)
                os.remove(merged_chunks_file_path)

                await self.__redis_client.delete(redis_uuid)

                return result
            except Exception as e:
                raise ValueError(f"Processing error: {str(e)}")
