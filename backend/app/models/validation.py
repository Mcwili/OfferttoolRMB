"""
Datenbankmodelle für Validierung und Reports
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base
from app.core.config import settings

# SQLite-kompatible Timestamp-Funktion
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import text
    sqlite_now = text("CURRENT_TIMESTAMP")
else:
    sqlite_now = func.now()


class ValidationIssue(Base):
    """Validierungsproblem"""
    __tablename__ = "validation_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    project_data_version = Column(Integer, nullable=True)
    file_id = Column(Integer, ForeignKey("project_files.id", ondelete="SET NULL"), nullable=True)
    kategorie = Column(String(100), nullable=False)
    beschreibung = Column(Text, nullable=False)
    fundstellen = Column(JSON)  # JSONB
    schweregrad = Column(String(50), nullable=False, index=True)
    empfehlung = Column(Text, nullable=True)
    betroffene_entitaet = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    
    # Relationships
    project = relationship("Project", backref="validation_issues")
    file = relationship("ProjectFile", backref="validation_issues")
    
    def __repr__(self):
        return f"<ValidationIssue(id={self.id}, kategorie='{self.kategorie}', schweregrad='{self.schweregrad}')>"


class GeneratedReport(Base):
    """Generierter Report"""
    __tablename__ = "generated_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    project_data_version = Column(Integer, nullable=True)
    report_type = Column(String(50), nullable=False, index=True)  # offerte, risikoanalyse, timeline, org
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    generated_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    generated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    project = relationship("Project", backref="generated_reports")
    
    def __repr__(self):
        return f"<GeneratedReport(id={self.id}, report_type='{self.report_type}', filename='{self.filename}')>"
