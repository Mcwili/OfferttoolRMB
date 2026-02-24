"""
JSON-Datenmodell-Schema für Projekt-Daten
Definiert die Struktur des zentralen JSON-Datenmodells
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Quelle(BaseModel):
    """Quellenverweis für extrahierte Daten"""
    datei: str
    datei_id: Optional[int] = None
    upload_am: Optional[str] = None
    blatt: Optional[str] = None
    zeile: Optional[int] = None
    absatz: Optional[int] = None
    ifc_guid: Optional[str] = None
    objekt: Optional[str] = None


class ProjektInfo(BaseModel):
    """Projekt-Informationen"""
    id: Optional[str] = None
    name: str
    beschreibung: Optional[str] = None
    standort: Optional[str] = None
    version: int = 1
    dateien: List[Dict[str, Any]] = Field(default_factory=list)


class RaumAnforderungen(BaseModel):
    """Anforderungen für einen Raum"""
    luftwechsel_pro_h: Optional[float] = None
    temperatur_min: Optional[float] = None
    temperatur_max: Optional[float] = None
    luftfeuchtigkeit_min: Optional[float] = None
    luftfeuchtigkeit_max: Optional[float] = None
    belegungsdichte: Optional[float] = None
    sonstige: Optional[str] = None


class Raum(BaseModel):
    """Raum-Entität"""
    id: str
    name: Optional[str] = None
    nummer: Optional[str] = None
    flaeche_m2: Optional[float] = None
    volumen_m3: Optional[float] = None
    hoehe_m: Optional[float] = None
    nutzungsart: Optional[str] = None
    geschoss: Optional[str] = None
    zone: Optional[str] = None
    anforderungen: Optional[RaumAnforderungen] = None
    zugehoerige_anlagen: List[str] = Field(default_factory=list)
    zugehoerige_geraete: List[str] = Field(default_factory=list)
    position: Optional[Dict[str, Any]] = None  # Koordinaten falls aus Plan
    quelle: Quelle


class Anlage(BaseModel):
    """Anlage-Entität (HLKS-Anlage)"""
    id: str
    typ: str  # z.B. "Lüftungsanlage", "Heizungsanlage", "Kälteanlage"
    name: Optional[str] = None
    leistung_kw: Optional[float] = None
    leistung_m3_h: Optional[float] = None  # Volumenstrom für Lüftung
    position: Optional[Dict[str, Any]] = None
    zugehoerige_raeume: List[str] = Field(default_factory=list)
    zugehoerige_geraete: List[str] = Field(default_factory=list)
    system_id: Optional[str] = None  # IFC System-ID
    ifc_guid: Optional[str] = None
    spezifikation: Optional[Dict[str, Any]] = None
    quelle: Quelle


class Geraet(BaseModel):
    """Gerät-Entität"""
    id: str
    typ: str  # z.B. "Ventilator", "Wärmepumpe", "Kühler"
    name: Optional[str] = None
    leistung_kw: Optional[float] = None
    zugehoerige_anlage: Optional[str] = None
    zugehoeriger_raum: Optional[str] = None
    position: Optional[Dict[str, Any]] = None
    spezifikation: Optional[Dict[str, Any]] = None
    ifc_guid: Optional[str] = None
    quelle: Quelle


class Anforderung(BaseModel):
    """Anforderung/Leistungsanforderung"""
    id: str
    beschreibung: str
    kategorie: Optional[str] = None  # z.B. "Technisch", "Organisatorisch", "Termin"
    prioritaet: Optional[str] = None  # "hoch", "mittel", "niedrig"
    sia_phase: Optional[str] = None  # SIA-Phase zugeordnet
    zugehoerige_raeume: List[str] = Field(default_factory=list)
    zugehoerige_anlagen: List[str] = Field(default_factory=list)
    quelle: Quelle


class Termin(BaseModel):
    """Termin/Meilenstein"""
    id: str
    beschreibung: str
    termin_datum: Optional[str] = None  # ISO-Format
    kategorie: Optional[str] = None  # "Meilenstein", "Abgabe", "Freigabe"
    zugehoerige_leistung: Optional[str] = None
    sia_phase: Optional[str] = None
    quelle: Quelle


class Leistung(BaseModel):
    """Leistungsposition"""
    id: str
    beschreibung: str
    sia_phase: Optional[str] = None
    kategorie: Optional[str] = None
    einheit: Optional[str] = None
    menge: Optional[float] = None
    zugehoerige_raeume: List[str] = Field(default_factory=list)
    zugehoerige_anlagen: List[str] = Field(default_factory=list)
    quelle: Quelle


class Risiko(BaseModel):
    """Risiko-Identifikation"""
    id: str
    beschreibung: str
    kategorie: str  # "Datenqualität", "Projektkomplexität", "Termin", "Technisch"
    wahrscheinlichkeit: Optional[str] = None  # "hoch", "mittel", "niedrig"
    auswirkung: Optional[str] = None  # "hoch", "mittel", "niedrig"
    massnahme: Optional[str] = None
    quelle: Optional[Quelle] = None


class ValidationIssue(BaseModel):
    """Validierungsproblem"""
    kategorie: str  # "Widerspruch", "Fehlende Angabe", "Referenzfehler", "Plausibilitätsfehler"
    beschreibung: str
    fundstellen: List[str] = Field(default_factory=list)
    schweregrad: str  # "kritisch", "warnung", "hinweis"
    empfehlung: Optional[str] = None
    betroffene_entitaet: Optional[str] = None  # ID der betroffenen Entität


class ProjectDataSchema(BaseModel):
    """Hauptschema für Projekt-Datenmodell"""
    projekt: ProjektInfo
    raeume: List[Raum] = Field(default_factory=list)
    anlagen: List[Anlage] = Field(default_factory=list)
    geraete: List[Geraet] = Field(default_factory=list)
    anforderungen: List[Anforderung] = Field(default_factory=list)
    termine: List[Termin] = Field(default_factory=list)
    leistungen: List[Leistung] = Field(default_factory=list)
    risiken: List[Risiko] = Field(default_factory=list)
    pruefungs_ergebnisse: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic Config"""
        json_schema_extra = {
            "example": {
                "projekt": {
                    "id": "PROJ_000001",
                    "name": "Beispielprojekt",
                    "beschreibung": "HLKS-Planung für Bürogebäude",
                    "standort": "Zürich",
                    "version": 1,
                    "dateien": []
                },
                "raeume": [],
                "anlagen": [],
                "geraete": [],
                "anforderungen": [],
                "termine": [],
                "leistungen": [],
                "risiken": []
            }
        }


def create_empty_project_data(project_name: str, project_id: int, standort: Optional[str] = None) -> Dict[str, Any]:
    """
    Erstellt leeres Projekt-Datenmodell
    """
    return {
        "projekt": {
            "id": f"PROJ_{project_id:06d}",
            "name": project_name,
            "beschreibung": "",
            "standort": standort or "",
            "version": 1,
            "dateien": []
        },
        "raeume": [],
        "anlagen": [],
        "geraete": [],
        "anforderungen": [],
        "termine": [],
        "leistungen": [],
        "risiken": [],
        "pruefungs_ergebnisse": {
            "konsistenz_ok": None,
            "fehler": [],
            "warnungen": [],
            "hinweise": []
        }
    }
