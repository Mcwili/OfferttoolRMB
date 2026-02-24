"""
API v1 Router
Sammelt alle API-Endpunkte
"""

from fastapi import APIRouter
import json
import os
import time

# #region agent log
log_path = r"c:\Users\micha\Offerttool RMB\.cursor\debug.log"
def write_log(message, location, hypothesis_id, data=None):
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"startup","hypothesisId":hypothesis_id,"location":location,"message":message,"data":data or {},"timestamp":int(time.time()*1000)})+"\n")
    except: pass

write_log("Starting API router imports", "api/v1/__init__.py:imports", "A,D")
# #endregion

try:
    write_log("Importing projects module", "api/v1/__init__.py:imports", "A,D")
    from app.api.v1 import projects
    write_log("Projects module imported", "api/v1/__init__.py:imports", "A,D")
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    write_log("Failed to import projects", "api/v1/__init__.py:imports", "A,D", {"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:1000]})
    raise

try:
    write_log("Importing remaining API modules", "api/v1/__init__.py:imports", "A,D")
    from app.api.v1 import files, extraction, validation, reports, settings, legal_review, question_list, debug_logs
    write_log("All API modules imported successfully", "api/v1/__init__.py:imports", "A,D")
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    write_log("Failed to import API modules", "api/v1/__init__.py:imports", "A,D", {"error_type":type(e).__name__,"error_msg":str(e)[:200],"traceback":error_details[:1000]})
    raise

api_router = APIRouter()

# Router registrieren
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(legal_review.router, prefix="/legal-review", tags=["legal_review"])
api_router.include_router(question_list.router, prefix="/question-list", tags=["question_list"])
api_router.include_router(debug_logs.router, prefix="", tags=["debug"])
