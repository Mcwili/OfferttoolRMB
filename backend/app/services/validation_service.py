"""
Validierungs-Service
Führt Konsistenzprüfungen und YAML-Abgleich durch
"""

from typing import Dict, Any, List
from pydantic import BaseModel
import yaml
import os


class ValidationIssue(BaseModel):
    """Einzelnes Validierungsproblem"""
    kategorie: str
    beschreibung: str
    fundstellen: List[str]
    schweregrad: str
    empfehlung: str
    betroffene_entitaet: str | None = None


class ValidationService:
    """Service für Projekt-Validierung"""
    
    def __init__(self):
        import os
        from pathlib import Path
        # YAML-Offertvorgabe laden
        config_dir = Path(__file__).parent.parent.parent / "config"
        self.offerte_spec_path = config_dir / "offerte_spec.yaml"
        self.offerte_spec = None
        if self.offerte_spec_path.exists():
            with open(self.offerte_spec_path, 'r', encoding='utf-8') as f:
                self.offerte_spec = yaml.safe_load(f)
    
    async def validate_project_data(self, project_data: Dict[str, Any]) -> Dict[str, List[ValidationIssue]]:
        """
        Führt alle Validierungsprüfungen durch
        Returns: Dict mit fehler, warnungen, hinweise und konsistenz_ok Flag
        """
        fehler = []
        warnungen = []
        hinweise = []
        
        # 1. Datenkonsistenz prüfen
        consistency_issues = self._check_data_consistency(project_data)
        fehler.extend([i for i in consistency_issues if i.schweregrad == "kritisch"])
        warnungen.extend([i for i in consistency_issues if i.schweregrad == "warnung"])
        
        # 2. Referenzintegrität prüfen
        reference_issues = self._check_reference_integrity(project_data)
        fehler.extend([i for i in reference_issues if i.schweregrad == "kritisch"])
        warnungen.extend([i for i in reference_issues if i.schweregrad == "warnung"])
        
        # 3. Numerische Plausibilität prüfen
        plausibility_issues = self._check_numerical_plausibility(project_data)
        warnungen.extend([i for i in plausibility_issues if i.schweregrad == "warnung"])
        hinweise.extend([i for i in plausibility_issues if i.schweregrad == "hinweis"])
        
        # 4. YAML-Offertvorgabe abgleichen (falls vorhanden)
        if self.offerte_spec:
            yaml_issues = await self._check_offerte_spec(project_data)
            fehler.extend([i for i in yaml_issues if i.schweregrad == "kritisch"])
            warnungen.extend([i for i in yaml_issues if i.schweregrad == "warnung"])
        
        konsistenz_ok = len(fehler) == 0
        
        return {
            "konsistenz_ok": konsistenz_ok,
            "fehler": fehler,
            "warnungen": warnungen,
            "hinweise": hinweise
        }
    
    def _check_data_consistency(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Prüft Datenkonsistenz (z.B. gleiche Raumnummern müssen gleiche Fläche haben)"""
        issues = []
        
        # Räume: Gleiche ID/Nummer muss gleiche Fläche haben
        raeume = data.get("raeume", [])
        raum_dict = {}
        raum_by_nummer = {}
        
        for raum in raeume:
            raum_id = raum.get("id")
            raum_nummer = raum.get("nummer", "").lower()
            flaeche = raum.get("flaeche_m2")
            volumen = raum.get("volumen_m3")
            hoehe = raum.get("hoehe_m")
            
            # Prüfe ID-Duplikate
            if raum_id in raum_dict:
                existing = raum_dict[raum_id]
                existing_flaeche = existing.get("flaeche_m2")
                if existing_flaeche and flaeche and abs(existing_flaeche - flaeche) > 0.1:
                    issues.append(ValidationIssue(
                        kategorie="Widerspruch",
                        beschreibung=f"Raum {raum_id} hat unterschiedliche Flächenangaben: {existing_flaeche} m² vs {flaeche} m²",
                        fundstellen=self._get_fundstellen([existing, raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Flächenangabe für Raum {raum_id} prüfen und vereinheitlichen",
                        betroffene_entitaet=raum_id
                    ))
            else:
                raum_dict[raum_id] = raum
            
            # Prüfe Nummer-Duplikate
            if raum_nummer and raum_nummer in raum_by_nummer:
                existing = raum_by_nummer[raum_nummer]
                existing_flaeche = existing.get("flaeche_m2")
                if existing_flaeche and flaeche and abs(existing_flaeche - flaeche) > 0.1:
                    issues.append(ValidationIssue(
                        kategorie="Widerspruch",
                        beschreibung=f"Raum mit Nummer '{raum_nummer}' hat unterschiedliche Flächenangaben: {existing_flaeche} m² vs {flaeche} m²",
                        fundstellen=self._get_fundstellen([existing, raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Flächenangabe für Raum {raum_nummer} prüfen und vereinheitlichen",
                        betroffene_entitaet=raum_id
                    ))
            else:
                raum_by_nummer[raum_nummer] = raum
            
            # Prüfe Volumen = Fläche × Höhe (wenn alle vorhanden)
            if flaeche and hoehe and volumen:
                expected_volumen = flaeche * hoehe
                if abs(volumen - expected_volumen) > 0.5:  # Toleranz 0.5 m³
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Raum {raum_id}: Volumen ({volumen} m³) stimmt nicht mit Fläche × Höhe ({expected_volumen} m³) überein",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="warnung",
                        empfehlung=f"Bitte Volumen oder Höhe für Raum {raum_id} prüfen",
                        betroffene_entitaet=raum_id
                    ))
        
        # Anlagen: Gleiche ID muss gleiche Leistung haben
        anlagen = data.get("anlagen", [])
        anlage_dict = {}
        
        for anlage in anlagen:
            anlage_id = anlage.get("id")
            leistung_kw = anlage.get("leistung_kw")
            
            if anlage_id in anlage_dict:
                existing = anlage_dict[anlage_id]
                existing_leistung = existing.get("leistung_kw")
                if existing_leistung and leistung_kw and abs(existing_leistung - leistung_kw) > 0.1:
                    issues.append(ValidationIssue(
                        kategorie="Widerspruch",
                        beschreibung=f"Anlage {anlage_id} hat unterschiedliche Leistungsangaben: {existing_leistung} kW vs {leistung_kw} kW",
                        fundstellen=self._get_fundstellen([existing, anlage]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Leistungsangabe für Anlage {anlage_id} prüfen und vereinheitlichen",
                        betroffene_entitaet=anlage_id
                    ))
            else:
                anlage_dict[anlage_id] = anlage
        
        return issues
    
    def _get_fundstellen(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Extrahiert Fundstellen aus Entitäten"""
        fundstellen = []
        for entity in entities:
            quelle = entity.get("quelle", {})
            if isinstance(quelle, dict):
                datei = quelle.get("datei", "unbekannt")
                if datei not in fundstellen:
                    fundstellen.append(datei)
            elif isinstance(quelle, list):
                for q in quelle:
                    datei = q.get("datei", "unbekannt")
                    if datei not in fundstellen:
                        fundstellen.append(datei)
        return fundstellen
    
    def _check_reference_integrity(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Prüft Referenzintegrität (z.B. Gerät referenziert existierenden Raum)"""
        issues = []
        
        raeume_ids = {r.get("id") for r in data.get("raeume", [])}
        anlagen_ids = {a.get("id") for a in data.get("anlagen", [])}
        geraete_ids = {g.get("id") for g in data.get("geraete", [])}
        leistungen_ids = {l.get("id") for l in data.get("leistungen", [])}
        
        # Geräte-Referenzen prüfen
        geraete = data.get("geraete", [])
        for geraet in geraete:
            geraet_id = geraet.get("id")
            zugehoerige_anlage = geraet.get("zugehoerige_anlage")
            zugehoeriger_raum = geraet.get("zugehoeriger_raum")
            
            if not zugehoerige_anlage and not zugehoeriger_raum:
                issues.append(ValidationIssue(
                    kategorie="Fehlende Angabe",
                    beschreibung=f"Gerät {geraet_id} ist keinem Raum oder keiner Anlage zugeordnet",
                    fundstellen=self._get_fundstellen([geraet]),
                    schweregrad="warnung",
                    empfehlung=f"Bitte Zuordnung für Gerät {geraet_id} ergänzen",
                    betroffene_entitaet=geraet_id
                ))
            elif zugehoerige_anlage and zugehoerige_anlage not in anlagen_ids:
                issues.append(ValidationIssue(
                    kategorie="Referenzfehler",
                    beschreibung=f"Gerät {geraet_id} referenziert nicht existierende Anlage {zugehoerige_anlage}",
                    fundstellen=self._get_fundstellen([geraet]),
                    schweregrad="kritisch",
                    empfehlung=f"Bitte Anlage {zugehoerige_anlage} prüfen oder Gerät korrigieren",
                    betroffene_entitaet=geraet_id
                ))
            elif zugehoeriger_raum and zugehoeriger_raum not in raeume_ids:
                issues.append(ValidationIssue(
                    kategorie="Referenzfehler",
                    beschreibung=f"Gerät {geraet_id} referenziert nicht existierenden Raum {zugehoeriger_raum}",
                    fundstellen=self._get_fundstellen([geraet]),
                    schweregrad="kritisch",
                    empfehlung=f"Bitte Raum {zugehoeriger_raum} prüfen oder Gerät korrigieren",
                    betroffene_entitaet=geraet_id
                ))
        
        # Anlagen-Referenzen prüfen
        anlagen = data.get("anlagen", [])
        for anlage in anlagen:
            anlage_id = anlage.get("id")
            zugehoerige_raeume = anlage.get("zugehoerige_raeume", [])
            zugehoerige_geraete = anlage.get("zugehoerige_geraete", [])
            
            for raum_id in zugehoerige_raeume:
                if raum_id not in raeume_ids:
                    issues.append(ValidationIssue(
                        kategorie="Referenzfehler",
                        beschreibung=f"Anlage {anlage_id} referenziert nicht existierenden Raum {raum_id}",
                        fundstellen=self._get_fundstellen([anlage]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Raum {raum_id} prüfen oder Anlage korrigieren",
                        betroffene_entitaet=anlage_id
                    ))
            
            for geraet_id in zugehoerige_geraete:
                if geraet_id not in geraete_ids:
                    issues.append(ValidationIssue(
                        kategorie="Referenzfehler",
                        beschreibung=f"Anlage {anlage_id} referenziert nicht existierendes Gerät {geraet_id}",
                        fundstellen=self._get_fundstellen([anlage]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Gerät {geraet_id} prüfen oder Anlage korrigieren",
                        betroffene_entitaet=anlage_id
                    ))
        
        # Räume-Referenzen prüfen
        raeume = data.get("raeume", [])
        for raum in raeume:
            raum_id = raum.get("id")
            zugehoerige_anlagen = raum.get("zugehoerige_anlagen", [])
            zugehoerige_geraete = raum.get("zugehoerige_geraete", [])
            
            for anlage_id in zugehoerige_anlagen:
                if anlage_id not in anlagen_ids:
                    issues.append(ValidationIssue(
                        kategorie="Referenzfehler",
                        beschreibung=f"Raum {raum_id} referenziert nicht existierende Anlage {anlage_id}",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Anlage {anlage_id} prüfen oder Raum korrigieren",
                        betroffene_entitaet=raum_id
                    ))
            
            for geraet_id in zugehoerige_geraete:
                if geraet_id not in geraete_ids:
                    issues.append(ValidationIssue(
                        kategorie="Referenzfehler",
                        beschreibung=f"Raum {raum_id} referenziert nicht existierendes Gerät {geraet_id}",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Gerät {geraet_id} prüfen oder Raum korrigieren",
                        betroffene_entitaet=raum_id
                    ))
        
        # Termine-Referenzen prüfen
        termine = data.get("termine", [])
        for termin in termine:
            termin_id = termin.get("id")
            zugehoerige_leistung = termin.get("zugehoerige_leistung")
            
            if zugehoerige_leistung and zugehoerige_leistung not in leistungen_ids:
                issues.append(ValidationIssue(
                    kategorie="Referenzfehler",
                    beschreibung=f"Termin {termin_id} referenziert nicht existierende Leistung {zugehoerige_leistung}",
                    fundstellen=self._get_fundstellen([termin]),
                    schweregrad="warnung",
                    empfehlung=f"Bitte Leistung {zugehoerige_leistung} prüfen oder Termin korrigieren",
                    betroffene_entitaet=termin_id
                ))
        
        return issues
    
    def _check_numerical_plausibility(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Prüft numerische Plausibilität (z.B. Flächen > 0, realistische Werte)"""
        issues = []
        
        # Raumflächen müssen positiv und realistisch sein
        for raum in data.get("raeume", []):
            raum_id = raum.get("id")
            flaeche = raum.get("flaeche_m2")
            volumen = raum.get("volumen_m3")
            hoehe = raum.get("hoehe_m")
            
            if flaeche is not None:
                if flaeche <= 0:
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Raum {raum_id} hat ungültige Fläche: {flaeche} m² (muss > 0 sein)",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Fläche für Raum {raum_id} prüfen",
                        betroffene_entitaet=raum_id
                    ))
                elif flaeche > 10000:  # Unrealistisch große Fläche
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Raum {raum_id} hat sehr große Fläche: {flaeche} m² (ungewöhnlich)",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="hinweis",
                        empfehlung=f"Bitte Fläche für Raum {raum_id} überprüfen",
                        betroffene_entitaet=raum_id
                    ))
            
            if volumen is not None and volumen <= 0:
                issues.append(ValidationIssue(
                    kategorie="Plausibilitätsfehler",
                    beschreibung=f"Raum {raum_id} hat ungültiges Volumen: {volumen} m³ (muss > 0 sein)",
                    fundstellen=self._get_fundstellen([raum]),
                    schweregrad="kritisch",
                    empfehlung=f"Bitte Volumen für Raum {raum_id} prüfen",
                    betroffene_entitaet=raum_id
                ))
            
            if hoehe is not None:
                if hoehe <= 0:
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Raum {raum_id} hat ungültige Höhe: {hoehe} m (muss > 0 sein)",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Höhe für Raum {raum_id} prüfen",
                        betroffene_entitaet=raum_id
                    ))
                elif hoehe > 10:  # Unrealistisch hohe Raumhöhe
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Raum {raum_id} hat sehr hohe Raumhöhe: {hoehe} m (ungewöhnlich)",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="hinweis",
                        empfehlung=f"Bitte Höhe für Raum {raum_id} überprüfen",
                        betroffene_entitaet=raum_id
                    ))
        
        # Anlagen-Leistungen müssen positiv und realistisch sein
        for anlage in data.get("anlagen", []):
            anlage_id = anlage.get("id")
            leistung_kw = anlage.get("leistung_kw")
            leistung_m3_h = anlage.get("leistung_m3_h")
            
            if leistung_kw is not None:
                if leistung_kw < 0:
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Anlage {anlage_id} hat negative Leistung: {leistung_kw} kW",
                        fundstellen=self._get_fundstellen([anlage]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte Leistung für Anlage {anlage_id} prüfen",
                        betroffene_entitaet=anlage_id
                    ))
                elif leistung_kw > 10000:  # Sehr große Leistung
                    issues.append(ValidationIssue(
                        kategorie="Plausibilitätsfehler",
                        beschreibung=f"Anlage {anlage_id} hat sehr große Leistung: {leistung_kw} kW (ungewöhnlich)",
                        fundstellen=self._get_fundstellen([anlage]),
                        schweregrad="hinweis",
                        empfehlung=f"Bitte Leistung für Anlage {anlage_id} überprüfen",
                        betroffene_entitaet=anlage_id
                    ))
            
            if leistung_m3_h is not None and leistung_m3_h < 0:
                issues.append(ValidationIssue(
                    kategorie="Plausibilitätsfehler",
                    beschreibung=f"Anlage {anlage_id} hat negativen Volumenstrom: {leistung_m3_h} m³/h",
                    fundstellen=self._get_fundstellen([anlage]),
                    schweregrad="kritisch",
                    empfehlung=f"Bitte Volumenstrom für Anlage {anlage_id} prüfen",
                    betroffene_entitaet=anlage_id
                ))
        
        # Geräte-Leistungen prüfen
        for geraet in data.get("geraete", []):
            geraet_id = geraet.get("id")
            leistung_kw = geraet.get("leistung_kw")
            
            if leistung_kw is not None and leistung_kw < 0:
                issues.append(ValidationIssue(
                    kategorie="Plausibilitätsfehler",
                    beschreibung=f"Gerät {geraet_id} hat negative Leistung: {leistung_kw} kW",
                    fundstellen=self._get_fundstellen([geraet]),
                    schweregrad="kritisch",
                    empfehlung=f"Bitte Leistung für Gerät {geraet_id} prüfen",
                    betroffene_entitaet=geraet_id
                ))
        
        return issues
    
    async def _check_offerte_spec(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Prüft Abgleich mit YAML-Offertvorgabe"""
        issues = []
        
        if not self.offerte_spec:
            return issues
        
        mindestanforderungen = self.offerte_spec.get("mindestanforderungen", {})
        
        # Projekt-Parameter prüfen
        projekt = data.get("projekt", {})
        projekt_felder = mindestanforderungen.get("projekt", {}).get("erforderliche_felder", [])
        for feld in projekt_felder:
            if feld not in projekt or not projekt[feld]:
                issues.append(ValidationIssue(
                    kategorie="Fehlende Angabe",
                    beschreibung=f"Projekt-Parameter '{feld}' fehlt (erforderlich für Offerte)",
                    fundstellen=[],
                    schweregrad="kritisch",
                    empfehlung=f"Bitte '{feld}' für das Projekt ergänzen"
                ))
        
        # Räume prüfen
        raeume = data.get("raeume", [])
        raum_anforderungen = mindestanforderungen.get("raeume", {})
        min_anzahl = raum_anforderungen.get("min_anzahl", 0)
        erforderliche_felder = raum_anforderungen.get("erforderliche_felder", [])
        
        if len(raeume) < min_anzahl:
            issues.append(ValidationIssue(
                kategorie="Fehlende Angabe",
                beschreibung=f"Mindestens {min_anzahl} Raum/Räume erforderlich, aber nur {len(raeume)} vorhanden",
                fundstellen=[],
                schweregrad="kritisch",
                empfehlung=f"Bitte mindestens {min_anzahl} Raum/Räume hinzufügen"
            ))
        
        for raum in raeume:
            for feld in erforderliche_felder:
                if feld not in raum or raum[feld] is None:
                    issues.append(ValidationIssue(
                        kategorie="Fehlende Angabe",
                        beschreibung=f"Raum {raum.get('id', 'unbekannt')} hat kein Feld '{feld}' (erforderlich)",
                        fundstellen=self._get_fundstellen([raum]),
                        schweregrad="kritisch",
                        empfehlung=f"Bitte '{feld}' für Raum {raum.get('id')} ergänzen",
                        betroffene_entitaet=raum.get("id")
                    ))
        
        # Anlagen prüfen
        anlagen = data.get("anlagen", [])
        anlage_anforderungen = mindestanforderungen.get("anlagen", {})
        erforderliche_felder_anlage = anlage_anforderungen.get("erforderliche_felder", [])
        
        for anlage in anlagen:
            for feld in erforderliche_felder_anlage:
                if feld not in anlage or anlage[feld] is None:
                    issues.append(ValidationIssue(
                        kategorie="Fehlende Angabe",
                        beschreibung=f"Anlage {anlage.get('id', 'unbekannt')} hat kein Feld '{feld}' (erforderlich)",
                        fundstellen=self._get_fundstellen([anlage]),
                        schweregrad="warnung",
                        empfehlung=f"Bitte '{feld}' für Anlage {anlage.get('id')} ergänzen",
                        betroffene_entitaet=anlage.get("id")
                    ))
        
        return issues
