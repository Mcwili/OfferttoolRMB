# 🚀 Backend gestartet!

## ✅ Status

Das Backend wurde gestartet und läuft im Hintergrund.

## 📍 Zugriff

- **API Dokumentation (Swagger UI)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/health

## 🔧 Verfügbare Endpunkte

### Projekte
- `GET /api/v1/projects/` - Alle Projekte auflisten
- `POST /api/v1/projects/` - Neues Projekt erstellen
- `GET /api/v1/projects/{id}` - Projekt abrufen
- `GET /api/v1/projects/{id}/data` - Projekt-Datenmodell abrufen
- `GET /api/v1/projects/{id}/questions` - Fragenliste abrufen

### Dateien
- `POST /api/v1/files/` - Datei hochladen
- `GET /api/v1/files/{id}` - Datei abrufen

### Extraktion
- `POST /api/v1/extraction/project/{id}` - Extraktion starten

### Validierung
- `POST /api/v1/validation/project/{id}` - Validierung durchführen
- `GET /api/v1/validation/project/{id}/issues` - Validierungsprobleme abrufen

### Reports
- `POST /api/v1/reports/project/{id}/generate` - Reports generieren
- `GET /api/v1/reports/project/{id}/list` - Reports auflisten

## 🧪 Erste Schritte

1. **Öffne die API-Dokumentation**: http://localhost:8000/docs
2. **Erstelle ein Projekt**:
   - Klicke auf `POST /api/v1/projects/`
   - Klicke auf "Try it out"
   - Ändere den Request Body:
     ```json
     {
       "name": "Mein erstes Projekt",
       "standort": "Zürich"
     }
     ```
   - Klicke auf "Execute"

## ⚠️ Frontend

**Hinweis**: Es existiert noch kein Frontend-Verzeichnis. Das Backend kann über die Swagger UI oder direkt über HTTP-Requests verwendet werden.

Falls du ein Frontend erstellen möchtest, kann ich dir dabei helfen!

## 🛑 Backend stoppen

Das Backend läuft in einem separaten PowerShell-Fenster. Um es zu stoppen:
1. Öffne das PowerShell-Fenster
2. Drücke `Ctrl+C`

## 📝 Nächste Schritte

- Teste die API mit der Swagger UI
- Lade erste Dateien hoch
- Starte Extraktion und Validierung
- Generiere Reports
