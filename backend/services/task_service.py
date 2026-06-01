from sqlalchemy.orm import Session
from models import Task
from datetime import datetime
from schemas.task_schema import TaskCreate
import repository

def get_tasks(db: Session):
    return repository.get_tasks(db)

def get_task(db: Session, task_id: int):
    return repository.get_task(db, task_id)

def create_task(db: Session, task_data: TaskCreate):
    task = Task(
        name = task_data.name,
        status = "pending",
        created_at = datetime.now(),
        updated_at = datetime.now(),
    )
    return repository.create_task(db, task)

def delete_task(db: Session, task_id: int):
    task = get_task(db, task_id)
    if not task:
        return None
    return repository.delete_task(db, task_id)

def update_status(db: Session, task_id: int, status: str):
    task = get_task(db, task_id)
    if not task:
        return None
    return repository.update_task_status(db, task_id, status)

def update_task(db: Session, task_id: int, status: str = None, message_count: int = None, error_message: str = None):
    task = get_task(db, task_id)
    if not task:
        return None
    return repository.update_task(db, task_id, status=status, message_count=message_count, error_message=error_message)
