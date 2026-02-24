"""
Risikoanalyse-Reporter
Generiert Risikoanalyse basierend auf Projekt-Daten
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from app.models.project import Project

# Optional import - reportlab might not be installed
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    colors = None
    A4 = None
    SimpleDocTemplate = None
    Table = None
    TableStyle = None
    Paragraph = None
    Spacer = None
    getSampleStyleSheet = None


class RisikoReporter:
    """Reporter für Risikoanalyse"""
    
    def __init__(self):
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate(self, project: Project, project_data: Dict[str, Any]) -> str:
        if not REPORTLAB_AVAILABLE:
            raise ValueError("reportlab ist nicht installiert. Bitte installieren Sie es mit: pip install reportlab")
        """
        Generiert Risikoanalyse als PDF
        Returns: Pfad zur generierten Datei
        """
        filename = f"risikoanalyse_{project.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Titel
        title = Paragraph(f"Risikoanalyse: {project.name}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Risiken analysieren
        risiken = self._analyze_risks(project_data)
        
        # Risikomatrix erstellen
        story.append(Paragraph("Risikomatrix", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        # Risiko-Tabelle
        data = [["Kategorie", "Beschreibung", "Wahrscheinlichkeit", "Auswirkung", "Risiko"]]
        
        for risiko in risiken:
            risiko_level = self._calculate_risk_level(
                risiko.get("wahrscheinlichkeit", "mittel"),
                risiko.get("auswirkung", "mittel")
            )
            data.append([
                risiko.get("kategorie", "-"),
                risiko.get("beschreibung", "-")[:50] + "...",
                risiko.get("wahrscheinlichkeit", "-"),
                risiko.get("auswirkung", "-"),
                risiko_level
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 12))
        
        # Maßnahmen
        story.append(Paragraph("Empfohlene Maßnahmen", styles['Heading1']))
        story.append(Spacer(1, 12))
        
        for risiko in risiken:
            if risiko.get("massnahme"):
                story.append(Paragraph(f"<b>{risiko.get('kategorie')}:</b> {risiko.get('massnahme')}", styles['Normal']))
                story.append(Spacer(1, 6))
        
        doc.build(story)
        return str(filepath)
    
    def _analyze_risks(self, project_data: Dict[str, Any]) -> list:
        """Analysiert Risiken basierend auf Projekt-Daten"""
        risiken = []
        
        # Datenqualität
        raeume = project_data.get("raeume", [])
        anlagen = project_data.get("anlagen", [])
        
        # Prüfe auf fehlende Daten
        raeume_ohne_flaeche = [r for r in raeume if not r.get("flaeche_m2")]
        if raeume_ohne_flaeche:
            risiken.append({
                "kategorie": "Datenqualität",
                "beschreibung": f"{len(raeume_ohne_flaeche)} Räume ohne Flächenangabe",
                "wahrscheinlichkeit": "hoch",
                "auswirkung": "mittel",
                "massnahme": "Fehlende Flächenangaben ergänzen"
            })
        
        # Projektkomplexität
        if len(raeume) > 100:
            risiken.append({
                "kategorie": "Projektkomplexität",
                "beschreibung": f"Hohe Anzahl von Räumen ({len(raeume)})",
                "wahrscheinlichkeit": "mittel",
                "auswirkung": "hoch",
                "massnahme": "Projekt in Phasen aufteilen, zusätzliche Ressourcen einplanen"
            })
        
        if len(anlagen) > 20:
            risiken.append({
                "kategorie": "Projektkomplexität",
                "beschreibung": f"Hohe Anzahl von Anlagen ({len(anlagen)})",
                "wahrscheinlichkeit": "mittel",
                "auswirkung": "hoch",
                "massnahme": "Anlagen-Koordination intensivieren"
            })
        
        # Validierungsprobleme
        pruefungs_ergebnisse = project_data.get("pruefungs_ergebnisse", {})
        fehler = pruefungs_ergebnisse.get("fehler", [])
        if fehler:
            risiken.append({
                "kategorie": "Datenqualität",
                "beschreibung": f"{len(fehler)} kritische Validierungsfehler gefunden",
                "wahrscheinlichkeit": "hoch",
                "auswirkung": "hoch",
                "massnahme": "Validierungsfehler beheben bevor mit Offerte fortgefahren wird"
            })
        
        return risiken
    
    def _calculate_risk_level(self, wahrscheinlichkeit: str, auswirkung: str) -> str:
        """Berechnet Risiko-Level"""
        levels = {
            ("hoch", "hoch"): "KRITISCH",
            ("hoch", "mittel"): "HOCH",
            ("hoch", "niedrig"): "MITTEL",
            ("mittel", "hoch"): "HOCH",
            ("mittel", "mittel"): "MITTEL",
            ("mittel", "niedrig"): "NIEDRIG",
            ("niedrig", "hoch"): "MITTEL",
            ("niedrig", "mittel"): "NIEDRIG",
            ("niedrig", "niedrig"): "NIEDRIG"
        }
        return levels.get((wahrscheinlichkeit, auswirkung), "UNBEKANNT")
