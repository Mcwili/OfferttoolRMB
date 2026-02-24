"""
Benutzer-Modell (für Authentifizierung, falls benötigt)
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from app.core.database import Base
from app.core.config import settings

# SQLite-kompatible Timestamp-Funktion
if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import text
    sqlite_now = text("CURRENT_TIMESTAMP")
else:
    sqlite_now = func.now()


class User(Base):
    """Benutzer-Modell"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=sqlite_now)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
