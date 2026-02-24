"""
API-Endpunkte für Frageliste-Generierung
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging
import traceback

from app.core.database import get_db
from app.models.project import Project
from app.api.v1.files import FileResponse

# Optional import - question list service might fail if dependencies are missing
try:
    from app.services.question_list_service import QuestionListService
    QUESTION_LIST_SERVICE_AVAILABLE = True
except Exception as e:
    QUESTION_LIST_SERVICE_AVAILABLE = False
    QuestionListService = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"QuestionListService konnte nicht importiert werden: {e}")

logger = logging.getLogger(__name__)
router = APIRouter()


class QuestionListStartResponse(BaseModel):
    """Response nach Start der Frageliste-Generierung"""
    success: bool
    message: str
    file: FileResponse | None = None


@router.post("/project/{project_id}/start", response_model=QuestionListStartResponse, status_code=status.HTTP_201_CREATED)
async def start_question_list(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Startet die Frageliste-Generierung für ein Projekt
    
    Analysiert alle extrahierten Dokumente mittels AI und erstellt ein Word-Dokument
    mit strukturierter Frageliste. Das Word-Dokument wird als ProjectFile dem Projekt hinzugefügt.
    """
    # Projekt prüfen
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    try:
        logger.info(f"Starte Frageliste-Generierung für Projekt {project_id}")
        
        # Question List Service initialisieren und Generierung durchführen
        if not QUESTION_LIST_SERVICE_AVAILABLE or QuestionListService is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="QuestionListService ist nicht verfügbar. Bitte installieren Sie openai und python-docx."
            )
        question_list_service = QuestionListService(db)
        db_file = await question_list_service.perform_question_list(project_id)
        
        logger.info(f"Frageliste-Generierung erfolgreich abgeschlossen für Projekt {project_id}, Datei-ID: {db_file.id}")
        
        # FileResponse erstellen
        upload_date_str = db_file.upload_date.isoformat() if db_file.upload_date else None
        file_response = FileResponse(
            id=db_file.id,
            original_filename=db_file.original_filename,
            stored_filename=db_file.stored_filename,
            file_type=db_file.file_type,
            document_type=db_file.document_type,
            discipline=db_file.discipline,
            revision=db_file.revision,
            upload_date=upload_date_str,
            processed=db_file.processed
        )
        
        return QuestionListStartResponse(
            success=True,
            message=f"Frageliste erfolgreich generiert. Word-Dokument wurde erstellt.",
            file=file_response
        )
    
    except ValueError as e:
        logger.error(f"ValueError bei Frageliste-Generierung für Projekt {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Fehler bei Frageliste-Generierung für Projekt {project_id}: {str(e)}\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Frageliste-Generierung: {str(e)}"
        )
