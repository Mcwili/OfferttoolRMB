"""
Celery-Tasks für Datenextraktion
Führt rechenintensive Parsing-Operationen asynchron aus
"""

from celery import Task
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.project import ProjectFile, ProjectData, Project
from app.services.extraction_service import ExtractionService
from app.services.storage import StorageService
import traceback


class DatabaseTask(Task):
    """Base-Task mit DB-Session-Management"""
    
    _db: Session = None
    
    def before_start(self, task_id, args, kwargs):
        """Erstellt DB-Session vor Task-Start"""
        self._db = SessionLocal()
    
    def after_return(self, *args, **kwargs):
        """Schließt DB-Session nach Task-Ende"""
        if self._db:
            self._db.close()
            self._db = None
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Behandelt Task-Fehler"""
        if self._db:
            try:
                # Fehler in Datenbank speichern
                file_id = args[0] if args else None
                if file_id:
                    file_obj = self._db.query(ProjectFile).filter(
                        ProjectFile.id == file_id
                    ).first()
                    if file_obj:
                        file_obj.processing_error = str(exc)
                        self._db.commit()
            except Exception:
                self._db.rollback()
            finally:
                self._db.close()
                self._db = None


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name="app.tasks.extraction_tasks.extract_file",
    max_retries=3,
    default_retry_delay=60  # 1 Minute zwischen Retries
)
def extract_file(self, file_id: int):
    """
    Extrahiert Daten aus einer Datei asynchron
    
    Args:
        file_id: ID der ProjectFile in der Datenbank
    """
    db = self._db
    if not db:
        db = SessionLocal()
    
    try:
        # Datei aus DB laden
        file_obj = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
        if not file_obj:
            raise ValueError(f"Datei mit ID {file_id} nicht gefunden")
        
        # Projekt laden
        project = db.query(Project).filter(Project.id == file_obj.project_id).first()
        if not project:
            raise ValueError(f"Projekt mit ID {file_obj.project_id} nicht gefunden")
        
        # Aktuelles Datenmodell laden
        current_data = db.query(ProjectData).filter(
            ProjectData.project_id == project.id,
            ProjectData.is_active == True
        ).first()
        
        if not current_data:
            raise ValueError("Kein aktives Datenmodell für dieses Projekt gefunden")
        
        # Extraktion durchführen
        extraction_service = ExtractionService(db)
        extracted_data = extraction_service.extract_file(file_obj)
        
        # Daten ins JSON-Modell integrieren
        updated_data = extraction_service.merge_extracted_data(
            current_data.data_json.copy(),
            extracted_data,
            file_obj
        )
        
        # Neue Version des JSON-Modells speichern
        old_version = current_data.version
        current_data.is_active = False
        
        new_data = ProjectData(
            project_id=project.id,
            version=old_version + 1,
            data_json=updated_data,
            is_active=True
        )
        db.add(new_data)
        
        # Datei als verarbeitet markieren
        file_obj.processed = True
        file_obj.processing_error = None
        
        db.commit()
        
        return {
            "success": True,
            "file_id": file_id,
            "entities_extracted": {
                entity_type: len(extracted_data.get(entity_type, []))
                for entity_type in ["raeume", "anlagen", "geraete", "anforderungen", "termine"]
            }
        }
    
    except Exception as exc:
        # Fehler in Datenbank speichern
        try:
            file_obj = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
            if file_obj:
                file_obj.processing_error = f"{str(exc)}\n{traceback.format_exc()}"
                db.commit()
        except Exception:
            db.rollback()
        
        # Retry bei bestimmten Fehlern
        if isinstance(exc, (ConnectionError, TimeoutError)):
            raise self.retry(exc=exc)
        
        raise exc
    
    finally:
        if self._db != db:
            db.close()


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name="app.tasks.extraction_tasks.extract_project_files",
    max_retries=1
)
def extract_project_files(self, project_id: int, file_ids: list[int] | None = None):
    """
    Extrahiert Daten aus mehreren Dateien eines Projekts
    
    Args:
        project_id: ID des Projekts
        file_ids: Liste von Datei-IDs (optional, wenn None werden alle nicht verarbeiteten Dateien genommen)
    """
    db = self._db
    if not db:
        db = SessionLocal()
    
    try:
        # Dateien zum Verarbeiten finden
        if file_ids:
            files_to_process = db.query(ProjectFile).filter(
                ProjectFile.id.in_(file_ids),
                ProjectFile.project_id == project_id,
                ProjectFile.processed == False
            ).all()
        else:
            files_to_process = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.processed == False
            ).all()
        
        results = []
        for file_obj in files_to_process:
            try:
                # Einzelne Datei extrahieren
                result = extract_file.delay(file_obj.id)
                results.append({
                    "file_id": file_obj.id,
                    "task_id": result.id,
                    "status": "queued"
                })
            except Exception as e:
                results.append({
                    "file_id": file_obj.id,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "success": True,
            "project_id": project_id,
            "files_queued": len(results),
            "results": results
        }
    
    finally:
        if self._db != db:
            db.close()
