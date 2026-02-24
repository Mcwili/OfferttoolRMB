"""
Debug-Logs API Endpoint
Speichert Debug-Logs vom Frontend in Dateien
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
import json
import os
from datetime import datetime
from pathlib import Path

router = APIRouter()

class DebugLogEntry(BaseModel):
    timestamp: str
    message: str
    data: Optional[Any] = None

class DebugLogRequest(BaseModel):
    fileId: int
    filename: str
    timestamp: str
    logs: List[DebugLogEntry]
    summary: Optional[dict] = None

@router.post("/debug-logs")
async def save_debug_logs(request: DebugLogRequest):
    """
    Speichert Debug-Logs vom Frontend in eine JSON-Datei
    """
    try:
        # Erstelle Debug-Logs Verzeichnis falls nicht vorhanden
        # Verwende absoluten Pfad relativ zum Backend-Verzeichnis
        backend_dir = Path(__file__).parent.parent.parent.parent  # Gehe zurück zum backend-Verzeichnis
        debug_logs_dir = backend_dir / "debug_logs"
        debug_logs_dir.mkdir(exist_ok=True)
        
        # Erstelle Dateiname mit Timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ifc-viewer-debug-{request.fileId}-{timestamp_str}.json"
        file_path = debug_logs_dir / filename
        
        # Erstelle vollständiges Log-Objekt
        log_data = {
            "fileId": request.fileId,
            "filename": request.filename,
            "timestamp": request.timestamp,
            "saved_at": datetime.now().isoformat(),
            "logs": [log.dict() for log in request.logs],
            "summary": request.summary or {}
        }
        
        # Schreibe JSON-Datei
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": "Debug-Logs erfolgreich gespeichert",
            "file_path": str(file_path),
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Speichern der Debug-Logs: {str(e)}"
        )

class DebugLogEntryDirect(BaseModel):
    sessionId: str
    runId: str
    hypothesisId: str
    location: str
    message: str
    data: Optional[Any] = None
    timestamp: int

@router.post("/debug-logs-direct")
async def save_debug_logs_direct(entry: DebugLogEntryDirect):
    """
    Speichert einzelne Debug-Log-Einträge direkt in NDJSON-Format
    """
    try:
        # Verwende absoluten Pfad: Gehe vom Backend-Verzeichnis zum Workspace-Root
        backend_dir = Path(__file__).parent.parent.parent.parent  # backend/
        workspace_root = backend_dir.parent  # Workspace-Root
        log_path = workspace_root / ".cursor" / "debug.log"
        log_path.parent.mkdir(exist_ok=True)
        
        # Schreibe NDJSON-Zeile
        with open(log_path, 'a', encoding='utf-8') as f:
            json.dump(entry.dict(), f, ensure_ascii=False)
            f.write('\n')
            f.flush()
        
        return {"success": True, "message": "Log entry saved"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Speichern des Log-Eintrags: {str(e)}"
        )
