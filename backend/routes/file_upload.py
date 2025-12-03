from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path
import redis.asyncio as redis
import os
import uuid
import logging
import asyncio
import aiofiles
import math

from backend.routes.utils.file_processing import get_model, process_pdf_file, process_txt_file, embed_chunks
from backend.models.messages import SuccessfulMessage, UnsuccessfulResponse
from backend.models.uploading import ChunkedUploadMetadata, ChunkDataInfo
from qdrant_client.http.models import VectorParams, Distance
from backend.logging_config import setup_logging
from backend.CustomHTTPException import CustomHTTPException


load_dotenv()
setup_logging()
PROJECT_ROOT = Path(__file__).resolve().parent
VECTOR_DB_COLLECTION_NAME = os.environ.get("VECTOR_DB_COLLECTION_NAME", "talks_transcripts")
MAX_FILESIZE = int(os.environ.get("MAX_FILESIZE", 81920000)) # 80MB
MAX_CHUNK_SIZE = int(os.environ.get("MAX_CHUNK_SIZE", 10485760)) # 10MB
CHUNK_TTL = int(os.environ.get("CHUNK_TTL", 86400))  # 1 day in seconds
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))
MERGING_CHUNK_SIZE = int(os.environ.get("MERGING_CHUNK_SIZE", 5 * 1024 * 1024)) # 5MB when merging chunks in one file
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")

info_log = logging.getLogger("info_logger")
debug_log = logging.getLogger("debug_logger")

route = APIRouter(prefix="/api", tags=["database_router"])
redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True) # docker run -p 6379:6379 redis
client = QdrantClient(url=f"http://{QDRANT_HOST}:6333")  # docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant   

SUPPORTED_FILE_TYPES = [".pdf", ".txt"] 

upload_locks: dict[str, asyncio.Lock] = {}
upload_locks_lock = asyncio.Lock()


async def get_upload_lock(upload_id: str) -> asyncio.Lock:
    async with upload_locks_lock:
        if upload_id not in upload_locks:
            upload_locks[upload_id] = asyncio.Lock()
        return upload_locks[upload_id]

def merge_chunks(file_extention: str, chunks_dir: str, merged_file_name = None, block_size: int = MERGING_CHUNK_SIZE):
    if merged_file_name is None:
        merged_file_name = Path(chunks_dir).name
    debug_log.debug(os.listdir(chunks_dir))
    
    all_files = os.listdir(chunks_dir)
    chunk_files = [f for f in all_files if f.startswith('chunk_') and f.endswith('.txt')]
    if len(chunk_files) == 0:
        raise ValueError("No chunk files found in directory")
    
    filenames = sorted(chunk_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
    merged_path = os.path.join(chunks_dir, merged_file_name) + f".{file_extention}"
    
    # Delete existing merged if present (cleanup leftovers)
    if os.path.exists(merged_path):
        os.remove(merged_path)
    
    with open(merged_path, "wb") as merged_file:
        for file in filenames:
            chunk_path = os.path.join(chunks_dir, file)
            with open(chunk_path, "rb") as f:
                while True:
                    block = f.read(block_size)
                    if not block:
                        break
                    merged_file.write(block)
    return merged_path

def upload_file(file_path: str):
    collection_name = Path(file_path).stem
        
    # create collection
    model = get_model()
    dimension = model.get_sentence_embedding_dimension()
    if dimension is None:
        raise HTTPException(status_code=500, detail="Model embedding dimension is None.")
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=dimension,
            distance=Distance.COSINE
        )
    )
    
    # embedd file contents
    is_pdf = file_path.lower().endswith('.pdf')
    is_txt = file_path.lower().endswith('.txt')
    
    with open(file_path, 'rb') as f:
        if is_txt:
            points = process_txt_file(f, os.path.basename(file_path), collection_name)
        elif is_pdf:
            points = process_pdf_file(f, os.path.basename(file_path), collection_name)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for '{os.path.basename(file_path)}'. Only {SUPPORTED_FILE_TYPES} supported."
            )
    
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    
    return SuccessfulMessage(
        status_code=200, 
        detail=f"Successfully processed {os.path.basename(file_path)}"
    )
    
