"""
PDF-Parser
Verwendet pdfplumber für Text, Bilder und Tabellen
"""

from typing import Dict, Any, List
import pdfplumber
from pdfplumber.page import Page
from io import BytesIO
import base64
from PIL import Image
from app.models.project import ProjectFile

# Optional import - camelot might not be installed
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False


class PDFParser:
    """Parser für PDF-Dateien"""
    
    async def parse(self, file_content: bytes, file_obj: ProjectFile) -> Dict[str, Any]:
        """
        Extrahiert Daten aus PDF-Datei
        Returns: Dict mit extrahierten Entitäten
        """
        source_info = {
            "datei": file_obj.original_filename,
            "datei_id": file_obj.id,
            "upload_am": file_obj.upload_date.isoformat() if file_obj.upload_date else None
        }
        
        extracted_data = {
            "raeume": [],
            "anlagen": [],
            "geraete": [],
            "anforderungen": [],
            "termine": [],
            "leistungen": [],
            "raw_tables": [],
            "full_text": "",
            "images": [],  # Neue Sektion für Bilder
            "metadata": {
                "page_count": 0,
                "has_images": False
            }
        }
        
        # PDF mit pdfplumber öffnen
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            extracted_data["metadata"]["page_count"] = len(pdf.pages)
            
            # Text extrahieren
            text_content = self._extract_text(pdf)
            extracted_data["full_text"] = text_content
            
            # Bilder extrahieren
            images_data = await self._extract_images(pdf, source_info, file_obj)
            extracted_data["images"].extend(images_data)
            extracted_data["metadata"]["has_images"] = len(images_data) > 0
            
            # Tabellen extrahieren
            tables = self._extract_tables(pdf, source_info)
            extracted_data["raw_tables"].extend(tables)
            
            # Entitäten aus Text und Tabellen erkennen
            # TODO: NLP-basierte Erkennung implementieren
        
        return extracted_data
    
    def _extract_text(self, pdf) -> str:
        """Extrahiert Text aus PDF"""
        text_parts = []
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Seite {page_num} ---\n{page_text}")
        return "\n\n".join(text_parts)
    
    async def _extract_images(self, pdf, source_info: Dict[str, Any], file_obj: ProjectFile) -> List[Dict[str, Any]]:
        """Extrahiert alle Bilder aus PDF"""
        images = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                # Bilder aus der Seite extrahieren
                page_images = page.images
                
                for img_idx, img in enumerate(page_images):
                    try:
                        # Bilddaten extrahieren
                        # pdfplumber gibt Bilder als Dictionary mit Koordinaten zurück
                        x0, y0, x1, y1 = img['x0'], img['y0'], img['x1'], img['y1']
                        
                        # Bild aus Seite extrahieren
                        # pdfplumber kann Bilder nicht direkt extrahieren, daher verwenden wir pdf2image als Fallback
                        # Oder wir versuchen es mit PyMuPDF (fitz) falls verfügbar
                        try:
                            import fitz  # PyMuPDF
                            doc = fitz.open(stream=pdf.stream, filetype="pdf")
                            page_obj = doc[page_num - 1]
                            image_list = page_obj.get_images()
                            
                            if img_idx < len(image_list):
                                xref = image_list[img_idx][0]
                                base_image = doc.extract_image(xref)
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                
                                # Bildformat
                                image_format = image_ext.lower()
                                
                                # Bildgröße
                                pil_image = Image.open(BytesIO(image_bytes))
                                image_width, image_height = pil_image.size
                                image_mode = pil_image.mode
                                
                                # Base64 kodieren
                                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                
                                # OCR auf Bild anwenden
                                ocr_text = None
                                try:
                                    import pytesseract
                                    from app.core.config import settings
                                    ocr_text = pytesseract.image_to_string(
                                        pil_image,
                                        lang=settings.OCR_LANGUAGE if hasattr(settings, 'OCR_LANGUAGE') else 'deu',
                                        config='--psm 6'
                                    ).strip()
                                except Exception:
                                    pass
                                
                                image_data = {
                                    "id": f"IMG_{file_obj.id}_p{page_num}_{img_idx}",
                                    "index": img_idx,
                                    "page": page_num,
                                    "format": image_format,
                                    "width_px": image_width,
                                    "height_px": image_height,
                                    "mode": image_mode,
                                    "size_bytes": len(image_bytes),
                                    "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                                    "data_base64": image_base64[:1000] + "..." if len(image_base64) > 1000 else image_base64,
                                    "has_text": bool(ocr_text),
                                    "ocr_text": ocr_text if ocr_text else None,
                                    "quelle": {
                                        **source_info,
                                        "seite": page_num,
                                        "typ": "image",
                                        "position": img_idx
                                    }
                                }
                                
                                images.append(image_data)
                                
                        except ImportError:
                            # PyMuPDF nicht verfügbar, verwende Metadaten nur
                            image_data = {
                                "id": f"IMG_{file_obj.id}_p{page_num}_{img_idx}",
                                "index": img_idx,
                                "page": page_num,
                                "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                                "note": "PyMuPDF nicht installiert - Bilddaten nicht extrahiert",
                                "quelle": {
                                    **source_info,
                                    "seite": page_num,
                                    "typ": "image",
                                    "position": img_idx
                                }
                            }
                            images.append(image_data)
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        return images
    
    def _extract_tables(self, pdf, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrahiert Tabellen aus PDF"""
        tables = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                # Tabellen mit pdfplumber extrahieren
                page_tables = page.extract_tables()
                
                for table_idx, table in enumerate(page_tables):
                    if not table or len(table) < 2:
                        continue
                    
                    # Header (erste Zeile)
                    headers = [str(cell).strip() if cell else f"Spalte_{i+1}" 
                              for i, cell in enumerate(table[0])]
                    
                    # Datenzeilen
                    rows_data = []
                    for row_idx, row in enumerate(table[1:], start=1):
                        row_dict = {}
                        for col_idx, cell in enumerate(row):
                            if col_idx < len(headers):
                                row_dict[headers[col_idx]] = str(cell).strip() if cell else ""
                        
                        if any(value for value in row_dict.values()):
                            rows_data.append(row_dict)
                    
                    if rows_data:
                        table_data = {
                            "table_index": table_idx,
                            "page": page_num,
                            "headers": headers,
                            "rows": rows_data,
                            "row_count": len(rows_data),
                            "column_count": len(headers),
                            "quelle": {
                                **source_info,
                                "seite": page_num,
                                "tabelle": table_idx
                            }
                        }
                        tables.append(table_data)
                        
            except Exception as e:
                continue
        
        return tables
