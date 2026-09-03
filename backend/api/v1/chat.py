from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
import services.chat_service as chat_service
import services.task_service as task_service
from schemas.chat_schema import ImportRequest, ImportResponse
from schemas.message_schema import MessageResponse
from schemas.contact_schema import ContactResponse

router = APIRouter()

@router.post("/chat/import", response_model=ImportResponse)
def import_chat(data: ImportRequest, db: Session = Depends(get_db)):
    task = task_service.get_task(db, data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_service.update_status(db, task.id, "importing")

    chat_service.start_import(
        db=db,
        task_id=data.task_id,
        folder_path=data.folder_path,
        file_content=data.file_content,
        file_name=data.file_name
    )

    return ImportResponse(message_count=0)

@router.get("/tasks/{task_id}/import-status")
def get_import_status(task_id: int):
    return chat_service.get_import_status(task_id)

@router.get("/tasks/{task_id}/import-logs")
def get_import_logs(task_id: int):
    return chat_service.get_import_logs(task_id)

@router.post("/tasks/{task_id}/import/cancel")
def cancel_import(task_id: int):
    chat_service.cancel_import(task_id)
    return {"message": "取消请求已发送"}

@router.get("/tasks/{task_id}/messages", response_model=List[MessageResponse])
def get_messages(task_id: int, db: Session = Depends(get_db)):
    messages = chat_service.get_messages_by_task(db, task_id)
    return messages

@router.get(
    "/tasks/{task_id}/contacts",
    response_model=List[ContactResponse],
)
def get_contacts(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = task_service.get_task(db, task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在",
        )

    return chat_service.get_contacts_by_task(db, task_id)