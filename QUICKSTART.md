# Quick Start - Schnellstart-Anleitung

## 🚀 In 5 Schritten zum laufenden System

### Schritt 1: PostgreSQL starten

**Option A: Mit Docker (wenn Docker installiert ist)**
```powershell
cd "C:\Users\micha\Offerttool RMB"
docker compose up -d postgres
```

**Option B: Ohne Docker**
1. PostgreSQL installieren: https://www.postgresql.org/download/windows/
2. Datenbank erstellen:
   ```sql
   CREATE DATABASE hlks_db;
   CREATE USER hlks_user WITH PASSWORD 'hlks_password';
   GRANT ALL PRIVILEGES ON DATABASE hlks_db TO hlks_user;
   ```

### Schritt 2: Datenbank-Migration ausführen

```powershell
cd "C:\Users\micha\Offerttool RMB\backend"
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

### Schritt 3: Backend starten

```powershell
# Im gleichen Terminal
uvicorn main:app --reload
```

### Schritt 4: API testen

Öffne im Browser: **http://localhost:8000/docs**

### Schritt 5: Erstes Projekt erstellen

In der Swagger UI:
1. Klicke auf `POST /api/v1/projects/`
2. Klicke auf "Try it out"
3. Ändere den JSON-Body:
   ```json
   {
     "name": "Mein erstes Projekt",
     "standort": "Zürich"
   }
   ```
4. Klicke auf "Execute"

## ✅ Fertig!

Das System läuft jetzt. Du kannst:
- Projekte erstellen
- Dateien hochladen
- Daten extrahieren
- Validierungen durchführen
- Reports generieren

## 📖 Weitere Informationen

- **Detaillierte Anleitung:** `SETUP_GUIDE.md`
- **API-Dokumentation:** `docs/API.md`
- **Nächste Schritte:** `NEXT_STEPS.md`
