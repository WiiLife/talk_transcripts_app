from fastapi import HTTPException

class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str, payload: dict = None):
        super().__init__(status_code=status_code, detail=detail)
        self.payload = payload