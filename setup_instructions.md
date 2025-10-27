# Настройка системы пользователей

## Переменные окружения

Создайте файл `.env` в папке Backend со следующим содержимым:

```env
# Ollama API настройки
OLLAMA_API=http://localhost:11434/api/generate
MODEL_NAME=mistral

# База данных PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_bank

# JWT настройки
SECRET_KEY=your-super-secret-key-change-in-production-please
```

## Установка зависимостей

```bash
cd Backend
pip install -r requirements.txt
```

## Настройка PostgreSQL

1. Установите PostgreSQL
2. Создайте базу данных:

```sql
CREATE DATABASE ai_bank;
```

3. Создайте пользователя (опционально):

```sql
CREATE USER postgres WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE ai_bank TO postgres;
```

## Запуск приложения

```bash
cd Backend
uvicorn main:app --reload
```

## Новые эндпоинты

### Аутентификация

- `POST /register` - Регистрация пользователя
- `POST /login` - Вход и получение токена
- `GET /me` - Профиль текущего пользователя

### Анализ файлов (обновлено)

- `POST /analyze-expenses` - Теперь требует авторизации, сохраняет результаты в БД

### Админ-панель

- `GET /admin/reports` - Отчеты всех пользователей (только для админов)

### Пользовательские файлы

- `GET /my-files` - Файлы текущего пользователя

## Создание админа

Для создания первого администратора используйте SQL:

```sql
INSERT INTO user (username, email, password_hash, role)
VALUES ('admin', 'admin@example.com', '$2b$12$...', 'admin');
```

Или создайте скрипт для создания админа.

