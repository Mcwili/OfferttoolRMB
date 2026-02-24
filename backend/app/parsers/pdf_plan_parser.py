"""
PDF-Plan-Parser
Verarbeitet Architektur- und HLKS-Pläne (SIA-konform)
Extrahiert Text, Symbole und Strukturen aus PDF-Plänen
"""

from typing import Dict, Any, List, Optional, Tuple
import pdfplumber
from PIL import Image
from io import BytesIO
import re
from app.models.project import ProjectFile
from app.core.config import settings

# Optional imports - might not be installed
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

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None


class PDFPlanParser:
    """Parser für PDF-Pläne (Architektur, HLKS)"""
    
    def __init__(self):
        self.sia_symbols = self._load_sia_symbol_templates()
    
    async def parse(self, file_content: bytes, file_obj: ProjectFile) -> Dict[str, Any]:
        """
        Extrahiert Daten aus PDF-Plan
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
            "termine": []
        }
        
        try:
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                # Jede Seite verarbeiten
                for page_num, page in enumerate(pdf.pages, 1):
                    # Text extrahieren
                    text_data = self._extract_text_from_page(page, source_info, page_num)
                    extracted_data["raeume"].extend(text_data.get("raeume", []))
                    extracted_data["anlagen"].extend(text_data.get("anlagen", []))
                    
                    # PDF-Seite als Bild konvertieren für Symbol-Erkennung
                    if NUMPY_AVAILABLE and CV2_AVAILABLE and PYTESSERACT_AVAILABLE:
                        page_image = page.to_image(resolution=150)
                        if page_image:
                            image_array = np.array(page_image.original)
                            symbol_data = self._extract_symbols_from_image(image_array, source_info, page_num)
                            extracted_data["geraete"].extend(symbol_data.get("geraete", []))
                            extracted_data["anlagen"].extend(symbol_data.get("anlagen", []))
        except Exception as e:
            # Fallback: OCR auf gesamtes PDF
            extracted_data = await self._fallback_ocr_parse(file_content, source_info)
        
        return extracted_data
    
    def _load_sia_symbol_templates(self) -> Dict[str, Any]:
        """
        Lädt SIA-Symbol-Templates (vereinfacht - später durch ML-Modell ersetzen)
        """
        # Basis-Symbole für HLKS (vereinfacht)
        return {
            "lueftungsauslass": {
                "pattern": r"[ZL]A|Zuluft|Abluft",
                "type": "geraet"
            },
            "heizkoerper": {
                "pattern": r"HK|Heizkörper|Radiator",
                "type": "geraet"
            },
            "ventilator": {
                "pattern": r"VENT|Ventilator|Fan",
                "type": "geraet"
            },
            "waermepumpe": {
                "pattern": r"WP|Wärmepumpe|Heat Pump",
                "type": "anlage"
            },
            "lueftungsanlage": {
                "pattern": r"LÜA|Lüftungsanlage|Ventilation",
                "type": "anlage"
            }
        }
    
    def _extract_text_from_page(self, page, source_info: Dict[str, Any], page_num: int) -> Dict[str, Any]:
        """Extrahiert Text aus PDF-Seite"""
        extracted = {
            "raeume": [],
            "anlagen": []
        }
        
        text = page.extract_text()
        if not text:
            return extracted
        
        # Raumbezeichnungen erkennen
        # Pattern: Raum-Nummern wie "R.01", "Raum 101", "R101", etc.
        raum_patterns = [
            r"R\.?\s*(\d+[A-Z]?)",
            r"Raum\s+(\d+[A-Z]?)",
            r"R\s*(\d+[A-Z]?)",
            r"(\d+\.\d+)"  # Format wie 1.01, 2.05
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
                    "seite": page_num,
                    "typ": "text_extraktion"
                }
            }
            extracted["raeume"].append(raum)
        
        # Maßangaben extrahieren (Flächen)
        flaeche_patterns = [
            r"(\d+[,\.]\d+)\s*m²",
            r"(\d+[,\.]\d+)\s*m2",
            r"Fläche[:\s]+(\d+[,\.]\d+)"
        ]
        
        for pattern in flaeche_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                flaeche_str = match.group(1).replace(',', '.')
                try:
                    flaeche = float(flaeche_str)
                    # Versuche Fläche einem Raum zuzuordnen (vorherige Zeile)
                    # Vereinfacht - könnte verbessert werden
                    if extracted["raeume"]:
                        last_raum = extracted["raeume"][-1]
                        if "flaeche_m2" not in last_raum:
                            last_raum["flaeche_m2"] = flaeche
                except ValueError:
                    pass
        
        # Anlagen-Bezeichnungen erkennen
        anlagen_patterns = [
            r"(LÜA|Lüftungsanlage|Ventilation)\s*(\d+)?",
            r"(HK|Heizungsanlage|Heating)\s*(\d+)?",
            r"(WP|Wärmepumpe|Heat Pump)\s*(\d+)?"
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
                        "seite": page_num,
                        "typ": "text_extraktion"
                    }
                }
                extracted["anlagen"].append(anlage)
        
        return extracted
    
    def _extract_symbols_from_image(self, image_array: Any, source_info: Dict[str, Any], page_num: int) -> Dict[str, Any]:
        """Extrahiert Symbole aus Bild mit Computer Vision"""
        extracted = {
            "geraete": [],
            "anlagen": []
        }
        
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE or not PYTESSERACT_AVAILABLE:
            return extracted
        
        # Bildvorverarbeitung
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        # OCR auf Bild anwenden für Text-Erkennung
        pil_image = Image.fromarray(image_array)
        ocr_text = pytesseract.image_to_string(
            pil_image,
            lang=settings.OCR_LANGUAGE,
            config='--psm 6'
        )
        
        # Symbole anhand von Text-Mustern erkennen
        for symbol_name, symbol_info in self.sia_symbols.items():
            pattern = symbol_info["pattern"]
            matches = re.finditer(pattern, ocr_text, re.IGNORECASE)
            
            for match in matches:
                entity = {
                    "id": f"{symbol_info['type'].upper()}_{symbol_name}_{page_num}_{match.start()}",
                    "typ": symbol_name,
                    "name": match.group(0),
                    "quelle": {
                        **source_info,
                        "seite": page_num,
                        "typ": "symbol_erkennung",
                        "position": match.start()
                    }
                }
                
                if symbol_info["type"] == "geraet":
                    extracted["geraete"].append(entity)
                elif symbol_info["type"] == "anlage":
                    extracted["anlagen"].append(entity)
        
        # Template-Matching für einfache geometrische Symbole
        # (vereinfacht - später durch ML-Modell ersetzen)
        circles = self._detect_circles(gray)
        rectangles = self._detect_rectangles(gray)
        
        # Kreise könnten Lüftungsauslässe sein
        for idx, circle in enumerate(circles[:10]):  # Maximal 10
            geraet = {
                "id": f"GER_CIRCLE_{page_num}_{idx}",
                "typ": "Lüftungsauslass (erkannt)",
                "quelle": {
                    **source_info,
                    "seite": page_num,
                    "typ": "geometrie_erkennung",
                    "form": "kreis"
                }
            }
            extracted["geraete"].append(geraet)
        
        return extracted
    
    def _detect_circles(self, gray_image: Any) -> List[Tuple[int, int, int]]:
        """Erkennt Kreise im Bild (vereinfacht)"""
        circles = []
        if not CV2_AVAILABLE or not NUMPY_AVAILABLE:
            return circles
        try:
            # HoughCircles für Kreis-Erkennung
            detected = cv2.HoughCircles(
                gray_image,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=50,
                param1=50,
                param2=30,
                minRadius=5,
                maxRadius=50
            )
            
            if detected is not None:
                detected = np.round(detected[0, :]).astype("int")
                circles = [(x, y, r) for (x, y, r) in detected]
        except Exception:
            pass
        
        return circles
    
    def _detect_rectangles(self, gray_image: Any) -> List[Tuple[int, int, int, int]]:
        """Erkennt Rechtecke im Bild (vereinfacht)"""
        rectangles = []
        if not CV2_AVAILABLE:
            return rectangles
        try:
            # Canny Edge Detection
            edges = cv2.Canny(gray_image, 50, 150)
            
            # Konturen finden
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Rechteck approximieren
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    rectangles.append((x, y, w, h))
        except Exception:
            pass
        
        return rectangles
    
    async def _fallback_ocr_parse(self, file_content: bytes, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: OCR auf gesamtes PDF anwenden"""
        extracted_data = {
            "raeume": [],
            "anlagen": [],
            "geraete": [],
            "anforderungen": [],
            "termine": []
        }
        
        # PDF zu Bild konvertieren und OCR anwenden
        # Vereinfacht - könnte verbessert werden
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(file_content, dpi=200)
            
            if not PYTESSERACT_AVAILABLE:
                return extracted_data
                
            for page_num, image in enumerate(images, 1):
                ocr_text = pytesseract.image_to_string(
                    image,
                    lang=settings.OCR_LANGUAGE,
                    config='--psm 6'
                )
                
                # Text analysieren wie in _extract_text_from_page
                text_data = self._extract_text_from_page_text(ocr_text, source_info, page_num)
                extracted_data["raeume"].extend(text_data.get("raeume", []))
                extracted_data["anlagen"].extend(text_data.get("anlagen", []))
        except ImportError:
            # pdf2image nicht verfügbar - überspringen
            pass
        except Exception:
            pass
        
        return extracted_data
    
    def _extract_text_from_page_text(self, text: str, source_info: Dict[str, Any], page_num: int) -> Dict[str, Any]:
        """Extrahiert Entitäten aus OCR-Text (ähnlich wie _extract_text_from_page)"""
        extracted = {
            "raeume": [],
            "anlagen": []
        }
        
        # Gleiche Logik wie _extract_text_from_page, aber mit String statt Page-Objekt
        raum_patterns = [
            r"R\.?\s*(\d+[A-Z]?)",
            r"Raum\s+(\d+[A-Z]?)",
            r"R\s*(\d+[A-Z]?)",
            r"(\d+\.\d+)"
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
                    "seite": page_num,
                    "typ": "ocr_fallback"
                }
            }
            extracted["raeume"].append(raum)
        
        return extracted
