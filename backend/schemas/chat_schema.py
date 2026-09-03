from pydantic import BaseModel, Field
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
    prompt: str = Field(min_length=1, max_length=500)
    contact_id: Optional[int] = None

class ChatSource(BaseModel):
    source_id: int
    chunk_id: str
    contact_id: int
    start_message_id: int
    end_message_id: int
    similarity: float
    content: str

class ChatResponse(BaseModel):
    response: str
    context_count: int
    expanded_queries: List[str]
    sources: List[ChatSource] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
