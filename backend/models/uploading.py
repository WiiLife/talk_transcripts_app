from pydantic import BaseModel
from datetime import datetime


class ChunkDataInfo(BaseModel):
    chunk_index: int
    file_path: str
    timestamp: datetime = datetime.utcnow()

class ChunkedUploadMetadata(BaseModel):
    file_name: str
    file_size: int
    chunk_size: int
    total_chunks: int
    content_type: str
    chunk_metadata: list[ChunkDataInfo]
    retry: int = 0
    timestamp: datetime = datetime.utcnow()
