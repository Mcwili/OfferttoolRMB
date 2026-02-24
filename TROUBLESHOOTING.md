# Troubleshooting - Weiße Seite im Frontend

## Problem
Das Frontend zeigt nur eine weiße Seite.

## Mögliche Ursachen und Lösungen

### 1. Backend läuft nicht
**Symptom**: Browser-Konsole zeigt CORS-Fehler oder "Failed to fetch"

**Lösung**: Backend starten
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. JavaScript-Fehler
**Symptom**: Browser-Konsole zeigt Fehler

**Lösung**: 
1. Öffne Browser-Entwicklertools (F12)
2. Prüfe die Konsole auf Fehler
3. Prüfe die Network-Tab auf fehlgeschlagene Requests

### 3. CSS wird nicht geladen
**Symptom**: Seite ist weiß, aber Text ist sichtbar (ohne Styling)

**Lösung**: 
- Hard Refresh: Ctrl+Shift+R oder Ctrl+F5
- Cache leeren

### 4. Port-Konflikte
**Symptom**: Frontend startet nicht oder zeigt Fehler

**Lösung**: 
```powershell
# Prüfe ob Ports belegt sind
netstat -ano | findstr ":3000"
netstat -ano | findstr ":8000"

# Falls belegt, ändere Port in vite.config.ts
```

### 5. TypeScript-Kompilierungsfehler
**Symptom**: Build schlägt fehl

**Lösung**: 
```powershell
cd frontend
npm run build
# Prüfe Fehlermeldungen
```

## Schnelle Diagnose

1. **Browser-Konsole öffnen** (F12)
2. **Prüfe Fehler** in der Console
3. **Prüfe Network-Tab**:
   - Wird `main.tsx` geladen?
   - Wird `index.css` geladen?
   - Gibt es CORS-Fehler?

## Häufige Fehler

### CORS-Fehler
```
Access to fetch at 'http://localhost:8000/api/v1/projects/' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Lösung**: Stelle sicher, dass das Backend läuft und CORS richtig konfiguriert ist.

### 404-Fehler
```
GET http://localhost:8000/api/v1/projects/ 404 (Not Found)
```

**Lösung**: Backend läuft nicht oder API-Route ist falsch.

### Module not found
```
Failed to resolve import "./components/FileUpload"
```

**Lösung**: Stelle sicher, dass alle Dateien vorhanden sind.

## Debug-Schritte

1. ✅ Backend läuft? → http://localhost:8000/docs öffnen
2. ✅ Frontend läuft? → http://localhost:3000 öffnen
3. ✅ Browser-Konsole prüfen
4. ✅ Network-Tab prüfen
5. ✅ Hard Refresh (Ctrl+Shift+R)

## Hilfe

Falls das Problem weiterhin besteht:
1. Öffne Browser-Entwicklertools (F12)
2. Kopiere alle Fehlermeldungen aus der Console
3. Prüfe den Network-Tab auf fehlgeschlagene Requests
