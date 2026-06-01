from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageResponse(BaseModel):
    id: int
    task_id: int
    sender: str
    content: str
    timestamp: datetime
    message_type: str
    raw_content: Optional[str] = None
    clean_content: Optional[str] = None

    class Config:
        from_attributes = True
