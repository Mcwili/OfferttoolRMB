"""
Datenbankverbindung und Session-Management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import json
import os
import time

from app.core.config import settings, DEBUG_LOG_PATH

# #region agent log
log_path = DEBUG_LOG_PATH
try:
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:init","message":"Initializing database","data":{"database_url":settings.DATABASE_URL[:50]},"timestamp":int(time.time()*1000)})+"\n")
except: pass
# #endregion

# SQLite-spezifische Konfiguration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:sqlite_setup","message":"Setting up SQLite","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    # SQLite benötigt check_same_thread=False für FastAPI
    connect_args = {"check_same_thread": False}
    # Stelle sicher, dass das data-Verzeichnis existiert
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:sqlite_setup","message":"Database directory created","data":{"path":str(db_path.parent)},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:sqlite_setup","message":"Failed to create database directory","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        raise

# Datenbank-Engine erstellen
# SQLite verwendet kein Connection Pooling wie PostgreSQL
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

try:
    if is_sqlite:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:engine_create","message":"Creating SQLite engine","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # SQLite: Kein Connection Pooling
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            echo=settings.DEBUG  # SQL-Queries in Debug-Modus ausgeben
        )
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:engine_create","message":"SQLite engine created successfully","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    else:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:engine_create","message":"Creating PostgreSQL engine","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # PostgreSQL: Mit Connection Pooling
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=settings.DEBUG
        )
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:engine_create","message":"PostgreSQL engine created successfully","data":{},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
except Exception as e:
    # #region agent log
    try:
        import traceback
        error_details = traceback.format_exc()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"B","location":"database.py:engine_create","message":"Failed to create database engine","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:1000]},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    raise

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class für Models
Base = declarative_base()


def get_db():
    """
    Dependency für FastAPI: Liefert DB-Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
