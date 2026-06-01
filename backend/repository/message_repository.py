from sqlalchemy.orm import Session
from models import Message
from typing import Optional, List
from sqlalchemy import func, text

def get_message_by_id(db: Session, message_id: int) -> Optional[Message]:
    return db.query(Message).filter(Message.id == message_id).first()

def get_messages_by_task(db: Session, task_id: int) -> List[Message]:
    return db.query(Message).filter(Message.task_id == task_id).order_by(Message.timestamp.asc()).all()

def get_messages_by_contact(db: Session, contact_id: int) -> List[Message]:
    return db.query(Message).filter(Message.contact_id == contact_id).order_by(Message.timestamp.asc()).all()

def create_message(db: Session, message: Message) -> Message:
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def create_messages_bulk(db: Session, messages: List[Message]) -> int:
    if not messages:
        return 0

    seen = set()
    unique_messages = []
    for msg in messages:
        key = (msg.sender, msg.content, msg.timestamp)
        if key not in seen:
            seen.add(key)
            unique_messages.append(msg)

    if not unique_messages:
        return 0

    db.execute(
        text("""
            INSERT IGNORE INTO message
            (task_id, user_id, contact_id, sender, content, timestamp, message_type, raw_content, clean_content, created_at)
            VALUES (:task_id, :user_id, :contact_id, :sender, :content, :timestamp, :message_type, :raw_content, :clean_content, :created_at)
        """),
        [
            {
                "task_id": msg.task_id,
                "user_id": msg.user_id,
                "contact_id": msg.contact_id,
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "message_type": msg.message_type,
                "raw_content": msg.raw_content,
                "clean_content": msg.clean_content,
                "created_at": msg.created_at,
            }
            for msg in unique_messages
        ]
    )
    db.commit()
    return len(messages)

def count_messages_by_task(db: Session, task_id: int) -> int:
    return db.query(func.count(Message.id)).filter(Message.task_id == task_id).scalar()

def delete_message(db: Session, message_id: int) -> Optional[Message]:
    message = db.query(Message).filter(Message.id == message_id).first()
    if message:
        db.delete(message)
        db.commit()
    return message
