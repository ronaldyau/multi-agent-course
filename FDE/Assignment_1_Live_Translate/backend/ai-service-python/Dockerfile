# AI service (FastAPI) — build from this directory as context.
FROM python:3.12-slim

WORKDIR /app

# Install deps first so this layer caches unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cache DB lives on a mounted Fly volume so it survives deploys/restarts.
ENV TRANSLATION_DB_PATH=/data/translations.db

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
