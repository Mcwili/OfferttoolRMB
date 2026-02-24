"""
Question List Service
Orchestriert die Frageliste-Generierung: AI-Analyse und Word-Generierung
"""

from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import re
import uuid
from app.models.project import Project, ProjectData, ProjectFile
from app.models.settings import AppSettings
from app.services.storage import StorageService

# Optional imports - might fail if dependencies are missing
try:
    from app.services.ai_service import AIService
    AI_SERVICE_AVAILABLE = True
except Exception:
    AI_SERVICE_AVAILABLE = False
    AIService = None

try:
    from app.reporters.question_list_reporter import QuestionListReporter
    QUESTION_LIST_REPORTER_AVAILABLE = True
except Exception:
    QUESTION_LIST_REPORTER_AVAILABLE = False
    QuestionListReporter = None

logger = logging.getLogger(__name__)


class QuestionListService:
    """Service für Frageliste-Generierung"""
    
    # Standard-Prompt als Fallback
    DEFAULT_PROMPT = """Du bist ein erfahrener Schweizer Ingenieurberater im Bereich HLKS und Fachkoordination mit sehr guter Kenntnis der SIA-Ordnungen und der üblichen Honoraroffertenpraxis.

Deine Aufgabe ist es, die zur Verfügung gestellten Projektunterlagen kritisch zu prüfen mit dem Ziel, eine Honorarofferte zu erstellen. Die Offerte kann nur erstellt werden, wenn alle notwendigen Grundlagen klar, widerspruchsfrei und ausreichend definiert sind.

Gehe strukturiert vor und prüfe die Unterlagen insbesondere in folgenden Punkten:

Leistungsumfang
Prüfe, ob der Leistungsumfang klar beschrieben ist oder ob er Interpretationsspielraum enthält.
Erkenne fehlende, unklare oder widersprüchliche Leistungsbeschriebe.
Beurteile, ob der Umfang realistisch zu den angegebenen Projektzielen passt.

Gewerke
Prüfe, für welche Gewerke Leistungen erwartet werden.
Berücksichtige mindestens folgende Gewerke:
Heizung
Kälte
Sanitär
Lüftung
Sprinkler
Fachkoordination
Andere Gewerke, falls implizit oder explizit erwähnt

Identifiziere fehlende Zuordnungen, Mehrdeutigkeiten oder implizite Annahmen.
Prüfe, ob Zusatzgewerke eindeutig als solche deklariert sind.

SIA-Phasen
Prüfe für jedes Gewerk, welche SIA-Phasen beauftragt sind oder erwartet werden.
Berücksichtige folgende Phasen:
SIA 31 Vorprojekt
SIA 32 Bauprojekt
SIA 33 Bewilligung
SIA 41 Ausschreibung
SIA 51 Ausführungsplanung
SIA 52 Realisierung
SIA 53 Abnahmen

Identifiziere fehlende Phasenangaben, widersprüchliche Aussagen oder unklare Abgrenzungen.
Prüfe, ob Phasen ausgelassen wurden und ob dies begründet ist.

Zusatzleistungen
Prüfe, ob Zusatzleistungen klar als solche definiert sind oder implizit erwartet werden.
Typische Zusatzleistungen können sein:
Sprinklerplanung
Erweiterte Fachbauleitung
Leistungen für weitere Gewerke
Besondere Nachweise, Simulationen, Studien oder Konzepte

Zeige auf, wo Zusatzleistungen vermischt oder nicht sauber abgegrenzt sind.

Projektgrundlagen
Prüfe, ob folgende Grundlagen ausreichend vorhanden sind oder fehlen:
Projektbeschrieb
Nutzungsangaben
Flächen, Volumen oder Kennwerte
Qualitäts- und Nachhaltigkeitsanforderungen
Schnittstellen zu anderen Planern
Terminvorgaben

Risiken und Unklarheiten
Identifiziere Risiken für den Auftragnehmer aufgrund unklarer oder fehlender Angaben.
Beurteile, wo Nachforderungen, Mehraufwand oder Streitpotenzial entstehen können.

Ergebnis

Erstelle als Resultat eine strukturierte Frageliste an den Auftraggeber.
Die Frageliste soll:
klar und präzise formuliert sein
nach Themen gegliedert sein
nur offene oder unklare Punkte enthalten
keine Annahmen treffen
keine Lösungen vorschlagen

Ziel ist es, mit dieser Frageliste alle offenen Punkte zu klären, damit eine transparente, faire und belastbare Honorarofferte erstellt werden kann.

Ausgabeformat - WICHTIG: JSON-Format
Deine Antwort MUSS IMMER als gültiges JSON-Objekt erfolgen. Kein zusätzlicher Text, keine Erklärungen, nur das JSON-Objekt.

Das JSON-Format ist exakt wie folgt definiert:
{
  "zusammenfassung": "Kurze Zusammenfassung der offenen Punkte und der wichtigsten Fragen",
  "fragen": [
    {
      "nummer": 1,
      "kategorie": "Leistungsumfang",
      "frage": "Ist der Leistungsumfang für die HLKS-Planung klar definiert?",
      "begruendung": "Im Dokument wird nur allgemein von 'Planungsleistungen' gesprochen, ohne konkrete Aufgaben zu benennen.",
      "prioritaet": "hoch"
    }
  ]
}

Wichtige Regeln für JSON-Ausgabe:
- Die Antwort muss ein gültiges JSON-Objekt sein
- "prioritaet" muss exakt einer der Werte sein: "hoch", "mittel" oder "niedrig"
- "nummer" muss eine fortlaufende Zahl sein, beginnend bei 1
- "kategorie" sollte eine der folgenden sein: "Leistungsumfang", "Gewerke", "SIA-Phasen", "Zusatzleistungen", "Projektgrundlagen", "Risiken und Unklarheiten" oder eine passende andere Kategorie
- Jede Frage in "fragen" muss alle Felder enthalten
- Keine zusätzlichen Felder, keine Kommentare, nur das JSON-Objekt
- Alle Textfelder müssen als Strings formatiert sein
- Mehrzeilige Texte bleiben als Strings erhalten

Gib NUR das JSON-Objekt zurück, keine zusätzlichen Erklärungen."""
    
    def __init__(self, db: Session):
        if not AI_SERVICE_AVAILABLE or AIService is None:
            raise ValueError("AIService ist nicht verfügbar. Bitte installieren Sie openai.")
        if not QUESTION_LIST_REPORTER_AVAILABLE or QuestionListReporter is None:
            raise ValueError("QuestionListReporter ist nicht verfügbar. Bitte installieren Sie python-docx.")
        self.db = db
        self.ai_service = AIService(db)
        self.reporter = QuestionListReporter()
        self.storage = StorageService()
    
    def _get_prompt(self) -> str:
        """Lädt Prompt aus Einstellungen oder verwendet Standard-Prompt"""
        setting = self.db.query(AppSettings).filter(AppSettings.key == "question_list_prompt").first()
        if setting and setting.value:
            return setting.value
        return self.DEFAULT_PROMPT
    
    def _extract_full_text(self, project_data: Dict[str, Any]) -> str:
        """
        Extrahiert Full Text aus ProjectData
        
        Returns:
            Formatted text string mit Quellenmarkierungen
        """
        full_text_parts = []
        
        # Full Text aus verschiedenen Quellen sammeln
        if "full_text" in project_data:
            full_text_data = project_data["full_text"]
            if isinstance(full_text_data, list):
                for entry in full_text_data:
                    if isinstance(entry, dict):
                        content = entry.get("content", "")
                        quelle = entry.get("quelle", {})
                    else:
                        content = str(entry)
                        quelle = {}
                    
                    if content:
                        # Quelleninformationen extrahieren
                        datei = quelle.get("datei", "Unbekannte Datei")
                        absatz = quelle.get("absatz")
                        
                        # Text mit Quellenmarkierung formatieren
                        source_marker = f"[Datei: {datei}"
                        if absatz is not None:
                            source_marker += f", Absatz {absatz + 1}"
                        source_marker += "]"
                        
                        formatted_content = f"{source_marker}\n{content}"
                        full_text_parts.append(formatted_content)
            elif isinstance(full_text_data, str):
                if full_text_data.strip():
                    full_text_parts.append(full_text_data)
        
        # Falls kein Full Text vorhanden, versuche aus anderen Feldern zu extrahieren
        if not full_text_parts:
            # Versuche Text aus anderen Entitäten zu extrahieren
            for entity_type in ["anforderungen", "leistungen"]:
                if entity_type in project_data:
                    for entity in project_data[entity_type]:
                        if isinstance(entity, dict):
                            beschreibung = entity.get("beschreibung", "") or entity.get("text", "")
                            quelle = entity.get("quelle", {})
                            
                            if beschreibung:
                                datei = quelle.get("datei", "Unbekannte Datei")
                                absatz = quelle.get("absatz")
                                
                                source_marker = f"[Datei: {datei}"
                                if absatz is not None:
                                    source_marker += f", Absatz {absatz + 1}"
                                source_marker += "]"
                                
                                formatted_content = f"{source_marker}\n{beschreibung}"
                                full_text_parts.append(formatted_content)
        
        formatted_text = "\n\n".join(full_text_parts) if full_text_parts else ""
        return formatted_text
    
    async def perform_question_list(self, project_id: int) -> ProjectFile:
        """
        Führt die Frageliste-Generierung für ein Projekt durch
        
        Args:
            project_id: ID des Projekts
            
        Returns:
            ProjectFile mit dem generierten Word-Dokument
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Projekt mit ID {project_id} nicht gefunden")
        
        project_data_obj = self.db.query(ProjectData).filter(
            ProjectData.project_id == project_id,
            ProjectData.is_active == True
        ).first()
        
        if not project_data_obj:
            raise ValueError("Kein aktives Datenmodell für dieses Projekt gefunden")
        
        project_data = project_data_obj.data_json
        
        # Full Text extrahieren
        logger.info(f"Extrahiere Full Text für Projekt {project_id}")
        full_text = self._extract_full_text(project_data)
        if not full_text:
            logger.warning(f"Kein Text gefunden für Projekt {project_id}")
            raise ValueError("Kein Text zum Analysieren gefunden. Bitte zuerst Dokumente hochladen und extrahieren.")
        
        logger.info(f"Full Text extrahiert: {len(full_text)} Zeichen für Projekt {project_id}")
        
        # Prompt laden
        prompt = self._get_prompt()
        logger.info(f"Prompt geladen: {len(prompt)} Zeichen")
        
        # AI-Analyse durchführen
        logger.info(f"Starte AI-Analyse für Frageliste, Projekt {project_id}")
        try:
            analysis_result = await self.ai_service.analyze_for_question_list(prompt, full_text)
            logger.info(f"AI-Analyse erfolgreich: {len(analysis_result.get('fragen', []))} Fragen gefunden")
        except Exception as e:
            logger.error(f"Fehler bei AI-Analyse für Projekt {project_id}: {str(e)}")
            raise
        
        # Word-Dokument generieren
        logger.info(f"Generiere Word-Dokument für Projekt {project_id}")
        try:
            word_content = await self.reporter.generate(project.name, analysis_result)
            logger.info(f"Word-Dokument generiert: {len(word_content)} Bytes")
        except Exception as e:
            logger.error(f"Fehler bei Word-Generierung für Projekt {project_id}: {str(e)}")
            raise
        
        # Datei speichern
        # Dateiname: Projektnummer + Leerzeichen + Projektname + "Frageliste"
        # Entferne ungültige Zeichen für Dateinamen
        safe_project_name = project.name.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Extrahiere Projektnummer aus description falls vorhanden
        project_number = ""
        if project.description:
            # Versuche Projektnummer zu extrahieren (z.B. "Projektnummer: 2026-01-MWI" oder direkt "2026-01-MWI")
            # Zuerst nach "Projektnummer: " Pattern suchen (wie im Frontend)
            # Unterstützt auch Zeilenumbrüche nach dem Doppelpunkt
            match = re.search(r'Projektnummer:\s*([^\n\r]+)', project.description, re.IGNORECASE | re.MULTILINE)
            if match:
                extracted = match.group(1).strip()
                # Entferne mögliche weitere Zeichen nach der Projektnummer (z.B. wenn danach noch Text kommt)
                # Nimm nur die erste Zeile oder bis zum nächsten Doppelpunkt/Strich
                extracted = extracted.split('\n')[0].split(':')[0].strip()
                if extracted:
                    project_number = extracted + " "
            else:
                # Fallback: Suche nach Format "2026-01-MWI" (irgendwo im Text)
                match = re.search(r'\d{4}-\d{2}-[A-Z]+', project.description)
                if match:
                    project_number = match.group(0) + " "
        
        filename = f"{project_number}{safe_project_name} Frageliste.docx"
        stored_filename = f"{uuid.uuid4()}.docx"
        file_path = await self.storage.save_file(
            file_content=word_content,
            filename=stored_filename,
            project_id=project_id
        )
        
        # ProjectFile erstellen
        db_file = ProjectFile(
            project_id=project_id,
            original_filename=filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_type="Word",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=len(word_content),
            document_type="frageliste",
            discipline=None,
            revision=None,
            processed=True
        )
        
        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)
        
        return db_file
