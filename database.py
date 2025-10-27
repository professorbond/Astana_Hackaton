from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os

load_dotenv()

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/ai_bank")

# Создание движка базы данных
engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    """Создает таблицы в базе данных"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Получение сессии базы данных"""
    with Session(engine) as session:
        yield session

