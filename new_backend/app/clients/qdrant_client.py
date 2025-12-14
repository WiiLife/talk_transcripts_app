from config.config import settings
from qdrant_client import QdrantClient

class QuadrantClient:
    def __init__(self) -> None:
        self.__client = QdrantClient(url=f"http://{settings.QDRANT_HOST}:6333")
        
    @property
    def client(self):
        return self.__client
