"""
API-Endpunkte für Datei-Upload und -Verwaltung
Modul: Datenaufnahme (Intake)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, field_validator
import os
import uuid
from datetime import datetime
import logging
import json
from io import BytesIO

from app.core.database import get_db, SessionLocal
from app.core.config import settings, DEBUG_LOG_PATH
from app.models.project import Project, ProjectFile, ProjectData
from app.services.storage import get_storage_service
from app.services.file_classifier import FileClassifier
from app.services.zip_handler import ZIPHandler

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

logger = logging.getLogger(__name__)

router = APIRouter()


class FileResponse(BaseModel):
    """Schema für Datei-Antwort"""
    id: int
    original_filename: str
    file_type: str
    document_type: str | None
    discipline: str | None
    revision: str | None
    upload_date: str | None = None
    processed: bool
    
    @field_validator('upload_date', mode='before')
    @classmethod
    def convert_datetime(cls, v):
        """Konvertiert datetime Objekte zu ISO-Format Strings"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v
    
    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response für Upload mit mehreren Dateien (z.B. aus ZIP)"""
    message: str
    files: List[FileResponse]
    task_ids: List[str] | None = None


async def trigger_extraction_background(project_id: int):
    """
    Führt die Extraktion für ein Projekt im Hintergrund aus
    Wird von BackgroundTasks aufgerufen
    """
    # #region agent log
    import json
    try:
        with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"files.py:60","message":"Background task started","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
    except: pass
    # #endregion
    db = SessionLocal()
    try:
        # Projekt laden
        project = db.query(Project).filter(Project.id == project_id).first()
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"files.py:68","message":"Project loaded","data":{"project_id":project_id,"project_found":project is not None,"project_status":project.status if project else None},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        if not project:
            logger.error(f"Projekt {project_id} nicht gefunden für Extraktion")
            return
        
        # Projekt-Status auf "processing" setzen
        project.status = "processing"
        db.commit()
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"files.py:75","message":"Status set to processing","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        # Alle nicht verarbeiteten Dateien finden
        files_to_process = db.query(ProjectFile).filter(
            ProjectFile.project_id == project_id,
            ProjectFile.processed == False
        ).all()
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"files.py:82","message":"Files to process found","data":{"project_id":project_id,"files_count":len(files_to_process),"file_ids":[f.id for f in files_to_process]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        if not files_to_process:
            logger.info(f"Keine Dateien zum Verarbeiten für Projekt {project_id}")
            # Prüfen, ob alle Dateien bereits verarbeitet sind
            all_files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
            if all_files and all(file.processed for file in all_files):
                project.status = "validated"
                db.commit()
            return
        
        # Aktuelles JSON-Modell laden oder erstellen
        current_data = db.query(ProjectData).filter(
            ProjectData.project_id == project_id,
            ProjectData.is_active == True
        ).first()
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"files.py:96","message":"ProjectData lookup","data":{"project_id":project_id,"current_data_found":current_data is not None,"current_data_id":current_data.id if current_data else None},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        if not current_data:
            # Kein aktives Datenmodell gefunden - erstelle eines
            logger.info(f"Kein aktives Datenmodell für Projekt {project_id} gefunden, erstelle neues")
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"files.py:100","message":"Creating new ProjectData","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            from app.schemas.project_data_schema import create_empty_project_data
            initial_data = create_empty_project_data(
                project_name=project.name,
                project_id=project.id,
                standort=project.standort
            )
            current_data = ProjectData(
                project_id=project.id,
                version=1,
                data_json=initial_data,
                is_active=True
            )
            db.add(current_data)
            db.commit()
            db.refresh(current_data)
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"files.py:137","message":"ProjectData created","data":{"project_id":project_id,"current_data_id":current_data.id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
        
        # Extraktion durchführen
        if not EXTRACTION_SERVICE_AVAILABLE or ExtractionService is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ExtractionService ist nicht verfügbar. Bitte installieren Sie die erforderlichen Parser-Module."
            )
        extraction_service = ExtractionService(db)
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"files.py:103","message":"Starting extraction loop","data":{"project_id":project_id,"files_to_process_count":len(files_to_process)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        files_processed = 0
        for file_obj in files_to_process:
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"files.py:107","message":"Processing file","data":{"project_id":project_id,"file_id":file_obj.id,"filename":file_obj.original_filename,"file_type":file_obj.file_type},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            try:
                # Datei extrahieren
                extracted_data = await extraction_service.extract_file(file_obj)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"files.py:110","message":"Extraction completed","data":{"project_id":project_id,"file_id":file_obj.id,"extracted_keys":list(extracted_data.keys()) if extracted_data else []},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                
                # Daten ins JSON-Modell integrieren
                merged_data = extraction_service.merge_extracted_data(
                    current_data.data_json.copy(),  # Kopie erstellen, um Referenzprobleme zu vermeiden
                    extracted_data,
                    file_obj
                )
                
                # Validierung: Prüfe, ob alle extrahierten Daten auch im merged_data vorhanden sind
                missing_keys = []
                for key in extracted_data.keys():
                    if key not in merged_data:
                        missing_keys.append(key)
                    elif key in ["raw_tables", "full_text"]:
                        # Prüfe, ob die Anzahl der Einträge übereinstimmt
                        extracted_count = len(extracted_data[key]) if isinstance(extracted_data[key], list) else (1 if extracted_data[key] else 0)
                        merged_count = len(merged_data[key]) if isinstance(merged_data[key], list) else (1 if merged_data[key] else 0)
                        if extracted_count > merged_count:
                            logger.warning(
                                f"Potentieller Datenverlust bei {key}: "
                                f"extrahierte {extracted_count}, gemergt {merged_count} "
                                f"(Datei: {file_obj.original_filename})"
                            )
                    elif key == "metadata":
                        # Prüfe, ob metadata für diese Datei vorhanden ist
                        if isinstance(extracted_data[key], dict) and extracted_data[key]:
                            # Metadata sollte unter file_id gespeichert sein
                            if "metadata" not in merged_data or str(file_obj.id) not in merged_data["metadata"]:
                                logger.warning(
                                    f"Metadaten für Datei {file_obj.id} nicht im merged_data gefunden "
                                    f"(Datei: {file_obj.original_filename})"
                                )
                
                if missing_keys:
                    logger.error(
                        f"KRITISCH: Datenverlust erkannt! Fehlende Keys im merged_data: {missing_keys} "
                        f"(Datei: {file_obj.original_filename})"
                    )
                
                # Erweiterte Logging für extrahierte Daten
                raw_tables_count = len(extracted_data.get('raw_tables', []))
                full_text_count = len(extracted_data.get('full_text', [])) if isinstance(extracted_data.get('full_text'), list) else (1 if extracted_data.get('full_text') else 0)
                metadata_sheets_count = len(extracted_data.get('metadata', {}).get('sheets', []))
                
                logger.info(
                    f"Extraktion abgeschlossen für Datei {file_obj.id} ({file_obj.original_filename}): "
                    f"raw_tables={raw_tables_count}, "
                    f"full_text={full_text_count}, "
                    f"metadata_sheets={metadata_sheets_count}"
                )
                
                # Zusätzliche Logging-Details für Debugging
                if raw_tables_count > 0:
                    logger.debug(f"  -> {raw_tables_count} raw_tables extrahiert")
                if full_text_count > 0:
                    logger.debug(f"  -> {full_text_count} full_text Einträge extrahiert")
                if metadata_sheets_count > 0:
                    logger.debug(f"  -> {metadata_sheets_count} Sheets in Metadaten")
                
                current_data.data_json = merged_data
                
                # WICHTIG: SQLAlchemy muss explizit informiert werden, dass sich die JSON-Spalte geändert hat
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(current_data, "data_json")
                
                # Datei als verarbeitet markieren
                file_obj.processed = True
                file_obj.processing_error = None  # Fehler zurücksetzen
                db.add(file_obj)  # Explizit hinzufügen für Commit
                db.add(current_data)  # Explizit hinzufügen für Commit
                db.commit()  # Commit nach jeder Datei, damit Änderungen persistiert werden
                db.refresh(file_obj)
                # WICHTIG: current_data NICHT refresh() aufrufen, da die JSON-Daten bereits gemergt sind
                # und refresh() würde die Daten aus der DB laden, die möglicherweise noch nicht aktualisiert sind
                files_processed += 1
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"files.py:119","message":"File marked as processed","data":{"project_id":project_id,"file_id":file_obj.id,"files_processed":files_processed},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                logger.info(f"Datei {file_obj.id} ({file_obj.original_filename}) erfolgreich extrahiert")
                
            except Exception as e:
                file_obj.processing_error = str(e)
                # #region agent log
                try:
                    with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"files.py:124","message":"Extraction error","data":{"project_id":project_id,"file_id":file_obj.id,"error":str(e)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
                except: pass
                # #endregion
                logger.error(f"Fehler beim Extrahieren von Datei {file_obj.id}: {str(e)}")
                # Datei bleibt processed=False, kann später erneut versucht werden
        
        # Neue Version des JSON-Modells speichern (nur wenn Dateien verarbeitet wurden)
        # WICHTIG: current_data.data_json wurde bereits nach jeder Datei aktualisiert und committed
        # ABER: SQLAlchemy erkennt Änderungen an JSON-Spalten nicht automatisch!
        # Daher müssen wir die Daten direkt aus dem aktuellen Objekt nehmen, bevor wir refresh() aufrufen
        if files_processed > 0:
            # WICHTIG: Daten kopieren BEVOR refresh(), da refresh() die Daten aus der DB lädt
            # und die DB möglicherweise noch die alten Daten enthält (wenn flag_modified fehlte)
            import copy
            
            # Deep copy der aktuellen Daten erstellen (die bereits alle Merges enthalten)
            current_data_json = copy.deepcopy(current_data.data_json)
            
            # Version aus dem aktuellen Objekt holen (nicht aus DB, da refresh() die Daten überschreiben würde)
            old_version = current_data.version
            
            # Alte Version deaktivieren
            current_data.is_active = False
            db.add(current_data)
            
            # Neue Version mit den gemergten Daten erstellen
            new_data = ProjectData(
                project_id=project_id,
                version=old_version + 1,
                data_json=current_data_json,  # Verwende die kopierten Daten (mit allen Merges)
                is_active=True
            )
            db.add(new_data)
            db.commit()  # Commit für neue Version
            db.refresh(new_data)
            current_data = new_data  # Verwende die neue Version für weitere Prüfungen
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"files.py:139","message":"New ProjectData version created","data":{"project_id":project_id,"old_version":old_version,"new_version":old_version+1},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
        
        # Prüfen, ob alle Dateien verarbeitet sind
        all_files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"files.py:142","message":"Checking all files processed","data":{"project_id":project_id,"all_files_count":len(all_files),"all_processed":all(file.processed for file in all_files) if all_files else False,"processed_statuses":[{"id":f.id,"processed":f.processed} for f in all_files]},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        if all_files and all(file.processed for file in all_files):
            project.status = "validated"
            db.add(project)
            db.commit()
            db.refresh(project)
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"files.py:144","message":"Status set to validated","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            logger.info(f"Projekt {project_id} erfolgreich extrahiert - alle Dateien verarbeitet")
        else:
            # Es gibt noch nicht verarbeitete Dateien - Status bleibt "processing" oder wird auf "error" gesetzt wenn Fehler
            unprocessed_with_errors = [f for f in all_files if not f.processed and f.processing_error]
            if unprocessed_with_errors:
                project.status = "error"
            else:
                project.status = "processing"
            db.add(project)
            db.commit()
            db.refresh(project)
            # #region agent log
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"files.py:148","message":"Status updated","data":{"project_id":project_id,"files_processed":files_processed,"status":project.status,"unprocessed_with_errors":len(unprocessed_with_errors)},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            logger.info(f"Projekt {project_id}: {files_processed} Datei(en) verarbeitet, Status: {project.status}")
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"files.py:150","message":"Commit completed","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        
    except Exception as e:
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"files.py:152","message":"Exception in background task","data":{"project_id":project_id,"error":str(e),"error_type":type(e).__name__},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        logger.error(f"Fehler bei Hintergrund-Extraktion für Projekt {project_id}: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        # #region agent log
        try:
            with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"files.py:156","message":"Background task finished","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
        except: pass
        # #endregion
        db.close()


@router.post("/upload/{project_id}", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Datei für ein Projekt hochladen
    Unterstützt Drag-and-Drop, Mehrfachauswahl und ZIP-Archive
    """
    try:
        # Projekt prüfen
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projekt mit ID {project_id} nicht gefunden"
            )
        
        # Dateiname prüfen
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dateiname fehlt"
            )
        
        # Dateityp prüfen
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dateityp {file_ext} nicht erlaubt. Erlaubt: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Dateigröße prüfen
        file_content = await file.read()
        file_size = len(file_content)
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Datei zu groß. Maximum: {settings.MAX_UPLOAD_SIZE / 1024 / 1024} MB"
            )
        
        uploaded_files = []
        # StorageService initialisiert sich automatisch mit lokalem Fallback
        storage_service = get_storage_service()
        
        # Prüfen, ob es ein ZIP-Archiv ist
        if file_ext == ".zip":
            try:
                # ZIP-Archiv extrahieren
                zip_handler = ZIPHandler()
                extracted_files = await zip_handler.extract_and_list_files(file_content, project_id)
                
                if not extracted_files:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ZIP-Archiv enthält keine gültigen Dateien"
                    )
                
                # Jede extrahierte Datei einzeln verarbeiten
                for file_info in extracted_files:
                    extracted_content = file_info["content"]
                    filename = file_info["filename"]
                    extracted_ext = os.path.splitext(filename)[1].lower()
                    
                    # Prüfen, ob Dateityp erlaubt ist
                    if extracted_ext not in settings.ALLOWED_EXTENSIONS:
                        continue  # Überspringe nicht erlaubte Dateien
                    
                    # Datei im Storage speichern
                    stored_filename = f"{uuid.uuid4()}{extracted_ext}"
                    file_path = await storage_service.save_file(
                        file_content=extracted_content,
                        filename=stored_filename,
                        project_id=project_id
                    )
                    
                    # Dateityp erkennen
                    file_type = file_info["file_type"]
                    
                    # Dokumentenklassifikation (statische Methode)
                    classification = await FileClassifier.classify_file(
                        filename=filename,
                        file_type=file_type,
                        file_content=extracted_content
                    )
                    
                    # Datenbankeintrag erstellen
                    db_file = ProjectFile(
                        project_id=project_id,
                        original_filename=filename,
                        stored_filename=stored_filename,
                        file_path=file_path,
                        file_type=file_type,
                        mime_type=file_info.get("mime_type"),
                        file_size=file_info.get("size", len(extracted_content)),
                        document_type=classification.get("document_type"),
                        discipline=classification.get("discipline"),
                        revision=classification.get("revision")
                    )
                    db.add(db_file)
                    uploaded_files.append(db_file)
                
                db.commit()
                # Refresh alle Dateien und erstelle FileResponse-Objekte
                file_responses = []
                for db_file in uploaded_files:
                    db.refresh(db_file)
                    # Erstelle FileResponse mit konvertiertem upload_date
                    upload_date_str = None
                    if db_file.upload_date:
                        if isinstance(db_file.upload_date, datetime):
                            upload_date_str = db_file.upload_date.isoformat()
                        else:
                            upload_date_str = str(db_file.upload_date)
                    
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
                    file_responses.append(file_response)
                
                # Extraktion im Hintergrund starten
                background_tasks.add_task(trigger_extraction_background, project_id)
                
                return UploadResponse(
                    message=f"{len(file_responses)} Datei(en) aus ZIP-Archiv hochgeladen",
                    files=file_responses,
                    task_ids=None
                )
            
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fehler beim Verarbeiten des ZIP-Archivs: {str(e)}"
                )
        
        else:
            # Normale Datei (nicht ZIP)
            stored_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = await storage_service.save_file(
                file_content=file_content,
                filename=stored_filename,
                project_id=project_id
            )
            
            # MIME-Typ und Dateityp erkennen
            file_type = FileClassifier.detect_file_type(file_ext, file.content_type)
            # Dokumentenklassifikation (statische Methode)
            classification = await FileClassifier.classify_file(
                filename=file.filename,
                file_type=file_type,
                file_content=file_content
            )
            # Datenbankeintrag erstellen
            db_file = ProjectFile(
                project_id=project_id,
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=file_path,
                file_type=file_type,
                mime_type=file.content_type,
                file_size=file_size,
                document_type=classification.get("document_type"),
                discipline=classification.get("discipline"),
                revision=classification.get("revision")
            )
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
            # Erstelle FileResponse mit konvertiertem upload_date
            upload_date_str = None
            if db_file.upload_date:
                if isinstance(db_file.upload_date, datetime):
                    upload_date_str = db_file.upload_date.isoformat()
                else:
                    upload_date_str = str(db_file.upload_date)
            
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
            
            # Extraktion im Hintergrund starten
            # #region agent log
            import json
            try:
                with open(DEBUG_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"files.py:284","message":"Adding background task (ZIP)","data":{"project_id":project_id},"timestamp":int(__import__('time').time()*1000)}) + '\n')
            except: pass
            # #endregion
            background_tasks.add_task(trigger_extraction_background, project_id)
            
            upload_response = UploadResponse(
                message="Datei hochgeladen",
                files=[file_response],
                task_ids=None
            )
            return upload_response
    
    except HTTPException:
        # HTTP-Fehler weiterwerfen
        raise
    except Exception as e:
        # Alle anderen Fehler loggen und als 500 zurückgeben
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Fehler beim Upload: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(error_msg)
        print(f"Traceback:\n{error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interner Serverfehler beim Upload: {type(e).__name__}: {str(e)}"
        )


