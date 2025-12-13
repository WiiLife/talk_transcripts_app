from pydantic import BaseModel
from typing import List


class ChatMessage(BaseModel):
    role: str = "system"
    content: str = ""

class LLMChatMessageRequest(BaseModel):
    model: str 
    messages: List[ChatMessage]
