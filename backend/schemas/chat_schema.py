from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional

class ImportRequest(BaseModel):
    task_id: int
    file_content: Optional[str] = None
    file_name: Optional[str] = None
    folder_path: Optional[str] = None

class ImportResponse(BaseModel):
    message_count: int