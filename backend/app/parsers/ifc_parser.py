"""
IFC-Parser
Verwendet IfcOpenShell für BIM-Daten
"""

from typing import Dict, Any, List, Optional
from io import BytesIO
from app.models.project import ProjectFile
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

# Optional import - ifcopenshell might not be installed
try:
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.pset
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False
    ifcopenshell = None


class IFCParser:
    """Parser für IFC-Dateien (Building Information Models)"""
    
    async def parse(self, file_content: bytes, file_obj: ProjectFile) -> Dict[str, Any]:
        """
        Extrahiert Daten aus IFC-Datei
        Returns: Dict mit extrahierten Entitäten
        """
        logger.info(f"Starte IFC-Extraktion für Datei: {file_obj.original_filename} (ID: {file_obj.id})")
        logger.info(f"Dateigröße: {len(file_content)} Bytes")
        
        if not IFC_AVAILABLE:
            error_msg = "ifcopenshell ist nicht installiert. Bitte installieren Sie es mit: pip install ifcopenshell"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        source_info = {
            "datei": file_obj.original_filename,
            "datei_id": file_obj.id,
            "upload_am": file_obj.upload_date.isoformat() if file_obj.upload_date else None
        }
        
        extracted_data = {
            "raeume": [],
            "anlagen": [],
            "geraete": [],
            "anforderungen": [],
            "termine": []
        }
        
        # IFC-Datei öffnen
        # ifcopenshell.open() benötigt einen Dateipfad
        # BytesIO funktioniert möglicherweise nicht direkt, daher verwenden wir eine temporäre Datei
        ifc_file = None
        temp_file_path = None
        
        try:
            # Erstelle temporäre Datei
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.ifc', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            logger.debug(f"Temporäre IFC-Datei erstellt: {temp_file_path}")
            
            # Versuche mit Dateipfad zu öffnen
            try:
                logger.debug("Versuche IFC-Datei mit ifcopenshell.open() zu öffnen...")
                ifc_file = ifcopenshell.open(temp_file_path)
                logger.info("IFC-Datei erfolgreich geöffnet")
            except Exception as e:
                logger.warning(f"Fehler beim Öffnen mit ifcopenshell.open(): {str(e)}")
                # Fallback: Versuche als String zu öffnen (für IFC-SPF Format)
                try:
                    logger.debug("Versuche IFC-Datei als String zu öffnen...")
                    # Versuche zu dekodieren - IFC-Dateien können UTF-8 oder ISO-8859-1 sein
                    try:
                        decoded_content = file_content.decode('utf-8', errors='ignore')
                    except Exception:
                        decoded_content = file_content.decode('iso-8859-1', errors='ignore')
                    
                    ifc_file = ifcopenshell.file.from_string(decoded_content)
                    logger.info("IFC-Datei erfolgreich als String geöffnet")
                except Exception as e2:
                    error_msg = f"Konnte IFC-Datei nicht öffnen. Dateipfad Fehler: {str(e)}, String Fehler: {str(e2)}"
                    logger.error(error_msg, exc_info=True)
                    raise ValueError(error_msg)
            
            if not ifc_file:
                error_msg = "IFC-Datei konnte nicht geöffnet werden (unbekannter Fehler)"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Prüfe IFC-Schema
            schema = None
            try:
                schema = ifc_file.schema
                logger.info(f"IFC-Schema erkannt: {schema}")
            except Exception as e:
                logger.warning(f"Konnte IFC-Schema nicht ermitteln: {str(e)}")
            
            # Räume (IfcSpace) extrahieren
            try:
                logger.debug("Extrahiere Räume (IfcSpace)...")
                raeume = self._extract_spaces(ifc_file, source_info)
                extracted_data["raeume"].extend(raeume)
                logger.info(f"{len(raeume)} Räume extrahiert")
            except Exception as e:
                logger.error(f"Fehler beim Extrahieren von Räumen: {str(e)}", exc_info=True)
                # Weiter mit anderen Extraktionen
            
            # Anlagen (IfcSystem) extrahieren
            try:
                logger.debug("Extrahiere Anlagen (IfcSystem)...")
                anlagen = self._extract_systems(ifc_file, source_info)
                extracted_data["anlagen"].extend(anlagen)
                logger.info(f"{len(anlagen)} Anlagen extrahiert")
            except Exception as e:
                logger.error(f"Fehler beim Extrahieren von Anlagen: {str(e)}", exc_info=True)
                # Weiter mit anderen Extraktionen
            
            # Geräte (IfcMechanicalEquipment, IfcFlowTerminal) extrahieren
            try:
                logger.debug("Extrahiere Geräte...")
                geraete = self._extract_equipment(ifc_file, source_info, schema)
                extracted_data["geraete"].extend(geraete)
                logger.info(f"{len(geraete)} Geräte extrahiert")
            except Exception as e:
                logger.error(f"Fehler beim Extrahieren von Geräten: {str(e)}", exc_info=True)
                # Weiter mit anderen Extraktionen
            
            # Raum-Anlagen-Zuordnungen extrahieren
            try:
                logger.debug("Extrahiere Raum-Anlagen-Zuordnungen...")
                self._extract_space_equipment_relations(ifc_file, extracted_data)
                logger.info("Raum-Anlagen-Zuordnungen extrahiert")
            except Exception as e:
                logger.error(f"Fehler beim Extrahieren von Raum-Anlagen-Zuordnungen: {str(e)}", exc_info=True)
                # Nicht kritisch
            
            total_extracted = (
                len(extracted_data["raeume"]) +
                len(extracted_data["anlagen"]) +
                len(extracted_data["geraete"]) +
                len(extracted_data["anforderungen"]) +
                len(extracted_data["termine"])
            )
            
            if total_extracted == 0:
                logger.warning(f"Keine Daten aus IFC-Datei extrahiert. Möglicherweise enthält die Datei keine relevanten Elemente.")
            else:
                logger.info(f"IFC-Extraktion abgeschlossen: {total_extracted} Entitäten insgesamt extrahiert")
            
            return extracted_data
        
        finally:
            # Lösche temporäre Datei nach der Extraktion (auch im Fehlerfall)
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Temporäre Datei gelöscht: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Konnte temporäre Datei nicht löschen: {str(e)}")
    
    def _get_property_set(self, element, pset_name: str) -> Optional[Dict[str, Any]]:
        """Holt Property Set für ein Element"""
        try:
            psets = ifcopenshell.util.element.get_psets(element)
            return psets.get(pset_name)
        except Exception:
            return None
    
    def _get_property(self, element, prop_name: str, pset_name: Optional[str] = None) -> Optional[Any]:
        """Holt eine Property aus Property Sets"""
        try:
            if pset_name:
                pset = self._get_property_set(element, pset_name)
                if pset:
                    return pset.get(prop_name)
            else:
                # Durch alle Property Sets suchen
                psets = ifcopenshell.util.element.get_psets(element)
                for pset in psets.values():
                    if prop_name in pset:
                        return pset[prop_name]
        except Exception:
            pass
        return None
    
    def _extract_spaces(self, ifc_file, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrahiert Räume (IfcSpace) aus IFC mit Property Sets"""
        raeume = []
        
        try:
            spaces = ifc_file.by_type("IfcSpace")
            logger.debug(f"Gefundene IfcSpace-Objekte: {len(spaces)}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von IfcSpace-Objekten: {str(e)}", exc_info=True)
            return raeume
        
        for space in spaces:
            try:
                # Basis-Informationen
                raum = {
                    "id": f"Raum_{space.GlobalId}",
                    "name": space.LongName or space.Name or "",
                    "nummer": space.Name or "",
                    "ifc_guid": space.GlobalId,
                    "quelle": {
                        **source_info,
                        "ifc_guid": space.GlobalId,
                        "objekt": "IfcSpace"
                    }
                }
                
                # Property Sets extrahieren
                # Pset_SpaceCommon
                pset_common = self._get_property_set(space, "Pset_SpaceCommon")
                if pset_common:
                    raum["nutzungsart"] = pset_common.get("Usage")
                    raum["geschoss"] = pset_common.get("Level")
                
                # Fläche aus Property Sets
                flaeche = self._get_property(space, "NetFloorArea") or self._get_property(space, "GrossFloorArea")
                if flaeche:
                    raum["flaeche_m2"] = float(flaeche)
                
                # Volumen
                volumen = self._get_property(space, "NetVolume") or self._get_property(space, "GrossVolume")
                if volumen:
                    raum["volumen_m3"] = float(volumen)
                
                # Höhe
                hoehe = self._get_property(space, "Height")
                if hoehe:
                    raum["hoehe_m"] = float(hoehe)
                
                # Zone (IfcZone)
                zone = self._get_space_zone(ifc_file, space)
                if zone:
                    raum["zone"] = zone
                
                # Geschoss aus IfcBuildingStorey
                storey = self._get_space_storey(ifc_file, space)
                if storey:
                    raum["geschoss"] = storey
                
                raeume.append(raum)
            except Exception as e:
                logger.warning(f"Fehler beim Extrahieren eines Raumes (GUID: {getattr(space, 'GlobalId', 'unbekannt')}): {str(e)}", exc_info=True)
                # Weiter mit nächstem Raum
                continue
        
        return raeume
    
    def _get_space_zone(self, ifc_file, space) -> Optional[str]:
        """Holt die Zone eines Raumes"""
        try:
            # Suche IfcZone über IfcRelAssignsToGroup
            for rel in ifc_file.by_type("IfcRelAssignsToGroup"):
                if space in rel.RelatedObjects:
                    group = rel.RelatingGroup
                    if group.is_a("IfcZone"):
                        return group.Name or group.GlobalId
        except Exception:
            pass
        return None
    
    def _get_space_storey(self, ifc_file, space) -> Optional[str]:
        """Holt das Geschoss eines Raumes"""
        try:
            # Suche IfcBuildingStorey über Containment
            for rel in ifc_file.by_type("IfcRelContainedInSpatialStructure"):
                if space in rel.RelatedElements:
                    structure = rel.RelatingStructure
                    if structure.is_a("IfcBuildingStorey"):
                        return structure.Name or structure.GlobalId
        except Exception:
            pass
        return None
    
    def _extract_systems(self, ifc_file, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrahiert HLKS-Systeme (IfcSystem) aus IFC"""
        anlagen = []
        
        try:
            systems = ifc_file.by_type("IfcSystem")
            logger.debug(f"Gefundene IfcSystem-Objekte: {len(systems)}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von IfcSystem-Objekten: {str(e)}", exc_info=True)
            return anlagen
        
        for system in systems:
            try:
                # Nur HLKS-Systeme (Heating, Ventilation, Air Conditioning, Plumbing)
                system_type = system.get_info().get("SystemType", "")
                if not any(kw in system_type.lower() for kw in ["hvac", "heating", "ventilation", "plumbing", "sanitär"]):
                    continue
                
                anlage = {
                    "id": f"ANL_{system.GlobalId}",
                    "typ": system_type or system.Name or "HLKS-System",
                    "name": system.Name or "",
                    "system_id": system.GlobalId,
                    "ifc_guid": system.GlobalId,
                    "quelle": {
                        **source_info,
                        "ifc_guid": system.GlobalId,
                        "objekt": "IfcSystem"
                    }
                }
                
                # Property Sets für Systeme
                leistung = self._get_property(system, "TotalPower") or self._get_property(system, "Power")
                if leistung:
                    anlage["leistung_kw"] = float(leistung)
                
                volumenstrom = self._get_property(system, "AirFlowRate") or self._get_property(system, "FlowRate")
                if volumenstrom:
                    anlage["leistung_m3_h"] = float(volumenstrom)
                
                anlagen.append(anlage)
            except Exception as e:
                logger.warning(f"Fehler beim Extrahieren eines Systems (GUID: {getattr(system, 'GlobalId', 'unbekannt')}): {str(e)}", exc_info=True)
                # Weiter mit nächstem System
                continue
        
        return anlagen
    
    def _extract_equipment(self, ifc_file, source_info: Dict[str, Any], schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extrahiert Geräte aus IFC - unterstützt verschiedene IFC-Schemas"""
        geraete = []
        
        # IfcMechanicalEquipment existiert nur in IFC4 und höher
        # In IFC2X3 gibt es stattdessen IfcFlowMovingDevice, IfcPump, IfcFan, etc.
        equipment = []
        
        if schema and schema.startswith("IFC2X3"):
            # IFC2X3: Verwende alternative Entities
            logger.debug("IFC2X3 erkannt - verwende IFC2X3-spezifische Equipment-Entities")
            equipment_types = [
                "IfcFlowMovingDevice",  # Pumps, Fans, etc.
                "IfcPump",
                "IfcFan",
                "IfcCompressor",
                "IfcFlowController",  # Valves, Dampers, etc.
            ]
            for eq_type in equipment_types:
                try:
                    found = ifc_file.by_type(eq_type)
                    equipment.extend(found)
                    if found:
                        logger.debug(f"Gefundene {eq_type}-Objekte: {len(found)}")
                except Exception as e:
                    logger.debug(f"Entity {eq_type} nicht verfügbar: {str(e)}")
                    continue
        else:
            # IFC4 oder höher: Verwende IfcMechanicalEquipment
            # ABER: Prüfe zuerst, ob das Schema wirklich IFC4 ist
            # Wenn schema None ist oder nicht IFC4, versuche zuerst IFC2X3-Typen
            if schema and not schema.startswith("IFC2X3"):
                # Schema ist IFC4 oder höher
                try:
                    equipment = ifc_file.by_type("IfcMechanicalEquipment")
                    logger.debug(f"Gefundene IfcMechanicalEquipment-Objekte: {len(equipment)}")
                except Exception as e:
                    error_msg = str(e)
                    logger.debug(f"IfcMechanicalEquipment nicht verfügbar: {error_msg}")
                    # Wenn Fehler "not found in schema" enthält, ist es wahrscheinlich IFC2X3
                    if "not found in schema" in error_msg.lower() or "IFC2X3" in error_msg.upper():
                        logger.info("Schema scheint IFC2X3 zu sein, verwende IFC2X3-Typen")
                        schema = "IFC2X3"  # Aktualisiere Schema-Erkennung
                        # Verwende IFC2X3-Typen
                        equipment_types = ["IfcFlowMovingDevice", "IfcPump", "IfcFan", "IfcCompressor", "IfcFlowController"]
                        for eq_type in equipment_types:
                            try:
                                found = ifc_file.by_type(eq_type)
                                equipment.extend(found)
                                if found:
                                    logger.debug(f"Gefundene {eq_type}-Objekte: {len(found)}")
                            except Exception:
                                continue
                    else:
                        # Anderer Fehler - versuche Fallback
                        equipment_types = ["IfcFlowMovingDevice", "IfcFlowController"]
                        for eq_type in equipment_types:
                            try:
                                found = ifc_file.by_type(eq_type)
                                equipment.extend(found)
                                if found:
                                    logger.debug(f"Gefundene {eq_type}-Objekte (Fallback): {len(found)}")
                            except Exception:
                                continue
            else:
                # Schema ist unbekannt oder könnte IFC2X3 sein - versuche zuerst IFC2X3-Typen
                logger.debug("Schema unbekannt oder möglicherweise IFC2X3 - versuche IFC2X3-Typen zuerst")
                equipment_types = ["IfcFlowMovingDevice", "IfcPump", "IfcFan", "IfcCompressor", "IfcFlowController"]
                for eq_type in equipment_types:
                    try:
                        found = ifc_file.by_type(eq_type)
                        equipment.extend(found)
                        if found:
                            logger.debug(f"Gefundene {eq_type}-Objekte: {len(found)}")
                    except Exception:
                        continue
                
                # Wenn keine IFC2X3-Geräte gefunden wurden, versuche IFC4
                if len(equipment) == 0:
                    try:
                        equipment = ifc_file.by_type("IfcMechanicalEquipment")
                        logger.debug(f"Gefundene IfcMechanicalEquipment-Objekte: {len(equipment)}")
                    except Exception as e:
                        logger.debug(f"IfcMechanicalEquipment nicht verfügbar: {str(e)}")
        
        for eq in equipment:
            try:
                geraet = {
                    "id": f"GER_{eq.GlobalId}",
                    "typ": eq.ObjectType or eq.Name or "Mechanisches Gerät",
                    "name": eq.Name or "",
                    "ifc_guid": eq.GlobalId,
                    "quelle": {
                        **source_info,
                        "ifc_guid": eq.GlobalId,
                        "objekt": eq.is_a()  # Verwende den tatsächlichen Typ
                    }
                }
                
                # Property Sets
                pset_mech = self._get_property_set(eq, "Pset_MechanicalEquipment")
                if pset_mech:
                    leistung = pset_mech.get("Power") or pset_mech.get("TotalPower")
                    if leistung:
                        geraet["leistung_kw"] = float(leistung)
                
                geraete.append(geraet)
            except Exception as e:
                logger.warning(f"Fehler beim Extrahieren eines Gerätes (GUID: {getattr(eq, 'GlobalId', 'unbekannt')}): {str(e)}", exc_info=True)
                # Weiter mit nächstem Gerät
                continue
        
        # IfcFlowTerminal (Lüftungsauslässe, etc.)
        try:
            terminals = ifc_file.by_type("IfcFlowTerminal")
            logger.debug(f"Gefundene IfcFlowTerminal-Objekte: {len(terminals)}")
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von IfcFlowTerminal-Objekten: {str(e)}", exc_info=True)
            terminals = []
        
        for terminal in terminals:
            try:
                geraet = {
                    "id": f"GER_{terminal.GlobalId}",
                    "typ": terminal.ObjectType or terminal.Name or "Flow Terminal",
                    "name": terminal.Name or "",
                    "ifc_guid": terminal.GlobalId,
                    "quelle": {
                        **source_info,
                        "ifc_guid": terminal.GlobalId,
                        "objekt": "IfcFlowTerminal"
                    }
                }
                
                # Property Sets für Flow Terminals
                pset_flow = self._get_property_set(terminal, "Pset_FlowTerminal")
                if pset_flow:
                    leistung = pset_flow.get("FlowRate") or pset_flow.get("AirFlowRate")
                    if leistung:
                        geraet["leistung_m3_h"] = float(leistung)
                
                geraete.append(geraet)
            except Exception as e:
                logger.warning(f"Fehler beim Extrahieren eines Flow Terminals (GUID: {getattr(terminal, 'GlobalId', 'unbekannt')}): {str(e)}", exc_info=True)
                # Weiter mit nächstem Terminal
                continue
        
        return geraete
    
    def _extract_space_equipment_relations(self, ifc_file, extracted_data: Dict[str, Any]):
        """Extrahiert Beziehungen zwischen Räumen und Anlagen/Geräten"""
        # IfcRelServicesBuildings - verbindet Systeme mit Gebäuden/Räumen
        for rel in ifc_file.by_type("IfcRelServicesBuildings"):
            system = rel.RelatingSystem
            if not system or not system.is_a("IfcSystem"):
                continue
            
            system_id = system.GlobalId
            
            # Finde System in extrahierten Anlagen
            anlage = None
            for anl in extracted_data["anlagen"]:
                if anl.get("ifc_guid") == system_id:
                    anlage = anl
                    break
            
            if not anlage:
                continue
            
            # Verbundene Räume finden
            for element in rel.RelatedBuildingElement:
                if element.is_a("IfcSpace"):
                    space_id = element.GlobalId
                    # Finde Raum in extrahierten Räumen
                    for raum in extracted_data["raeume"]:
                        if raum.get("ifc_guid") == space_id:
                            # Zuordnung hinzufügen
                            if "zugehoerige_raeume" not in anlage:
                                anlage["zugehoerige_raeume"] = []
                            if raum["id"] not in anlage["zugehoerige_raeume"]:
                                anlage["zugehoerige_raeume"].append(raum["id"])
                            
                            if "zugehoerige_anlagen" not in raum:
                                raum["zugehoerige_anlagen"] = []
                            if anlage["id"] not in raum["zugehoerige_anlagen"]:
                                raum["zugehoerige_anlagen"].append(anlage["id"])
                            break
