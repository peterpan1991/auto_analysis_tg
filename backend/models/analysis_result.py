from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from core.database import Base
from datetime import datetime

class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, index=True)
    contact_id = Column(Integer, ForeignKey("contact.id", ondelete="CASCADE"), nullable=False, index=True)
    result_type = Column(String(50), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    map_summary = Column(Text)
    summary = Column(Text)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Integer, default=1)