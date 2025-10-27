#!/usr/bin/env python3
"""
Скрипт для создания администратора
Использование: python create_admin.py
"""

from sqlmodel import Session, select
from auth import get_password_hash
from models import User, UserRole
from database import engine

def create_admin():
    """Создает администратора"""
    with Session(engine) as session:
        # Проверяем, есть ли уже админ
        statement = select(User).where(User.role == UserRole.ADMIN)
        existing_admin = session.exec(statement).first()
        
        if existing_admin:
            print(f"Администратор уже существует: {existing_admin.username}")
            return
        
        # Создаем нового админа
        username = input("Введите имя пользователя для админа: ")
        email = input("Введите email для админа: ")
        password = input("Введите пароль для админа: ")
        
        hashed_password = get_password_hash(password)
        
        admin = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=UserRole.ADMIN
        )
        
        session.add(admin)
        session.commit()
        session.refresh(admin)
        
        print(f"Администратор {username} успешно создан!")

if __name__ == "__main__":
    create_admin()