@router.get("/project/{project_id}", response_model=List[FileResponse])
async def list_project_files(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Alle Dateien eines Projekts auflisten"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projekt mit ID {project_id} nicht gefunden"
        )
    
    files = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    return files


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Einzelne Datei abrufen"""
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei mit ID {file_id} nicht gefunden"
        )
    return file


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Datei herunterladen - mit echtem Streaming für große Dateien"""
    import time
    start_time = time.time()
    
    logger.info(f"Download request für Datei {file_id}")
    
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file:
        logger.warning(f"Datei {file_id} nicht gefunden")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei mit ID {file_id} nicht gefunden"
        )
    
    logger.info(f"Datei gefunden: {file.original_filename} (Typ: {file.file_type}, Größe: {file.file_size} bytes)")
    
    try:
        storage_service = get_storage_service()
        
        # Content-Type bestimmen
        content_type = file.mime_type or "application/octet-stream"
        logger.debug(f"Content-Type: {content_type}")
        
        # Für lokales Storage: Datei direkt streamen ohne komplett in Speicher zu laden
        if storage_service.use_local_storage:
            import os
            
            # Finde den korrekten Pfad
            file_path = file.file_path
            full_path = os.path.join(storage_service.local_storage_path, file_path)
            logger.debug(f"Versuche Datei zu öffnen: {full_path}")
            
            if not os.path.exists(full_path):
                logger.warning(f"Datei nicht gefunden unter {full_path}, versuche Fallback-Pfade")
                # Versuche Fallback-Pfade
                if file_path.startswith("projects/"):
                    parts = file_path.split("/")
                    if len(parts) >= 2:
                        project_id = parts[1]
                        filename = "/".join(parts[2:]) if len(parts) > 2 else parts[1]
                        full_path = os.path.join(storage_service.local_storage_path, f"project_{project_id}", filename)
                        logger.debug(f"Fallback-Pfad 1: {full_path}")
                
                if not os.path.exists(full_path) and file_path.startswith("project_"):
                    parts = file_path.split("/")
                    if len(parts) >= 2:
                        project_part = parts[0]
                        if project_part.startswith("project_"):
                            project_id = project_part.replace("project_", "")
                            filename = "/".join(parts[1:])
                            full_path = os.path.join(storage_service.local_storage_path, "projects", project_id, filename)
                            logger.debug(f"Fallback-Pfad 2: {full_path}")
            
            if not os.path.exists(full_path):
                logger.error(f"Datei nicht gefunden nach allen Versuchen: {file_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Datei nicht gefunden: {file_path}"
                )
            
            # Prüfe Dateigröße
            actual_size = os.path.getsize(full_path)
            logger.info(f"Dateigröße: erwartet {file.file_size} bytes, tatsächlich {actual_size} bytes")
            
            if file.file_size and actual_size != file.file_size:
                logger.warning(f"Dateigröße stimmt nicht überein: erwartet {file.file_size}, tatsächlich {actual_size}")
            
            # Generator-Funktion für echtes Streaming
            def file_stream():
                chunks_sent = 0
                total_bytes = 0
                try:
                    with open(full_path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)  # 8KB Chunks
                            if not chunk:
                                break
                            chunks_sent += 1
                            total_bytes += len(chunk)
                            yield chunk
                    logger.info(f"Streaming abgeschlossen: {chunks_sent} Chunks, {total_bytes} bytes gesendet")
                except Exception as stream_error:
                    logger.error(f"Fehler beim Streamen der Datei: {str(stream_error)}", exc_info=True)
                    raise
            
            response = StreamingResponse(
                file_stream(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{file.original_filename}"',
                    "Content-Length": str(actual_size) if actual_size else None,
                    "Accept-Ranges": "bytes"
                }
            )
            
            duration = time.time() - start_time
            logger.info(f"Download-Response erstellt in {duration:.2f}s für Datei {file_id}")
            return response
        else:
            # Für S3/MinIO: Datei aus Storage laden (kann bei sehr großen Dateien problematisch sein)
            logger.info(f"Lade Datei aus S3/MinIO: {file.file_path}")
            try:
                file_content = await storage_service.get_file(file.file_path)
                logger.info(f"Datei aus S3/MinIO geladen: {len(file_content)} bytes")
                
                response = StreamingResponse(
                    BytesIO(file_content),
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'attachment; filename="{file.original_filename}"',
                        "Content-Length": str(len(file_content))
                    }
                )
                
                duration = time.time() - start_time
                logger.info(f"Download-Response erstellt in {duration:.2f}s für Datei {file_id}")
                return response
            except Exception as s3_error:
                logger.error(f"Fehler beim Laden aus S3/MinIO: {str(s3_error)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Fehler beim Laden der Datei aus Storage: {str(s3_error)}"
                )
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Fehler beim Download der Datei {file_id} nach {duration:.2f}s: {str(e)}", exc_info=True)
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Traceback:\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Laden der Datei: {str(e)}"
        )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Datei löschen"""
    file = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei mit ID {file_id} nicht gefunden"
        )
    
    # Datei aus Storage löschen
    storage_service = get_storage_service()
    await storage_service.delete_file(file.file_path)
    
    db.delete(file)
    db.commit()
    return None
