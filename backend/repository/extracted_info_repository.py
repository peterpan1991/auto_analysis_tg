from sqlalchemy.orm import Session
from models import ExtractedInfo, Message, Contact
from typing import List, Optional

def delete_by_task(db: Session, task_id: int) -> int:
    count = db.query(ExtractedInfo).filter(ExtractedInfo.task_id == task_id).delete()
    db.commit()
    return count

def create_extracted_info(db: Session, info: ExtractedInfo) -> ExtractedInfo:
    db.add(info)
    db.commit()
    db.refresh(info)
    return info

def create_extracted_info_batch(db: Session, info_list: List[ExtractedInfo]) -> int:
    if not info_list:
        return 0
    db.add_all(info_list)
    db.commit()
    return len(info_list)

def get_extracted_info_by_task(db: Session, task_id: int) -> List[dict]:
    results = db.query(
        ExtractedInfo,
        Message.sender,
        Contact.name.label("contact_name")
    ).outerjoin(
        Message, ExtractedInfo.message_id == Message.id
    ).outerjoin(
        Contact, ExtractedInfo.contact_id == Contact.id
    ).filter(
        ExtractedInfo.task_id == task_id
    ).order_by(
        ExtractedInfo.created_at.desc()
    ).all()

    return [
        {
            "id": info.id,
            "task_id": info.task_id,
            "message_id": info.message_id,
            "contact_id": info.contact_id,
            "info_type": info.info_type,
            "value": info.value,
            "context": info.context,
            "confidence": info.confidence,
            "created_at": info.created_at,
            "sender": sender,
            "contact_name": contact_name,
        }
        for info, sender, contact_name in results
    ]

def get_messages_for_extraction(db: Session, task_id: int) -> List[Message]:
    return db.query(Message).join(
        Contact, Message.contact_id == Contact.id
    ).filter(
        Message.task_id == task_id,
        Contact.ignore == 0
    ).all()
