from typing import Any, List

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from pathlib import Path
import os
import redis
import uuid
import json

from .utils.file_processing import get_model, process_pdf_file, process_txt_file
from ..models.messages import SuccessfulMessage, UnsuccessfulResponse
from ..models.uploading import ChunkedUploadMetadata, ChunkDataInfo
from qdrant_client.http.models import VectorParams, Distance

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent
VECTOR_DB_COLLECTION_NAME = os.environ.get("VECTOR_DB_COLLECTION_NAME", "talks_transcripts")
MAX_FILESIZE = int(os.environ.get("MAX_FILESIZE", 81920000)) # 80MB
MAX_CHUNK_SIZE = int(os.environ.get("MAX_CHUNK_SIZE", 10485760)) # 10MB
CHUNK_TTL = int(os.environ.get("CHUNK_TTL", 86400))  # 1 day in seconds

route = APIRouter(prefix="/api", tags=["database_router"])
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True) # docker run -p 6379 redis
client = QdrantClient(url="http://localhost:6333")  # docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant   

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
        # Use filename (without extension) as collection name
        # Ensure filename is a str for the type checker / runtime
        if not f.filename:
            raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")
        collection_name = os.path.splitext(f.filename)[0]
        
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
        await redis_client.set(session_id, json.dumps(metadata), ex=CHUNK_TTL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")
    
    return SuccessfulMessage(
        status_code=200,
        detail="initation successful",
        payload={"metadata": metadata.dict(), "redis_uuid": session_id}
    )

@route.post("/upload/chunk")
async def process_chunk(req: Request):
    """
    Receives chunk
    Saves chunk to disk /tmp/uploads/<filename>
    Updates Redis:
    Mark chunk received in Set
    """
    
    data =  await req.json()
    chunk_data = data["chunk_data"]
    chunk_index = data["chunk_index"]
    file_name = data["file_name"]
    redis_uuid = data["redis_uuid"]
    
    try:
        upload_dir = PROJECT_ROOT / "uploads" / Path(file_name).stem
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        chunk_path = upload_dir / f"chunk_{chunk_index}.txt"
        with open(chunk_path, "wb") as f:
            f.write(chunk_data)
        
    except Exception as e: 
        raise HTTPException(status_code=500, detail=f"Error saving chunk: {str(e)}")
    
    try:
        redis_data = await redis_client.get(redis_uuid)
        metadata: ChunkedUploadMetadata = json.loads(redis_data)
        
        if metadata.chunk_metadata[-1].chunk_index != chunk_index - 1:
            return UnsuccessfulResponse(
                status_code=409,
                detail=f"Expected chunk index {chunk_index - 1}, but received {chunk_index}. Upload chunks in order.",
                payload={"resend_chunk": chunk_index - 1}
            )            
        
        metadata.chunk_metadata.append(ChunkDataInfo(chunk_index=chunk_index))
        
        await redis_client.set(redis_uuid, json.dumps(metadata), ex=CHUNK_TTL)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")
    
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
    
    data =  await req.json()
    redis_uuid = data["redis_uuid"]
    
    try: 
        redis_data = await redis_client.get(redis_uuid)
        metadata: ChunkedUploadMetadata = json.loads(redis_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")
    
    return SuccessfulMessage(
        status_code=200,
        detail="Successfully retrieved upload status",
        payload={"metadata": metadata.dict(), "progress_percentage": len(metadata.chunk_metadata) / metadata.total_chunks}    
    )
        

@route.post("/upload/complete")
async def complete_upload(req: Request):
    '''
    Checks Redis:
        If uploadedCount == totalChunks
    Merges chunks
    Deletes temp files
    Marks upload as "completed"
    '''
    
    data = await req.json()
    redis_uuid = data["redis_uuid"]
    
    try:       
        redis_data = await redis_client.get(redis_uuid)
        metadata: ChunkedUploadMetadata = json.loads(redis_data)
        
        if len(metadata.chunk_metadata) != metadata.total_chunks:
            raise HTTPException(status_code=400, detail="not all chunks have been uploaded")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    
    # save data in postgres
        