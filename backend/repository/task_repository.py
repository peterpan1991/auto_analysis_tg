from sqlalchemy.orm import Session
from models import Task
from typing import Optional, List

def get_tasks(db: Session) -> List[Task]:
    return db.query(Task).all()

def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()

def create_task(db: Session, task: Task) -> Task:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def delete_task(db: Session, task_id: int) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return task

def update_task_status(db: Session, task_id: int, status: str) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = status
        db.commit()
        db.refresh(task)
    return task

def update_task_message_count(db: Session, task_id: int, message_count: int) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.message_count = message_count
        db.commit()
        db.refresh(task)
    return task

def update_task(db: Session, task_id: int, status: Optional[str] = None,
                 message_count: Optional[int] = None, error_message: Optional[str] = None) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None

    if status is not None:
        task.status = status
    if message_count is not None:
        task.message_count = message_count
    if error_message is not None:
        task.error_message = error_message

    db.commit()
    db.refresh(task)
    return task