def scan_for_non_uploaded_chunks(metadata: ChunkedUploadMetadata):
    
    missing_chunk_indexs = []
    for i, cm in enumerate(metadata.chunk_metadata):
        if cm.chunk_index != i:
            missing_chunk_indexs.append(i)
            
    return missing_chunk_indexs

@route.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload files and create separate collections for each based on filename
    Collection name will be the filename (without .pdf extension)
    Returns error if any collection already exists
    """

    # Get existing collections once
    existing_collections = client.get_collections().collections
    existing_collection_names = [c.name for c in existing_collections]

    results = []

    for f in files:
        if not f.filename:
            raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")
        collection_name = Path(f.filename).stem
        
        # Check if collection already exists
        if collection_name in existing_collection_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Collection '{collection_name}' already exists."
            )
        
        # Create collection for this file
        model = get_model()
        dimension = model.get_sentence_embedding_dimension()
        if dimension is None:
            raise HTTPException(status_code=500, detail="Model embedding dimension is None.")

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=dimension,
                distance=Distance.COSINE
            )
        )
        
        is_pdf = (f.content_type == 'application/pdf' or 
                (f.filename and f.filename.lower().endswith('.pdf')))
        is_txt = (f.content_type == 'text/plain' or 
                (f.filename and f.filename.lower().endswith('.txt')))
        
        if is_txt:
            points = process_txt_file(f.file, f.filename, collection_name)
        elif is_pdf:
            points = process_pdf_file(f.file, f.filename, collection_name)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for '{f.filename}'. Only PDF and TXT files are supported."
            )
        
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        existing_collection_names.append(collection_name)
        results.append(f"'{f.filename}' -> collection '{collection_name}' ({len(points)} chunks)")

    return SuccessfulMessage(
        status_code=200, 
        detail=f"Successfully processed {len(files)} files: {', '.join(results)}"
    )
    
@route.get("/upload/instr")
async def upload_instructions():
    return SuccessfulMessage(
        status_code=200,
        detail="Successfully request chunked upload instructions",
        payload={
            "max_file_size": MAX_FILESIZE,
            "max_chunk_size": MAX_CHUNK_SIZE,
            "chunk_ttl": CHUNK_TTL
        }
    )

@route.post("/upload/init")
async def upload_init(req: Request):
    """
    Creates upload metadata
    - verifies data being sent does not exceed limitations
    - creates upload progress metadata in Redis, making sure none of the actual data is sent through redis but kept in /tmp/uploads
    """
    
    data = await req.json()
    file_name = data["file_name"]
    file_size = data["file_size"]
    chunk_size = data["chunk_size"]
    total_chunks = data["total_chunks"]
    content_type = data["content_type"]
    
    collection_name = Path(file_name).stem
    
    existing_collections = client.get_collections().collections
    if collection_name in [c.name for c in existing_collections]:
        raise HTTPException(status_code=400, detail=f"Collection '{collection_name}' already exists.")
    
    metadata = ChunkedUploadMetadata(
        file_name=file_name,
        file_size=file_size,
        chunk_size=chunk_size,
        total_chunks=total_chunks,
        content_type=content_type,
        chunk_metadata=[]
    )
    
    if file_size > MAX_FILESIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds the limit. {file_size} > {MAX_FILESIZE}")

    if chunk_size > MAX_CHUNK_SIZE:
        raise HTTPException(status_code=400, detail=f"Chunk size exceeds the limit.")
    
    try:
        session_id = str(uuid.uuid4())
        await redis_client.set(session_id, metadata.json(), ex=CHUNK_TTL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")
    
    return SuccessfulMessage(
        status_code=200,
        detail="initation successful",
        payload={"metadata": metadata.dict(), "redis_uuid": session_id}
    )

@route.post("/upload/chunk")
async def process_chunk(req: Request):

    data = await req.json()
    chunk_data = data["chunk_data"]
    chunk_index = data["chunk_index"]
    redis_uuid = data["redis_uuid"]
    embed: bool = data["embed_chunk"]

    # Get lock *for this specific upload UUID*
    upload_lock = await get_upload_lock(redis_uuid)

    async with upload_lock:

        redis_data = await redis_client.get(redis_uuid)
        metadata = ChunkedUploadMetadata.parse_raw(redis_data)

        try:
            upload_dir = PROJECT_ROOT / "uploads" / f"{Path(metadata.file_name).stem}_{redis_uuid}"
            upload_dir.mkdir(parents=True, exist_ok=True)

            chunk_path = upload_dir / f"chunk_{chunk_index}.txt"

            # Write file safely
            async with aiofiles.open(chunk_path, "wb") as f:
                await f.write(chunk_data.encode("utf-8"))

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving chunk: {str(e)}")

        # Check for duplicates
        if any(cm.chunk_index == chunk_index for cm in metadata.chunk_metadata):
            return CustomHTTPException(
                status_code=409,
                detail=f"Chunk {chunk_index} already uploaded.",
                payload={"ignore": True}
            )

        metadata.chunk_metadata.append(
            ChunkDataInfo(chunk_index=chunk_index, file_path=str(chunk_path))
        )
        
        if embed:
            embed_chunks([chunk_data])

        try:
            await redis_client.set(redis_uuid, metadata.json(), ex=CHUNK_TTL)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")

        debug_log.debug(f"len metadata: {len(metadata.chunk_metadata)}")

    return SuccessfulMessage(
        status_code=200,
        detail=f"Chunk {chunk_index} Successfully stored"
    )
    
@route.post("/upload/status")
async def chunking_status(req: Request):
    """
    Reads Redis to return:
    Received chunks
    Upload progress, etc.
    """
    
    data = await req.json()
    redis_uuid = data["redis_uuid"]
    
    try: 
        redis_data = await redis_client.get(redis_uuid)
        metadata = ChunkedUploadMetadata.parse_raw(redis_data)
        
        is_complete = len(metadata.chunk_metadata) == metadata.total_chunks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")
    
    return SuccessfulMessage(
        status_code=200,
        detail="Successfully retrieved upload status",
        payload={
            "metadata": metadata.dict(), 
            "progress_percentage": len(metadata.chunk_metadata) / metadata.total_chunks,
            "is_complete": is_complete
        }    
    )
        
@route.post("/upload/complete")
async def complete_upload(req: Request):
    data = await req.json()
    redis_uuid = data["redis_uuid"]
    retries = 0
    
    redis_data = await redis_client.get(redis_uuid)
    if not redis_data:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    metadata = ChunkedUploadMetadata.parse_raw(redis_data)
    
    while len(metadata.chunk_metadata) != metadata.total_chunks:
        if retries > MAX_RETRIES:
            return HTTPException(status_code=400, detail="all retries failed, data not fully uploaded")
        missing_indexs = scan_for_non_uploaded_chunks(metadata)
        retries += 1
        try:
            delay = math.factorial(retries)
            info_log.info(f"sleeping for {delay}s")
            await asyncio.sleep(delay)
            redis_data = await redis_client.get(redis_uuid)
            metadata = ChunkedUploadMetadata.parse_raw(redis_data)
        except Exception as e:
            info_log.info(f"retry: {retries} failed")
            return CustomHTTPException(
                status_code=400, 
                detail=f"Error during retry {retries}: {str(e)}", 
                payload={"missing_indexes": missing_indexs}
            )
    
    try:
        chunks_dir = str(PROJECT_ROOT / "uploads" / f"{Path(metadata.file_name).stem}_{redis_uuid}")
        ext = metadata.file_name.split('.')[-1]
        merged_chunks_file_path = merge_chunks(file_extention=ext, chunks_dir=chunks_dir)
        result = upload_file(merged_chunks_file_path)
        
        # consider creating a postgres database for the user data
        
        # Cleanup
        for chunk in metadata.chunk_metadata:
            os.remove(chunk.file_path)
        os.remove(merged_chunks_file_path)
        
        await redis_client.delete(redis_uuid)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
