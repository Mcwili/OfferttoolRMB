"""
API-Endpunkte für rechtliche Prüfung
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging
import traceback

from app.core.database import get_db
from app.models.project import Project, ProjectData
from app.api.v1.files import FileResponse

# Optional import - legal review service might fail if dependencies are missing
try:
    from app.services.legal_review_service import LegalReviewService
    LEGAL_REVIEW_SERVICE_AVAILABLE = True
except Exception as e:
    LEGAL_REVIEW_SERVICE_AVAILABLE = False
    LegalReviewService = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"LegalReviewService konnte nicht importiert werden: {e}")

logger = logging.getLogger(__name__)
router = APIRouter()


class LegalReviewStartResponse(BaseModel):
    """Response nach Start der rechtlichen Prüfung"""
    success: bool
    message: str
    file: FileResponse | None = None
    analysis_result: dict | None = None


@router.post("/project/{project_id}/start", response_model=LegalReviewStartResponse, status_code=status.HTTP_201_CREATED)
async def start_legal_review(
    project_id: int,
    return_analysis: bool = False,
    db: Session = Depends(get_db)
):
    """
    Startet die rechtliche Prüfung für ein Projekt
    
    Analysiert alle extrahierten Dokumente mittels AI und erstellt ein Word-Dokument
    mit kritischen Paragraphen. Das Word-Dokument wird als ProjectFile dem Projekt hinzugefügt.
    """
    # Projekt prüfen
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    try:
        logger.info(f"Starte rechtliche Prüfung für Projekt {project_id}")
        
        # Legal Review Service initialisieren und Prüfung durchführen
        if not LEGAL_REVIEW_SERVICE_AVAILABLE or LegalReviewService is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LegalReviewService ist nicht verfügbar. Bitte installieren Sie openai und python-docx."
            )
        legal_review_service = LegalReviewService(db)
        db_file, analysis_result = await legal_review_service.perform_legal_review(project_id, return_analysis=return_analysis)
        
        logger.info(f"Rechtliche Prüfung erfolgreich abgeschlossen für Projekt {project_id}, Datei-ID: {db_file.id}")
        
        # FileResponse erstellen
        upload_date_str = db_file.upload_date.isoformat() if db_file.upload_date else None
        file_response = FileResponse(
            id=db_file.id,
            original_filename=db_file.original_filename,
            file_type=db_file.file_type,
            document_type=db_file.document_type,
            discipline=db_file.discipline,
            revision=db_file.revision,
            upload_date=upload_date_str,
            processed=db_file.processed
        )
        
        return LegalReviewStartResponse(
            success=True,
            message=f"Rechtliche Prüfung erfolgreich abgeschlossen. Word-Dokument wurde erstellt.",
            file=file_response,
            analysis_result=analysis_result
        )
    
    except ValueError as e:
        logger.error(f"ValueError bei rechtlicher Prüfung für Projekt {project_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Fehler bei rechtlicher Prüfung für Projekt {project_id}: {str(e)}\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der rechtlichen Prüfung: {str(e)}"
        )


@router.get("/project/{project_id}/results")
async def get_legal_review_results(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Ruft die letzten Prüfungsergebnisse für ein Projekt ab
    """
    # Projekt prüfen
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    try:
        # Aktuelles Datenmodell laden
        project_data_obj = db.query(ProjectData).filter(
            ProjectData.project_id == project_id,
            ProjectData.is_active == True
        ).first()
        
        if not project_data_obj:
            return {"legal_review_results": []}
        
        project_data = project_data_obj.data_json
        legal_review_results = project_data.get("legal_review_results", [])
        
        # Neueste Prüfung zurückgeben
        if legal_review_results:
            latest_result = legal_review_results[-1]
            return {
                "legal_review_results": legal_review_results,
                "latest": latest_result.get("analysis_result")
            }
        else:
            return {"legal_review_results": [], "latest": None}
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Fehler beim Abrufen der Prüfungsergebnisse für Projekt {project_id}: {str(e)}\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Abrufen der Prüfungsergebnisse: {str(e)}"
        )
