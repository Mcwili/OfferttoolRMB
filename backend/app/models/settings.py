"""
Settings-Modell für Anwendungseinstellungen
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.config import settings

# SQLite-kompatible Timestamp-Funktion
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import text
    sqlite_now = text("CURRENT_TIMESTAMP")
else:
    sqlite_now = func.now()


class AppSettings(Base):
    """Anwendungseinstellungen"""
    __tablename__ = "app_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    updated_at = Column(DateTime(timezone=True), onupdate=sqlite_now)
    
    def __repr__(self):
        return f"<AppSettings(id={self.id}, key='{self.key}')>"
