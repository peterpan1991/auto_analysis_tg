from pydantic import BaseModel
from typing import Optional, List

class ImportRequest(BaseModel):
    task_id: int
    file_content: Optional[str] = None
    file_name: Optional[str] = None
    folder_path: Optional[str] = None

class ImportResponse(BaseModel):
    message_count: int

class VectorizeStatusResponse(BaseModel):
    task_id: int
    message_count: int
    messages_processed: int
    chunk_count: int
    is_vectorized: bool
    progress: float

class VectorizeRequest(BaseModel):
    task_id: int

class ChatRequest(BaseModel):
    task_id: int
    prompt: str

class ChatResponse(BaseModel):
    response: str
    context_messages: int
    expanded_queries: List[str]