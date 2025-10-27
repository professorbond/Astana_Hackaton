# Примеры использования API

## 1. Регистрация пользователя

```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

Ответ:

```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": "user",
  "created_at": "2024-01-15T10:30:00"
}
```

## 2. Вход пользователя

```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "securepassword123"
  }'
```

Ответ:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 3. Получение профиля

```bash
curl -X GET "http://localhost:8000/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 4. Анализ расходов

```bash
curl -X POST "http://localhost:8000/analyze-expenses" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -F "file=@expenses.csv"
```

Ответ:

```json
{
  "file_id": 1,
  "reply": "Анализ ваших расходов показывает...",
  "transactions": [...],
  "by_category": [...],
  "by_date": [...],
  "total_amount": 50000.0,
  "transactions_count": 25
}
```

## 5. Получение файлов пользователя

```bash
curl -X GET "http://localhost:8000/my-files" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 6. Админ-отчеты (только для админов)

```bash
curl -X GET "http://localhost:8000/admin/reports" \
  -H "Authorization: Bearer ADMIN_TOKEN_HERE"
```

Ответ:

```json
[
  {
    "user_id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "files_count": 3,
    "total_uploaded_amount": 150000.0,
    "last_upload": "2024-01-15T10:30:00",
    "files": [...]
  }
]
```

## Пример CSV файла для анализа

```csv
date,category,amount
2024-01-01,Продукты,5000
2024-01-02,Транспорт,2000
2024-01-03,Развлечения,3000
2024-01-04,Продукты,4000
2024-01-05,Услуги,1500
2024-01-06,Одежда,8000
2024-01-07,Продукты,3500
2024-01-08,Транспорт,1500
2024-01-09,Развлечения,5000
2024-01-10,Услуги,2000
```

## JavaScript примеры

### Регистрация

```javascript
const response = await fetch("http://localhost:8000/register", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    username: "john_doe",
    email: "john@example.com",
    password: "securepassword123",
  }),
});

const user = await response.json();
```

### Вход

```javascript
const response = await fetch("http://localhost:8000/login", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    username: "john_doe",
    password: "securepassword123",
  }),
});

const { access_token } = await response.json();
localStorage.setItem("token", access_token);
```

### Анализ файла

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const response = await fetch("http://localhost:8000/analyze-expenses", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${localStorage.getItem("token")}`,
  },
  body: formData,
});

const result = await response.json();
```

