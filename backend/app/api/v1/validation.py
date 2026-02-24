"""
API-Endpunkte für Validierung
Modul: Validierung (Konsistenzprüfung)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.models.project import Project, ProjectData
from app.services.validation_service import ValidationService, ValidationIssue

router = APIRouter()


class ValidationResponse(BaseModel):
    """Response nach Validierung"""
    konsistenz_ok: bool
    fehler: List[ValidationIssue]
    warnungen: List[ValidationIssue]
    hinweise: List[ValidationIssue]


@router.post("/project/{project_id}", response_model=ValidationResponse)
async def validate_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Führt Validierung für ein Projekt durch
    Prüft Konsistenz, YAML-Vorgaben und generiert Fragenliste
    """
    try:
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
        
        validation_service = ValidationService()
        validation_result = await validation_service.validate_project_data(data.data_json)
        
        data.data_json["pruefungs_ergebnisse"] = {
            "konsistenz_ok": validation_result["konsistenz_ok"],
            "fehler": [issue.dict() for issue in validation_result["fehler"]],
            "warnungen": [issue.dict() for issue in validation_result["warnungen"]],
            "hinweise": [issue.dict() for issue in validation_result["hinweise"]]
        }
        
        if validation_result["konsistenz_ok"]:
            project.status = "validated"
        else:
            project.status = "validation_errors"
        
        db.commit()
        return validation_result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei der Validierung: {str(e)}"
        )


@router.get("/project/{project_id}/issues", response_model=ValidationResponse)
async def get_validation_issues(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Aktuelle Validierungsprobleme eines Projekts abrufen"""
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
    
    if not data or "pruefungs_ergebnisse" not in data.data_json:
        return ValidationResponse(
            konsistenz_ok=None,
            fehler=[],
            warnungen=[],
            hinweise=[]
        )
    
    results = data.data_json["pruefungs_ergebnisse"]
    
    return ValidationResponse(
        konsistenz_ok=results.get("konsistenz_ok"),
        fehler=[ValidationIssue(**issue) for issue in results.get("fehler", [])],
        warnungen=[ValidationIssue(**issue) for issue in results.get("warnungen", [])],
        hinweise=[ValidationIssue(**issue) for issue in results.get("hinweise", [])]
    )
