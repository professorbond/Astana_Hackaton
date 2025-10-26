from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
import pdfplumber
import requests
import os
import re
import json
from io import BytesIO
from datetime import datetime, timedelta
from typing import List

# Импорты для аутентификации и базы данных
from models import (
    User, UploadedFile, UserCreate, UserLogin, UserResponse, 
    Token, FileAnalysisResponse, AdminReportItem
)
from simple_auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_current_admin_user, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)
from database_sqlite import get_session, create_db_and_tables

# === Инициализация приложения ===
app = FastAPI(title="AI Bank Backend", version="1.0.0")

# === Загружаем .env ===
load_dotenv()
OLLAMA_API = os.getenv("OLLAMA_API", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")

# === Настройка CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ при проде укажи конкретный домен фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Создание таблиц и seed данных при запуске ===
@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    
    # Создаем seed данные
    try:
        from simple_seed import create_simple_seed_data
        create_simple_seed_data()
    except Exception as e:
        print(f"Ошибка при создании seed данных: {e}")


# === CHAT ===
class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    """Простой чат через Ollama."""
    try:
        payload = {"model": MODEL_NAME, "prompt": request.message}
        response = requests.post(OLLAMA_API, json=payload, timeout=120, stream=True)

        if not response.ok:
            raise HTTPException(
                status_code=500, detail=f"Ollama error: {response.text}"
            )

        full_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    text = line.decode("utf-8").strip()
                    if text.startswith("{") and '"response"' in text:
                        match = re.search(r'"response"\s*:\s*"([^"]*)"', text)
                        if match:
                            full_text += match.group(1)
                except Exception:
                    continue

        return {"reply": full_text.strip() or "Нет ответа от модели."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# === АУТЕНТИФИКАЦИЯ ===
@app.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, session: Session = Depends(get_session)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    statement = select(User).where(
        (User.username == user_data.username) | (User.email == user_data.email)
    )
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Пользователь с таким именем или email уже существует"
        )
    
    # Создаем нового пользователя
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user


@app.post("/login", response_model=Token)
async def login(user_data: UserLogin, session: Session = Depends(get_session)):
    """Вход пользователя и получение токена"""
    user = authenticate_user(session, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Получение профиля текущего пользователя"""
    return current_user


# === АНАЛИЗ РАСХОДОВ (ОБНОВЛЕННЫЙ) ===
@app.post("/analyze-expenses")
async def analyze_expenses(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Загружает .pdf/.csv/.xlsx, анализирует расходы, сохраняет в БД и возвращает советы"""
    filename = file.filename.lower()
    try:
        content = await file.read()

        # --- 1. Парсим файл ---
        if filename.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(content))
        elif filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        elif filename.endswith(".pdf"):
            df = parse_pdf(BytesIO(content))
        else:
            raise HTTPException(400, "Поддерживаются только .xlsx, .csv, .pdf")

        if df.empty:
            raise HTTPException(400, "Файл не содержит данных")

        df.columns = [col.lower().strip() for col in df.columns]

        if "category" not in df.columns:
            if "description" in df.columns:
                df.rename(columns={"description": "category"}, inplace=True)
            else:
                df["category"] = "Не указано"

        if "amount" not in df.columns:
            for col in df.columns:
                if df[col].apply(lambda x: isinstance(x, (int, float))).any():
                    df.rename(columns={col: "amount"}, inplace=True)
                    break

        if "amount" not in df.columns:
            raise HTTPException(400, "Не найдена колонка с суммой")

        # --- 2. Отправляем часть данных в AI ---
        sample_data = df.head(20).to_dict(orient="records")
        prompt = f"""
        Вот пример расходов пользователя:
        {sample_data}

        Проанализируй траты и ответь:
        1. Какие категории перерасходуют бюджет?
        2. Какие советы по сокращению расходов?
        3. Какую сумму можно было бы сэкономить ежемесячно?
        """

        payload = {"model": MODEL_NAME, "prompt": prompt}
        response = requests.post(OLLAMA_API, json=payload, timeout=120, stream=True)

        if not response.ok:
            raise HTTPException(500, f"Ollama error: {response.text}")

        full_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    text = line.decode("utf-8").strip()
                    if text.startswith("{") and '"response"' in text:
                        match = re.search(r'"response"\s*:\s*"([^"]*)"', text)
                        if match:
                            full_text += match.group(1)
                except Exception:
                    continue

        # --- 3. Подготавливаем данные для графиков ---
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["amount"])

        # По категориям
        by_category = (
            df.groupby("category")["amount"]
            .sum()
            .reset_index()
            .to_dict(orient="records")
        )

        # По датам
        if "date" in df.columns:
            by_date = (
                df.groupby("date")["amount"]
                .sum()
                .reset_index()
                .to_dict(orient="records")
            )
        else:
            by_date = []

        # Все транзакции
        transactions = df.head(100).to_dict(orient="records")

        # --- 4. Сохраняем в базу данных ---
        total_amount = df["amount"].sum()
        transactions_count = len(df)
        
        uploaded_file = UploadedFile(
            user_id=current_user.id,
            filename=file.filename,
            category_stats=json.dumps(by_category),
            ai_analysis=full_text.strip() or "Нет ответа от модели.",
            total_amount=total_amount,
            transactions_count=transactions_count
        )
        
        session.add(uploaded_file)
        session.commit()
        session.refresh(uploaded_file)

        return {
            "file_id": uploaded_file.id,
            "reply": full_text.strip() or "Нет ответа от модели.",
            "transactions": transactions,
            "by_category": by_category,
            "by_date": by_date,
            "total_amount": total_amount,
            "transactions_count": transactions_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


# === АДМИН-ПАНЕЛЬ ===
@app.get("/admin/reports", response_model=List[AdminReportItem])
async def get_admin_reports(
    current_user: User = Depends(get_current_admin_user),
    session: Session = Depends(get_session)
):
    """Получение отчетов всех пользователей (только для админов)"""
    # Получаем всех пользователей с их файлами
    statement = select(User)
    users = session.exec(statement).all()
    
    reports = []
    for user in users:
        # Получаем файлы пользователя
        files_statement = select(UploadedFile).where(UploadedFile.user_id == user.id)
        files = session.exec(files_statement).all()
        
        # Подсчитываем статистику
        files_count = len(files)
        total_uploaded_amount = sum(file.total_amount or 0 for file in files)
        last_upload = max((file.upload_date for file in files), default=None)
        
        # Преобразуем файлы в формат ответа
        file_responses = [
            FileAnalysisResponse(
                id=file.id,
                filename=file.filename,
                upload_date=file.upload_date,
                ai_analysis=file.ai_analysis,
                total_amount=file.total_amount,
                transactions_count=file.transactions_count,
                category_stats=file.category_stats
            )
            for file in files
        ]
        
        reports.append(AdminReportItem(
            user_id=user.id,
            username=user.username,
            email=user.email,
            files_count=files_count,
            total_uploaded_amount=total_uploaded_amount,
            last_upload=last_upload,
            files=file_responses
        ))
    
    return reports


# === ПОЛУЧЕНИЕ ФАЙЛОВ ПОЛЬЗОВАТЕЛЯ ===
@app.get("/my-files", response_model=List[FileAnalysisResponse])
async def get_my_files(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Получение всех загруженных файлов текущего пользователя"""
    statement = select(UploadedFile).where(UploadedFile.user_id == current_user.id)
    files = session.exec(statement).all()
    
    return [
        FileAnalysisResponse(
            id=file.id,
            filename=file.filename,
            upload_date=file.upload_date,
            ai_analysis=file.ai_analysis,
            total_amount=file.total_amount,
            transactions_count=file.transactions_count,
            category_stats=file.category_stats
        )
        for file in files
    ]


@app.get("/")
def root():
    return {"message": "AI Bank Backend is running ✅"}


# === PDF ПАРСЕР (БЕЗ ИЗМЕНЕНИЙ) ===
date_re = re.compile(r"(\d{1,2}\.\d{1,2}\.\d{2,4})")
amount_re = re.compile(
    r"([+-]?\s?\d{1,3}(?:[\s\d]{0,}\d)?(?:[.,]\d{2})?)\s*(?:₸|KZT|т|тг|\$|₽)?"
)


def parse_pdf(file_obj):
    """Извлекает строки с датой, суммой и описанием из PDF."""
    rows = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for raw_line in text.split("\n"):
                line = raw_line.strip()
                if not line:
                    continue

                date_match = date_re.search(line)
                amount_match = list(amount_re.finditer(line))
                if not date_match or not amount_match:
                    continue

                date = date_match.group(1)
                date_end = date_match.end()

                chosen_amount = None
                chosen_amount_span = None
                for m in amount_match:
                    if m.start() >= date_end - 1:
                        chosen_amount = m.group(1)
                        chosen_amount_span = (m.start(), m.end())
                        break
                if not chosen_amount:
                    chosen_amount = amount_match[-1].group(1)
                    chosen_amount_span = (
                        amount_match[-1].start(),
                        amount_match[-1].end(),
                    )

                desc = line[date_end : chosen_amount_span[0]].strip()
                if not desc:
                    desc = line[chosen_amount_span[1] :].strip()

                amt_str = chosen_amount.replace(" ", "").replace(",", ".")
                amt_str = re.sub(r"[^\d\-\+\.]", "", amt_str)
                try:
                    amount = float(amt_str)
                except ValueError:
                    continue

                category = classify_description(desc)
                rows.append({"date": date, "category": category, "amount": amount})
    return pd.DataFrame(rows)


def classify_description(desc: str) -> str:
    """Простая классификация транзакции по ключевым словам."""
    d = desc.lower()
    if any(k in d for k in ["перевод", "пополнение", "deposit", "депозит"]):
        return "transfer/deposit"
    if any(k in d for k in ["покупк", "магазин", "ozon", "market", "shop"]):
        return "purchase"
    if any(k in d for k in ["коммун", "телеком", "kazakhtelecom", "услуги"]):
        return "utilities"
    if any(k in d for k in ["аппарат", "банкомат", "снятие"]):
        return "cash"
    return desc if len(desc) <= 80 else desc[:77] + "..."