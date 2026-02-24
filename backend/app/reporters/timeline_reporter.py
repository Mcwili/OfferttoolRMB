"""
Timeline/WBS-Reporter
Generiert Timeline und Work Breakdown Structure
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from app.models.project import Project


class TimelineReporter:
    """Reporter für Timeline und WBS"""
    
    def __init__(self):
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate(self, project: Project, project_data: Dict[str, Any]) -> str:
        """
        Generiert Timeline/WBS als Text-Datei (später PDF/Excel)
        Returns: Pfad zur generierten Datei
        """
        filename = f"timeline_{project.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Timeline / Work Breakdown Structure\n")
            f.write(f"Projekt: {project.name}\n")
            f.write(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write("=" * 80 + "\n\n")
            
            # SIA-Phasen als WBS-Level 1
            sia_phasen = [
                "SIA 103 - Projektierung",
                "SIA 104 - Vorprojekt",
                "SIA 105 - Bauprojekt"
            ]
            
            start_date = datetime.now()
            
            for idx, phase in enumerate(sia_phasen):
                f.write(f"\n{idx + 1}. {phase}\n")
                f.write("-" * 80 + "\n")
                
                # Leistungen für diese Phase
                leistungen = project_data.get("leistungen", [])
                phase_leistungen = [l for l in leistungen if phase in l.get("sia_phase", "")]
                
                if phase_leistungen:
                    for leistung in phase_leistungen:
                        f.write(f"  • {leistung.get('beschreibung', '-')}\n")
                
                # Termine für diese Phase
                termine = project_data.get("termine", [])
                phase_termine = [t for t in termine if phase in t.get("sia_phase", "")]
                
                if phase_termine:
                    f.write("\n  Termine:\n")
                    for termin in phase_termine:
                        termin_datum = termin.get("termin_datum", "-")
                        f.write(f"    - {termin_datum}: {termin.get('beschreibung', '-')}\n")
                
                # Geschätzte Dauer (vereinfacht)
                estimated_duration = 30 + idx * 30  # Tage
                end_date = start_date + timedelta(days=estimated_duration)
                f.write(f"\n  Geschätzte Dauer: {estimated_duration} Tage\n")
                f.write(f"  Von: {start_date.strftime('%d.%m.%Y')} bis: {end_date.strftime('%d.%m.%Y')}\n")
                
                start_date = end_date
        
        return str(filepath)
