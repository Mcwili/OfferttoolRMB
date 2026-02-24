"""
AI Service für OpenAI API-Aufrufe
Verwendet OpenAI API für rechtliche Dokumentenanalyse
"""

from typing import Dict, Any, Optional
import json
import re
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from app.models.settings import AppSettings

# Optional import - openai might not be installed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger(__name__)


class AIService:
    """Service für AI-Operationen mit OpenAI"""
    
    def __init__(self, db: Session):
        if not OPENAI_AVAILABLE:
            raise ValueError("openai ist nicht installiert. Bitte installieren Sie es mit: pip install openai")
        self.db = db
        self._client: Optional[OpenAI] = None
        self._executor = ThreadPoolExecutor(max_workers=3)
    
    def _get_client(self) -> OpenAI:
        """Initialisiert OpenAI Client mit API-Key aus Einstellungen"""
        if self._client is None:
            api_key = self._get_api_key()
            if not api_key:
                raise ValueError("OpenAI API-Key nicht gefunden. Bitte in Einstellungen konfigurieren.")
            self._client = OpenAI(api_key=api_key)
        return self._client
    
    def _get_api_key(self) -> Optional[str]:
        """Lädt OpenAI API-Key aus Einstellungen"""
        setting = self.db.query(AppSettings).filter(AppSettings.key == "chatgpt_api_key").first()
        return setting.value if setting else None
    
    def _call_openai_api(self, client: OpenAI, system_message: str, user_message: str) -> Any:
        """
        Ruft die OpenAI API synchron auf (wird in Thread Pool ausgeführt)
        
        Args:
            client: OpenAI Client
            system_message: System-Nachricht
            user_message: User-Nachricht
            
        Returns:
            OpenAI API Response
        """
        try:
            logger.info(f"Führe OpenAI API-Aufruf aus (Thread Pool)")
            logger.debug(f"System Message: {len(system_message)} Zeichen")
            logger.debug(f"User Message: {len(user_message)} Zeichen")
            
            # Schätze Token-Anzahl (ungefähr 4 Zeichen pro Token)
            estimated_tokens = (len(system_message) + len(user_message)) // 4
            logger.info(f"Geschätzte Token-Anzahl: {estimated_tokens}")
            
            # Prüfe Token-Limit (gpt-4o hat ~128k Context Window)
            if estimated_tokens > 100000:  # Sicherheitspuffer
                logger.warning(f"Text ist sehr lang ({estimated_tokens} geschätzte Tokens). Möglicherweise wird das Limit überschritten.")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=16000,
                response_format={"type": "json_object"},
                timeout=300.0  # 5 Minuten Timeout
            )
            
            logger.info("OpenAI API-Aufruf erfolgreich abgeschlossen")
            return response
            
        except Exception as e:
            logger.error(f"Fehler im OpenAI API-Aufruf (Thread Pool): {type(e).__name__}: {str(e)}", exc_info=True)
            raise
    
    async def analyze_legal_documents(self, prompt: str, full_text: str) -> Dict[str, Any]:
        """
        Analysiert Dokumente mit OpenAI API für rechtliche Prüfung
        
        Args:
            prompt: Der Prompt für die Analyse (inkl. Anweisungen)
            full_text: Der vollständige Text aus allen Dokumenten
            
        Returns:
            Dict mit strukturierten Analyse-Ergebnissen:
            {
                "allgemeine_einschaetzung": str,
                "kritische_punkte": [
                    {
                        "nummer": int,
                        "titel": str,
                        "zitat": str,
                        "beurteilung": str,
                        "risiko_rating": str,  # "rot", "orange", "grün"
                        "empfehlung": str
                    }
                ]
            }
        """
        client = self._get_client()
        
        # Vollständige Nachricht zusammenstellen
        system_message = prompt
        user_message = f"""Bitte analysiere die folgenden Offertunterlagen ABSCHLIESSEND und VOLLSTÄNDIG.

WICHTIG: Identifiziere ALLE problematischen Punkte, nicht nur eine Auswahl. Gehe systematisch durch alle Dokumente und alle Absätze. Erwarte 20-100+ kritische Punkte für umfangreiche Verträge. Jeder problematische Punkt muss einzeln aufgeführt werden.

Die Unterlagen:
{full_text}"""
        
        try:
            logger.info("Starte OpenAI API-Aufruf für rechtliche Prüfung")
            logger.info(f"System Message Länge: {len(system_message)} Zeichen")
            logger.info(f"User Message Länge: {len(user_message)} Zeichen")
            
            # API-Aufruf in Thread Pool verschieben, um Event Loop nicht zu blockieren
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                self._call_openai_api,
                client,
                system_message,
                user_message
            )
            
            if not response or not response.choices:
                raise ValueError("OpenAI API hat keine Antwort zurückgegeben")
            
            ai_response = response.choices[0].message.content
            if not ai_response:
                raise ValueError("OpenAI API-Antwort ist leer")
            
            logger.info(f"OpenAI API-Antwort erhalten: {len(ai_response)} Zeichen")
            logger.debug(f"Erste 500 Zeichen der Antwort: {ai_response[:500]}")
            
            # Parse die AI-Response als JSON
            parsed_result = self._parse_json_response(ai_response)
            logger.info(f"JSON erfolgreich geparst: {len(parsed_result.get('kritische_punkte', []))} Punkte")
            return parsed_result
            
        except asyncio.TimeoutError:
            logger.error("OpenAI API-Aufruf hat Timeout erreicht (5 Minuten)")
            raise ValueError("OpenAI API-Aufruf hat zu lange gedauert. Bitte versuchen Sie es erneut oder reduzieren Sie die Textmenge.")
        except ValueError as e:
            logger.error(f"ValueError bei AI-Analyse: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei AI-Analyse: {type(e).__name__}: {str(e)}", exc_info=True)
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Spezifische Fehlerbehandlung für OpenAI-Fehler
            if "timeout" in error_msg.lower() or "TimeoutError" in error_type:
                raise ValueError("OpenAI API-Aufruf hat zu lange gedauert. Bitte versuchen Sie es erneut oder reduzieren Sie die Textmenge.")
            elif "RateLimitError" in error_type or "rate_limit" in error_msg.lower():
                raise ValueError("OpenAI API Rate Limit erreicht. Bitte versuchen Sie es später erneut.")
            elif "AuthenticationError" in error_type or "invalid_api_key" in error_msg.lower():
                raise ValueError("OpenAI API-Key ist ungültig. Bitte überprüfen Sie die Einstellungen.")
            elif "InvalidRequestError" in error_type or "context_length_exceeded" in error_msg.lower():
                raise ValueError("Der Text ist zu lang für die OpenAI API. Bitte reduzieren Sie die Textmenge.")
            else:
                raise ValueError(f"Fehler bei AI-Analyse ({error_type}): {error_msg}")
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parsed die AI-Response als JSON
        
        Erwartetes JSON-Format:
        {
          "allgemeine_einschaetzung": "...",
          "kritische_punkte": [
            {
              "nummer": 1,
              "titel": "...",
              "zitat": "...",
              "beurteilung": "...",
              "risiko_rating": "rot|orange|grün",
              "empfehlung": "..."
            }
          ]
        }
        """
        try:
            # Entferne mögliche Markdown-Code-Blöcke (```json ... ```)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                # Entferne Code-Block-Markierungen
                lines = cleaned_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines)
            
            # Parse JSON
            result = json.loads(cleaned_text)
            
            # Validierung und Normalisierung
            if not isinstance(result, dict):
                raise ValueError("Response ist kein JSON-Objekt")
            
            # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
            if "allgemeine_einschaetzung" not in result:
                result["allgemeine_einschaetzung"] = ""
            
            if "kritische_punkte" not in result:
                result["kritische_punkte"] = []
            
            # Validiere und normalisiere kritische Punkte
            validated_punkte = []
            for punkt in result.get("kritische_punkte", []):
                if not isinstance(punkt, dict):
                    continue
                
                validated_punkt = {
                    "nummer": punkt.get("nummer", len(validated_punkte) + 1),
                    "titel": str(punkt.get("titel", "")).strip(),
                    "zitat": str(punkt.get("zitat", "")).strip(),
                    "beurteilung": str(punkt.get("beurteilung", "")).strip(),
                    "risiko_rating": str(punkt.get("risiko_rating", "")).lower().strip(),
                    "empfehlung": str(punkt.get("empfehlung", "")).strip(),
                    "quelle_datei": str(punkt.get("quelle_datei", "")).strip() if punkt.get("quelle_datei") else None,
                    "quelle_paragraph": punkt.get("quelle_paragraph") if punkt.get("quelle_paragraph") is not None else None
                }
                
                # Validiere risiko_rating
                if validated_punkt["risiko_rating"] not in ["rot", "orange", "grün"]:
                    # Fallback: versuche aus Text zu erkennen
                    rating_text = validated_punkt["risiko_rating"]
                    if "rot" in rating_text.lower():
                        validated_punkt["risiko_rating"] = "rot"
                    elif "orange" in rating_text.lower():
                        validated_punkt["risiko_rating"] = "orange"
                    elif "grün" in rating_text.lower() or "gruen" in rating_text.lower():
                        validated_punkt["risiko_rating"] = "grün"
                    else:
                        validated_punkt["risiko_rating"] = "orange"  # Default
                
                # Nur hinzufügen, wenn mindestens Titel vorhanden
                if validated_punkt["titel"]:
                    validated_punkte.append(validated_punkt)
            
            result["kritische_punkte"] = validated_punkte
            
            return result
            
        except json.JSONDecodeError as e:
            # Fallback: Versuche Text-Parsing wenn JSON fehlschlägt
            raise ValueError(f"Ungültiges JSON-Format in AI-Response: {str(e)}\nResponse: {response_text[:500]}")
        except Exception as e:
            raise ValueError(f"Fehler beim Parsen der AI-Response: {str(e)}")
    
    async def analyze_for_question_list(self, prompt: str, full_text: str) -> Dict[str, Any]:
        """
        Analysiert Dokumente mit OpenAI API für Frageliste-Generierung
        
        Args:
            prompt: Der Prompt für die Analyse (inkl. Anweisungen)
            full_text: Der vollständige Text aus allen Dokumenten
            
        Returns:
            Dict mit strukturierten Frageliste-Ergebnissen:
            {
                "zusammenfassung": str,
                "fragen": [
                    {
                        "nummer": int,
                        "kategorie": str,
                        "frage": str,
                        "begruendung": str,
                        "prioritaet": str  # "hoch", "mittel", "niedrig"
                    }
                ]
            }
        """
        client = self._get_client()
        
        # Vollständige Nachricht zusammenstellen
        system_message = prompt
        user_message = f"""Bitte analysiere die folgenden Projektunterlagen systematisch und erstelle eine strukturierte Frageliste.

