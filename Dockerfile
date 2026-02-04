FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry-core

COPY src/t2sql/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install .

CMD ["uvicorn", "t2sql.main:app", "--host", "0.0.0.0", "--port", "8000"]
