"""
Intelligentes Daten-Merging Service
Erkennt Duplikate und löst Konflikte beim Zusammenführen von Daten
"""

from typing import Dict, Any, List, Optional, Tuple
from app.models.project import ProjectFile
import difflib


class DataMergingService:
    """Service für intelligentes Daten-Merging"""
    
    def merge_extracted_data(
        self,
        current_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        source_file: ProjectFile
    ) -> Dict[str, Any]:
        """
        Integriert extrahierte Daten ins bestehende JSON-Modell
        Mit intelligenter Duplikat-Erkennung und Konflikt-Auflösung
        """
        source_info = {
            "datei": source_file.original_filename,
            "datei_id": source_file.id,
            "upload_am": source_file.upload_date.isoformat() if source_file.upload_date else None
        }
        
        # Entitäten-Typen verarbeiten
        entity_types = ["raeume", "anlagen", "geraete", "anforderungen", "termine", "leistungen", "images"]
        
        for entity_type in entity_types:
            if entity_type not in current_data:
                current_data[entity_type] = []
            
            if entity_type not in extracted_data:
                continue
            
            # Intelligentes Merging für jeden Entitätstyp
            if entity_type == "raeume":
                current_data[entity_type] = self._merge_raeume(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "anlagen":
                current_data[entity_type] = self._merge_anlagen(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "geraete":
                current_data[entity_type] = self._merge_geraete(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "anforderungen":
                current_data[entity_type] = self._merge_anforderungen(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "termine":
                current_data[entity_type] = self._merge_termine(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "leistungen":
                current_data[entity_type] = self._merge_leistungen(
                    current_data[entity_type],
                    extracted_data[entity_type],
                    source_info
                )
            elif entity_type == "images":
                # Bilder einfach hinzufügen (keine Duplikat-Erkennung nötig)
                if entity_type not in current_data:
                    current_data[entity_type] = []
                for img in extracted_data[entity_type]:
                    img["quelle"] = {**source_info, **img.get("quelle", {})}
                    current_data[entity_type].append(img)
        
        # Raw Tables mergen (wichtig: alle Tabellen müssen erhalten bleiben)
        current_data = self._merge_raw_tables(current_data, extracted_data, source_info)
        
        # Metadata mergen (pro Datei speichern)
        current_data = self._merge_metadata(current_data, extracted_data, source_info, source_file.id)
        
        # Full Text mergen (unstrukturierte Textdaten)
        current_data = self._merge_full_text(current_data, extracted_data, source_info)
        
        # Projekt-Metadaten aktualisieren
        if "projekt" in current_data:
            if "dateien" not in current_data["projekt"]:
                current_data["projekt"]["dateien"] = []
            
            file_entry = {
                "name": source_file.original_filename,
                "typ": source_file.file_type,
                "upload_am": source_file.upload_date.isoformat() if source_file.upload_date else None,
                "revision": source_file.revision or "-"
            }
            
            if not any(f["name"] == file_entry["name"] for f in current_data["projekt"]["dateien"]):
                current_data["projekt"]["dateien"].append(file_entry)
        
        return current_data
    
    def _merge_raeume(
        self,
        current_raeume: List[Dict[str, Any]],
        new_raeume: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Räume mit Duplikat-Erkennung"""
        merged = current_raeume.copy()
        
        for new_raum in new_raeume:
            # Quellenverweis hinzufügen
            new_raum["quelle"] = {**source_info, **new_raum.get("quelle", {})}
            
            # Prüfe auf Duplikate
            match, match_idx = self._find_duplicate_raum(new_raum, merged)
            
            if match:
                # Duplikat gefunden - merge Daten
                merged[match_idx] = self._merge_raum_entities(merged[match_idx], new_raum)
            else:
                # Neuer Raum - hinzufügen
                merged.append(new_raum)
        
        return merged
    
    def _find_duplicate_raum(
        self,
        raum: Dict[str, Any],
        existing_raeume: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Findet Duplikat eines Raumes"""
        raum_id = raum.get("id", "")
        raum_name = raum.get("name", "").lower()
        raum_nummer = raum.get("nummer", "").lower()
        raum_ifc_guid = raum.get("ifc_guid")
        
        for idx, existing in enumerate(existing_raeume):
            # Exakte ID-Übereinstimmung
            if existing.get("id") == raum_id:
                return existing, idx
            
            # IFC-GUID Übereinstimmung
            if raum_ifc_guid and existing.get("ifc_guid") == raum_ifc_guid:
                return existing, idx
            
            # Name-Ähnlichkeit (fuzzy matching)
            existing_name = existing.get("name", "").lower()
            existing_nummer = existing.get("nummer", "").lower()
            
            # Exakte Namens- oder Nummer-Übereinstimmung
            if raum_name and existing_name and raum_name == existing_name:
                return existing, idx
            if raum_nummer and existing_nummer and raum_nummer == existing_nummer:
                return existing, idx
            
            # Ähnlichkeitsprüfung (String-Similarity)
            if raum_name and existing_name:
                similarity = difflib.SequenceMatcher(None, raum_name, existing_name).ratio()
                if similarity > 0.8:  # 80% Ähnlichkeit
                    return existing, idx
        
        return None, None
    
    def _merge_raum_entities(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mergt zwei Raum-Entitäten"""
        merged = existing.copy()
        
        # Quellenverweise zusammenführen
        if "quelle" not in merged:
            merged["quelle"] = []
        elif not isinstance(merged["quelle"], list):
            merged["quelle"] = [merged["quelle"]]
        
        if "quelle" in new:
            if isinstance(new["quelle"], list):
                merged["quelle"].extend(new["quelle"])
            else:
                merged["quelle"].append(new["quelle"])
        
        # Felder aktualisieren (neue Werte haben Vorrang, wenn vorhanden)
        for key, value in new.items():
            if key == "quelle" or key == "id":
                continue
            
            if value is not None:
                if key not in merged or merged[key] is None:
                    merged[key] = value
                elif isinstance(value, (int, float)) and isinstance(merged.get(key), (int, float)):
                    # Bei Zahlen: Konflikt markieren wenn unterschiedlich
                    if abs(value - merged[key]) > 0.01:
                        # Konflikt - behalte beide Werte mit Quelle
                        if "konflikte" not in merged:
                            merged["konflikte"] = {}
                        merged["konflikte"][key] = {
                            "alt": merged[key],
                            "neu": value,
                            "quelle_alt": existing.get("quelle", {}),
                            "quelle_neu": new.get("quelle", {})
                        }
        
        return merged
    
    def _merge_anlagen(
        self,
        current_anlagen: List[Dict[str, Any]],
        new_anlagen: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Anlagen mit Duplikat-Erkennung"""
        merged = current_anlagen.copy()
        
        for new_anlage in new_anlagen:
            new_anlage["quelle"] = {**source_info, **new_anlage.get("quelle", {})}
            
            match, match_idx = self._find_duplicate_anlage(new_anlage, merged)
            
            if match:
                merged[match_idx] = self._merge_anlage_entities(merged[match_idx], new_anlage)
            else:
                merged.append(new_anlage)
        
        return merged
    
    def _find_duplicate_anlage(
        self,
        anlage: Dict[str, Any],
        existing_anlagen: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Findet Duplikat einer Anlage"""
        anlage_id = anlage.get("id", "")
        anlage_name = anlage.get("name", "").lower()
        anlage_ifc_guid = anlage.get("ifc_guid")
        anlage_system_id = anlage.get("system_id")
        
        for idx, existing in enumerate(existing_anlagen):
            if existing.get("id") == anlage_id:
                return existing, idx
            
            if anlage_ifc_guid and existing.get("ifc_guid") == anlage_ifc_guid:
                return existing, idx
            
            if anlage_system_id and existing.get("system_id") == anlage_system_id:
                return existing, idx
            
            existing_name = existing.get("name", "").lower()
            if anlage_name and existing_name:
                similarity = difflib.SequenceMatcher(None, anlage_name, existing_name).ratio()
                if similarity > 0.8:
                    return existing, idx
        
        return None, None
    
    def _merge_anlage_entities(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mergt zwei Anlagen-Entitäten"""
        merged = existing.copy()
        
        # Quellenverweise zusammenführen
        if "quelle" not in merged:
            merged["quelle"] = []
        elif not isinstance(merged["quelle"], list):
            merged["quelle"] = [merged["quelle"]]
        
        if "quelle" in new:
            if isinstance(new["quelle"], list):
                merged["quelle"].extend(new["quelle"])
            else:
                merged["quelle"].append(new["quelle"])
        
        # Felder aktualisieren
        for key, value in new.items():
            if key in ["quelle", "id"]:
                continue
            
            if value is not None:
                if key not in merged or merged[key] is None:
                    merged[key] = value
                elif key in ["zugehoerige_raeume", "zugehoerige_geraete"]:
                    # Listen zusammenführen
                    if key not in merged:
                        merged[key] = []
                    merged[key] = list(set(merged[key] + (value if isinstance(value, list) else [value])))
        
        return merged
    
    def _merge_geraete(
        self,
        current_geraete: List[Dict[str, Any]],
        new_geraete: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Geräte mit Duplikat-Erkennung"""
        merged = current_geraete.copy()
        
        for new_geraet in new_geraete:
            new_geraet["quelle"] = {**source_info, **new_geraet.get("quelle", {})}
            
            match, match_idx = self._find_duplicate_geraet(new_geraet, merged)
            
            if match:
                merged[match_idx] = self._merge_geraet_entities(merged[match_idx], new_geraet)
            else:
                merged.append(new_geraet)
        
        return merged
    
    def _find_duplicate_geraet(
        self,
        geraet: Dict[str, Any],
        existing_geraete: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Findet Duplikat eines Geräts"""
        geraet_id = geraet.get("id", "")
        geraet_name = geraet.get("name", "").lower()
        geraet_ifc_guid = geraet.get("ifc_guid")
        
        for idx, existing in enumerate(existing_geraete):
            if existing.get("id") == geraet_id:
                return existing, idx
            
            if geraet_ifc_guid and existing.get("ifc_guid") == geraet_ifc_guid:
                return existing, idx
            
            existing_name = existing.get("name", "").lower()
            existing_typ = existing.get("typ", "").lower()
            geraet_typ = geraet.get("typ", "").lower()
            
            if geraet_name and existing_name and geraet_name == existing_name:
                return existing, idx
            
            if geraet_typ and existing_typ and geraet_typ == existing_typ:
                # Gleicher Typ + gleiche Position könnte Duplikat sein
                # (vereinfacht - könnte verbessert werden)
                similarity = difflib.SequenceMatcher(None, geraet_name, existing_name).ratio()
                if similarity > 0.7:
                    return existing, idx
        
        return None, None
    
    def _merge_geraet_entities(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mergt zwei Gerät-Entitäten"""
        merged = existing.copy()
        
        # Quellenverweise zusammenführen
        if "quelle" not in merged:
            merged["quelle"] = []
        elif not isinstance(merged["quelle"], list):
            merged["quelle"] = [merged["quelle"]]
        
        if "quelle" in new:
            if isinstance(new["quelle"], list):
                merged["quelle"].extend(new["quelle"])
            else:
                merged["quelle"].append(new["quelle"])
        
        # Felder aktualisieren
        for key, value in new.items():
            if key in ["quelle", "id"]:
                continue
            
            if value is not None:
                if key not in merged or merged[key] is None:
                    merged[key] = value
        
        return merged
    
    def _merge_anforderungen(
        self,
        current_anforderungen: List[Dict[str, Any]],
        new_anforderungen: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Anforderungen"""
        merged = current_anforderungen.copy()
        
        for new_anforderung in new_anforderungen:
            new_anforderung["quelle"] = {**source_info, **new_anforderung.get("quelle", {})}
            
            # Anforderungen werden normalerweise nicht als Duplikate behandelt
            # (jede Anforderung ist einzigartig)
            merged.append(new_anforderung)
        
        return merged
    
    def _merge_termine(
        self,
        current_termine: List[Dict[str, Any]],
        new_termine: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Termine"""
        merged = current_termine.copy()
        
        for new_termin in new_termine:
            new_termin["quelle"] = {**source_info, **new_termin.get("quelle", {})}
            
            # Prüfe auf Duplikate basierend auf Beschreibung und Datum
            match, match_idx = self._find_duplicate_termin(new_termin, merged)
            
            if match:
                merged[match_idx] = self._merge_termin_entities(merged[match_idx], new_termin)
            else:
                merged.append(new_termin)
        
        return merged
    
    def _find_duplicate_termin(
        self,
        termin: Dict[str, Any],
        existing_termine: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        """Findet Duplikat eines Termins"""
        termin_beschreibung = termin.get("beschreibung", "").lower()
        termin_datum = termin.get("termin_datum")
        
        for idx, existing in enumerate(existing_termine):
            existing_beschreibung = existing.get("beschreibung", "").lower()
            existing_datum = existing.get("termin_datum")
            
            # Gleiche Beschreibung und Datum = Duplikat
            if termin_beschreibung and existing_beschreibung:
                similarity = difflib.SequenceMatcher(None, termin_beschreibung, existing_beschreibung).ratio()
                if similarity > 0.9 and termin_datum == existing_datum:
                    return existing, idx
        
        return None, None
    
    def _merge_termin_entities(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mergt zwei Termin-Entitäten"""
        merged = existing.copy()
        
        if "quelle" not in merged:
            merged["quelle"] = []
        elif not isinstance(merged["quelle"], list):
            merged["quelle"] = [merged["quelle"]]
        
        if "quelle" in new:
            if isinstance(new["quelle"], list):
                merged["quelle"].extend(new["quelle"])
            else:
                merged["quelle"].append(new["quelle"])
        
        return merged
    
    def _merge_leistungen(
        self,
        current_leistungen: List[Dict[str, Any]],
        new_leistungen: List[Dict[str, Any]],
        source_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mergt Leistungen"""
        merged = current_leistungen.copy()
        
        for new_leistung in new_leistungen:
            new_leistung["quelle"] = {**source_info, **new_leistung.get("quelle", {})}
            merged.append(new_leistung)
        
        return merged
    
    def _merge_raw_tables(
        self,
        current_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mergt raw_tables aus extracted_data in current_data
        Wichtig: Alle Tabellen müssen erhalten bleiben (keine Duplikat-Erkennung)
        """
        if "raw_tables" not in current_data:
            current_data["raw_tables"] = []
        
        if "raw_tables" not in extracted_data:
            return current_data
        
        # Alle raw_tables aus extracted_data hinzufügen
        for table in extracted_data["raw_tables"]:
            # Quelle-Info zu jeder Tabelle hinzufügen
            if "quelle" not in table:
                table["quelle"] = {}
            table["quelle"] = {**source_info, **table.get("quelle", {})}
            current_data["raw_tables"].append(table)
        
        return current_data
    
    def _merge_metadata(
        self,
        current_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        source_info: Dict[str, Any],
        file_id: int
    ) -> Dict[str, Any]:
        """
        Mergt metadata aus extracted_data in current_data
        Metadaten werden pro Datei gespeichert: metadata[file_id] = {...}
        """
        if "metadata" not in current_data:
            current_data["metadata"] = {}
        
        if "metadata" not in extracted_data:
            return current_data
        
        # Metadaten pro Datei speichern
        file_metadata = extracted_data["metadata"].copy()
        
        # Quelle-Info hinzufügen
        file_metadata["quelle"] = {**source_info, **file_metadata.get("quelle", {})}
        
        # Metadaten unter file_id speichern
        current_data["metadata"][str(file_id)] = file_metadata
        
        return current_data
    
    def _merge_full_text(
        self,
        current_data: Dict[str, Any],
        extracted_data: Dict[str, Any],
        source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Mergt full_text aus extracted_data in current_data
        Unstrukturierte Textdaten werden als Array gespeichert mit Quellenangabe
        """
        if "full_text" not in current_data:
            current_data["full_text"] = []
        
        if "full_text" not in extracted_data:
            return current_data
        
        # full_text kann ein Array oder ein String sein
        new_full_text = extracted_data["full_text"]
        
        if isinstance(new_full_text, str):
            # Wenn es ein String ist, in ein Array mit einem Eintrag umwandeln
            if new_full_text.strip():
                current_data["full_text"].append({
                    "content": new_full_text,
                    "quelle": source_info
                })
        elif isinstance(new_full_text, list):
            # Wenn es bereits ein Array ist, alle Einträge hinzufügen
            for text_entry in new_full_text:
                if isinstance(text_entry, str):
                    # Einfacher String - in Dict umwandeln
                    if text_entry.strip():
                        current_data["full_text"].append({
                            "content": text_entry,
                            "quelle": source_info
                        })
                elif isinstance(text_entry, dict):
                    # Bereits ein Dict - Quelle hinzufügen/aktualisieren
                    text_entry["quelle"] = {**source_info, **text_entry.get("quelle", {})}
                    current_data["full_text"].append(text_entry)
        
        return current_data