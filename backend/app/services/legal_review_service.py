"""
Legal Review Service
Orchestriert die rechtliche Prüfung: AI-Analyse und Word-Generierung
"""

from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import re
import uuid
import asyncio
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
    from app.reporters.legal_review_reporter import LegalReviewReporter
    LEGAL_REVIEW_REPORTER_AVAILABLE = True
except Exception:
    LEGAL_REVIEW_REPORTER_AVAILABLE = False
    LegalReviewReporter = None

logger = logging.getLogger(__name__)


class LegalReviewService:
    """Service für rechtliche Prüfung"""
    
    # Standard-Prompt als Fallback
    DEFAULT_PROMPT = """Rolle
Du bist ein spezialisierter Vertrags und Risikoanalyst für schweizer Ingenieur und Haustechnik Planungsfirmen. Dein Fokus liegt auf HLKS, Gebäudetechnik, Generalplaner und Fachplanerverträgen. Du denkst aus Sicht der Auftragnehmerseite. Dein Auftraggeber ist RMB Engineering, eine Haustechnik Planungsfirma in der Schweiz.

Aufgabe
Prüfe die nachfolgenden Offertunterlagen VOLLSTÄNDIG und ABSCHLIESSEND auf kritische, unklare oder nachteilige vertragliche Inhalte für RMB Engineering. Der Schwerpunkt liegt auf Planungsvertragsentwürfen, Vertragsbedingungen, AGB, Zusatzbedingungen, Haftungsklauseln, Vergütungsmodellen, Terminvorgaben, Koordinationspflichten und Risikoübertragungen.

KRITISCH WICHTIG - ABSCHLIESSENDE PRÜFUNG:
- Du musst ALLE problematischen Punkte identifizieren, nicht nur die wichtigsten oder eine Auswahl
- KEINE Zusammenfassung oder Gruppierung - jeder einzelne problematische Punkt muss separat aufgeführt werden
- Die Prüfung soll abschliessend sein - auch wenn das Ergebnis sehr umfangreich wird (50+ Punkte sind möglich und erwünscht)
- Keine Punkte auslassen, auch wenn sie ähnlich erscheinen - ähnliche Probleme sind separate Punkte
- Jeder kritische Punkt muss einzeln aufgeführt werden mit eigenem Zitat
- Gehe ZEILE FÜR ZEILE durch alle Dokumente
- Prüfe jeden Absatz, jede Klausel, jede Bedingung einzeln
- Wenn ein Dokument 100 problematische Stellen hat, müssen alle 100 aufgeführt werden

Du musst alle Unterlagen vollständig lesen, auch wenn sie umfangreich sind. Falls mehrere Dokumente vorhanden sind, bewerte sie gesamthaft und systematisch durch - Dokument für Dokument, Absatz für Absatz.

Bewertungsschwerpunkte - DETAILLIERTE CHECKLISTE
Prüfe insbesondere, aber nicht ausschliesslich, folgende Themen systematisch:

1. HAFTUNG UND VERANTWORTUNG
Detaillierte Prüfpunkte:
- Unbegrenzte oder übermässige Haftung (z.B. "volle Haftung", "unbeschränkte Haftung", "Haftung für alle Schäden")
- Haftung für Leistungen Dritter (z.B. "Haftung für Fehler von Subunternehmern", "Haftung für Lieferanten")
- Haftung für Kosten, Termine oder Betrieb (z.B. "Haftung für Kostenüberschreitungen", "Haftung für Terminverzögerungen", "Haftung für Betriebsstörungen")
- Abweichungen von SIA Normen (z.B. "abweichend von SIA 112", "nicht nach SIA Standard")
- Haftungsdauer und Verjährung (z.B. "Haftung über 5 Jahre hinaus", "Verjährung ausgeschlossen")
- Haftung für Planungsfehler ohne Verschulden (z.B. "Haftung auch ohne Verschulden", "Gefährdungshaftung")
- Haftung für versteckte Mängel (z.B. "Haftung für Mängel, die erst später auftreten")
- Haftung für Umweltschäden oder Altlasten
- Haftung für Schäden an Dritten ohne direkten Vertrag
- Haftung für geistiges Eigentum oder Urheberrechtsverletzungen

Beispiele für kritische Formulierungen:
- "Der Planer haftet für alle Schäden, die im Zusammenhang mit der Planung entstehen" → ROT
- "Haftung auch für Fehler von Subunternehmern" → ROT
- "Haftung für Kostenüberschreitungen, auch wenn diese nicht verschuldet sind" → ROT
- "Haftungsdauer von 10 Jahren" → ORANGE (üblich sind 5 Jahre)

2. LEISTUNGSUMFANG
Detaillierte Prüfpunkte:
- Unklare oder offene Leistungsbeschriebe (z.B. "alle erforderlichen Leistungen", "nach bestem Wissen und Gewissen", "vollständige Planung")
- Versteckte Zusatzleistungen (z.B. "sowie alle damit verbundenen Leistungen", "inklusive aller Nebenleistungen")
- Koordinations- und Gesamtverantwortung (z.B. "Koordination aller Gewerke", "Gesamtverantwortung für die Planung")
- Bauherrenvertretung oder GU ähnliche Pflichten (z.B. "Vertretung des Bauherrn", "Bauleitung", "Koordination der Bauarbeiten")
- Leistungen ohne klare Honorierung (z.B. "zusätzliche Leistungen nach Vereinbarung", "Leistungen ohne Honorarvereinbarung")
- Unklare Abgrenzung zwischen Planungsphasen (z.B. "inklusive Ausführungsplanung", "bis zur Bauabnahme")
- Leistungen, die über den Standard hinausgehen (z.B. "mehrfache Überarbeitung", "unbegrenzte Änderungen")
- Dokumentationspflichten ohne Honorierung (z.B. "umfassende Dokumentation", "laufende Berichterstattung")
- Prüf- und Freigabepflichten für andere Gewerke
- Übernahme von Verantwortlichkeiten, die nicht zur Planung gehören

Beispiele für kritische Formulierungen:
- "Der Planer erbringt alle erforderlichen Leistungen für eine vollständige Planung" → ROT (zu unklar)
- "Koordination aller am Bau beteiligten Gewerke" → ORANGE (kann sehr umfangreich sein)
- "Zusätzliche Leistungen nach Vereinbarung" → ORANGE (Honorierung unklar)

3. HONORIERUNG UND VERGÜTUNG
Detaillierte Prüfpunkte:
- Pauschalhonorare mit offenem Leistungsumfang (z.B. "Pauschalhonorar für alle Leistungen", "Festpreis ohne Leistungsbeschrieb")
- Fehlende Regelungen zu Zusatzleistungen (z.B. "Zusatzleistungen nicht geregelt", "keine Honorarvereinbarung für Änderungen")
- Abhängigkeit von Projektfortschritt oder Baukosten (z.B. "Honorar abhängig von Baukosten", "Honorar bei Projektfortschritt")
- Zahlungsziele, Rückbehalte, Abzüge (z.B. "Zahlung erst nach Abnahme", "Rückbehalt von 10%", "Abzug bei Verzug")
- Honorar bei Projektabbruch oder Kündigung (z.B. "kein Honorar bei Kündigung", "Honorar nur bei Fertigstellung")
- Unklare Honorarberechnungsgrundlage (z.B. "nach Aufwand", "nach Vereinbarung", "angemessenes Honorar")
- Honorar bei Änderungen oder Mehrfachbearbeitung (z.B. "kein zusätzliches Honorar bei Änderungen", "Änderungen im Honorar enthalten")
- Honorar bei Verzögerungen durch Dritte (z.B. "kein Honorar bei Verzögerungen", "Honorar nur bei Termineinhaltung")
- Fehlende Regelungen zu Spesen oder Nebenkosten
- Unklare Regelungen zu Rechnungsstellung oder Zahlungsfristen

Beispiele für kritische Formulierungen:
- "Pauschalhonorar für alle Leistungen, auch bei Änderungen" → ROT (keine Honorierung für Mehrarbeit)
- "Zahlung erst nach vollständiger Abnahme" → ORANGE (lange Zahlungsfrist)
- "Honorar abhängig von den tatsächlichen Baukosten" → ORANGE (Risiko bei Kostensteigerungen)

4. TERMINE UND VERZUG
Detaillierte Prüfpunkte:
- Verbindliche Termine ohne Abgrenzung (z.B. "Termin verbindlich", "Termin ohne Wenn und Aber")
- Konventionalstrafen (z.B. "Konventionalstrafe bei Verzug", "Strafe pro Tag Verzug")
- Verantwortung für Verzögerungen Dritter (z.B. "Haftung für Verzögerungen durch andere", "Termin auch bei Verzögerungen Dritter")
- Unklare Terminvereinbarungen (z.B. "Termin nach Vereinbarung", "Termin flexibel")
- Termine ohne Berücksichtigung von Genehmigungsverfahren (z.B. "Termin ohne Berücksichtigung von Bewilligungen")
- Termine abhängig von anderen Gewerken (z.B. "Termin abhängig von anderen Planern")
- Fehlende Regelungen zu Terminverlängerungen (z.B. "keine Verlängerung möglich", "Termin nicht verlängerbar")
- Verantwortung für Terminverzögerungen durch Auftraggeber (z.B. "Termin auch bei Verzögerungen durch Auftraggeber")
- Unklare Regelungen zu Terminverschiebungen oder -änderungen
- Termine ohne Berücksichtigung von Planungsphasen

Beispiele für kritische Formulierungen:
- "Konventionalstrafe von 500 CHF pro Tag Verzug" → ROT (bei unklaren Terminen)
- "Termin verbindlich, auch bei Verzögerungen durch Dritte" → ROT (keine Abgrenzung)
- "Termin nach Vereinbarung" → ORANGE (zu unklar)

5. RECHTE UND PFLICHTEN
Detaillierte Prüfpunkte:
- Kündigungsrechte des Auftraggebers (z.B. "jederzeitige Kündigung", "Kündigung ohne Angabe von Gründen")
- Einseitige Vertragsänderungen (z.B. "Änderungen durch Auftraggeber jederzeit möglich", "Vertrag einseitig änderbar")
- Dokumentations- und Reportingpflichten (z.B. "umfassende Dokumentation", "laufende Berichterstattung", "detaillierte Protokolle")
- Versicherungsanforderungen über Standard (z.B. "erweiterte Haftpflichtversicherung", "Versicherungssumme über Standard")
- Geheimhaltungspflichten ohne zeitliche Begrenzung (z.B. "unbegrenzte Geheimhaltung", "Geheimhaltung auch nach Vertragsende")
- Nutzungsrechte an Planungsunterlagen (z.B. "alle Rechte gehen an Auftraggeber über", "keine Nutzungsrechte für Planer")
- Veröffentlichungsrechte oder Namensnennung (z.B. "keine Namensnennung erlaubt", "Veröffentlichung nur mit Zustimmung")
- Weitergabe von Planungsunterlagen an Dritte (z.B. "Weitergabe an Dritte ohne Zustimmung", "Planungsunterlagen für alle Gewerke")
- Fehlende Regelungen zu Urheberrechten oder geistigem Eigentum
- Unklare Regelungen zu Vertraulichkeit oder Datenschutz

Beispiele für kritische Formulierungen:
- "Der Auftraggeber kann den Vertrag jederzeit ohne Angabe von Gründen kündigen" → ORANGE (kein Schutz für Planer)
- "Alle Rechte an den Planungsunterlagen gehen an den Auftraggeber über" → ORANGE (keine Nutzungsrechte)
- "Umfassende Dokumentationspflicht ohne Honorierung" → ORANGE (zusätzliche Leistung)

6. RECHTLICHES
Detaillierte Prüfpunkte:
- Gerichtsstand und anwendbares Recht (z.B. "Gerichtsstand am Sitz des Auftraggebers", "ausländisches Recht")
- Abweichungen von schweizer Standardverträgen (z.B. "abweichend von SIA 112", "nicht nach Standardvertrag")
- Unklare Rangordnung der Vertragsdokumente (z.B. "AGB gehen vor", "Rangordnung unklar")
- Schiedsgerichtsvereinbarungen (z.B. "Schiedsgericht statt ordentliche Gerichte", "Schiedsgericht am Sitz des Auftraggebers")
- Fehlende Regelungen zu Streitbeilegung oder Mediation
- Unklare Regelungen zu Vertragsänderungen oder Ergänzungen
- Fehlende Regelungen zu Vertragsende oder Abwicklung
- Unklare Regelungen zu Gewährleistung oder Garantie
- Abweichungen von gesetzlichen Bestimmungen (z.B. "abweichend von OR", "nicht nach gesetzlichen Bestimmungen")
- Unklare Regelungen zu Vertragsstrafen oder Schadensersatz

Beispiele für kritische Formulierungen:
- "Gerichtsstand am Sitz des Auftraggebers (ausserhalb der Schweiz)" → ROT (Nachteil für Planer)
- "Abweichend von SIA 112 gelten folgende Bestimmungen" → ORANGE (Abweichung von Standard)
- "Schiedsgericht am Sitz des Auftraggebers" → ORANGE (Nachteil für Planer)

SYSTEMATISCHE DOKUMENTENPRÜFUNG
Für jedes Dokument gehe wie folgt vor:
1. Lies den vollständigen Text des Dokuments durch
2. Identifiziere alle Absätze, die zu den oben genannten Themenbereichen gehören
3. Prüfe jeden Absatz einzeln auf problematische Formulierungen
4. Erstelle für jeden problematischen Absatz einen separaten Eintrag mit exaktem Zitat
5. Wiederhole für jedes weitere Dokument

ZITIERUNG - WICHTIGE REGELN
- Das Zitat muss den EXAKTEN WORTLAUT aus den Unterlagen enthalten
- Zitiere immer den vollständigen Satz oder Absatz, nicht nur einen Teil
- Füge genügend Kontext hinzu, damit das Zitat verständlich ist
- Verwende die Quellenmarkierungen [Datei: ..., Absatz ...] um die Quelle zu identifizieren
- Falls mehrere Sätze problematisch sind, zitiere alle relevanten Sätze
- Zitiere immer im Originalwortlaut, keine Paraphrasierung

Ausgabeformat - WICHTIG: JSON-Format
Deine Antwort MUSS IMMER als gültiges JSON-Objekt erfolgen. Kein zusätzlicher Text, keine Erklärungen, nur das JSON-Objekt.

Das JSON-Format ist exakt wie folgt definiert:
{
  "allgemeine_einschaetzung": "Kurze Gesamtbeurteilung der Unterlagen aus Sicht von RMB Engineering. Fokus auf Gesamtrisiko.",
  "kritische_punkte": [
    {
      "nummer": 1,
      "titel": "Kurzer, prägnanter Titel des Risikos",
      "zitat": "Exakter Wortlaut aus den Unterlagen (vollständiges Zitat)",
      "beurteilung": "Fachliche Einschätzung, warum dieser Punkt für RMB Engineering kritisch, unklar oder nachteilig ist. Bezug auf typische Praxis in der Schweiz und SIA Normen, ohne Paragraphen zu zitieren.",
      "risiko_rating": "rot",
      "empfehlung": "Konkrete Handlungsempfehlung für RMB Engineering (z.B. Anpassung verlangen, präzisieren, streichen, akzeptabel mit Vorbehalt)",
      "quelle_datei": "Name der Datei, aus der das Zitat stammt (z.B. 'Vertrag.docx')",
      "quelle_paragraph": 5
    }
  ]
}

Wichtige Regeln für JSON-Ausgabe:
- Die Antwort muss ein gültiges JSON-Objekt sein
- "risiko_rating" muss exakt einer der Werte sein: "rot", "orange" oder "grün"
- "nummer" muss eine fortlaufende Zahl sein, beginnend bei 1
- Jeder Punkt in "kritische_punkte" muss alle Felder enthalten
- "quelle_datei" muss der exakte Dateiname sein (wie in den Quellenmarkierungen [Datei: ...] angegeben)
- "quelle_paragraph" muss die Absatznummer sein (wie in den Quellenmarkierungen angegeben, z.B. "Absatz 5" -> 5)
- Falls Quelle nicht eindeutig identifizierbar ist, verwende "Unbekannte Quelle" für quelle_datei und null für quelle_paragraph
- Keine zusätzlichen Felder, keine Kommentare, nur das JSON-Objekt
- Alle Textfelder müssen als Strings formatiert sein
- Mehrzeilige Texte bleiben als Strings erhalten

Wichtige Regeln für die Analyse:
- Nummerierung immer fortlaufend beginnen bei 1 und fortlaufend weiter (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, ...)
- Jeder Punkt darf nur ein Thema behandeln
- Keine Vermischung mehrerer Risiken in einem Punkt
- Keine juristischen Floskeln, klare und praxisnahe Sprache
- Keine Absicherung zugunsten des Auftraggebers formulieren
- Denke strikt aus Sicht von RMB Engineering
- Falls etwas unklar ist, bewerte es als Risiko
- Falls etwas fehlt, das üblich wäre, weise explizit darauf hin
- ABSCHLIESSENDE PRÜFUNG: Identifiziere ALLE problematischen Punkte, nicht nur die wichtigsten
- Auch ähnliche oder wiederkehrende Probleme müssen einzeln aufgeführt werden
- Die Prüfung soll vollständig sein - auch wenn das Ergebnis sehr umfangreich wird (50+ Punkte sind normal und erwünscht)
- Gehe systematisch durch alle Dokumente und alle relevanten Themenbereiche
- KEINE Zusammenfassung - jeder Punkt einzeln
- KEINE Gruppierung - ähnliche Probleme sind separate Punkte
- Prüfe jeden Absatz, jede Klausel, jede Bedingung einzeln
- Wenn mehrere Probleme in einem Absatz sind, erstelle für jedes ein separates Eintrag

Farblogik
rot = wesentliches Risiko mit möglich grossem finanziellem oder haftungsrechtlichem Schaden
orange = relevantes Risiko, das verhandelt oder präzisiert werden sollte
grün = geringes Risiko oder marktüblich, Hinweis reicht

Start
Beginne mit der Analyse, sobald die Unterlagen eingefügt werden. 

KRITISCH WICHTIG - ABSCHLIESSENDE PRÜFUNG:
1. Führe eine ABSCHLIESSENDE und VOLLSTÄNDIGE Prüfung durch
2. Identifiziere ALLE problematischen Punkte - nicht nur 5 oder 10, sondern ALLE
3. Gehe systematisch durch alle Dokumente - Dokument für Dokument
4. Gehe durch alle Absätze - Absatz für Absatz
5. Prüfe jeden einzelnen problematischen Punkt
6. Keine Punkte auslassen, auch wenn sie ähnlich erscheinen
7. Jeder kritische Punkt muss einzeln aufgeführt werden mit eigenem Zitat
8. Wenn ein Dokument viele problematische Stellen hat, müssen alle aufgeführt werden
9. Erwartete Anzahl: 20-100+ Punkte sind normal für umfangreiche Verträge
10. KEINE Zusammenfassung - jeder Punkt einzeln

Vorgehen:
- Lies das erste Dokument komplett durch
- Identifiziere jeden problematischen Punkt einzeln
- Erstelle für jeden Punkt einen separaten Eintrag
- Wiederhole für jedes weitere Dokument
- Stelle sicher, dass wirklich ALLE Punkte erfasst sind

Gib NUR das JSON-Objekt zurück, keine zusätzlichen Erklärungen. Das JSON-Objekt muss ALLE gefundenen kritischen Punkte enthalten."""
    
    def __init__(self, db: Session):
        if not AI_SERVICE_AVAILABLE or AIService is None:
            raise ValueError("AIService ist nicht verfügbar. Bitte installieren Sie openai.")
        if not LEGAL_REVIEW_REPORTER_AVAILABLE or LegalReviewReporter is None:
            raise ValueError("LegalReviewReporter ist nicht verfügbar. Bitte installieren Sie python-docx.")
        self.db = db
        self.ai_service = AIService(db)
        self.reporter = LegalReviewReporter()
        self.storage = StorageService()
    
    def _get_prompt(self) -> str:
        """Lädt Prompt aus Einstellungen oder verwendet Standard-Prompt"""
        setting = self.db.query(AppSettings).filter(AppSettings.key == "legal_review_prompt").first()
        if setting and setting.value:
            return setting.value
        return self.DEFAULT_PROMPT
    
    def _extract_full_text(self, project_data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Extrahiert Full Text aus ProjectData mit Quelleninformationen
        
        Returns:
            Tuple von (formatted_text, source_mapping)
            - formatted_text: Text mit Quellenmarkierungen für AI
            - source_mapping: Mapping von Textabschnitten zu Quelleninformationen
        """
        full_text_parts = []
        source_mapping = {}  # Mapping von Textabschnitten zu Quellen
        
        # Full Text aus verschiedenen Quellen sammeln
        if "full_text" in project_data:
            full_text_data = project_data["full_text"]
            if isinstance(full_text_data, list):
                for entry_idx, entry in enumerate(full_text_data):
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
                        datei_id = quelle.get("datei_id")
                        
                        # Text mit Quellenmarkierung formatieren
                        source_marker = f"[Datei: {datei}"
                        if absatz is not None:
                            source_marker += f", Absatz {absatz + 1}"  # +1 für Benutzerfreundlichkeit
                        source_marker += "]"
                        
                        formatted_content = f"{source_marker}\n{content}"
                        full_text_parts.append(formatted_content)
                        
                        # Mapping speichern für spätere Zuordnung
                        source_key = f"entry_{entry_idx}"
                        source_mapping[source_key] = {
                            "datei": datei,
                            "absatz": absatz,
                            "datei_id": datei_id,
                            "content": content
                        }
            elif isinstance(full_text_data, str):
                if full_text_data.strip():
                    full_text_parts.append(full_text_data)
        
        # Falls kein Full Text vorhanden, versuche aus anderen Feldern zu extrahieren
        if not full_text_parts:
            # Versuche Text aus anderen Entitäten zu extrahieren
            for entity_type in ["anforderungen", "leistungen"]:
                if entity_type in project_data:
                    for entity_idx, entity in enumerate(project_data[entity_type]):
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
                                
                                source_key = f"{entity_type}_{entity_idx}"
                                source_mapping[source_key] = {
                                    "datei": datei,
                                    "absatz": absatz,
                                    "datei_id": quelle.get("datei_id"),
                                    "content": beschreibung
                                }
        
        formatted_text = "\n\n".join(full_text_parts) if full_text_parts else ""
        return formatted_text, source_mapping
    
    def _add_source_information(
        self, 
        analysis_result: Dict[str, Any], 
        source_mapping: Dict[str, Any],
        full_text: str
    ) -> Dict[str, Any]:
        """
        Fügt Quelleninformationen zu kritischen Punkten hinzu
        
        Versucht, für jedes Zitat die Quelle zu finden, falls nicht bereits angegeben
        """
        kritische_punkte = analysis_result.get("kritische_punkte", [])
        
        for punkt in kritische_punkte:
            zitat = punkt.get("zitat", "")
            quelle_datei = punkt.get("quelle_datei")
            quelle_paragraph = punkt.get("quelle_paragraph")
            
            # Falls Quelle bereits vorhanden, überspringe
            if quelle_datei:
                continue
            
            # Versuche, Quelle aus dem Zitat zu finden
            # Suche nach Quellenmarkierungen im Text
            zitat_lower = zitat.lower()
            
            # Suche im source_mapping
            for source_key, source_info in source_mapping.items():
                content = source_info.get("content", "").lower()
                # Prüfe, ob das Zitat im Content enthalten ist
                if zitat_lower in content or content in zitat_lower:
                    punkt["quelle_datei"] = source_info.get("datei", "Unbekannte Datei")
                    absatz = source_info.get("absatz")
                    if absatz is not None:
                        punkt["quelle_paragraph"] = absatz + 1  # +1 für Benutzerfreundlichkeit
                    break
            
            # Falls immer noch keine Quelle gefunden, versuche im formatierten Text zu suchen
            if not punkt.get("quelle_datei"):
                # Suche nach Quellenmarkierungen im Text
                # Finde alle Quellenmarkierungen im Text
                source_pattern = r'\[Datei: ([^\]]+)\]'
                matches = list(re.finditer(source_pattern, full_text))
                
                for match in matches:
                    source_info_str = match.group(1)
                    # Extrahiere Dateiname und Absatz
                    if ", Absatz" in source_info_str:
                        datei_name, absatz_str = source_info_str.split(", Absatz", 1)
                        datei_name = datei_name.strip()
                        try:
                            absatz_num = int(absatz_str.strip())
                        except:
                            absatz_num = None
                    else:
                        datei_name = source_info_str.strip()
                        absatz_num = None
                    
                    # Prüfe, ob das Zitat nach dieser Markierung kommt
                    text_after_marker = full_text[match.end():match.end() + 2000]  # Nächste 2000 Zeichen
                    if zitat_lower in text_after_marker.lower():
                        punkt["quelle_datei"] = datei_name
                        if absatz_num:
                            punkt["quelle_paragraph"] = absatz_num
                        break
        
        analysis_result["kritische_punkte"] = kritische_punkte
        return analysis_result
    
    def _split_text_by_document(self, full_text: str, source_mapping: Dict[str, Any]) -> Dict[str, tuple[str, Dict[str, Any]]]:
        """
        Teilt den Full Text nach Dokumenten auf
        
        Returns:
            Dict mit Dateinamen als Key und (text, source_mapping) als Value
        """
        documents = {}
        
        # Suche nach Quellenmarkierungen im Text
        import re
        source_pattern = r'\[Datei: ([^\]]+)\]'
        matches = list(re.finditer(source_pattern, full_text))
        
        current_doc = None
        current_text_parts = []
        current_source_mapping = {}
        
        for i, match in enumerate(matches):
            source_info_str = match.group(1)
            # Extrahiere Dateiname
            if ", Absatz" in source_info_str:
                datei_name = source_info_str.split(", Absatz", 1)[0].strip()
            else:
                datei_name = source_info_str.strip()
            
            # Wenn neues Dokument, speichere vorheriges
            if current_doc and current_doc != datei_name:
                if current_text_parts:
                    documents[current_doc] = ("\n\n".join(current_text_parts), current_source_mapping)
                current_text_parts = []
                current_source_mapping = {}
            
            current_doc = datei_name
            
            # Text nach dieser Markierung bis zur nächsten Markierung
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(full_text)
            
            text_segment = full_text[start_pos:end_pos].strip()
            if text_segment:
                current_text_parts.append(f"[Datei: {source_info_str}]\n{text_segment}")
                
                # Füge zu source_mapping hinzu
                source_key = f"doc_{datei_name}_{len(current_text_parts)}"
                current_source_mapping[source_key] = {
                    "datei": datei_name,
                    "content": text_segment
                }
        
        # Letztes Dokument speichern
        if current_doc and current_text_parts:
            documents[current_doc] = ("\n\n".join(current_text_parts), current_source_mapping)
        
        # Falls keine Dokumente gefunden, verwende gesamten Text
        if not documents:
            documents["Alle Dokumente"] = (full_text, source_mapping)
        
        return documents
    
    def _merge_and_deduplicate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fusioniert mehrere Analyse-Ergebnisse und dedupliziert ähnliche Punkte
        
        Args:
            results: Liste von Analyse-Ergebnissen
            
        Returns:
            Fusioniertes Analyse-Ergebnis
        """
        if not results:
            return {"allgemeine_einschaetzung": "", "kritische_punkte": []}
        
        # Alle kritischen Punkte sammeln
        all_points = []
        for result in results:
            points = result.get("kritische_punkte", [])
            all_points.extend(points)
        
        # Deduplizierung: Ähnliche Punkte zusammenführen
        # Zwei Punkte sind ähnlich, wenn:
        # 1. Das Zitat sehr ähnlich ist (über 80% Übereinstimmung)
        # 2. Oder Titel und Beurteilung sehr ähnlich sind
        
        deduplicated = []
        seen_zitate = set()
        
        for punkt in all_points:
            zitat = punkt.get("zitat", "").strip().lower()
            
            # Prüfe auf exakte Duplikate
            if zitat in seen_zitate:
                continue
            
            # Prüfe auf ähnliche Zitate
            is_duplicate = False
            for seen_zitat in seen_zitate:
                # Einfache Ähnlichkeitsprüfung: Überlappung der Wörter
                zitat_words = set(zitat.split())
                seen_words = set(seen_zitat.split())
                
                if len(zitat_words) > 0 and len(seen_words) > 0:
                    overlap = len(zitat_words & seen_words) / max(len(zitat_words), len(seen_words))
                    if overlap > 0.8:  # Über 80% Übereinstimmung
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                seen_zitate.add(zitat)
                deduplicated.append(punkt)
        
        # Nummerierung neu setzen
        for idx, punkt in enumerate(deduplicated, 1):
            punkt["nummer"] = idx
        
        # Allgemeine Einschätzung kombinieren
        allgemeine_parts = []
        for result in results:
            einschaetzung = result.get("allgemeine_einschaetzung", "").strip()
            if einschaetzung:
                allgemeine_parts.append(einschaetzung)
        
        allgemeine_einschaetzung = " | ".join(allgemeine_parts) if allgemeine_parts else ""
        
        return {
            "allgemeine_einschaetzung": allgemeine_einschaetzung,
            "kritische_punkte": deduplicated
        }
    
    async def _analyze_by_document(self, prompt: str, full_text: str, source_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt Analyse pro Dokument durch
        
        Returns:
            Fusioniertes Analyse-Ergebnis
        """
        documents = self._split_text_by_document(full_text, source_mapping)
        
        if len(documents) <= 1:
            # Nur ein Dokument oder keine Dokumente gefunden, normale Analyse
            logger.info("Nur ein Dokument gefunden, führe normale Analyse durch")
            return await self.ai_service.analyze_legal_documents(prompt, full_text)
        
        logger.info(f"Analysiere {len(documents)} Dokumente einzeln")
        results = []
        
        for doc_name, (doc_text, doc_source_mapping) in documents.items():
            logger.info(f"Analysiere Dokument: {doc_name}")
            try:
                result = await self.ai_service.analyze_legal_documents(prompt, doc_text)
                # Quelleninformationen hinzufügen
                result = self._add_source_information(result, doc_source_mapping, doc_text)
                results.append(result)
            except Exception as e:
                logger.error(f"Fehler bei Analyse von Dokument {doc_name}: {str(e)}")
                # Weiter mit nächstem Dokument
                continue
        
        # Ergebnisse fusionieren
        return self._merge_and_deduplicate(results)
    
    async def _analyze_by_category(self, prompt: str, full_text: str, source_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt Analyse pro Themenbereich durch
        
        Returns:
            Fusioniertes Analyse-Ergebnis
        """
        categories = {
            "Haftung": ["haftung", "verantwortung", "schaden", "mängel"],
            "Leistungsumfang": ["leistung", "umfang", "koordination", "verantwortung"],
            "Honorierung": ["honorar", "vergütung", "zahlung", "kosten"],
            "Termine": ["termin", "verzug", "frist", "strafe"],
            "Rechte": ["kündigung", "änderung", "recht", "pflicht"],
            "Rechtliches": ["gericht", "recht", "schiedsgericht", "norm"]
        }
        
        logger.info("Analysiere nach Themenbereichen")
        results = []
        
        for category_name, keywords in categories.items():
            # Filtere Text nach Keywords (vereinfacht: Suche nach Keywords im Text)
            category_text_parts = []
            lines = full_text.split('\n')
            
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in keywords):
                    category_text_parts.append(line)
            
            if category_text_parts:
                category_text = '\n'.join(category_text_parts)
                logger.info(f"Analysiere Themenbereich: {category_name} ({len(category_text)} Zeichen)")
                
                # Erweitere Prompt für spezifischen Themenbereich
                category_prompt = f"{prompt}\n\nFOKUS: Prüfe jetzt speziell den Themenbereich '{category_name}'. Identifiziere ALLE problematischen Punkte in diesem Bereich."
                
                try:
                    result = await self.ai_service.analyze_legal_documents(category_prompt, category_text)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Fehler bei Analyse von Themenbereich {category_name}: {str(e)}")
                    continue
        
        # Falls keine kategoriespezifischen Ergebnisse, führe normale Analyse durch
        if not results:
            logger.info("Keine kategoriespezifischen Ergebnisse, führe normale Analyse durch")
            return await self.ai_service.analyze_legal_documents(prompt, full_text)
        
        # Ergebnisse fusionieren
        return self._merge_and_deduplicate(results)
    
    async def perform_legal_review(self, project_id: int, return_analysis: bool = False):
        """
        Führt rechtliche Prüfung für ein Projekt durch
        
        Args:
            project_id: ID des Projekts
            return_analysis: Ob das Analyse-Ergebnis zurückgegeben werden soll
        
        Returns:
            Tuple von (ProjectFile, analysis_result | None)
            - ProjectFile: Das generierte Word-Dokument
            - analysis_result: Das Analyse-Ergebnis, falls return_analysis=True, sonst None
        """
        # Projekt laden
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Projekt mit ID {project_id} nicht gefunden")
        
        # Aktuelles Datenmodell laden
        project_data_obj = self.db.query(ProjectData).filter(
            ProjectData.project_id == project_id,
            ProjectData.is_active == True
        ).first()
        
        if not project_data_obj:
            raise ValueError("Kein aktives Datenmodell für dieses Projekt gefunden")
        
        project_data = project_data_obj.data_json
        
        # Full Text extrahieren mit Quelleninformationen
        logger.info(f"Extrahiere Full Text für Projekt {project_id}")
        full_text, source_mapping = self._extract_full_text(project_data)
        if not full_text:
            logger.warning(f"Kein Text gefunden für Projekt {project_id}")
            raise ValueError("Kein Text zum Analysieren gefunden. Bitte zuerst Dokumente hochladen und extrahieren.")
        
        logger.info(f"Full Text extrahiert: {len(full_text)} Zeichen für Projekt {project_id}")
        
        # Prompt laden
        prompt = self._get_prompt()
        logger.info(f"Prompt geladen: {len(prompt)} Zeichen")
        
        # AI-Analyse durchführen - mehrfache Analyse
        logger.info(f"Starte mehrfache AI-Analyse für Projekt {project_id}")
        try:
            # Führe alle drei Analysen parallel aus, um Zeit zu sparen
            logger.info("Starte parallele AI-Analysen (pro Dokument, pro Themenbereich, Gesamtanalyse)")
            
            # Starte alle drei Analysen parallel
            tasks = [
                self._analyze_by_document(prompt, full_text, source_mapping),
                self._analyze_by_category(prompt, full_text, source_mapping),
                self.ai_service.analyze_legal_documents(prompt, full_text)
            ]
            
            # Warte auf alle Ergebnisse (mit Timeout)
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=900.0  # 15 Minuten Gesamt-Timeout für alle drei Analysen
                )
            except asyncio.TimeoutError:
                logger.error("AI-Analysen haben Gesamt-Timeout erreicht (15 Minuten)")
                raise ValueError("Die Analyse hat zu lange gedauert. Bitte versuchen Sie es erneut oder reduzieren Sie die Textmenge.")
            
            # Prüfe auf Fehler in den Ergebnissen
            result_by_document = results[0]
            result_by_category = results[1]
            result_overall = results[2]
            
            # Wenn eine Analyse fehlgeschlagen ist, verwende die anderen
            if isinstance(result_by_document, Exception):
                error_msg = str(result_by_document)
                error_type = type(result_by_document).__name__
                logger.warning(f"Analyse pro Dokument fehlgeschlagen ({error_type}): {error_msg}")
                result_by_document = {"allgemeine_einschaetzung": "", "kritische_punkte": []}
            
            if isinstance(result_by_category, Exception):
                error_msg = str(result_by_category)
                error_type = type(result_by_category).__name__
                logger.warning(f"Analyse pro Themenbereich fehlgeschlagen ({error_type}): {error_msg}")
                result_by_category = {"allgemeine_einschaetzung": "", "kritische_punkte": []}
            
            if isinstance(result_overall, Exception):
                error_msg = str(result_overall)
                error_type = type(result_overall).__name__
                logger.warning(f"Gesamtanalyse fehlgeschlagen ({error_type}): {error_msg}")
                result_overall = {"allgemeine_einschaetzung": "", "kritische_punkte": []}
            
            # Wenn alle Analysen fehlgeschlagen sind, werfe einen Fehler
            if (isinstance(result_by_document, Exception) and 
                isinstance(result_by_category, Exception) and 
                isinstance(result_overall, Exception)):
                # Verwende die erste Exception als Hauptfehler
                first_error = result_by_document if isinstance(result_by_document, Exception) else (
                    result_by_category if isinstance(result_by_category, Exception) else result_overall
                )
                logger.error("Alle drei AI-Analysen sind fehlgeschlagen")
                raise ValueError(f"Alle AI-Analysen sind fehlgeschlagen. Letzter Fehler: {str(first_error)}")
            
            # Alle Ergebnisse fusionieren und deduplizieren
            logger.info("Fusioniere Ergebnisse")
            all_results = [result_by_document, result_by_category, result_overall]
            analysis_result = self._merge_and_deduplicate(all_results)
            
            logger.info(f"Mehrfache AI-Analyse erfolgreich: {len(analysis_result.get('kritische_punkte', []))} kritische Punkte gefunden")
            logger.debug(f"Nach Fusion: {len(analysis_result.get('kritische_punkte', []))} kritische Punkte")
            
            # Quelleninformationen zu kritischen Punkten hinzufügen
            analysis_result = self._add_source_information(analysis_result, source_mapping, full_text)
            logger.info(f"Nach Quelleninformationen: {len(analysis_result.get('kritische_punkte', []))} kritische Punkte")
        except Exception as e:
            logger.error(f"Fehler bei AI-Analyse für Projekt {project_id}: {str(e)}", exc_info=True)
            raise
        
        # WICHTIG: Erstelle eine tiefe Kopie von analysis_result für die Datenbank
        # Dies stellt sicher, dass die Daten für Word-Generierung nicht verändert werden
        import copy
        import json
        analysis_result_for_db = copy.deepcopy(analysis_result)
        
        # Analyse-Ergebnisse in ProjectData speichern
        logger.info(f"Speichere Analyse-Ergebnisse für Projekt {project_id}")
        logger.debug(f"Vor Speichern: {len(analysis_result_for_db.get('kritische_punkte', []))} kritische Punkte")
        try:
            if "legal_review_results" not in project_data:
                project_data["legal_review_results"] = []
            
            # Neue Prüfung hinzufügen (mit Kopie der Daten)
            review_entry = {
                "created_at": datetime.now().isoformat(),
                "analysis_result": analysis_result_for_db
            }
            project_data["legal_review_results"].append(review_entry)
            
            # Nur die letzten 10 Prüfungen behalten
            if len(project_data["legal_review_results"]) > 10:
                project_data["legal_review_results"] = project_data["legal_review_results"][-10:]
            
            # ProjectData aktualisieren
            project_data_obj.data_json = project_data
            self.db.commit()
            logger.info(f"Analyse-Ergebnisse gespeichert für Projekt {project_id}")
            logger.debug(f"Nach Speichern: {len(analysis_result.get('kritische_punkte', []))} kritische Punkte (sollte unverändert sein)")
        except Exception as e:
            logger.warning(f"Fehler beim Speichern der Analyse-Ergebnisse für Projekt {project_id}: {str(e)}")
            # Nicht kritisch, weiter mit Word-Generierung
        
        # Word-Dokument generieren
        logger.info(f"Generiere Word-Dokument für Projekt {project_id}")
        
        # Logging: Prüfe, welche Daten übergeben werden
        logger.info(f"Daten für Word-Generierung: {len(analysis_result.get('kritische_punkte', []))} kritische Punkte")
        logger.debug(f"Allgemeine Einschätzung Länge: {len(analysis_result.get('allgemeine_einschaetzung', ''))} Zeichen")
        if analysis_result.get('kritische_punkte'):
            logger.debug(f"Erster kritischer Punkt: {analysis_result['kritische_punkte'][0].get('titel', 'Kein Titel')}")
            logger.debug(f"Letzter kritischer Punkt: {analysis_result['kritische_punkte'][-1].get('titel', 'Kein Titel')}")
        
        try:
            # Verwende die frisch generierten Daten direkt (nicht aus der Datenbank)
            # analysis_result enthält die neuesten, vollständigen Daten
            logger.info(f"Übergebe {len(analysis_result.get('kritische_punkte', []))} kritische Punkte an Word-Reporter")
            
            word_content = await self.reporter.generate(project.name, analysis_result)
            logger.info(f"Word-Dokument generiert: {len(word_content)} Bytes")
        except Exception as e:
            logger.error(f"Fehler bei Word-Generierung für Projekt {project_id}: {str(e)}", exc_info=True)
            raise
        
        # Rückgabe vorbereiten
        analysis_to_return = analysis_result if return_analysis else None
        
        # Datei speichern
        # Dateiname: Projektnummer + Leerzeichen + Projektname + "RechtPr"
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
        
        filename = f"{project_number}{safe_project_name} RechtPr.docx"
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
            document_type="rechtliche_pruefung",
            discipline=None,
            revision=None,
            processed=True
        )
        
        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)
        
        return db_file, analysis_to_return
