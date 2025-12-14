from starlette.datastructures import UploadFile as StarletteUploadFile, Headers
from fastapi import UploadFile
from qdrant_client.http.models import VectorParams, Distance
from tempfile import SpooledTemporaryFile
from typing import List, BinaryIO, cast
from pathlib import Path
from app.clients.qdrant_client import QuadrantClient
from app.utils.file_processing_pipeline import FileProcessingPipeline


class UploadController:
    def __init__(self) -> None:
        self.__qdrant_client = QuadrantClient().client
        self.__file_processing_pipeline = FileProcessingPipeline()
        self.__processable_file_types = [".txt"]
        
    def _create_upload_file(self, file_path: str) -> StarletteUploadFile:
        with open(file_path, 'rb') as file:
            file_content = file.read()
        
        spooled_file = SpooledTemporaryFile()
        spooled_file.write(file_content)
        spooled_file.seek(0)
        
        upload_file = StarletteUploadFile(
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
        
        if file_collection_name in [c.name for c in self.__qdrant_client.get_collections().collections]:
            raise ValueError(f"Collection for file: {file.filename} already present")
        
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

    async def chunked_upload_init(self):
        pass
    
    async def process_chunk(self):
        pass
    
    async def chunked_chunking_status(self):
        pass
    
    async def complete_chunked_upload(self):
        pass