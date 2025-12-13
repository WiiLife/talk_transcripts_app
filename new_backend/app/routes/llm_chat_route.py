from fastapi import APIRouter, Request, HTTPException
from controllers.chat_controller import ChatController
from app.models.chat_model import LLMChatMessageRequest


route = APIRouter(prefix="/api/v1", tags=["llm_router"])

@route.post("/chat/completions")
async def chat_completion(request: Request):
    data: LLMChatMessageRequest = await request.json()
    
    chat_controller = ChatController(model=data.model)
    chat_controller.messages = data.messages
    
    try:
        await chat_controller.stream_chat()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while streaming from llm: {e}")
