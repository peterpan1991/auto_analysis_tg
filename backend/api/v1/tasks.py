from fastapi import APIRouter, Depends, HTTPException
from core.database import get_db
from sqlalchemy.orm import Session
import services.task_service as task_service
from schemas.task_schema import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()

@router.get("/tasks", response_model=list[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    tasks = task_service.get_tasks(db)
    return tasks

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    return task_service.create_task(db, task)

@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
def update_task_status(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    updated_task = task_service.update_task(
        db, task_id,
        status=data.status,
        message_count=data.message_count,
        error_message=data.error_message
    )

    return updated_task

@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    result = task_service.delete_task(db, task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "删除成功"}
