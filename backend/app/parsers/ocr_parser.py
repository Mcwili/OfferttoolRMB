"""
OCR-Parser
Verwendet Tesseract OCR und OpenCV für gescannte Dokumente
"""

from typing import Dict, Any, List, Optional
from PIL import Image
from io import BytesIO
import re
from app.models.project import ProjectFile
from app.core.config import settings

# Optional imports - might not be installed
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


class OCRParser:
    """Parser für gescannte Bilder/PDFs mit OCR"""
    
    async def parse(self, file_content: bytes, file_obj: ProjectFile) -> Dict[str, Any]:
        """
        Extrahiert Text aus Bilddatei mittels OCR mit Layout-Erhaltung
        Returns: Dict mit extrahierten Entitäten
        """
        source_info = {
            "datei": file_obj.original_filename,
            "datei_id": file_obj.id,
            "upload_am": file_obj.upload_date.isoformat() if file_obj.upload_date else None
        }
        
        # Prüfe ob erforderliche Module verfügbar sind
        if not PYTESSERACT_AVAILABLE:
            raise ValueError("pytesseract ist nicht installiert. Bitte installieren Sie es mit: pip install pytesseract")
        if not CV2_AVAILABLE:
            raise ValueError("opencv-python ist nicht installiert. Bitte installieren Sie es mit: pip install opencv-python")
        if not NUMPY_AVAILABLE:
            raise ValueError("numpy ist nicht installiert. Bitte installieren Sie es mit: pip install numpy")
        
        # Bild laden
        image = Image.open(BytesIO(file_content))
        
        # Bildvorverarbeitung mit OpenCV
        processed_image = self._preprocess_image(image)
        
        extracted_data = {
            "raeume": [],
            "anlagen": [],
            "geraete": [],
            "anforderungen": [],
            "termine": []
        }
        
        # OCR mit Layout-Erhaltung (PSM 6 für einheitlichen Block, PSM 4 für einzelne Spalten)
        # Versuche verschiedene Modi für bessere Ergebnisse
        text_blocks = []
        
        # Modus 1: Einheitlicher Textblock
        text_block = pytesseract.image_to_string(
            processed_image,
            lang=settings.OCR_LANGUAGE,
            config='--psm 6'
        )
        text_blocks.append(text_block)
        
        # Modus 2: Einzelne Textblöcke (für Tabellen besser)
        text_blocks_data = pytesseract.image_to_data(
            processed_image,
            lang=settings.OCR_LANGUAGE,
            config='--psm 6',
            output_type=pytesseract.Output.DICT
        )
        
        # Tabellen erkennen und extrahieren
        tables = self._extract_tables_from_ocr(processed_image, text_blocks_data)
        if tables:
            table_data = self._parse_tables(tables, source_info)
            extracted_data["raeume"].extend(table_data.get("raeume", []))
            extracted_data["geraete"].extend(table_data.get("geraete", []))
            extracted_data["anlagen"].extend(table_data.get("anlagen", []))
        
        # Text aus allen Blöcken zusammenführen
        full_text = "\n".join(text_blocks)
        
        # Entitäten aus Text extrahieren
        text_entities = self._extract_entities_from_text(full_text, source_info)
        extracted_data["raeume"].extend(text_entities.get("raeume", []))
        extracted_data["anlagen"].extend(text_entities.get("anlagen", []))
        extracted_data["anforderungen"].extend(text_entities.get("anforderungen", []))
        
        return extracted_data
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Bildvorverarbeitung für bessere OCR-Ergebnisse"""
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            # Fallback: Keine Vorverarbeitung möglich
            return image
            
        # Zu OpenCV-Format konvertieren
        img_array = np.array(image)
        
        # Graustufen konvertieren
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Rauschen reduzieren
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Kontrast erhöhen
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Binarisierung für bessere Text-Erkennung
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Zu PIL zurückkonvertieren
        return Image.fromarray(binary)
    
    def _extract_tables_from_ocr(self, image: Image.Image, ocr_data: Dict) -> List[List[List[str]]]:
        """Erkennt Tabellen-Struktur aus OCR-Daten"""
        tables = []
        
        # Gruppiere Text nach Zeilen basierend auf Y-Koordinaten
        lines = {}
        for i, text in enumerate(ocr_data.get('text', [])):
            if text.strip():
                y = ocr_data['top'][i]
                line_key = y // 20  # Gruppiere ähnliche Y-Koordinaten
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'width': ocr_data['width'][i]
                })
        
        # Sortiere Zeilen nach Y-Koordinate
        sorted_lines = sorted(lines.items())
        
        # Erkenne Tabellen-Struktur (mehrere Spalten)
        table = []
        for _, line_items in sorted_lines:
            # Sortiere Items nach X-Koordinate
            sorted_items = sorted(line_items, key=lambda x: x['left'])
            
            # Prüfe ob es wie eine Tabellenzeile aussieht (mehrere Spalten)
            if len(sorted_items) >= 2:
                row = [item['text'] for item in sorted_items]
                table.append(row)
        
        if table:
            tables.append(table)
        
        return tables
    
    def _parse_tables(self, tables: List[List[List[str]]], source_info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Parst Tabellen und extrahiert Entitäten"""
        extracted = {
            "raeume": [],
            "geraete": [],
            "anlagen": []
        }
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            # Erste Zeile als Header verwenden
            header = table[0]
            header_lower = [h.lower() for h in header]
            
            # Raumliste erkennen
            if any(kw in " ".join(header_lower) for kw in ["raum", "room", "fläche", "flaeche"]):
                for row_idx, row in enumerate(table[1:], start=1):
                    if len(row) < len(header):
                        continue
                    
                    raum_data = {}
                    for col_idx, header_cell in enumerate(header_lower):
                        if col_idx < len(row):
                            if any(kw in header_cell for kw in ["raum", "room", "nummer"]):
                                raum_data["name"] = row[col_idx]
                            elif any(kw in header_cell for kw in ["fläche", "flaeche", "m²"]):
                                try:
                                    raum_data["flaeche_m2"] = float(row[col_idx].replace(",", "."))
                                except ValueError:
                                    pass
                            elif any(kw in header_cell for kw in ["nutzung", "art"]):
                                raum_data["nutzungsart"] = row[col_idx]
                    
                    if raum_data.get("name"):
                        raum = {
                            "id": f"Raum_{raum_data['name'].replace(' ', '_')}_{table_idx}_{row_idx}",
                            "name": raum_data["name"],
                            "flaeche_m2": raum_data.get("flaeche_m2"),
                            "nutzungsart": raum_data.get("nutzungsart"),
                            "quelle": {
                                **source_info,
                                "tabelle": table_idx,
                                "zeile": row_idx,
                                "typ": "ocr_tabelle"
                            }
                        }
                        extracted["raeume"].append(raum)
            
            # Geräteliste erkennen
            elif any(kw in " ".join(header_lower) for kw in ["geraet", "equipment", "gerät", "typ"]):
                for row_idx, row in enumerate(table[1:], start=1):
                    if len(row) < len(header):
                        continue
                    
                    geraet_data = {}
                    for col_idx, header_cell in enumerate(header_lower):
                        if col_idx < len(row):
                            if any(kw in header_cell for kw in ["geraet", "equipment", "gerät", "name"]):
                                geraet_data["name"] = row[col_idx]
                            elif any(kw in header_cell for kw in ["typ", "type"]):
                                geraet_data["typ"] = row[col_idx]
                            elif any(kw in header_cell for kw in ["leistung", "power", "kw"]):
                                try:
                                    geraet_data["leistung_kw"] = float(row[col_idx].replace(",", "."))
                                except ValueError:
                                    pass
                    
                    if geraet_data.get("name") or geraet_data.get("typ"):
                        geraet = {
                            "id": f"GER_{table_idx}_{row_idx}",
                            "typ": geraet_data.get("typ") or geraet_data.get("name"),
                            "name": geraet_data.get("name"),
                            "leistung_kw": geraet_data.get("leistung_kw"),
                            "quelle": {
                                **source_info,
                                "tabelle": table_idx,
                                "zeile": row_idx,
                                "typ": "ocr_tabelle"
                            }
                        }
                        extracted["geraete"].append(geraet)
        
        return extracted
    
    def _extract_entities_from_text(self, text: str, source_info: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Extrahiert Entitäten aus OCR-Text"""
        extracted = {
            "raeume": [],
            "anlagen": [],
            "anforderungen": []
        }
        
        # Raumbezeichnungen erkennen
        raum_patterns = [
            r"R\.?\s*(\d+[A-Z]?)",
            r"Raum\s+(\d+[A-Z]?)",
            r"R\s*(\d+[A-Z]?)"
        ]
        
        raum_matches = set()
        for pattern in raum_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                raum_matches.add(match.group(1) if match.groups() else match.group(0))
        
        for raum_nr in raum_matches:
            raum = {
                "id": f"Raum_{raum_nr.replace('.', '_')}",
                "name": f"Raum {raum_nr}",
                "nummer": raum_nr,
                "quelle": {
                    **source_info,
                    "typ": "ocr_text"
                }
            }
            extracted["raeume"].append(raum)
        
        # Anlagen-Bezeichnungen
        anlagen_patterns = [
            r"(LÜA|Lüftungsanlage|Ventilation)\s*(\d+)?",
            r"(HK|Heizungsanlage|Heating)\s*(\d+)?"
        ]
        
        for pattern in anlagen_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                anlage_name = match.group(1)
                anlage_nr = match.group(2) if len(match.groups()) > 1 else ""
                
                anlage = {
                    "id": f"ANL_{anlage_name.replace(' ', '_')}_{anlage_nr or '1'}",
                    "typ": anlage_name,
                    "name": f"{anlage_name} {anlage_nr}".strip(),
                    "quelle": {
                        **source_info,
                        "typ": "ocr_text"
                    }
                }
                extracted["anlagen"].append(anlage)
        
        # Anforderungen erkennen
        requirement_keywords = [
            "anforderung", "vorgabe", "muss", "soll", "erforderlich",
            "luftwechsel", "temperatur", "feuchtigkeit"
        ]
        
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            if any(kw in line.lower() for kw in requirement_keywords):
                anforderung = {
                    "id": f"REQ_OCR_{line_idx:04d}",
                    "beschreibung": line.strip(),
                    "kategorie": "allgemein",
                    "prioritaet": "mittel",
                    "quelle": {
                        **source_info,
                        "zeile": line_idx,
                        "typ": "ocr_text"
                    }
                }
                extracted["anforderungen"].append(anforderung)
        
        return extracted
