"""
API-Endpunkte für Berichtsgenerierung
Modul: Berichtsgenerierung (Reportgenerator)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.database import get_db
from app.models.project import Project, ProjectData
from app.services.report_service import ReportService

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    """Request für Berichtsgenerierung"""
    report_types: List[str]  # ["offerte", "risikoanalyse", "timeline", "org"]


class ReportInfo(BaseModel):
    """Informationen zu einem generierten Bericht"""
    report_type: str
    filename: str
    version: int
    generated_at: str
    download_url: str


class ReportGenerateResponse(BaseModel):
    """Response nach Berichtsgenerierung"""
    success: bool
    reports: List[ReportInfo]
    message: str


@router.post("/project/{project_id}/generate", response_model=ReportGenerateResponse)
async def generate_reports(
    project_id: int,
    request: ReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generiert Berichte für ein Projekt
    Nur möglich, wenn Projekt als offertreif markiert ist
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # Prüfen, ob Projekt offertreif ist
    if project.status != "offertreif":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Projekt muss als 'offertreif' markiert sein, bevor Berichte generiert werden können"
        )
    
    # Aktuelles Datenmodell laden
    data = db.query(ProjectData).filter(
        ProjectData.project_id == project_id,
        ProjectData.is_active == True
    ).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kein Datenmodell für dieses Projekt gefunden"
        )
    
    # Berichte generieren
    report_service = ReportService()
    generated_reports = []
    
    for report_type in request.report_types:
        try:
            report_info = await report_service.generate_report(
                project=project,
                project_data=data.data_json,
                report_type=report_type
            )
            generated_reports.append(report_info)
        except Exception as e:
            # Fehler wird geloggt, aber andere Berichte werden weiter generiert
            print(f"Fehler beim Generieren von {report_type}: {e}")
    
    return ReportGenerateResponse(
        success=len(generated_reports) > 0,
        reports=generated_reports,
        message=f"{len(generated_reports)} Bericht(e) erfolgreich generiert"
    )


@router.get("/project/{project_id}/list", response_model=List[ReportInfo])
async def list_reports(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Listet alle generierten Berichte eines Projekts"""
    # TODO: Implementierung - Berichte aus Storage/DB auflisten
    return []


@router.get("/project/{project_id}/download/{report_type}")
async def download_report(
    project_id: int,
    report_type: str,
    version: int | None = None,
    db: Session = Depends(get_db)
):
    """
    Lädt einen generierten Bericht herunter
    report_type: offerte, risikoanalyse, timeline, org
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    # TODO: Implementierung - Bericht aus Storage laden und zurückgeben
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Download-Funktion noch nicht implementiert"
    )
