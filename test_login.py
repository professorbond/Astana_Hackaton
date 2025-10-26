#!/usr/bin/env python3
"""
Тест входа с тестовыми аккаунтами
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login(username, password):
    """Тест входа пользователя"""
    data = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=data)
        print(f"Вход {username}: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            token = result["access_token"]
            print(f"✅ Успешный вход! Токен: {token[:50]}...")
            return token
        else:
            error = response.json()
            print(f"❌ Ошибка: {error.get('detail', 'Неизвестная ошибка')}")
            return None
    except Exception as e:
        print(f"❌ Ошибка соединения: {e}")
        return None

def test_profile(token):
    """Тест получения профиля"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers)
        print(f"Профиль: {response.status_code}")
        
        if response.status_code == 200:
            profile = response.json()
            print(f"✅ Профиль: {profile['username']} ({profile['role']})")
            return True
        else:
            print(f"❌ Ошибка получения профиля")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    print("=== Тестирование входа с тестовыми аккаунтами ===\n")
    
    # Тестовые аккаунты
    accounts = [
        ("admin", "admin123"),
        ("alex_kazakh", "password123"),
        ("maria_finance", "password123"),
        ("dmitry_business", "password123")
    ]
    
    for username, password in accounts:
        print(f"🔐 Тестируем: {username}")
        token = test_login(username, password)
        
        if token:
            test_profile(token)
        
        print("-" * 50)

if __name__ == "__main__":
    main()
