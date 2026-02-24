# Setup-Anleitung

## Voraussetzungen

- Python 3.10+
- PostgreSQL 15+
- Redis (für Celery)
- MinIO oder S3-kompatibler Objektspeicher
- Tesseract OCR (für OCR-Funktionen)

## Installation

### 1. Repository klonen

```bash
git clone <repository-url>
cd "Offerttool RMB"
```

### 2. Python-Umgebung einrichten

```bash
cd backend
py -m venv venv
venv\Scripts\activate  # Windows
# oder
source venv/bin/activate  # Linux/Mac
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

Erstelle `.env` Datei im `backend/` Verzeichnis:

```env
DATABASE_URL=postgresql://hlks_user:hlks_password@localhost:5432/hlks_db
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET=hlks-documents
SECRET_KEY=your-secret-key-here
```

### 5. Datenbank einrichten

```bash
# Mit Docker Compose
docker-compose up -d postgres

# Oder manuell PostgreSQL starten und Datenbank erstellen
createdb hlks_db

# Migrations ausführen
cd backend
alembic upgrade head
```

### 6. Redis starten

```bash
# Mit Docker Compose
docker-compose up -d redis

# Oder lokal
redis-server
```

### 7. MinIO starten (optional)

```bash
# Mit Docker Compose
docker-compose up -d minio
```

### 8. Backend starten

```bash
cd backend
uvicorn main:app --reload
```

Die API ist dann verfügbar unter `http://localhost:8000`

## Docker Setup

Alternativ kann alles mit Docker Compose gestartet werden:

```bash
docker-compose up -d
```

## Tesseract OCR installieren

### Windows
Download von: https://github.com/UB-Mannheim/tesseract/wiki

### Linux
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-deu
```

### Mac
```bash
brew install tesseract tesseract-lang
```

## Entwicklung

### Tests ausführen

```bash
pytest
```

### Linting

```bash
flake8 backend/app
pylint backend/app
```

### Migrations erstellen

```bash
cd backend
alembic revision --autogenerate -m "Beschreibung"
alembic upgrade head
```

## Troubleshooting

### Datenbank-Verbindungsfehler
- Prüfe, ob PostgreSQL läuft
- Prüfe DATABASE_URL in .env

### OCR-Fehler
- Prüfe, ob Tesseract installiert ist
- Prüfe TESSERACT_CMD in config.py

### Storage-Fehler
- Prüfe MinIO/S3-Verbindung
- Prüfe S3_*-Umgebungsvariablen
