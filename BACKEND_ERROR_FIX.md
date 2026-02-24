# Backend Network Error - Lösung

## Problem
Der Upload-Button zeigt "Network Error" - das Backend ist nicht erreichbar.

## Lösung

### Schritt 1: Backend starten

Das Backend wurde in einem neuen PowerShell-Fenster gestartet. Warte bis du die Meldung "Application startup complete" siehst.

**Manuell starten:**
```powershell
cd "C:\Users\micha\Offerttool RMB\backend"
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Schritt 2: Backend-Status prüfen

Öffne im Browser: **http://localhost:8000/docs**

Wenn die Swagger UI erscheint, läuft das Backend korrekt.

### Schritt 3: Frontend testen

1. Öffne http://localhost:3000
2. Gib einen Projektnamen ein
3. Wähle Dateien aus
4. Klicke auf "Datei(en) hochladen"

## Verbesserte Fehlermeldungen

Das Frontend zeigt jetzt klarere Fehlermeldungen:
- ✅ "Backend nicht erreichbar" wenn das Backend nicht läuft
- ✅ Detaillierte Fehlermeldungen bei API-Fehlern
- ✅ Warnung wenn kein Projektname eingegeben wurde

## Troubleshooting

### Backend läuft nicht
1. Prüfe ob Port 8000 frei ist: `netstat -ano | findstr ":8000"`
2. Prüfe ob Python venv aktiviert ist
3. Prüfe ob alle Dependencies installiert sind: `pip install -r requirements.txt`

### CORS-Fehler
- Backend sollte CORS für `http://localhost:3000` erlauben (ist bereits konfiguriert)

### Port-Konflikte
- Backend: Port 8000
- Frontend: Port 3000
- Falls Ports belegt sind, ändere sie in den Config-Dateien

## Status prüfen

**Backend prüfen:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/"
```

**Frontend prüfen:**
- Öffne http://localhost:3000
- Prüfe Browser-Konsole (F12) auf Fehler
