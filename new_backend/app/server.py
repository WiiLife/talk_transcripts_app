from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

from config.config import settings
from app.routes.llm_chat_route import route as llm_route
from app.routes.upload_file_route import route as vector_db_route
from middleware.middleware import MaxContentLengthMiddleware


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
    app.add_middleware(MaxContentLengthMiddleware)

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
