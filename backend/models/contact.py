from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from core.database import Base
from datetime import datetime

class Contact(Base):
    __tablename__ = "contact"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    name = Column(String(100), nullable=False)
    is_group = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    ignore = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Integer, default=1)