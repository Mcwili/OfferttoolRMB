# Parser-Dokumentation

## Übersicht

Das System unterstützt verschiedene Dateiformate für die Datenextraktion:

## Unterstützte Formate

### Excel (.xlsx, .xls)

**Erkannte Tabellentypen:**
- Raumlisten
- Gerätelisten
- Anlagenlisten
- Terminpläne
- Leistungsverzeichnisse

**Extraktion:**
- Automatische Tabellenerkennung
- Intelligente Spaltenzuordnung
- Unterstützung für verschiedene Tabellenstrukturen

### Word (.docx)

**Extraktion:**
- Strukturierte Abschnitte (Überschriften-Hierarchie)
- Tabellen
- Listen und Aufzählungen
- Anforderungen aus Text

**NLP-Funktionen:**
- Erkennung von Anforderungen (Muss-/Soll-Anforderungen)
- Kategorisierung
- SIA-Phasen-Erkennung

### PDF-Pläne

**Funktionen:**
- Text-Extraktion (Raumbezeichnungen, Maßangaben)
- Symbol-Erkennung (SIA-Symbole)
- Struktur-Analyse
- OCR-Fallback für gescannte Pläne

**Erkannte Symbole:**
- Lüftungsauslässe
- Heizkörper
- Ventilatoren
- Wärmepumpen
- Lüftungsanlagen

### IFC (Building Information Model)

**Extraktion:**
- Räume (IfcSpace) mit Property Sets
- HLKS-Systeme (IfcSystem)
- Geräte (IfcMechanicalEquipment, IfcFlowTerminal)
- Raum-Hierarchien (Geschosse, Zonen)
- Anlagen-Zuordnungen zu Räumen
- System-Beziehungen

**Property Sets:**
- Pset_SpaceCommon (Fläche, Volumen, Nutzung)
- Pset_MechanicalEquipment (Leistung)
- Pset_FlowTerminal (Volumenstrom)

### OCR (Gescannte Dokumente)

**Funktionen:**
- Layout-Erhaltung
- Tabellen-Erkennung
- Mehrsprachigkeit (Deutsch/Englisch)
- Bildvorverarbeitung für bessere Ergebnisse

## Daten-Merging

Das System führt intelligentes Merging durch:

- **Duplikat-Erkennung:** Basierend auf ID, Name, IFC-GUID
- **Konflikt-Auflösung:** Markiert Widersprüche mit Quellenverweisen
- **Quellenverweise:** Jede Entität enthält Informationen über ihre Quelle

## JSON-Datenmodell

Alle extrahierten Daten werden in einem einheitlichen JSON-Format gespeichert:

```json
{
  "projekt": {...},
  "raeume": [...],
  "anlagen": [...],
  "geraete": [...],
  "anforderungen": [...],
  "termine": [...],
  "leistungen": [...]
}
```

Siehe `backend/app/schemas/project_data_schema.py` für die vollständige Struktur.
