from sqlalchemy import Column, Integer, String, DateTime, Text
from core.database import Base
from datetime import datetime

class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    status = Column(String(20), default="pending", index=True)
    message_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)