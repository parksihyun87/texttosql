FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry-core

COPY src/t2sql/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install .

# Railway uses $PORT env var, default to 8000 for local
ENV PORT=8000
CMD ["sh", "-c", "uvicorn t2sql.main:app --host 0.0.0.0 --port $PORT"]
