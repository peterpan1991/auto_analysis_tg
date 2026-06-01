from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    contact_id = Column(Integer, ForeignKey("contact.id", ondelete="CASCADE"), index=True)
    sender = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    message_type = Column(String(20), default="text")
    raw_content = Column(Text)
    clean_content = Column(Text)
    path = Column(String(500), nullable=True)
    extra_info = Column(Text)
    created_at = Column(DateTime, default=datetime.now)