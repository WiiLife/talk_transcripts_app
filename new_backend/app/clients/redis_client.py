from config.config import settings
import redis.asyncio as redis_async


class RedisClient:
    def __init__(self) -> None:
        self.__client = redis_async.Redis(host=settings.REDIS_HOST, port=6379, db=0, decode_responses=True)
        
    @property
    def client(self):
        return self.__client
