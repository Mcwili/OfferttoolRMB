"""
Dokumentenklassifikation
Erkennt Dokumenttyp, Disziplin und Revision basierend auf Dateinamen und Inhalten
"""

import re
from typing import Dict, Optional
import mimetypes


class FileClassifier:
    """Klassifiziert hochgeladene Dateien"""
    
    # Mapping Dateiendungen -> Dateityp
    FILE_TYPE_MAPPING = {
        ".pdf": "PDF",
        ".docx": "Word",
        ".doc": "Word",
        ".xlsx": "Excel",
        ".xls": "Excel",
        ".csv": "CSV",
        ".ifc": "IFC",
        ".zip": "ZIP",
        ".jpg": "Image",
        ".jpeg": "Image",
        ".png": "Image",
        ".tiff": "Image",
        ".tif": "Image"
    }
    
    # Schlüsselwörter für Dokumenttyp-Erkennung
    DOCUMENT_TYPE_KEYWORDS = {
        "raumliste": ["raumliste", "raum_liste", "raeume", "room_list"],
        "grundrissplan": ["grundriss", "grundrissplan", "floor_plan", "geschossplan"],
        "geräteliste": ["geräteliste", "geraeteliste", "equipment", "geraete"],
        "ausschreibungstext": ["ausschreibung", "ausschreibung", "tender", "specification"],
        "terminplan": ["terminplan", "zeitplan", "schedule", "gantt", "meilenstein"],
        "leistungsaufstellung": ["leistung", "leistungsaufstellung", "scope"],
        "anschreiben": ["anschreiben", "cover_letter", "brief"]
    }
    
    # Schlüsselwörter für Disziplin-Erkennung
    DISCIPLINE_KEYWORDS = {
        "HLKS": ["hlks", "heizung", "lüftung", "klima", "sanitär", "hvac", "zuluft", "abluft", 
                 "wärmepumpe", "kälte", "klimaanlage", "ventilator"],
        "Architektur": ["architektur", "architekt", "architecture", "grundriss", "fassade"],
        "Elektro": ["elektro", "elektrik", "electrical", "strom", "beleuchtung"],
        "Tragwerk": ["tragwerk", "statik", "structure", "beton", "stahl"]
    }
    
    @staticmethod
    def detect_file_type(file_ext: str, mime_type: Optional[str] = None) -> str:
        """Erkennt den Dateityp basierend auf Endung und MIME-Type"""
        file_ext_lower = file_ext.lower()
        
        # Zuerst Mapping prüfen
        if file_ext_lower in FileClassifier.FILE_TYPE_MAPPING:
            return FileClassifier.FILE_TYPE_MAPPING[file_ext_lower]
        
        # Fallback: MIME-Type verwenden
        if mime_type:
            type_mapping = {
                "application/pdf": "PDF",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
                "application/zip": "ZIP",
                "image/jpeg": "Image",
                "image/png": "Image"
            }
            if mime_type in type_mapping:
                return type_mapping[mime_type]
        
        return "Unknown"
    
    @staticmethod
    async def classify_file(
        filename: str,
        file_type: str,
        file_content: bytes
    ) -> Dict[str, Optional[str]]:
        """
        Klassifiziert eine Datei nach Dokumenttyp, Disziplin und Revision
        Returns: Dict mit document_type, discipline, revision
        """
        filename_lower = filename.lower()
        
        # Dokumenttyp erkennen
        document_type = None
        for doc_type, keywords in FileClassifier.DOCUMENT_TYPE_KEYWORDS.items():
            if any(keyword in filename_lower for keyword in keywords):
                document_type = doc_type
                break
        
        # Disziplin erkennen
        discipline = None
        for disc, keywords in FileClassifier.DISCIPLINE_KEYWORDS.items():
            if any(keyword in filename_lower for keyword in keywords):
                discipline = disc
                break
        
        # Revision erkennen (z.B. "PlanXYZ_RevB.pdf" oder "v1.2", "Revision 3")
        revision = FileClassifier._extract_revision(filename)
        
        # TODO: Bei Bedarf kann hier auch eine Analyse des Dateiinhalts erfolgen
        # (z.B. erste Seiten eines PDFs lesen, Excel-Header analysieren)
        
        return {
            "document_type": document_type,
            "discipline": discipline,
            "revision": revision
        }
    
    @staticmethod
    def _extract_revision(filename: str) -> Optional[str]:
        """Extrahiert Revisionsnummer aus Dateinamen"""
        # Pattern: RevA, RevB, Revision_1, v1.2, V2.0, etc.
        patterns = [
            r"[Rr]ev(?:ision)?[_\s]?([A-Z0-9.]+)",
            r"[Vv](\d+\.?\d*)",
            r"_([Rr]\d+)",
            r"([Rr]\d+)_"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None
