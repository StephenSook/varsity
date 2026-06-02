# VARSITY backend (FastAPI + SSE) container.
# Builds the public API that streams the explanation pipeline to the front end.
# Deploy targets: IBM Cloud Code Engine (on-theme), Render, or Fly.io.
FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + the committed StatsBomb fixture (the deterministic demo floor).
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Code Engine / Render inject $PORT; default to 8000 locally.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
