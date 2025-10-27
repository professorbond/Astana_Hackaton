#!/usr/bin/env python3
"""
Тестовый скрипт для проверки эндпоинтов
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Тест регистрации"""
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = requests.post(f"{BASE_URL}/register", json=data)
    print(f"Register: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.json() if response.status_code == 200 else None

def test_login():
    """Тест входа"""
    data = {
        "username": "testuser",
        "password": "testpassword123"
    }
    response = requests.post(f"{BASE_URL}/login", json=data)
    print(f"Login: {response.status_code}")
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"Token: {token[:50]}...")
        return token
    return None

def test_me(token):
    """Тест получения профиля"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    print(f"Me: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))

def test_analyze_expenses(token):
    """Тест анализа расходов"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Создаем тестовый CSV файл
    csv_content = """date,category,amount
2024-01-01,Продукты,5000
2024-01-02,Транспорт,2000
2024-01-03,Развлечения,3000
2024-01-04,Продукты,4000
2024-01-05,Услуги,1500"""
    
    files = {"file": ("test_expenses.csv", csv_content, "text/csv")}
    response = requests.post(f"{BASE_URL}/analyze-expenses", headers=headers, files=files)
    print(f"Analyze expenses: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"File ID: {result.get('file_id')}")
        print(f"Total amount: {result.get('total_amount')}")
        print(f"Transactions count: {result.get('transactions_count')}")

def test_my_files(token):
    """Тест получения файлов пользователя"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/my-files", headers=headers)
    print(f"My files: {response.status_code}")
    if response.status_code == 200:
        files = response.json()
        print(f"Files count: {len(files)}")
        for file in files:
            print(f"- {file['filename']}: {file['total_amount']} тенге")

def main():
    print("=== Тестирование эндпоинтов ===\n")
    
    # Регистрация
    print("1. Регистрация пользователя")
    user = test_register()
    print()
    
    # Вход
    print("2. Вход пользователя")
    token = test_login()
    if not token:
        print("Ошибка входа!")
        return
    print()
    
    # Профиль
    print("3. Получение профиля")
    test_me(token)
    print()
    
    # Анализ расходов
    print("4. Анализ расходов")
    test_analyze_expenses(token)
    print()
    
    # Мои файлы
    print("5. Получение файлов пользователя")
    test_my_files(token)
    print()
    
    print("=== Тестирование завершено ===")

if __name__ == "__main__":
    main()

