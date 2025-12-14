from fastapi import APIRouter, UploadFile, HTTPException, Request
from typing import List
from app.controllers.upload_controller import UploadController
from app.models.messages import SuccessfulMessage
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
    pass

@route.post("/upload/chunk")
async def process_chunk(req: Request):
    pass

@route.post("/upload/status")
async def chunking_status(req: Request):
    pass

@route.post("/upload/complete")
async def complete_upload(req: Request):
    pass
