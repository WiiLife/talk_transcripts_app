from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SuccessfulMessage(BaseModel):
    status_code: int = 200
    detail: str
    timestamp: datetime = datetime.utcnow()
    payload: Optional[dict] = None
    
class UnsuccessfulResponse(BaseModel):
    status_code: int
    detail: str
    timestamp: datetime = datetime.utcnow()
    payload: Optional[dict] = None
    
class ErrorMessage(BaseModel):
    status_code: int
    details: str
    timestamp: datetime = datetime.utcnow()
    payload: Optional[dict] = None