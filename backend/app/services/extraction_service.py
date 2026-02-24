"""
Extraktions-Service
Koordiniert die verschiedenen Parser-Module
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.models.project import ProjectFile
from app.services.storage import StorageService
from app.services.data_merging_service import DataMergingService

# Optional parser imports - might fail if dependencies are missing
# Catch all exceptions, not just ImportError, as missing dependencies might cause other errors
try:
    from app.parsers.excel_parser import ExcelParser
    EXCEL_PARSER_AVAILABLE = True
except Exception:
    EXCEL_PARSER_AVAILABLE = False
    ExcelParser = None

try:
    from app.parsers.word_parser import WordParser
    WORD_PARSER_AVAILABLE = True
except Exception:
    WORD_PARSER_AVAILABLE = False
    WordParser = None

try:
    from app.parsers.pdf_parser import PDFParser
    PDF_PARSER_AVAILABLE = True
except Exception:
    PDF_PARSER_AVAILABLE = False
    PDFParser = None

try:
    from app.parsers.pdf_plan_parser import PDFPlanParser
    PDF_PLAN_PARSER_AVAILABLE = True
except Exception:
    PDF_PLAN_PARSER_AVAILABLE = False
    PDFPlanParser = None

try:
    from app.parsers.ifc_parser import IFCParser
    IFC_PARSER_AVAILABLE = True
except Exception:
    IFC_PARSER_AVAILABLE = False
    IFCParser = None

try:
    from app.parsers.ocr_parser import OCRParser
    OCR_PARSER_AVAILABLE = True
except Exception:
    OCR_PARSER_AVAILABLE = False
    OCRParser = None


class ExtractionService:
    """Service für Datenextraktion aus verschiedenen Dateiformaten"""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage = StorageService()
        
        # Parser initialisieren (nur wenn verfügbar)
        self.excel_parser = ExcelParser() if EXCEL_PARSER_AVAILABLE else None
        self.word_parser = WordParser() if WORD_PARSER_AVAILABLE else None
        self.pdf_parser = PDFParser() if PDF_PARSER_AVAILABLE else None
        self.pdf_plan_parser = PDFPlanParser() if PDF_PLAN_PARSER_AVAILABLE else None
        self.ifc_parser = IFCParser() if IFC_PARSER_AVAILABLE else None
        self.ocr_parser = OCRParser() if OCR_PARSER_AVAILABLE else None
        
        # Merging Service
        self.merging_service = DataMergingService()
    
    async def extract_file(self, file_obj: ProjectFile) -> Dict[str, Any]:
        """
        Extrahiert Daten aus einer Datei basierend auf ihrem Typ
        Returns: Dict mit extrahierten Entitäten
        """
        # Datei aus Storage laden
        file_content = await self.storage.get_file(file_obj.file_path)
        
        # Je nach Dateityp entsprechenden Parser verwenden
        if file_obj.file_type == "Excel":
            if not self.excel_parser:
                raise ValueError("Excel-Parser ist nicht verfügbar. Bitte installieren Sie openpyxl und pandas.")
            return await self.excel_parser.parse(file_content, file_obj)
        elif file_obj.file_type == "Word":
            if not self.word_parser:
                raise ValueError("Word-Parser ist nicht verfügbar. Bitte installieren Sie python-docx.")
            return await self.word_parser.parse(file_content, file_obj)
        elif file_obj.file_type == "PDF":
            # Unterscheide zwischen normalem PDF und Plan-PDF
            if file_obj.document_type and any(kw in file_obj.document_type.lower() for kw in ["plan", "grundriss", "schnitt"]):
                if not self.pdf_plan_parser:
                    raise ValueError("PDF-Plan-Parser ist nicht verfügbar. Bitte installieren Sie die erforderlichen Module.")
                return await self.pdf_plan_parser.parse(file_content, file_obj)
            else:
                if not self.pdf_parser:
                    raise ValueError("PDF-Parser ist nicht verfügbar. Bitte installieren Sie pdfplumber.")
                return await self.pdf_parser.parse(file_content, file_obj)
        elif file_obj.file_type == "IFC":
            if not self.ifc_parser:
                raise ValueError("IFC-Parser ist nicht verfügbar. Bitte installieren Sie ifcopenshell.")
            return await self.ifc_parser.parse(file_content, file_obj)
        elif file_obj.file_type == "Image":
            if not self.ocr_parser:
                raise ValueError("OCR-Parser ist nicht verfügbar. Bitte installieren Sie pytesseract und opencv-python.")
            return await self.ocr_parser.parse(file_content, file_obj)
        else:
            raise ValueError(f"Dateityp {file_obj.file_type} wird noch nicht unterstützt")
    
    def merge_extracted_data(
        self,
        current_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        source_file: ProjectFile
    ) -> Dict[str, Any]:
        """
        Integriert extrahierte Daten ins bestehende JSON-Modell
        Verwendet intelligentes Merging mit Duplikat-Erkennung
        """
        return self.merging_service.merge_extracted_data(
            current_data,
            extracted_data,
            source_file
        )
