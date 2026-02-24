"""
Report-Generierungs-Service
Erstellt verschiedene Berichte basierend auf dem JSON-Datenmodell
"""

from typing import Dict, Any
from datetime import datetime
from app.models.project import Project
from app.services.storage import StorageService

# Optional reporter imports - might fail if dependencies are missing
try:
    from app.reporters.offerte_reporter import OfferteReporter
    OFFERTE_REPORTER_AVAILABLE = True
except Exception:
    OFFERTE_REPORTER_AVAILABLE = False
    OfferteReporter = None

try:
    from app.reporters.risiko_reporter import RisikoReporter
    RISIKO_REPORTER_AVAILABLE = True
except Exception:
    RISIKO_REPORTER_AVAILABLE = False
    RisikoReporter = None

try:
    from app.reporters.timeline_reporter import TimelineReporter
    TIMELINE_REPORTER_AVAILABLE = True
except Exception:
    TIMELINE_REPORTER_AVAILABLE = False
    TimelineReporter = None

try:
    from app.reporters.org_reporter import OrgReporter
    ORG_REPORTER_AVAILABLE = True
except Exception:
    ORG_REPORTER_AVAILABLE = False
    OrgReporter = None


class ReportService:
    """Service für Berichtsgenerierung"""
    
    def __init__(self):
        self.storage = StorageService()
        self.offerte_reporter = OfferteReporter() if OFFERTE_REPORTER_AVAILABLE else None
        self.risiko_reporter = RisikoReporter() if RISIKO_REPORTER_AVAILABLE else None
        self.timeline_reporter = TimelineReporter() if TIMELINE_REPORTER_AVAILABLE else None
        self.org_reporter = OrgReporter() if ORG_REPORTER_AVAILABLE else None
    
    async def generate_report(
        self,
        project: Project,
        project_data: Dict[str, Any],
        report_type: str
    ) -> Dict[str, Any]:
        """
        Generiert einen Bericht des angegebenen Typs
        Returns: Dict mit report_type, filename, version, generated_at, download_url
        """
        if report_type == "offerte":
            if not self.offerte_reporter:
                raise ValueError("Offerte-Reporter ist nicht verfügbar. Bitte installieren Sie python-docx.")
            file_path = await self.offerte_reporter.generate(project, project_data)
        elif report_type == "risikoanalyse":
            if not self.risiko_reporter:
                raise ValueError("Risiko-Reporter ist nicht verfügbar. Bitte installieren Sie reportlab.")
            file_path = await self.risiko_reporter.generate(project, project_data)
        elif report_type == "timeline":
            if not self.timeline_reporter:
                raise ValueError("Timeline-Reporter ist nicht verfügbar.")
            file_path = await self.timeline_reporter.generate(project, project_data)
        elif report_type == "org":
            if not self.org_reporter:
                raise ValueError("Org-Reporter ist nicht verfügbar.")
            file_path = await self.org_reporter.generate(project, project_data)
        else:
            raise ValueError(f"Unbekannter Report-Typ: {report_type}")
        
        # Download-URL generieren
        download_url = self.storage.get_presigned_url(file_path)
        
        return {
            "report_type": report_type,
            "filename": file_path.split("/")[-1],
            "version": project_data.get("projekt", {}).get("version", 1),
            "generated_at": datetime.now().isoformat(),
            "download_url": download_url
        }
