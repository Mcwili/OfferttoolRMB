# Setup-Anleitung - Schritt für Schritt

## Übersicht

Diese Anleitung führt dich durch die Einrichtung des Projekts von Grund auf.

## Schritt 1: PostgreSQL installieren und starten

### Option A: Mit Docker (empfohlen, wenn Docker installiert ist)

1. **Docker Desktop installieren** (falls noch nicht vorhanden):
   - Download: https://www.docker.com/products/docker-desktop/
   - Installieren und starten

2. **Services starten:**
   ```powershell
   cd "C:\Users\micha\Offerttool RMB"
   docker compose up -d postgres redis
   ```

3. **Prüfen ob PostgreSQL läuft:**
   ```powershell
   docker compose ps
   ```

### Option B: PostgreSQL lokal installieren

1. **PostgreSQL herunterladen und installieren:**
   - Download: https://www.postgresql.org/download/windows/
   - Während der Installation:
     - Port: `5432` (Standard)
     - Passwort für `postgres` Benutzer merken

2. **Datenbank und Benutzer erstellen:**
   ```powershell
   # PostgreSQL Command Line öffnen (pgAdmin oder psql)
   psql -U postgres
   ```

   Dann in psql ausführen:
   ```sql
   CREATE DATABASE hlks_db;
   CREATE USER hlks_user WITH PASSWORD 'hlks_password';
   GRANT ALL PRIVILEGES ON DATABASE hlks_db TO hlks_user;
   \q
   ```

3. **PostgreSQL Service starten** (falls nicht automatisch):
   ```powershell
   # Als Administrator
   net start postgresql-x64-15  # Version kann variieren
   ```

## Schritt 2: Datenbank-Migration ausführen

```powershell
cd "C:\Users\micha\Offerttool RMB\backend"
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

**Erwartete Ausgabe:**
```
INFO  [alembic.runtime.migration] Running upgrade -> d7a2ddc45378, initial schema
INFO  [alembic.runtime.migration] Running upgrade d7a2ddc45378 -> ..., add validation and reports tables
```

## Schritt 3: .env Datei erstellen (falls noch nicht vorhanden)

Erstelle `backend/.env` mit folgendem Inhalt:

```env
# Database
DATABASE_URL=postgresql://hlks_user:hlks_password@localhost:5432/hlks_db

# Redis (für Celery - optional)
REDIS_URL=redis://localhost:6379/0

# S3/Object Storage (MinIO - optional)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET=hlks-documents
S3_REGION=us-east-1
S3_USE_SSL=False

# Application
DEBUG=True
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# Security
SECRET_KEY=change-me-in-production-please-use-strong-random-key

# OCR Settings (optional)
TESSERACT_CMD=tesseract
OCR_LANGUAGE=deu+eng

# NLP Settings (optional)
SPACY_MODEL=de_core_news_sm
```

## Schritt 4: Backend starten

```powershell
cd "C:\Users\micha\Offerttool RMB\backend"
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

**Erwartete Ausgabe:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Schritt 5: API testen

### Option A: Im Browser

1. Öffne: `http://localhost:8000/docs`
2. Du siehst die Swagger UI mit allen verfügbaren Endpunkten

### Option B: Mit curl/PowerShell

```powershell
# Projekt erstellen
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/projects/" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"name": "Testprojekt", "standort": "Zürich"}'

# Projekte auflisten
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/projects/" `
  -Method GET
```

## Schritt 6: Erste Datei hochladen (optional)

```powershell
# Beispiel: Excel-Datei hochladen
$filePath = "C:\Pfad\zu\deiner\raumliste.xlsx"
$projectId = 1  # ID aus Schritt 5

$formData = @{
    file = Get-Item $filePath
    project_id = $projectId
}

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/files/" `
  -Method POST `
  -Form $formData
```

## Schritt 7: Extraktion starten (optional)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/extraction/project/1" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{}'
```

## Schritt 8: Validierung durchführen (optional)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/validation/project/1" `
  -Method POST
```

## Schritt 9: Fragenliste abrufen (optional)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/projects/1/questions" `
  -Method GET
```

## Schritt 10: Report generieren (optional)

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/reports/project/1/generate" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"report_types": ["offerte", "risikoanalyse"]}'
```

## Troubleshooting

### Problem: PostgreSQL-Verbindung schlägt fehl

**Lösung:**
1. Prüfe ob PostgreSQL läuft:
   ```powershell
   # Mit Docker
   docker compose ps
   
   # Lokal
   Get-Service | Where-Object {$_.Name -like "*postgres*"}
   ```

2. Prüfe die DATABASE_URL in `backend/.env`
3. Teste die Verbindung:
   ```powershell
   psql -U hlks_user -d hlks_db -h localhost
   ```

### Problem: Migration schlägt fehl

**Lösung:**
1. Prüfe ob die Datenbank existiert:
   ```sql
   \l  -- Liste aller Datenbanken
   ```

2. Prüfe ob der Benutzer existiert:
   ```sql
   \du  -- Liste aller Benutzer
   ```

### Problem: Port 8000 bereits belegt

**Lösung:**
```powershell
# Anderen Port verwenden
uvicorn main:app --reload --port 8001
```

### Problem: Module nicht gefunden

**Lösung:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Nächste Schritte nach erfolgreichem Setup

1. **Frontend entwickeln** (optional)
2. **Echte Dokumente testen**
3. **YAML-Spezifikation anpassen** (`backend/config/offerte_spec.yaml`)
4. **Report-Templates anpassen** (`backend/app/reporters/`)
5. **spaCy installieren** (für erweiterte NLP-Features)

## Wichtige Dateien

- **API-Dokumentation:** `docs/API.md`
- **Parser-Dokumentation:** `docs/PARSER.md`
- **Setup-Anleitung:** `docs/SETUP.md`
- **Konfiguration:** `backend/app/core/config.py`
- **Datenbank-Modelle:** `backend/app/models/`

## Support

Bei Problemen:
1. Prüfe die Logs im Terminal
2. Prüfe die API-Dokumentation unter `http://localhost:8000/docs`
3. Prüfe die Fehlermeldungen in der Datenbank
