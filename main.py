from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
import pdfplumber
import requests
import os
import re
from io import BytesIO

# === Инициализация приложения ===
app = FastAPI()

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


@app.get("/")
def root():
    return {"message": "AI Bank Backend is running ✅"}


# === ANALYZE EXPENSES ===
@app.post("/analyze-expenses")
async def analyze_expenses(file: UploadFile = File(...)):
    """Загружает .pdf/.csv/.xlsx, анализирует расходы, возвращает советы и данные для графиков"""
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

        return {
            "reply": full_text.strip() or "Нет ответа от модели.",
            "transactions": transactions,
            "by_category": by_category,
            "by_date": by_date,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


# === PDF ПАРСЕР ===
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
