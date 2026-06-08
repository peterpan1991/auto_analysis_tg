from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import services.vectorize_service as vectorize_service
import services.task_service as task_service
from schemas.chat_schema import VectorizeStatusResponse, ChatRequest, ChatResponse

router = APIRouter()

@router.get("/tasks/{task_id}/vectorize-status", response_model=VectorizeStatusResponse)
def get_vectorize_status(task_id: int, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return vectorize_service.get_vectorization_status(db, task_id)

@router.post("/tasks/{task_id}/vectorize")
def start_vectorize(task_id: int, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    vectorize_service.start_vectorization(db, task_id)
    return {"message": "向量化任务已启动", "task_id": task_id}

@router.get("/tasks/{task_id}/vectorize-status-detail")
def get_vectorize_status_detail(task_id: int):
    return vectorize_service.get_vectorize_status(task_id)

@router.post("/tasks/{task_id}/vectorize/cancel")
def cancel_vectorize(task_id: int):
    vectorize_service.cancel_vectorization(task_id)
    return {"message": "取消请求已发送"}

@router.post("/chat/ai", response_model=ChatResponse)
def chat_with_ai(data: ChatRequest, db: Session = Depends(get_db)):
    task = task_service.get_task(db, data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = vectorize_service.get_vectorization_status(db, data.task_id)
    if not status.get("is_vectorized", False):
        raise HTTPException(status_code=400, detail="请先向量化聊天记录")

    result = vectorize_service.chat_with_context(db, data.task_id, data.prompt)
    return ChatResponse(**result)