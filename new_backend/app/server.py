from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests

from .logging_config import setup_logging
from .config import settings
from .clients import qdrant_client, redis_client

from .routes.llm_response import route as llm_route
from .routes.file_upload import route as vector_db_route

load_dotenv()
setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title="backend for talks trascript processing",
        description="Handles the processing of the transcript processing and other functionalities",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def home():
        return {"message": "welcome to talks transcripts backend"}

    @app.get("/health")
    def get_health():
        response = requests.get("http://localhost:8000/api/v1/chat/completions-test")
        return {
            "message": "backend running",
            "llm_endpoint": "running" if bool(response) else "not running",
        }

    app.include_router(llm_route)
    app.include_router(vector_db_route)

    return app


app = create_app()
