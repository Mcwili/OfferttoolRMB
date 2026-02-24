"""Prüft Datei-Informationen aus der Datenbank"""
from app.core.database import SessionLocal
from app.models.project import ProjectFile
import os

db = SessionLocal()
file = db.query(ProjectFile).filter(ProjectFile.id == 29).first()

if file:
    print(f"File ID: {file.id}")
    print(f"Filename: {file.original_filename}")
    print(f"File Type: {file.file_type}")
    print(f"File Size: {file.file_size} bytes ({file.file_size / 1024 / 1024:.2f} MB)")
    print(f"File Path: {file.file_path}")
    print(f"Stored Filename: {file.stored_filename}")
    
    # Prüfe ob Datei existiert
    from app.services.storage import get_storage_service
    storage = get_storage_service()
    
    print(f"\nStorage Service:")
    print(f"  Use Local Storage: {storage.use_local_storage}")
    print(f"  Local Storage Path: {storage.local_storage_path}")
    
    # Versuche verschiedene Pfade
    possible_paths = [
        os.path.join(storage.local_storage_path, file.file_path),
        os.path.join("uploads", file.file_path),
    ]
    
    if file.file_path.startswith("projects/"):
        parts = file.file_path.split("/")
        if len(parts) >= 2:
            project_id = parts[1]
            filename = "/".join(parts[2:]) if len(parts) > 2 else parts[1]
            possible_paths.append(os.path.join(storage.local_storage_path, f"project_{project_id}", filename))
            possible_paths.append(os.path.join("uploads", f"project_{project_id}", filename))
    
    print(f"\nChecking possible paths:")
    for path in possible_paths:
        exists = os.path.exists(path)
        print(f"  {path}: {'EXISTS' if exists else 'NOT FOUND'}")
        if exists:
            actual_size = os.path.getsize(path)
            print(f"    Size: {actual_size} bytes ({actual_size / 1024 / 1024:.2f} MB)")
            if file.file_size and actual_size != file.file_size:
                print(f"    WARNING: Size mismatch! Expected: {file.file_size}, Actual: {actual_size}")
else:
    print("File not found!")

db.close()
