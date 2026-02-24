"""
API-Endpunkte für Projektverwaltung
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel, field_validator
from datetime import datetime

from app.core.database import get_db
from app.models.project import Project, ProjectData
from app.services.question_service import QuestionService

router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema für Projekt-Erstellung"""
    name: str
    description: str | None = None
    standort: str | None = None


class ProjectResponse(BaseModel):
    """Schema für Projekt-Antwort"""
    id: int
    name: str
    description: str | None
    standort: str | None
    status: str
    created_at: str | None = None
    
    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        """Konvertiert datetime Objekte zu ISO-Format Strings"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    """Neues Projekt anlegen"""
    try:
        db_project = Project(
            name=project.name,
            description=project.description,
            standort=project.standort
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        
        from app.schemas.project_data_schema import create_empty_project_data
        initial_data = create_empty_project_data(
            project_name=db_project.name,
            project_id=db_project.id,
            standort=db_project.standort
        )
        
        db_data = ProjectData(
            project_id=db_project.id,
            version=1,
            data_json=initial_data,
            is_active=True
        )
        db.add(db_data)
        db.commit()
        return db_project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Anlegen des Projekts: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Alle Projekte auflisten"""
    projects = db.query(Project).offset(skip).limit(limit).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Einzelnes Projekt abrufen"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    return project


