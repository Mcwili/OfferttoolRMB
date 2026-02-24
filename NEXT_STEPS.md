# Nächste Schritte - Zusammenfassung

## ✅ Erledigt

1. **Python-Umgebung erstellt** (`backend/venv/`)
2. **Dependencies installiert** (mit Python 3.13-kompatiblen Versionen)
3. **Code-Implementierung abgeschlossen:**
   - JSON-Datenmodell-Schema
   - Alle Parser erweitert (Excel, Word, IFC, PDF-Plan, OCR)
   - Intelligentes Daten-Merging
   - Konsistenzprüfung erweitert
   - YAML-Vorgaben-System
   - Fragenliste-Service
   - Alle Report-Generatoren
   - API-Endpunkte erweitert
   - Datenbank-Migration erstellt
   - Dokumentation erstellt

## ⚠️ Noch zu erledigen

### 1. PostgreSQL starten

**Option A: Mit Docker (falls installiert)**
```bash
cd "C:\Users\micha\Offerttool RMB"
docker compose up -d postgres redis
```

**Option B: Manuell**
- PostgreSQL lokal installieren und starten
- Datenbank `hlks_db` erstellen
- Benutzer `hlks_user` mit Passwort `hlks_password` erstellen

### 2. Datenbank-Migration ausführen

Sobald PostgreSQL läuft:
```bash
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

### 3. Redis starten (optional, für Celery)

Falls Celery verwendet werden soll:
```bash
# Mit Docker
docker compose up -d redis

# Oder lokal
redis-server
```

### 4. Backend starten

```bash
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

API verfügbar unter: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Optional: spaCy installieren

Für erweiterte NLP-Funktionen:
```bash
.\venv\Scripts\Activate.ps1
pip install spacy
py -m spacy download de_core_news_sm
```

**Hinweis:** spaCy 3.7.2 ist nicht Python 3.13-kompatibel. Verwende spaCy >= 3.8.0 wenn verfügbar, oder überspringe es zunächst.

### 6. Tesseract OCR installieren

Für OCR-Funktionen:
- Download: https://github.com/UB-Mannheim/tesseract/wiki
- Installieren und Pfad zu `tesseract.exe` in `.env` setzen

## 📝 Wichtige Hinweise

1. **PostgreSQL muss laufen** bevor die Migration ausgeführt werden kann
2. **.env Datei** wurde nicht erstellt (blockiert durch .gitignore) - muss manuell erstellt werden
3. **Docker** ist nicht verfügbar - Services müssen manuell gestartet werden
4. **spaCy** ist optional - Parser funktionieren auch ohne NLP-Features

## 🧪 Erste Tests

Nachdem PostgreSQL läuft und Migration ausgeführt wurde:

1. **Backend starten:**
   ```bash
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn main:app --reload
   ```

2. **API testen:**
   - Öffne `http://localhost:8000/docs` im Browser
   - Teste `POST /api/v1/projects/` um ein Projekt zu erstellen

## 📚 Dokumentation

- **API-Dokumentation:** `docs/API.md`
- **Parser-Dokumentation:** `docs/PARSER.md`
- **Setup-Anleitung:** `docs/SETUP.md`

## 🔧 Bekannte Probleme

- **Python 3.13 Kompatibilität:** Einige Pakete wurden auf neuere Versionen aktualisiert
- **spaCy:** Nicht installiert (Python 3.13 Kompatibilität) - optional
- **PostgreSQL:** Muss manuell gestartet werden
