from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SuccessfulMessage(BaseModel):
    status_code: int
    detail: str
    timestamp: datetime = datetime.utcnow()
    payload: Optional[dict] = None