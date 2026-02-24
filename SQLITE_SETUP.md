# SQLite Setup - Keine Installation nötig!

## ✅ Was wurde geändert?

Das Projekt wurde auf **SQLite** umgestellt - eine Datei-basierte Datenbank, die:
- ✅ **Keine Installation** benötigt
- ✅ **Im App-Verzeichnis** gespeichert wird (`backend/data/hlks.db`)
- ✅ **Einfach zu verwenden** ist
- ✅ **Portable** ist (kann einfach kopiert werden)

## 🚀 Schnellstart

### Schritt 1: Datenbank-Migration ausführen

```powershell
cd "C:\Users\micha\Offerttool RMB\backend"
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

Die Datenbank wird automatisch im Verzeichnis `backend/data/hlks.db` erstellt.

### Schritt 2: Backend starten

```powershell
# Im gleichen Terminal
uvicorn main:app --reload
```

### Schritt 3: API testen

Öffne im Browser: **http://localhost:8000/docs**

## 📁 Dateistruktur

```
backend/
├── data/
│   └── hlks.db          ← SQLite Datenbank (wird automatisch erstellt)
├── app/
├── alembic/
└── ...
```

## 🔄 Unterschiede zu PostgreSQL

### Was funktioniert gleich:
- ✅ Alle Tabellen und Beziehungen
- ✅ JSON-Felder (SQLite unterstützt JSON seit Version 3.38)
- ✅ Foreign Keys
- ✅ Indizes
- ✅ Transaktionen

### Was anders ist:
- ⚠️ **Keine GIN-Indizes** für JSON (SQLite verwendet einfache Indizes)
- ⚠️ **Kein Connection Pooling** (nicht nötig bei SQLite)
- ⚠️ **JSON-Abfragen** sind etwas langsamer (aber für die meisten Anwendungsfälle ausreichend)

## 📊 Datenbank verwalten

### Datenbank anzeigen

Du kannst die SQLite-Datenbank mit verschiedenen Tools öffnen:

1. **DB Browser for SQLite** (empfohlen):
   - Download: https://sqlitebrowser.org/
   - Öffne `backend/data/hlks.db`

2. **VS Code Extension**:
   - Installiere "SQLite Viewer" Extension
   - Rechtsklick auf `hlks.db` → "Open Database"

3. **Command Line**:
   ```powershell
   sqlite3 backend/data/hlks.db
   ```

### Datenbank sichern

Einfach die Datei kopieren:
```powershell
Copy-Item "backend/data/hlks.db" "backend/data/hlks_backup.db"
```

### Datenbank zurücksetzen

Einfach die Datei löschen und Migration erneut ausführen:
```powershell
Remove-Item "backend/data/hlks.db"
alembic upgrade head
```

## 🔧 Konfiguration

Die Datenbank-URL ist in `backend/app/core/config.py` und `backend/.env` konfiguriert:

```python
DATABASE_URL = "sqlite:///./data/hlks.db"
```

**Hinweis:** Die drei Schrägstriche (`///`) sind korrekt für SQLite (relativer Pfad).

## ⚡ Performance

SQLite ist für die meisten Anwendungsfälle ausreichend schnell:
- ✅ Bis zu **100.000 Zeilen** pro Tabelle: Sehr schnell
- ✅ Bis zu **1 Million Zeilen**: Gut
- ✅ Mehr als **10 Millionen Zeilen**: Kann langsamer werden

Für größere Projekte kann später auf PostgreSQL umgestellt werden.

## 🔄 Zurück zu PostgreSQL

Falls du später auf PostgreSQL umstellen möchtest:

1. **Config ändern:**
   ```python
   DATABASE_URL = "postgresql://hlks_user:hlks_password@localhost:5432/hlks_db"
   ```

2. **Migration erneut ausführen:**
   ```powershell
   alembic upgrade head
   ```

3. **Daten migrieren** (optional):
   - SQLite-Daten exportieren
   - In PostgreSQL importieren

## ✅ Vorteile von SQLite

- ✅ **Keine Installation** nötig
- ✅ **Einfach zu sichern** (nur eine Datei)
- ✅ **Portable** (kann auf USB-Stick kopiert werden)
- ✅ **Keine Konfiguration** nötig
- ✅ **Ideal für Entwicklung** und kleine Projekte

## 📝 Nächste Schritte

1. Migration ausführen (siehe oben)
2. Backend starten
3. API testen unter `http://localhost:8000/docs`
4. Erste Projekte erstellen!

## 🆘 Troubleshooting

### Problem: "database is locked"

**Lösung:** Stelle sicher, dass keine anderen Prozesse auf die Datenbank zugreifen.

### Problem: Migration schlägt fehl

**Lösung:** Lösche die Datenbank und führe die Migration erneut aus:
```powershell
Remove-Item "backend/data/hlks.db"
alembic upgrade head
```

### Problem: Datenbank-Datei wird nicht erstellt

**Lösung:** Stelle sicher, dass das `data/` Verzeichnis existiert:
```powershell
New-Item -ItemType Directory -Force -Path "backend/data"
```
