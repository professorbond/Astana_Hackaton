from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import pdfplumber
import requests
from io import BytesIO
import re

app = FastAPI()

# Разрешаем запросы с фронтенда (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # замени на адрес фронтенда при деплое
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_API = "http://localhost:11434/api/generate"


@app.get("/")
def root():
    return {"message": "AI Bank Backend is running"}


@app.post("/analyze-expenses")
async def analyze_expenses(file: UploadFile = File(...)):
    """
    Принимает .xlsx, .csv или .pdf
    → парсит расходы
    → отправляет их в Ollama (Mistral)
    → возвращает рекомендации
    """
    filename = file.filename.lower()

    try:
        # читаем содержимое файла
        content = await file.read()

        # читаем по типу файла
        if filename.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(content))
        elif filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        elif filename.endswith(".pdf"):
            df = parse_pdf(BytesIO(content))
        else:
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только .xlsx, .csv или .pdf файлы",
            )

        if df.empty:
            raise HTTPException(
                status_code=400, detail="Не удалось извлечь данные из файла"
            )

        # нормализуем имена колонок
        df.columns = [col.lower().strip() for col in df.columns]

        # проверяем наличие основных колонок
        if "category" not in df.columns and "категория" not in df.columns:
            if "description" in df.columns:
                df.rename(columns={"description": "category"}, inplace=True)
            else:
                df["category"] = "Не указано"

        if "amount" not in df.columns and "сумма" not in df.columns:
            # пробуем найти похожие числовые колонки
            for col in df.columns:
                if df[col].apply(lambda x: isinstance(x, (int, float))).any():
                    df.rename(columns={col: "amount"}, inplace=True)
                    break

        if "amount" not in df.columns:
            raise HTTPException(
                status_code=400, detail="Не удалось определить колонку 'amount' (сумма)"
            )

        # берём первые 20 строк
        sample_data = df.head(20).to_dict(orient="records")

        # создаём промпт для модели
        prompt = f"""
        Вот пример расходов пользователя:
        {sample_data}

        Проанализируй траты и ответь:
        1. Какие категории перерасходуют бюджет?
        2. Какие советы по сокращению расходов?
        3. Какую сумму можно было бы сэкономить ежемесячно?
        """

        # отправляем в Ollama (с построчным чтением JSON)
        payload = {"model": "mistral", "prompt": prompt}
        response = requests.post(OLLAMA_API, json=payload, timeout=120, stream=True)

        if not response.ok:
            raise HTTPException(
                status_code=500, detail=f"Ollama error: {response.text}"
            )

        # Ollama возвращает несколько JSON-объектов построчно
        full_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    text = line.decode("utf-8").strip()
                    if text.startswith("{") and '"response"' in text:
                        # безопасно извлекаем текст из строки
                        match = re.search(r'"response"\s*:\s*"([^"]*)"', text)
                        if match:
                            full_text += match.group(1)
                except Exception:
                    continue

        return {"reply": full_text.strip() or "Нет ответа от модели."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {str(e)}")


# === Парсер PDF ==========================================================================

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
