from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AnalysisResponse(BaseModel):
    result_count: int

class AnalysisResultResponse(BaseModel):
    id: int
    task_id: int
    result_type: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}

class AnalyzeStatusResponse(BaseModel):
    status: str
    result_count: int
    logs: List[str]
    error: Optional[str] = None

class AnalyzeLogsResponse(BaseModel):
    logs: List[str]

class CancelResponse(BaseModel):
    message: str
