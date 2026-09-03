from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.exceptions import (
    LLMResponseError,
    LLMServiceUnavailableError,
    RetrievalServiceUnavailableError,
)
import services.vectorize_service as vectorize_service
import services.task_service as task_service
from schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    VectorizeStatusResponse,
)

router = APIRouter()

@router.get(
    "/tasks/{task_id}/vectorize-status",
    response_model=VectorizeStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        503: {"model": ErrorResponse, "description": "向量数据库不可用"},
    },
)
def get_vectorize_status(task_id: int, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        return vectorize_service.get_vectorization_status(db, task_id)
    except RetrievalServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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

@router.post(
    "/chat/ai",
    response_model=ChatResponse,
    responses={
        404: {"model": ErrorResponse, "description": "任务不存在"},
        409: {"model": ErrorResponse, "description": "任务尚未完成向量化"},
        502: {"model": ErrorResponse, "description": "LLM 返回内容无效"},
        503: {"model": ErrorResponse, "description": "Embedding、向量数据库或 LLM 不可用"},
    },
)
def chat_with_ai(data: ChatRequest, db: Session = Depends(get_db)):
    task = task_service.get_task(db, data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        status = vectorize_service.get_vectorization_status(db, data.task_id)
    except RetrievalServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not status.get("is_vectorized", False):
        raise HTTPException(status_code=409, detail="请先向量化聊天记录")

    try:
        result = vectorize_service.chat_with_context(
            db=db,
            task_id=data.task_id,
            prompt=data.prompt,
            contact_id=data.contact_id,
        )
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (RetrievalServiceUnavailableError, LLMServiceUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(**result)
