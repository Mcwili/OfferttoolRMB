# Storage-Fix: Lokales Dateisystem als Fallback

## Problem
Status 500 Fehler beim Upload - StorageService konnte nicht mit S3/MinIO verbinden.

## Lösung

Der `StorageService` wurde so angepasst, dass er automatisch auf **lokales Dateisystem** umschaltet, wenn S3/MinIO nicht verfügbar ist.

### Was wurde geändert:

1. **Automatischer Fallback**:
   - Wenn S3/MinIO nicht erreichbar ist → lokales Dateisystem
   - Dateien werden in `backend/uploads/project_{id}/` gespeichert

2. **Fehlerbehandlung verbessert**:
   - Graceful degradation statt Crash
   - Warnungen statt Fehler

3. **Upload-Verzeichnis erstellt**:
   - `backend/uploads/` Verzeichnis wurde erstellt
   - Wird automatisch für jedes Projekt erstellt

## Dateispeicherung

**Ohne MinIO/S3:**
- Dateien werden lokal gespeichert: `backend/uploads/project_{id}/{filename}`
- Funktioniert ohne zusätzliche Installation

**Mit MinIO/S3:**
- Dateien werden im S3-kompatiblen Storage gespeichert
- Automatischer Wechsel wenn verfügbar

## Test

1. **Backend neu starten** (falls es läuft):
   ```powershell
   # Im Backend-Terminal: Ctrl+C
   # Dann neu starten:
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Upload testen**:
   - Projektname eingeben
   - Datei auswählen
   - Upload starten

3. **Prüfen**:
   - Datei sollte in `backend/uploads/project_{id}/` gespeichert sein
   - Kein 500-Fehler mehr

## Hinweis

Das Backend muss **neu gestartet** werden, damit die Änderungen wirksam werden!
