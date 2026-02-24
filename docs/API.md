# API-Dokumentation

## Übersicht

Die API ist eine REST-API basierend auf FastAPI. Die Dokumentation ist automatisch verfügbar unter `/docs` (Swagger UI) und `/redoc`.

## Basis-URL

```
http://localhost:8000/api/v1
```

## Endpunkte

### Projekte

#### `POST /projects/`
Erstellt ein neues Projekt.

**Request Body:**
```json
{
  "name": "Projektname",
  "description": "Beschreibung",
  "standort": "Zürich"
}
```

**Response:** Projekt-Objekt

#### `GET /projects/`
Listet alle Projekte auf.

**Query Parameters:**
- `skip`: Anzahl zu überspringender Einträge (Standard: 0)
- `limit`: Maximale Anzahl Einträge (Standard: 100)

#### `GET /projects/{project_id}`
Ruft ein einzelnes Projekt ab.

#### `GET /projects/{project_id}/data`
Ruft das JSON-Datenmodell eines Projekts ab.

**Response:** Vollständiges JSON-Datenmodell mit Räumen, Anlagen, Geräten, etc.

#### `GET /projects/{project_id}/questions`
Ruft die Fragenliste für ein Projekt ab.

**Response:** Liste von Fragen basierend auf Validierungsproblemen

### Dateien

#### `POST /files/`
Lädt eine Datei hoch.

**Form Data:**
- `file`: Datei
- `project_id`: Projekt-ID

### Extraktion

#### `POST /extraction/project/{project_id}`
Startet die Datenextraktion für ein Projekt.

**Request Body:**
```json
{
  "file_id": 123  // Optional: spezifische Datei, sonst alle nicht verarbeiteten
}
```

### Validierung

#### `POST /validation/project/{project_id}`
Führt Validierung für ein Projekt durch.

**Response:** Validierungsergebnisse mit Fehlern, Warnungen, Hinweisen

#### `GET /validation/project/{project_id}/issues`
Ruft aktuelle Validierungsprobleme ab.

### Reports

#### `POST /reports/project/{project_id}/generate`
Generiert Berichte für ein Projekt.

**Request Body:**
```json
{
  "report_types": ["offerte", "risikoanalyse", "timeline", "org"]
}
```

**Hinweis:** Projekt muss als "offertreif" markiert sein.

## Authentifizierung

Aktuell nicht implementiert. Wird in zukünftiger Version hinzugefügt.
