from pydantic import BaseSettings
from typing import List


class Settings(BaseSettings):
    LLM_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    LLM_SERVICE_API_KEY: str | None = None
    VECTOR_DB_COLLECTION_NAME: str = "talks_transcripts"
    DEFAULT_MODEL: str = "qwen/qwen3-coder:free"

    MAX_FILESIZE: int = 81920000
    MAX_CHUNK_SIZE: int = 10485760
    CHUNK_TTL: int = 86400
    MAX_RETRIES: int = 3
    MERGING_CHUNK_SIZE: int = 5 * 1024 * 1024

    REDIS_HOST: str = "localhost"
    QDRANT_HOST: str = "localhost"

    CHUNK_SIZE: int = 800
    OVERLAP: int = 100
    BATCH_SIZE: int = 32
    SENTENCE_TRANSFORMER_MODEL_NAME: str = "all-MiniLM-L6-v2"

    ALLOW_ORIGINS: List[str] = ["http://localhost:5173"]
    MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024

    class Config:
        env_file = ".env"


settings = Settings()
