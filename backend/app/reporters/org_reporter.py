"""
Organisationsempfehlung-Reporter
Generiert Empfehlungen für Team-Größe und Organisation
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from app.models.project import Project


class OrgReporter:
    """Reporter für Organisationsempfehlungen"""
    
    def __init__(self):
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate(self, project: Project, project_data: Dict[str, Any]) -> str:
        """
        Generiert Organisationsempfehlung als Text-Datei
        Returns: Pfad zur generierten Datei
        """
        filename = f"org_empfehlung_{project.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.output_dir / filename
        
        raeume = project_data.get("raeume", [])
        anlagen = project_data.get("anlagen", [])
        geraete = project_data.get("geraete", [])
        
        # Team-Größe berechnen
        team_size = self._calculate_team_size(len(raeume), len(anlagen))
        
        # RACI-Matrix
        raci_roles = self._generate_raci_matrix()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Organisationsempfehlung\n")
            f.write(f"Projekt: {project.name}\n")
            f.write(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("1. Team-Größe\n")
            f.write("-" * 80 + "\n")
            f.write(f"Empfohlene Team-Größe: {team_size} Personen\n")
            f.write(f"Begründung:\n")
            f.write(f"  - Anzahl Räume: {len(raeume)}\n")
            f.write(f"  - Anzahl Anlagen: {len(anlagen)}\n")
            f.write(f"  - Anzahl Geräte: {len(geraete)}\n\n")
            
            f.write("2. Rollenverteilung (RACI-Matrix)\n")
            f.write("-" * 80 + "\n")
            for role, responsibilities in raci_roles.items():
                f.write(f"\n{role}:\n")
                for resp, level in responsibilities.items():
                    f.write(f"  - {resp}: {level}\n")
            
            f.write("\n3. Ressourcen-Bedarf\n")
            f.write("-" * 80 + "\n")
            f.write(f"  - Projektleiter: 1 Person\n")
            f.write(f"  - HLKS-Ingenieure: {max(1, team_size - 1)} Personen\n")
            f.write(f"  - CAD-Zeichner: {max(1, team_size // 2)} Personen\n")
        
        return str(filepath)
    
    def _calculate_team_size(self, num_raeume: int, num_anlagen: int) -> int:
        """Berechnet empfohlene Team-Größe"""
        # Vereinfachte Formel
        base_size = 2  # Mindestgröße
        raum_factor = max(0, (num_raeume - 10) // 20)  # +1 pro 20 Räume über 10
        anlage_factor = max(0, (num_anlagen - 5) // 5)  # +1 pro 5 Anlagen über 5
        
        return base_size + raum_factor + anlage_factor
    
    def _generate_raci_matrix(self) -> Dict[str, Dict[str, str]]:
        """Generiert RACI-Matrix"""
        return {
            "Projektleiter": {
                "Projektkoordination": "R",
                "Kostenplanung": "A",
                "Terminplanung": "A",
                "Qualitätssicherung": "A"
            },
            "HLKS-Ingenieur": {
                "Planung": "R",
                "Berechnungen": "R",
                "Ausschreibung": "C",
                "Abnahme": "C"
            },
            "CAD-Zeichner": {
                "Planerstellung": "R",
                "Planprüfung": "C"
            }
        }
