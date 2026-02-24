"""
Fragenliste-Service
Generiert automatisch Fragen basierend auf Validierungsproblemen
"""

from typing import Dict, Any, List
from app.services.validation_service import ValidationService


class QuestionService:
    """Service für automatische Fragenliste-Generierung"""
    
    def __init__(self):
        self.validation_service = ValidationService()
    
    async def generate_questions(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generiert Fragenliste basierend auf Validierungsproblemen
        Returns: Liste von Fragen mit Kategorien
        """
        # Validierung durchführen
        validation_result = await self.validation_service.validate_project_data(project_data)
        
        questions = []
        
        # Fragen aus Fehlern generieren
        for fehler in validation_result.get("fehler", []):
            question = self._create_question_from_issue(fehler, "kritisch")
            questions.append(question)
        
        # Fragen aus Warnungen generieren
        for warnung in validation_result.get("warnungen", []):
            question = self._create_question_from_issue(warnung, "wichtig")
            questions.append(question)
        
        # Fragen aus Hinweisen generieren
        for hinweis in validation_result.get("hinweise", []):
            question = self._create_question_from_issue(hinweis, "information")
            questions.append(question)
        
        return questions
    
    def _create_question_from_issue(self, issue, priority: str) -> Dict[str, Any]:
        """Erstellt Frage aus Validierungsproblem"""
        return {
            "kategorie": issue.kategorie,
            "frage": issue.beschreibung,
            "prioritaet": priority,
            "fundstellen": issue.fundstellen,
            "empfehlung": issue.empfehlung,
            "betroffene_entitaet": getattr(issue, "betroffene_entitaet", None)
        }
