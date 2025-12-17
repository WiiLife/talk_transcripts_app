from fastapi import APIRouter, UploadFile, HTTPException, Request
from typing import List
from app.controllers.upload_controller import UploadController
from app.models.messages import SuccessfulMessage
from app.models.uploading import UploadInitRequest, UploadChunkRequest, UploadStatusRequest, UploadCompleteRequest
from config.config import settings


route = APIRouter(prefix="/api", tags=["database_router"])

@route.post("/upload")
async def upload_files(files: List[UploadFile]):
    upload_controller = UploadController()
    
    try:
        await upload_controller.upload_files_to_qdrant(list(files))
    except Exception as e:
        HTTPException(
            status_code=500,
            detail=f"upload failed: {e}"
        )

@route.get("/upload/instr")
async def upload_instructions():
    return SuccessfulMessage(
        detail="Successfully request chunked upload instructions",
        payload={
            "max_file_size": settings.MAX_FILESIZE,
            "max_chunk_size": settings.MAX_CHUNK_SIZE,
            "chunk_ttl": settings.CHUNK_TTL,
        }
    )

@route.post("/upload/init")
async def upload_init(req: Request):
    data: UploadInitRequest = await req.json()
    
    upload_controller = UploadController()
    
    try:
        init_data = await upload_controller.chunked_upload_init(data.file_name, data.file_size, data.chunk_size, data.total_chunks, data.content_type)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while requesting upload initlization: {e}"
        )
        
    return SuccessfulMessage(
        detail="successfully retrieved init rules",
        payload=init_data
    )

@route.post("/upload/chunk")
async def process_chunk(req: Request):
    data: UploadChunkRequest = await req.json()
    
    upload_controller = UploadController()
    
    try:
        process_res = await upload_controller.process_chunk(data.chunk_data, data.chunk_index, data.redis_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while processing chunk: {e}"
        )

    return SuccessfulMessage(
        status_code=202,
        detail=f"succesfully processed chunk: {data.chunk_index}",
        payload=process_res
    )

@route.post("/upload/status")
async def chunking_status(req: Request):
    data: UploadStatusRequest = await req.json()
    
    upload_controller = UploadController()
    
    try:
        chunking_status_res = await upload_controller.chunked_chunking_status(data.redis_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error while retrieving uploading status: {e}"
        )
        
    return SuccessfulMessage(
        detail="chunking status retrieved successfully",
        payload=chunking_status_res
    )

@route.post("/upload/complete")
async def complete_upload(req: Request):
    data: UploadCompleteRequest = await req.json()
    
    upload_controller = UploadController()
    
    try:
        upload_complete_res = await upload_controller.complete_chunked_upload(data.redis_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error while completeing chunk upload: {e}"
        )
        
    return SuccessfulMessage(
        detail="Successfully retrieved chunked upload",
        payload=upload_complete_res
    )
