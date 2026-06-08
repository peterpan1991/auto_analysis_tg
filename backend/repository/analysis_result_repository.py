from sqlalchemy.orm import Session
from models import AnalysisResult, Message, Contact
from typing import List, Set, Optional
from core.constants import MAX_DAYS_FOR_ANALYSIS, LIMIT_MESSAGE_COUNT

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
    from datetime import datetime, timedelta
    from sqlalchemy import func

    latest_msg = db.query(func.max(Message.timestamp)).join(
        Contact, Message.contact_id == Contact.id
    ).filter(
        Message.task_id == task_id,
        Contact.ignore == 0,
        Message.content.isnot(None),
        ~Message.content.in_(ignore_words),
        Contact.message_count > LIMIT_MESSAGE_COUNT
    ).scalar()

    if latest_msg is None:
        return []

    one_year_ago = latest_msg - timedelta(days=MAX_DAYS_FOR_ANALYSIS)

    messages = db.query(Message).join(
        Contact, Message.contact_id == Contact.id
    ).filter(
        Message.task_id == task_id,
        Contact.ignore == 0,
        Message.content.isnot(None),
        ~Message.content.in_(ignore_words),
        Contact.message_count > LIMIT_MESSAGE_COUNT,
        Message.timestamp >= one_year_ago
    ).order_by(Message.timestamp.asc()).all()

    if max_content_length > 0:
        for msg in messages:
            if msg.content and len(msg.content) > max_content_length:
                msg.content = msg.content[:max_content_length] + "..."

    return messages
