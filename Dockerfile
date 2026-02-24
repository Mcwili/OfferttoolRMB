# HLKS Offert-Tool - Backend + Frontend (Railway)
# Stage 1: Frontend bauen
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY frontend/ .
# API-Relativ-URL für Same-Origin-Deployment
ENV VITE_API_URL=/api
RUN npm run build:deploy

# Stage 2: Backend + statische Frontend-Dateien
FROM python:3.12-slim

WORKDIR /app

# System dependencies: poppler (pdf2image), build tools (matplotlib from source)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    build-essential \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend-Code
COPY backend/ .

# Frontend-Build aus Stage 1
COPY --from=frontend-build /app/frontend/dist ./static

EXPOSE 8000
CMD ["/bin/sh", "-c", "echo 'Starting uvicorn on port '${PORT:-8000} && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
