"""
API-Endpunkte für Datenextraktion
Modul: Datenextraktion (Extraction)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any

from app.core.database import get_db
from app.models.project import Project, ProjectFile, ProjectData

# Optional import - extraction service might fail if parsers are missing
try:
    from app.services.extraction_service import ExtractionService
    EXTRACTION_SERVICE_AVAILABLE = True
except Exception as e:
    EXTRACTION_SERVICE_AVAILABLE = False
    ExtractionService = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"ExtractionService konnte nicht importiert werden: {e}")

router = APIRouter()


class ExtractionRequest(BaseModel):
    """Request für Extraktion"""
    file_id: int | None = None  # Wenn None, werden alle nicht verarbeiteten Dateien extrahiert


class ExtractionResponse(BaseModel):
    """Response nach Extraktion"""
    success: bool
    files_processed: int
    entities_extracted: Dict[str, int]
    message: str


@router.post("/project/{project_id}", response_model=ExtractionResponse)
async def extract_project_data(
    project_id: int,
    request: ExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Startet die Datenextraktion für ein Projekt
    Verarbeitet alle nicht verarbeiteten Dateien oder eine spezifische Datei
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # Dateien zum Verarbeiten finden
    if request.file_id:
        files_to_process = db.query(ProjectFile).filter(
            ProjectFile.id == request.file_id,
            ProjectFile.project_id == project_id,
            ProjectFile.processed == False
        ).all()
    else:
        files_to_process = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.processed == False
        ).all()
    
    if not files_to_process:
        return ExtractionResponse(
            success=True,
            files_processed=0,
            entities_extracted={},
            message="Keine Dateien zum Verarbeiten gefunden"
        )
    
    # Extraktion durchführen
    if not EXTRACTION_SERVICE_AVAILABLE or ExtractionService is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ExtractionService ist nicht verfügbar. Bitte installieren Sie die erforderlichen Parser-Module."
        )
    extraction_service = ExtractionService(db)
    
    # Aktuelles JSON-Modell laden
    current_data = db.query(ProjectData).filter(
        ProjectData.project_id == project_id,
        ProjectData.is_active == True
    ).first()
    
    if not current_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kein aktives Datenmodell für dieses Projekt gefunden"
        )
    
    entities_count = {
        "raeume": 0,
        "anlagen": 0,
        "geraete": 0,
        "anforderungen": 0,
        "termine": 0
    }
    
    files_processed = 0
    
    for file_obj in files_to_process:
        try:
            # Datei extrahieren
            extracted_data = await extraction_service.extract_file(file_obj)
            
            # Daten ins JSON-Modell integrieren
            current_data.data_json = extraction_service.merge_extracted_data(
                current_data.data_json,
                extracted_data,
                file_obj
            )
            
            # Zähler aktualisieren
            for entity_type in entities_count.keys():
                if entity_type in extracted_data:
                    entities_count[entity_type] += len(extracted_data[entity_type])
            
            # Datei als verarbeitet markieren
            file_obj.processed = True
            files_processed += 1
            
        except Exception as e:
            file_obj.processing_error = str(e)
            # Datei wird nicht als verarbeitet markiert, kann später erneut versucht werden
    
    try:
        old_version = current_data.version
        current_data.is_active = False
        
        new_data = ProjectData(
            project_id=project_id,
            version=old_version + 1,
            data_json=current_data.data_json,
            is_active=True
        )
        db.add(new_data)
        db.commit()
        
        return ExtractionResponse(
            success=True,
            files_processed=files_processed,
            entities_extracted=entities_count,
            message=f"{files_processed} Datei(en) erfolgreich verarbeitet"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Speichern der Extraktion: {str(e)}"
        )


@router.get("/project/{project_id}/data", response_model=Dict[str, Any])
async def get_project_data(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Aktuelles JSON-Datenmodell eines Projekts abrufen"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    data = db.query(ProjectData).filter(
        ProjectData.project_id == project_id,
        ProjectData.is_active == True
    ).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kein Datenmodell für dieses Projekt gefunden"
        )
    
    return data.data_json
