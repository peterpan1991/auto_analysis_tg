from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExtractResponse(BaseModel):
    extracted_count: int

class ExtractedInfoResponse(BaseModel):
    id: int
    task_id: int
    message_id: Optional[int] = None
    contact_id: Optional[int] = None
    info_type: str
    value: str
    context: Optional[str] = ""
    confidence: float
    created_at: datetime
    sender: Optional[str] = None
    contact_name: Optional[str] = None

    model_config = {"from_attributes": True}
