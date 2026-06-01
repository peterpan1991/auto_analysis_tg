from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    name: str    

class TaskResponse(BaseModel):
    id: int
    name: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    status: str

    model_config = {"from_attributes": True}

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    message_count: Optional[int] = None
    error_message: Optional[str] = None
