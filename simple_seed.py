#!/usr/bin/env python3
"""
Простое создание seed данных без bcrypt
"""

from sqlmodel import Session, select
from models import User, UploadedFile, UserRole
from database_sqlite import engine
import json
from datetime import datetime, timedelta
import random

def create_simple_seed_data():
    """Создает тестовые данные для демонстрации"""
    with Session(engine) as session:
        # Проверяем, есть ли уже данные
        statement = select(User)
        existing_users = session.exec(statement).all()
        
        if existing_users:
            print("Seed данные уже существуют, пропускаем создание...")
            return
        
        print("Создание seed данных...")
        
        # Создаем администратора (простой хеш для демо)
        admin = User(
            username="admin",
            email="admin@aibank.kz",
            password_hash="admin123_hash",  # Простой хеш для демо
            role=UserRole.ADMIN
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        
        # Создаем тестовых пользователей
        test_users = [
            {
                "username": "alex_kazakh",
                "email": "alex@example.com",
                "password": "password123",
                "role": UserRole.USER
            },
            {
                "username": "maria_finance",
                "email": "maria@example.com", 
                "password": "password123",
                "role": UserRole.USER
            },
            {
                "username": "dmitry_business",
                "email": "dmitry@example.com",
                "password": "password123", 
                "role": UserRole.USER
            }
        ]
        
        created_users = [admin]
        
        for user_data in test_users:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=f"{user_data['password']}_hash",  # Простой хеш для демо
                role=user_data["role"]
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            created_users.append(user)
        
        # Создаем тестовые файлы с анализом
        sample_analyses = [
            {
                "filename": "expenses_january_2024.csv",
                "ai_analysis": "Анализ ваших расходов за январь показывает перерасход в категории 'Развлечения' на 15%. Рекомендуем сократить походы в рестораны и кино. Общая экономия может составить 8,000 тенге в месяц.",
                "total_amount": 125000.0,
                "transactions_count": 45,
                "category_stats": json.dumps([
                    {"category": "Продукты", "amount": 45000},
                    {"category": "Транспорт", "amount": 18000},
                    {"category": "Развлечения", "amount": 35000},
                    {"category": "Услуги", "amount": 12000},
                    {"category": "Одежда", "amount": 15000}
                ])
            },
            {
                "filename": "bank_statement_february.pdf",
                "ai_analysis": "В феврале наблюдается рост расходов на 12% по сравнению с январем. Основной рост в категории 'Транспорт' из-за повышения цен на топливо. Рекомендуем использовать общественный транспорт чаще.",
                "total_amount": 140000.0,
                "transactions_count": 52,
                "category_stats": json.dumps([
                    {"category": "Продукты", "amount": 48000},
                    {"category": "Транспорт", "amount": 25000},
                    {"category": "Развлечения", "amount": 28000},
                    {"category": "Услуги", "amount": 15000},
                    {"category": "Одежда", "amount": 12000},
                    {"category": "Медицина", "amount": 12000}
                ])
            },
            {
                "filename": "expenses_march_2024.xlsx",
                "ai_analysis": "Отличный месяц! Расходы сократились на 8%. Экономия достигнута за счет сокращения развлечений и более разумных покупок продуктов. Продолжайте в том же духе!",
                "total_amount": 128000.0,
                "transactions_count": 38,
                "category_stats": json.dumps([
                    {"category": "Продукты", "amount": 42000},
                    {"category": "Транспорт", "amount": 20000},
                    {"category": "Развлечения", "amount": 25000},
                    {"category": "Услуги", "amount": 18000},
                    {"category": "Одежда", "amount": 13000},
                    {"category": "Образование", "amount": 10000}
                ])
            }
        ]
        
        # Добавляем файлы для каждого пользователя (кроме админа)
        for user in created_users[1:]:  # Пропускаем админа
            for i, file_data in enumerate(sample_analyses):
                # Создаем случайную дату в последние 3 месяца
                days_ago = random.randint(1, 90)
                upload_date = datetime.utcnow() - timedelta(days=days_ago)
                
                uploaded_file = UploadedFile(
                    user_id=user.id,
                    filename=file_data["filename"],
                    upload_date=upload_date,
                    ai_analysis=file_data["ai_analysis"],
                    total_amount=file_data["total_amount"],
                    transactions_count=file_data["transactions_count"],
                    category_stats=file_data["category_stats"]
                )
                session.add(uploaded_file)
        
        session.commit()
        
        print("✅ Seed данные успешно созданы!")
        print(f"👤 Создано пользователей: {len(created_users)}")
        print(f"📁 Создано файлов: {len(sample_analyses) * (len(created_users) - 1)}")
        print("\n🔑 Тестовые аккаунты:")
        print("Админ: admin / admin123")
        print("Пользователи: alex_kazakh, maria_finance, dmitry_business / password123")

if __name__ == "__main__":
    create_simple_seed_data()
