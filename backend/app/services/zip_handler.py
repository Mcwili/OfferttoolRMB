"""
ZIP-Archiv-Handler
Verarbeitet ZIP-Archive beim Upload und extrahiert enthaltene Dateien
"""

import zipfile
import os
import tempfile
from typing import List, Tuple
from pathlib import Path
import uuid


class ZIPHandler:
    """Handler für ZIP-Archiv-Verarbeitung"""
    
    MAX_EXTRACT_SIZE = 500 * 1024 * 1024  # 500 MB Gesamtgröße
    MAX_FILE_COUNT = 1000  # Maximale Anzahl Dateien im Archiv
    
    def __init__(self):
        self.extracted_files: List[Tuple[bytes, str]] = []  # (content, filename)
    
    def extract_archive(self, zip_content: bytes, max_depth: int = 3) -> List[Tuple[bytes, str]]:
        """
        Extrahiert Dateien aus einem ZIP-Archiv
        Unterstützt rekursive Verarbeitung verschachtelter Archive
        
        Args:
            zip_content: Bytes des ZIP-Archivs
            max_depth: Maximale Verschachtelungstiefe (verhindert Zip-Bomben)
        
        Returns:
            Liste von Tupeln (Dateiinhalt, Dateiname)
        """
        if max_depth <= 0:
            raise ValueError("Maximale Verschachtelungstiefe erreicht")
        
        self.extracted_files = []
        total_size = 0
        file_count = 0
        
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(zip_content)
                tmp_path = tmp_file.name
            
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                # Prüfe auf Zip-Bomben (zu viele Dateien oder zu groß)
                file_list = zip_ref.namelist()
                if len(file_list) > self.MAX_FILE_COUNT:
                    raise ValueError(f"Zu viele Dateien im Archiv: {len(file_list)} > {self.MAX_FILE_COUNT}")
                
                # Extrahiere jede Datei
                for file_info in zip_ref.infolist():
                    # Überspringe Verzeichnisse
                    if file_info.is_dir():
                        continue
                    
                    # Prüfe Gesamtgröße
                    total_size += file_info.file_size
                    if total_size > self.MAX_EXTRACT_SIZE:
                        raise ValueError(f"Archiv zu groß: {total_size} > {self.MAX_EXTRACT_SIZE}")
                    
                    file_count += 1
                    if file_count > self.MAX_FILE_COUNT:
                        raise ValueError(f"Zu viele Dateien: {file_count} > {self.MAX_FILE_COUNT}")
                    
                    # Extrahiere Datei
                    try:
                        file_content = zip_ref.read(file_info.filename)
                        filename = os.path.basename(file_info.filename)
                        
                        # Prüfe, ob es ein verschachteltes Archiv ist
                        if self._is_archive(filename):
                            # Rekursiv verarbeiten
                            nested_files = self._extract_nested_archive(file_content, max_depth - 1)
                            self.extracted_files.extend(nested_files)
                        else:
                            # Normale Datei hinzufügen
                            self.extracted_files.append((file_content, filename))
                    
                    except Exception as e:
                        # Fehler bei einer Datei blockiert nicht den Rest
                        print(f"Fehler beim Extrahieren von {file_info.filename}: {e}")
                        continue
            
            return self.extracted_files
        
        finally:
            # Temporäre Datei löschen
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def _is_archive(self, filename: str) -> bool:
        """Prüft, ob eine Datei ein Archiv ist"""
        archive_extensions = ['.zip', '.tar', '.gz', '.bz2', '.7z', '.rar']
        ext = Path(filename).suffix.lower()
        return ext in archive_extensions
    
    def _extract_nested_archive(self, archive_content: bytes, max_depth: int) -> List[Tuple[bytes, str]]:
        """
        Extrahiert verschachteltes Archiv rekursiv
        Aktuell nur ZIP unterstützt, andere Formate werden ignoriert
        """
        if max_depth <= 0:
            return []
        
        try:
            handler = ZIPHandler()
            return handler.extract_archive(archive_content, max_depth)
        except Exception as e:
            print(f"Fehler beim Extrahieren verschachtelten Archivs: {e}")
            return []
    
    async def extract_and_list_files(self, zip_content: bytes, project_id: int) -> List[dict]:
        """
        Extrahiert ZIP-Archiv und gibt Liste von Dateien mit Metadaten zurück
        Für Verwendung im Upload-Endpoint
        
        Returns:
            Liste von Dicts mit: content, filename, file_type, mime_type, size
        """
        extracted = self.extract_archive(zip_content)
        
        from app.services.file_classifier import FileClassifier
        classifier = FileClassifier()
        
        file_list = []
        for content, filename in extracted:
            file_ext = os.path.splitext(filename)[1].lower()
            file_type = classifier.detect_file_type(file_ext, None)
            
            # MIME-Type schätzen
            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            
            file_list.append({
                "content": content,
                "filename": filename,
                "file_type": file_type,
                "mime_type": mime_type or "application/octet-stream",
                "size": len(content)
            })
        
        return file_list
    
    def get_file_info(self, zip_content: bytes) -> dict:
        """
        Gibt Informationen über den Inhalt eines ZIP-Archivs zurück
        ohne es vollständig zu extrahieren
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(zip_content)
                tmp_path = tmp_file.name
            
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_size = sum(zip_ref.getinfo(f).file_size for f in file_list if not zip_ref.getinfo(f).is_dir())
                
                return {
                    "file_count": len([f for f in file_list if not zip_ref.getinfo(f).is_dir()]),
                    "total_size": total_size,
                    "files": [f for f in file_list if not zip_ref.getinfo(f).is_dir()]
                }
        
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