@router.get("/{project_id}/details", response_model=Dict[str, Any])
async def get_project_details(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Ruft alle Details eines Projekts ab (inkl. Files, Data, etc.)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # Lade alle zugehörigen Daten
    from app.models.project import ProjectFile, ProjectData
    from app.models.validation import ValidationIssue, GeneratedReport
    
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    data_snapshots = db.query(ProjectData).filter(ProjectData.project_id == project_id).all()
    validation_issues = db.query(ValidationIssue).filter(ValidationIssue.project_id == project_id).all()
    reports = db.query(GeneratedReport).filter(GeneratedReport.project_id == project_id).all()
    
    # Konvertiere zu Dict
    result = {
        "project": {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "standort": project.standort,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "created_by": project.created_by,
        },
        "files": [
            {
                "id": f.id,
                "original_filename": f.original_filename,
                "stored_filename": f.stored_filename,
                "file_path": f.file_path,
                "file_type": f.file_type,
                "mime_type": f.mime_type,
                "file_size": f.file_size,
                "document_type": f.document_type,
                "discipline": f.discipline,
                "revision": f.revision,
                "upload_date": f.upload_date.isoformat() if f.upload_date else None,
                "processed": f.processed,
                "processing_error": f.processing_error,
            }
            for f in files
        ],
        "data_snapshots": [
            {
                "id": d.id,
                "version": d.version,
                "is_active": d.is_active,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "created_by": d.created_by,
                "data_json": d.data_json,
            }
            for d in data_snapshots
        ],
        "validation_issues": [
            {
                "id": v.id,
                "project_data_version": v.project_data_version,
                "file_id": v.file_id,
                "kategorie": v.kategorie,
                "beschreibung": v.beschreibung,
                "fundstellen": v.fundstellen,
                "schweregrad": v.schweregrad,
                "empfehlung": v.empfehlung,
                "betroffene_entitaet": v.betroffene_entitaet,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in validation_issues
        ],
        "generated_reports": [
            {
                "id": r.id,
                "project_data_version": r.project_data_version,
                "report_type": r.report_type,
                "filename": r.filename,
                "file_path": r.file_path,
                "version": r.version,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
                "generated_by": r.generated_by,
            }
            for r in reports
        ],
    }
    
    return result


@router.post("/{project_id}/trigger-extraction", status_code=status.HTTP_202_ACCEPTED)
async def trigger_extraction(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manuell die Extraktion für ein Projekt auslösen"""
    from app.api.v1.files import trigger_extraction_background
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # Background-Task hinzufügen
    background_tasks.add_task(trigger_extraction_background, project_id)
    
    return {"message": f"Extraktion für Projekt {project_id} wurde gestartet", "project_id": project_id}


@router.get("/{project_id}/extracted-data-by-file")
async def get_extracted_data_by_file(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Ruft extrahierte Daten gruppiert nach Datei ab"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # Lade aktives Datenmodell
    from app.models.project import ProjectFile, ProjectData
    
    active_data = db.query(ProjectData).filter(
        ProjectData.project_id == project_id,
        ProjectData.is_active == True
    ).first()
    
    if not active_data:
        return {"files": []}
    
    # Lade alle Dateien des Projekts
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    
    # Gruppiere Daten nach Datei
    files_data = []
    data_json = active_data.data_json or {}
    
    for file_obj in files:
        file_data = {
            "file_id": file_obj.id,
            "filename": file_obj.original_filename,
            "file_type": file_obj.file_type,
            "processed": file_obj.processed,
            "processing_error": file_obj.processing_error,
            "upload_date": file_obj.upload_date.isoformat() if file_obj.upload_date else None,
            "extracted_data": {
                "raeume": [],
                "anlagen": [],
                "geraete": [],
                "anforderungen": [],
                "termine": [],
                "leistungen": [],
                "raw_tables": [],
                "full_text": [],
                "metadata": {}
            }
        }
        
        # Filtere Daten nach Quelle (datei_id)
        entity_types = ["raeume", "anlagen", "geraete", "anforderungen", "termine", "leistungen"]
        
        for entity_type in entity_types:
            if entity_type in data_json:
                for entity in data_json[entity_type]:
                    # Prüfe Quelle
                    quelle = entity.get("quelle", {})
                    if isinstance(quelle, dict):
                        if quelle.get("datei_id") == file_obj.id:
                            file_data["extracted_data"][entity_type].append(entity)
                    elif isinstance(quelle, list):
                        # Wenn Quelle eine Liste ist, prüfe alle Einträge
                        for q in quelle:
                            if isinstance(q, dict) and q.get("datei_id") == file_obj.id:
                                file_data["extracted_data"][entity_type].append(entity)
                                break
        
        # Rohdaten aus dem Datenmodell extrahieren
        if "raw_tables" in data_json:
            for raw_table in data_json["raw_tables"]:
                quelle = raw_table.get("quelle", {})
                if isinstance(quelle, dict) and quelle.get("datei_id") == file_obj.id:
                    file_data["extracted_data"]["raw_tables"].append(raw_table)
        
        # Full Text aus dem Datenmodell extrahieren
        if "full_text" in data_json:
            for text_entry in data_json["full_text"]:
                quelle = text_entry.get("quelle", {}) if isinstance(text_entry, dict) else {}
                if isinstance(quelle, dict) and quelle.get("datei_id") == file_obj.id:
                    file_data["extracted_data"]["full_text"].append(text_entry)
        
        # Metadaten aus dem Datenmodell extrahieren
        if "metadata" in data_json:
            file_metadata = data_json["metadata"].get(str(file_obj.id), {})
            if file_metadata:
                file_data["extracted_data"]["metadata"] = file_metadata
        
        files_data.append(file_data)
    
    return {"files": files_data}


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectCreate,
    db: Session = Depends(get_db)
):
    """Projekt aktualisieren"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projekt mit ID {project_id} nicht gefunden"
            )
        
        project.name = project_update.name
        project.description = project_update.description
        project.standort = project_update.standort
        
        db.commit()
        db.refresh(project)
        return project
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Aktualisieren des Projekts: {str(e)}"
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Projekt löschen (inkl. zugehöriger Dateien und Daten)"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projekt mit ID {project_id} nicht gefunden"
            )
        
        from app.models.project import ProjectFile
        from app.services.storage import get_storage_service
        
        files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        storage_service = get_storage_service()
        
        for file_obj in files:
            try:
                await storage_service.delete_file(file_obj.file_path)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Fehler beim Löschen der Datei {file_obj.file_path} aus Storage: {e}")
        
        db.delete(project)
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Löschen des Projekts: {str(e)}"
        )


@router.get("/{project_id}/data", response_model=Dict[str, Any])
async def get_project_data(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Ruft JSON-Datenmodell eines Projekts ab"""
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


@router.get("/{project_id}/questions", response_model=List[Dict[str, Any]])
async def get_project_questions(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Ruft Fragenliste für ein Projekt ab"""
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
    
    question_service = QuestionService()
    questions = await question_service.generate_questions(data.data_json)
    
    return questions
