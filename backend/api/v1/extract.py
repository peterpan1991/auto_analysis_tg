from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from schemas.extract_schema import ExtractResponse, ExtractedInfoResponse
from core.database import get_db
import services.extract_service as extract_service

router = APIRouter()

@router.post("/tasks/{task_id}/extract", response_model=ExtractResponse)
def extract_info(task_id: int, db: Session = Depends(get_db)):
    extracted_count, error = extract_service.extract_info(db, task_id)

    if error:
        if "不存在" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)

    return ExtractResponse(extracted_count=extracted_count)

@router.get("/tasks/{task_id}/extracted", response_model=List[ExtractedInfoResponse])
def get_extracted_info(task_id: int, db: Session = Depends(get_db)):
    results = extract_service.get_extracted_info(db, task_id)

    return [
        ExtractedInfoResponse(
            id=row["id"],
            task_id=row["task_id"],
            message_id=row["message_id"],
            contact_id=row["contact_id"],
            info_type=row["info_type"],
            value=row["value"],
            context=row["context"] or "",
            confidence=row["confidence"],
            created_at=row["created_at"],
            sender=row["sender"],
            contact_name=row["contact_name"],
        )
        for row in results
    ]
