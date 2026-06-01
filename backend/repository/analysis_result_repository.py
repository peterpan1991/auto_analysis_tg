from sqlalchemy.orm import Session
from models import AnalysisResult, Message, Contact
from typing import List, Set, Optional

def get_result_types_by_task(db: Session, task_id: int) -> Set[str]:
    results = db.query(AnalysisResult.result_type).filter(
        AnalysisResult.task_id == task_id
    ).all()
    return {r.result_type for r in results}

def delete_by_task_and_type(db: Session, task_id: int, result_type: str) -> int:
    count = db.query(AnalysisResult).filter(
        AnalysisResult.task_id == task_id,
        AnalysisResult.result_type == result_type
    ).delete()
    db.commit()
    return count

def create_analysis_result(db: Session, result: AnalysisResult) -> AnalysisResult:
    db.add(result)
    db.commit()
    db.refresh(result)
    return result

def get_analysis_results_by_task(db: Session, task_id: int) -> List[AnalysisResult]:
    return db.query(AnalysisResult).filter(
        AnalysisResult.task_id == task_id
    ).order_by(AnalysisResult.created_at.desc()).all()

def count_by_task(db: Session, task_id: int) -> int:
    from sqlalchemy import func
    return db.query(func.count(AnalysisResult.id)).filter(
        AnalysisResult.task_id == task_id
    ).scalar()

def get_messages_for_analysis(db: Session, task_id: int, ignore_words: tuple, max_content_length: int = 0) -> List[Message]:
    messages = db.query(Message).join(
        Contact, Message.contact_id == Contact.id
    ).filter(
        Message.task_id == task_id,
        Contact.ignore == 0,
        Message.content.isnot(None),
        ~Message.content.in_(ignore_words),
        Contact.message_count > 30
    ).order_by(Message.timestamp.asc()).all()

    if max_content_length > 0:
        for msg in messages:
            if msg.content and len(msg.content) > max_content_length:
                msg.content = msg.content[:max_content_length] + "..."

    return messages
