from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from core.database import Base
from datetime import datetime

class ExtractedInfo(Base):
    __tablename__ = "extracted_info"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("message.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(Integer, ForeignKey("contact.id", ondelete="SET NULL"), nullable=True)
    info_type = Column(String(50), nullable=False, index=True)
    value = Column(Text, nullable=False)
    context = Column(Text)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Integer, default=1)