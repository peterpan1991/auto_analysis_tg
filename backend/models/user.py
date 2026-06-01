from sqlalchemy import Column, Integer, String, DateTime
from core.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    chats_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Integer, default=1)