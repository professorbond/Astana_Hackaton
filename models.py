from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.USER)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Связь с загруженными файлами
    uploaded_files: List["UploadedFile"] = Relationship(back_populates="user")


class UploadedFile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    category_stats: Optional[str] = Field(default=None)  # JSON строка с результатами анализа
    ai_analysis: Optional[str] = Field(default=None)  # Ответ от ИИ
    total_amount: Optional[float] = Field(default=None)  # Общая сумма расходов
    transactions_count: Optional[int] = Field(default=None)  # Количество транзакций
    
    # Связь с пользователем
    user: User = Relationship(back_populates="uploaded_files")


# Pydantic модели для API
class UserCreate(SQLModel):
    username: str
    email: str
    password: str


class UserLogin(SQLModel):
    username: str
    password: str


class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: Optional[str] = None


class FileAnalysisResponse(SQLModel):
    id: int
    filename: str
    upload_date: datetime
    ai_analysis: Optional[str]
    total_amount: Optional[float]
    transactions_count: Optional[int]
    category_stats: Optional[str]


class AdminReportItem(SQLModel):
    user_id: int
    username: str
    email: str
    files_count: int
    total_uploaded_amount: float
    last_upload: Optional[datetime]
    files: List[FileAnalysisResponse]
