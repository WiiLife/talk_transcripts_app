from .config import settings
from qdrant_client import QdrantClient
import redis.asyncio as redis_async

# Centralized clients for the application
qdrant_client = QdrantClient(url=f"http://{settings.QDRANT_HOST}:6333")

# async redis client used across routes
redis_client = redis_async.Redis(host=settings.REDIS_HOST, port=6379, db=0, decode_responses=True)
