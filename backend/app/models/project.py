"""
Datenbankmodelle für Projekte und zugehörige Daten
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base
from app.core.config import settings

# SQLite-kompatible Timestamp-Funktion
# SQLite verwendet CURRENT_TIMESTAMP statt now()
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import text
    sqlite_now = text("CURRENT_TIMESTAMP")
else:
    sqlite_now = func.now()


class Project(Base):
    """Projekt-Modell"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    standort = Column(String(255))
    status = Column(String(50), default="draft")  # draft, processing, validated, offertreif
    created_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    updated_at = Column(DateTime(timezone=True), onupdate=sqlite_now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    data_snapshots = relationship("ProjectData", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"


class ProjectFile(Base):
    """Hochgeladene Datei eines Projekts"""
    __tablename__ = "project_files"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)  # Name im S3/Storage
    file_path = Column(String(1000), nullable=False)  # S3 Key oder lokaler Pfad
    file_type = Column(String(50), nullable=False)  # PDF, Excel, Word, IFC, etc.
    mime_type = Column(String(100))
    file_size = Column(Integer)  # in Bytes
    document_type = Column(String(100))  # Raumliste, Grundrissplan, etc.
    discipline = Column(String(50))  # HLKS, Architektur, Elektro, etc.
    revision = Column(String(50))  # Versionsnummer
    upload_date = Column(DateTime(timezone=True), server_default=sqlite_now)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="files")
    
    def __repr__(self):
        return f"<ProjectFile(id={self.id}, filename='{self.original_filename}', type='{self.file_type}')>"


class ProjectData(Base):
    """JSON-Datenmodell-Snapshot eines Projekts (versioniert)"""
    __tablename__ = "project_data"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    data_json = Column(JSON, nullable=False)  # PostgreSQL JSONB
    is_active = Column(Boolean, default=False, index=True)  # Nur neueste Version aktiv
    created_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="data_snapshots")
    
    def __repr__(self):
        return f"<ProjectData(project_id={self.project_id}, version={self.version}, active={self.is_active})>"
