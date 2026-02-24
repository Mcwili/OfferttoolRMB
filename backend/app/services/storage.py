"""
Storage Service für S3-kompatiblen Objektspeicher
Verwaltet Upload und Download von Dateien
"""

import os
from typing import BinaryIO
from botocore.exceptions import ClientError
import boto3
from botocore.config import Config

from app.core.config import settings

# Singleton-Instanz
_storage_service_instance = None


class StorageService:
    """Service für Dateispeicherung (S3/MinIO)"""
    
    def __init__(self):
        """S3-Client initialisieren oder lokales Dateisystem verwenden"""
        import json
        import time
        log_path = r"c:\Users\micha\Offerttool RMB\.cursor\debug.log"
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:__init__","message":"Initializing StorageService","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        self.use_local_storage = False
        self.local_storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
        self.s3_client = None
        self.bucket = settings.S3_BUCKET
        
        # Versuche S3/MinIO zu initialisieren mit sehr kurzem Timeout
        try:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:s3_init","message":"Attempting S3 client initialization","data":{"endpoint":settings.S3_ENDPOINT},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            # Verwende sehr kurze Timeouts, um schnell zu scheitern
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
                use_ssl=settings.S3_USE_SSL,
                config=Config(
                    signature_version='s3v4',
                    connect_timeout=1,  # 1 Sekunde statt 2
                    read_timeout=1,     # 1 Sekunde statt 2
                    retries={'max_attempts': 1}  # Nur 1 Versuch
                )
            )
            # Teste Verbindung mit einem sehr kurzen Timeout
            try:
                # Verwende einen sehr kurzen Timeout für head_bucket
                import socket
                socket.setdefaulttimeout(1)  # 1 Sekunde Timeout
                self.s3_client.head_bucket(Bucket=self.bucket)
                socket.setdefaulttimeout(None)  # Zurücksetzen
                # Wenn erfolgreich, verwende S3
                self._ensure_bucket_exists()
            except Exception as e:
                # Bucket nicht erreichbar, verwende lokales Storage
                socket.setdefaulttimeout(None)  # Zurücksetzen
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:s3_fallback","message":"S3 not reachable, using local storage","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                print(f"Info: S3/MinIO nicht erreichbar ({type(e).__name__}). Verwende lokales Dateisystem.")
                self.use_local_storage = True
                os.makedirs(self.local_storage_path, exist_ok=True)
                self.s3_client = None
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:s3_fallback","message":"Local storage initialized","data":{"path":self.local_storage_path},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
        except Exception as e:
            # Falls S3/MinIO nicht verfügbar, verwende lokales Dateisystem
            # #region agent log
            try:
                import traceback
                error_details = traceback.format_exc()
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:s3_init_error","message":"S3 initialization failed, using local storage","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:500]},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            print(f"Info: S3/MinIO nicht verfügbar ({type(e).__name__}: {str(e)[:100]}). Verwende lokales Dateisystem.")
            self.use_local_storage = True
            os.makedirs(self.local_storage_path, exist_ok=True)
            self.s3_client = None
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"C","location":"storage.py:s3_init_error","message":"StorageService initialization complete (local)","data":{},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
    
    def _ensure_bucket_exists(self):
        """Stellt sicher, dass der Bucket existiert"""
        if self.use_local_storage:
            return
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            # Bucket existiert nicht, erstellen
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
            except ClientError as e:
                # Falls Bucket-Erstellung fehlschlägt, verwende lokales Dateisystem
                print(f"Warnung: Bucket kann nicht erstellt werden ({e}). Verwende lokales Dateisystem.")
                self.use_local_storage = True
                os.makedirs(self.local_storage_path, exist_ok=True)
    
    async def save_file(
        self,
        file_content: bytes,
        filename: str,
        project_id: int
    ) -> str:
        """
        Datei im Storage speichern
        Returns: Pfad zur Datei (S3 Key oder lokaler Pfad)
        """
        if self.use_local_storage:
            # Lokales Dateisystem verwenden
            # Verwende "projects" statt "project_" für Konsistenz
            project_dir = os.path.join(self.local_storage_path, "projects", str(project_id))
            os.makedirs(project_dir, exist_ok=True)
            file_path = os.path.join(project_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Relativer Pfad zurückgeben (muss mit get_file übereinstimmen)
            return f"projects/{project_id}/{filename}"
        
        # S3/MinIO verwenden
        key = f"projects/{project_id}/{filename}"
        
        try:
            if self.s3_client is None:
                raise Exception("S3-Client nicht initialisiert")
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_content
            )
            return key
        except Exception as e:
            # Falls S3 fehlschlägt, wechsle zu lokalem Storage
            print(f"Warnung: S3-Upload fehlgeschlagen, wechsle zu lokalem Storage: {type(e).__name__}")
            self.use_local_storage = True
            # Verwende konsistentes Format: projects/{project_id}
            project_dir = os.path.join(self.local_storage_path, "projects", str(project_id))
            os.makedirs(project_dir, exist_ok=True)
            file_path = os.path.join(project_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return f"projects/{project_id}/{filename}"
    
    async def get_file(self, file_path: str) -> bytes:
        """Datei aus Storage laden"""
        if self.use_local_storage:
            # Lokales Dateisystem verwenden
            # file_path kann sein: "projects/{project_id}/{filename}" oder "project_{project_id}/{filename}"
            
            # Versuche zuerst den exakten Pfad
            full_path = os.path.join(self.local_storage_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    return f.read()
            
            # Fallback 1: Wenn "projects/..." versuche "project_..."
            if file_path.startswith("projects/"):
                parts = file_path.split("/")
                if len(parts) >= 2:
                    project_id = parts[1]
                    filename = "/".join(parts[2:]) if len(parts) > 2 else parts[1]
                    old_path = os.path.join(self.local_storage_path, f"project_{project_id}", filename)
                    if os.path.exists(old_path):
                        with open(old_path, 'rb') as f:
                            return f.read()
            
            # Fallback 2: Wenn "project_..." versuche "projects/..."
            if file_path.startswith("project_"):
                parts = file_path.split("/")
                if len(parts) >= 2:
                    project_part = parts[0]  # "project_3"
                    if project_part.startswith("project_"):
                        project_id = project_part.replace("project_", "")
                        filename = "/".join(parts[1:])
                        new_path = os.path.join(self.local_storage_path, "projects", project_id, filename)
                        if os.path.exists(new_path):
                            with open(new_path, 'rb') as f:
                                return f.read()
            
            # Fallback 3: Versuche direkt im uploads-Verzeichnis
            direct_path = os.path.join(self.local_storage_path, file_path)
            if os.path.exists(direct_path):
                with open(direct_path, 'rb') as f:
                    return f.read()
            
            raise Exception(f"Datei nicht gefunden: {file_path} (versucht: {full_path})")
        
        # S3/MinIO verwenden
        try:
            if self.s3_client is None:
                raise Exception("S3-Client nicht initialisiert")
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return response['Body'].read()
        except Exception as e:
            raise Exception(f"Fehler beim Laden der Datei: {e}")
    
    async def delete_file(self, file_path: str):
        """Datei aus Storage löschen"""
        if self.use_local_storage:
            # Lokales Dateisystem verwenden
            full_path = os.path.join(self.local_storage_path, file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"Warnung beim Löschen der Datei: {e}")
            return
        
        # S3/MinIO verwenden
        try:
            if self.s3_client is None:
                return  # Lokales Storage bereits behandelt
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_path
            )
        except Exception as e:
            # Fehler wird ignoriert, da Datei möglicherweise bereits gelöscht wurde
            print(f"Warnung beim Löschen der Datei: {e}")
    
    def get_presigned_url(self, file_path: str, expiration: int = 3600) -> str:
        """
        Generiert eine signierte URL für direkten Download
        expiration: Gültigkeit in Sekunden (Standard: 1 Stunde)
        """
        if self.use_local_storage:
            # Für lokales Dateisystem: relativer Pfad zurückgeben
            # In Produktion sollte hier ein eigener Download-Endpoint verwendet werden
            return f"/api/v1/files/download/{file_path}"
        
        # S3/MinIO verwenden
        try:
            if self.s3_client is None:
                return f"/api/v1/files/download/{file_path}"
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_path},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            # Fallback zu lokalem Storage
            return f"/api/v1/files/download/{file_path}"


def get_storage_service() -> StorageService:
    """Gibt die Singleton-Instanz von StorageService zurück"""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance
