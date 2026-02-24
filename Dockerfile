# HLKS Offert-Tool Backend - Railway Deployment
FROM python:3.12-slim

WORKDIR /app

# System dependencies (poppler for pdf2image, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY backend/ .

# Railway sets PORT at runtime - use shell form for variable expansion
EXPOSE 8000
CMD ["/bin/sh", "-c", "echo 'Starting uvicorn on port '${PORT:-8000} && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