Die Unterlagen:
{full_text}"""
        
        try:
            logger.info("Starte OpenAI API-Aufruf für Frageliste")
            logger.info(f"System Message Länge: {len(system_message)} Zeichen")
            logger.info(f"User Message Länge: {len(user_message)} Zeichen")
            
            # API-Aufruf in Thread Pool verschieben, um Event Loop nicht zu blockieren
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                self._call_openai_api,
                client,
                system_message,
                user_message
            )
            
            if not response or not response.choices:
                raise ValueError("OpenAI API hat keine Antwort zurückgegeben")
            
            ai_response = response.choices[0].message.content
            if not ai_response:
                raise ValueError("OpenAI API-Antwort ist leer")
            
            logger.info(f"OpenAI API-Antwort erhalten: {len(ai_response)} Zeichen")
            logger.debug(f"Erste 500 Zeichen der Antwort: {ai_response[:500]}")
            
            # Parse die AI-Response als JSON
            parsed_result = self._parse_question_list_json(ai_response)
            logger.info(f"JSON erfolgreich geparst: {len(parsed_result.get('fragen', []))} Fragen")
            return parsed_result
            
        except asyncio.TimeoutError:
            logger.error("OpenAI API-Aufruf für Frageliste hat Timeout erreicht (5 Minuten)")
            raise ValueError("OpenAI API-Aufruf hat zu lange gedauert. Bitte versuchen Sie es erneut oder reduzieren Sie die Textmenge.")
        except ValueError as e:
            logger.error(f"ValueError bei AI-Analyse für Frageliste: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei AI-Analyse für Frageliste: {type(e).__name__}: {str(e)}", exc_info=True)
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Spezifische Fehlerbehandlung für OpenAI-Fehler
            if "timeout" in error_msg.lower() or "TimeoutError" in error_type:
                raise ValueError("OpenAI API-Aufruf hat zu lange gedauert. Bitte versuchen Sie es erneut oder reduzieren Sie die Textmenge.")
            elif "RateLimitError" in error_type or "rate_limit" in error_msg.lower():
                raise ValueError("OpenAI API Rate Limit erreicht. Bitte versuchen Sie es später erneut.")
            elif "AuthenticationError" in error_type or "invalid_api_key" in error_msg.lower():
                raise ValueError("OpenAI API-Key ist ungültig. Bitte überprüfen Sie die Einstellungen.")
            elif "InvalidRequestError" in error_type or "context_length_exceeded" in error_msg.lower():
                raise ValueError("Der Text ist zu lang für die OpenAI API. Bitte reduzieren Sie die Textmenge.")
            else:
                raise ValueError(f"Fehler bei AI-Analyse ({error_type}): {error_msg}")
    
    def _parse_question_list_json(self, response_text: str) -> Dict[str, Any]:
        """
        Parsed die AI-Response als JSON für Frageliste
        
        Erwartetes JSON-Format:
        {
          "zusammenfassung": "...",
          "fragen": [
            {
              "nummer": 1,
              "kategorie": "Leistungsumfang",
              "frage": "...",
              "begruendung": "...",
              "prioritaet": "hoch|mittel|niedrig"
            }
          ]
        }
        """
        try:
            # Entferne mögliche Markdown-Code-Blöcke (```json ... ```)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                # Entferne Code-Block-Markierungen
                lines = cleaned_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines)
            
            # Parse JSON
            result = json.loads(cleaned_text)
            
            # Validierung und Normalisierung
            if not isinstance(result, dict):
                raise ValueError("Response ist kein JSON-Objekt")
            
            # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
            if "zusammenfassung" not in result:
                result["zusammenfassung"] = ""
            
            if "fragen" not in result:
                result["fragen"] = []
            
            # Validiere und normalisiere Fragen
            validated_fragen = []
            for frage in result.get("fragen", []):
                if not isinstance(frage, dict):
                    continue
                
                validated_frage = {
                    "nummer": frage.get("nummer", len(validated_fragen) + 1),
                    "kategorie": str(frage.get("kategorie", "")).strip(),
                    "frage": str(frage.get("frage", "")).strip(),
                    "begruendung": str(frage.get("begruendung", "")).strip(),
                    "prioritaet": str(frage.get("prioritaet", "")).lower().strip()
                }
                
                # Validiere prioritaet
                if validated_frage["prioritaet"] not in ["hoch", "mittel", "niedrig"]:
                    # Fallback: versuche aus Text zu erkennen
                    prioritaet_text = validated_frage["prioritaet"]
                    if "hoch" in prioritaet_text.lower() or "high" in prioritaet_text.lower():
                        validated_frage["prioritaet"] = "hoch"
                    elif "niedrig" in prioritaet_text.lower() or "low" in prioritaet_text.lower():
                        validated_frage["prioritaet"] = "niedrig"
                    else:
                        validated_frage["prioritaet"] = "mittel"  # Default
                
                # Nur hinzufügen, wenn mindestens Frage vorhanden
                if validated_frage["frage"]:
                    validated_fragen.append(validated_frage)
            
            result["fragen"] = validated_fragen
            
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Ungültiges JSON-Format in AI-Response: {str(e)}\nResponse: {response_text[:500]}")
        except Exception as e:
            raise ValueError(f"Fehler beim Parsen der AI-Response: {str(e)}")
