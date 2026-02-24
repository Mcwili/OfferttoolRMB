"""
Konfigurationsverwaltung für die Anwendung
Nutzt Pydantic Settings für Umgebungsvariablen
"""

import os
from pydantic_settings import BaseSettings
from typing import List

# Pfad für Debug-Log (plattformunabhängig, über DEBUG_LOG_PATH überschreibbar)
_log_base = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEBUG_LOG_PATH = os.environ.get("DEBUG_LOG_PATH", os.path.join(_log_base, "data", "debug.log"))


class Settings(BaseSettings):
    """Anwendungseinstellungen"""
    
    # Application
    APP_NAME: str = "HLKS Offert-Tool"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite Dev Server alternativer Port
        "http://127.0.0.1:5173"
    ]
    
    # Database
    # SQLite: Datei-basierte Datenbank, keine Installation nötig
    # Die Datenbank wird im backend/data/ Verzeichnis erstellt
    DATABASE_URL: str = "sqlite:///./data/hlks.db"
    
    # Redis (für Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # S3/Object Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin123"
    S3_BUCKET: str = "hlks-documents"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500 MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".xlsx", ".xls", ".csv",
        ".ifc", ".zip",
        ".jpg", ".jpeg", ".png", ".tiff"
    ]
    
    # OCR Settings
    TESSERACT_CMD: str = "tesseract"  # Pfad zu Tesseract executable
    OCR_LANGUAGE: str = "deu+eng"  # Deutsch + Englisch
    
    # NLP Settings
    SPACY_MODEL: str = "de_core_news_sm"  # spaCy Modell für Deutsch
    
    # Security
    SECRET_KEY: str = "change-me-in-production"  # TODO: Aus Umgebungsvariable laden
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
