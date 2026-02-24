"""
API-Endpunkte für Anwendungseinstellungen
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import os

from app.core.database import get_db
from app.models.settings import AppSettings

router = APIRouter()


def _get_templates_dir() -> Path:
    """Vorlagen unter data/: Konsolidiert für Railway-Volume /app/data."""
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    return backend_dir / "data" / "Vorlagen"


class SettingResponse(BaseModel):
    """Schema für Setting-Antwort"""
    key: str
    value: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Schema für Setting-Update"""
    value: str
    description: Optional[str] = None


@router.get("/", response_model=list[SettingResponse])
async def get_settings(db: Session = Depends(get_db)):
    """Ruft alle Einstellungen ab"""
    settings = db.query(AppSettings).all()
    return settings


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: Session = Depends(get_db)):
    """Ruft eine spezifische Einstellung ab"""
    setting = db.query(AppSettings).filter(AppSettings.key == key).first()
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Einstellung mit Key '{key}' nicht gefunden"
        )
    return setting


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_update: SettingUpdate,
    db: Session = Depends(get_db)
):
    """Aktualisiert oder erstellt eine Einstellung"""
    try:
        setting = db.query(AppSettings).filter(AppSettings.key == key).first()
        
        if setting:
            # Update existing setting
            setting.value = setting_update.value
            if setting_update.description:
                setting.description = setting_update.description
        else:
            # Create new setting
            setting = AppSettings(
                key=key,
                value=setting_update.value,
                description=setting_update.description
            )
            db.add(setting)
        
        db.commit()
        db.refresh(setting)
        return setting
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Speichern: {str(e)}"
        )


@router.delete("/{key}")
async def delete_setting(key: str, db: Session = Depends(get_db)):
    """Löscht eine Einstellung"""
    try:
        setting = db.query(AppSettings).filter(AppSettings.key == key).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Einstellung mit Key '{key}' nicht gefunden"
            )
        db.delete(setting)
        db.commit()
        return {"message": f"Einstellung '{key}' wurde gelöscht"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Löschen: {str(e)}"
        )


@router.get("/legal-review-template/status")
async def get_legal_review_template_status():
    """
    Prüft, ob eine Word-Vorlage für die rechtliche Prüfung vorhanden ist
    """
    templates_dir = _get_templates_dir()
    template_path = templates_dir / "RMB A4 hoch.docx"
    
    exists = template_path.exists()
    result = {
        "exists": exists,
        "path": str(template_path) if exists else None,
    }
    
    if exists:
        # Zusätzliche Informationen über die Datei
        stat = template_path.stat()
        result.update({
            "filename": template_path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() if hasattr(datetime, 'fromtimestamp') else None
        })
    
    return result


@router.post("/legal-review-template/upload")
async def upload_legal_review_template(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Lädt die Word-Vorlage für die rechtliche Prüfung hoch
    """
    try:
        # Prüfe Dateityp
        if not file.filename or not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nur .docx Dateien sind erlaubt"
            )
        
        # Lese Dateiinhalt
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Die Datei ist leer"
            )
        
        templates_dir = _get_templates_dir()
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Speichere Vorlage
        template_path = templates_dir / "RMB A4 hoch.docx"
        try:
            with open(template_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fehler beim Speichern der Vorlage: {str(e)}"
            )
        
        # Speichere Pfad in Einstellungen (optional, für Referenz)
        try:
            setting = db.query(AppSettings).filter(AppSettings.key == "legal_review_template_path").first()
            if setting:
                setting.value = str(template_path)
            else:
                setting = AppSettings(
                    key="legal_review_template_path",
                    value=str(template_path),
                    description="Pfad zur Word-Vorlage für rechtliche Prüfung"
                )
                db.add(setting)
            db.commit()
        except Exception as e:
            db.rollback()
            # Fehler beim Speichern in DB ist nicht kritisch, Datei wurde bereits gespeichert
            print(f"Warnung: Fehler beim Speichern des Pfads in DB: {e}")
        
        return {
            "message": "Vorlage erfolgreich hochgeladen",
            "filename": file.filename,
            "path": str(template_path),
            "size": len(file_content),
            "exists": True
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Fehler beim Upload der Vorlage: {type(e).__name__}: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Upload der Vorlage: {type(e).__name__}: {str(e)}"
        )


@router.get("/question-list-template/status")
async def get_question_list_template_status():
    """
    Prüft, ob eine Word-Vorlage für die Frageliste vorhanden ist
    """
    templates_dir = _get_templates_dir()
    template_path = templates_dir / "Frageliste Vorlage.docx"
    
    exists = template_path.exists()
    result = {
        "exists": exists,
        "path": str(template_path) if exists else None,
    }
    
    if exists:
        # Zusätzliche Informationen über die Datei
        stat = template_path.stat()
        result.update({
            "filename": template_path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() if hasattr(datetime, 'fromtimestamp') else None
        })
    
    return result


@router.post("/question-list-template/upload")
async def upload_question_list_template(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Lädt die Word-Vorlage für die Frageliste hoch
    """
    try:
        # Prüfe Dateityp
        if not file.filename or not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nur .docx Dateien sind erlaubt"
            )
        
        # Lese Dateiinhalt
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Die Datei ist leer"
            )
        
        templates_dir = _get_templates_dir()
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Speichere Vorlage
        template_path = templates_dir / "Frageliste Vorlage.docx"
        try:
            with open(template_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fehler beim Speichern der Vorlage: {str(e)}"
            )
        
        # Speichere Pfad in Einstellungen (optional, für Referenz)
        try:
            setting = db.query(AppSettings).filter(AppSettings.key == "question_list_template_path").first()
            if setting:
                setting.value = str(template_path)
            else:
                setting = AppSettings(
                    key="question_list_template_path",
                    value=str(template_path),
                    description="Pfad zur Word-Vorlage für Frageliste"
                )
                db.add(setting)
            db.commit()
        except Exception as e:
            db.rollback()
            # Fehler beim Speichern in DB ist nicht kritisch, Datei wurde bereits gespeichert
            print(f"Warnung: Fehler beim Speichern des Pfads in DB: {e}")
        
        return {
            "message": "Vorlage erfolgreich hochgeladen",
            "filename": file.filename,
            "path": str(template_path),
            "size": len(file_content),
            "exists": True
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Fehler beim Upload der Vorlage: {type(e).__name__}: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Upload der Vorlage: {type(e).__name__}: {str(e)}"
        )
