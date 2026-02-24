"""
HLKS Planungsanalyse Tool - FastAPI Backend
Haupt-Einstiegspunkt der Anwendung
"""

import json
import os
import traceback
import time

# #region agent log
log_path = os.environ.get("DEBUG_LOG_PATH", os.path.join(os.path.dirname(__file__), "data", "debug.log"))
def write_log(message, location, hypothesis_id, data=None):
    try:
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":hypothesis_id,"location":location,"message":message,"data":data or {},"timestamp":int(time.time()*1000)})+"\n")
            f.flush()
    except Exception as e:
        print(f"Log write failed: {e}")
        import traceback
        print(traceback.format_exc())

try:
    write_log("Starting imports", "main.py:14", "A,B,C,D,E")
except Exception as e:
    print(f"Failed to write initial log: {e}")
    import traceback
    print(traceback.format_exc())
# #endregion

try:
    write_log("Importing FastAPI", "main.py:fastapi_import", "ALL")
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    write_log("FastAPI imported", "main.py:fastapi_import", "ALL")
except Exception as e:
    write_log("FastAPI import failed", "main.py:fastapi_import", "ALL", {"error":str(e),"traceback":traceback.format_exc()[:500]})
    raise

try:
    write_log("Importing config", "main.py:config_import", "B")
    from app.core.config import settings
    write_log("Config imported successfully", "main.py:config_import", "B", {"database_url":settings.DATABASE_URL[:50] if hasattr(settings,'DATABASE_URL') else 'N/A'})
except Exception as e:
    error_details = traceback.format_exc()
    write_log("Config import failed", "main.py:config_import", "B", {"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:1000]})
    raise

try:
    write_log("Importing api_router", "main.py:api_router_import", "A,D")
    from app.api.v1 import api_router
    write_log("API router imported successfully", "main.py:api_router_import", "A,D")
except Exception as e:
    error_details = traceback.format_exc()
    write_log("API router import failed", "main.py:api_router_import", "A,D", {"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:1000]})
    raise

app = FastAPI(
    title="HLKS Offert-Tool API",
    description="API für die automatisierte Analyse von HLKS-Planungsunterlagen",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # #region agent log
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"request","hypothesisId":"REQUEST","location":"main.py:middleware","message":"Request received","data":{"method":request.method,"url":str(request.url),"path":request.url.path},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        response = await call_next(request)
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"request","hypothesisId":"REQUEST","location":"main.py:middleware","message":"Request completed","data":{"method":request.method,"path":request.url.path,"status_code":response.status_code},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        return response
    except Exception as e:
        # #region agent log
        try:
            error_details = traceback.format_exc()
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"request","hypothesisId":"REQUEST","location":"main.py:middleware","message":"Request error","data":{"method":request.method,"path":request.url.path,"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        raise

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router einbinden
# #region agent log
try:
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"STARTUP","location":"main.py:31","message":"Including API router","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
except: pass
# #endregion
try:
    app.include_router(api_router, prefix="/api/v1")
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"STARTUP","location":"main.py:34","message":"API router included successfully","data":{},"timestamp":int(__import__('time').time()*1000)})+"\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        error_details = traceback.format_exc()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"STARTUP","location":"main.py:38","message":"Error including API router","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:500]},"timestamp":int(__import__('time').time()*1000)})+"\n")
    except: pass
    # #endregion
    raise


@app.on_event("startup")
async def startup():
    """Erstellt fehlende DB-Tabellen beim Start (wichtig für Deployment ohne manuelle Migrationen)."""
    try:
        from app.core.database import engine, Base
        import app.models  # Registriert alle Models bei Base
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        write_log("DB-Tabellenerstellung fehlgeschlagen", "main.py:startup", "B", {"error": str(e)[:200]})


@app.get("/health")
async def health_check():
    """Detaillierter Health Check"""
    return JSONResponse(
        content={
            "status": "healthy",
            "database": "connected",  # TODO: DB-Status prüfen
            "storage": "connected"     # TODO: S3-Status prüfen
        }
    )


# Frontend (statische Dateien) ausliefern – nur wenn static/ existiert (Docker-Deploy)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    import socket
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"E","location":"main.py:uvicorn_start","message":"Checking port 8000 availability","data":{},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        if result == 0:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"E","location":"main.py:uvicorn_start","message":"Port 8000 is already in use","data":{},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
        else:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"E","location":"main.py:uvicorn_start","message":"Port 8000 is available","data":{},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"E","location":"main.py:uvicorn_start","message":"Port check failed","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":"ALL","location":"main.py:uvicorn_start","message":"Starting uvicorn server","data":{"host":"0.0.0.0","port":8000},"timestamp":int(time.time()*1000)})+"\n")
    except: pass
    # #endregion
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
