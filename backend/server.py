from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests
import os

from .routes.llm_response import route as llm_route


load_dotenv()
LLM_URL = os.environ.get("LLM_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_SERVICE_API_KEY = os.environ.get("LLM_SERVICE_API_KEY", None)

app = FastAPI(
    title="backend for talks trascript processing", 
    description="Handles the processing of the transcript processing and other functionalities",
    version="1.0.0"    
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your Vite frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def home():
    """home directory of the backend"""
    return {"message": "welcome to talks transcripts backend"}

@app.get("/health")
def get_health():
    """Health monotring to see if the backend is running"""
    
    response = requests.get("http://localhost:8000/api/v1/chat/completions-test")   # check if we get a response from llm inference provider
    
    return {
        "message": "backend running",
        "llm_endpoint": "running" if bool(response) else "not running"
            }

app.include_router(llm_route)
