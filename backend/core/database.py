from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

def get_database_url():
    user = os.getenv('DATABASE_USER', 'root') or 'root'
    password = os.getenv('DATABASE_PASSWORD', '') or ''
    host = os.getenv('DATABASE_HOST', 'localhost') or 'localhost'
    port = os.getenv('DATABASE_PORT', '3306') or '3306'
    db_name = os.getenv('DATABASE_NAME', 'telegram_analysis') or 'telegram_analysis'
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()