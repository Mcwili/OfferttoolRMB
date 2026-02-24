# HLKS-Planungsanalyse Tool

Webanwendung zur automatisierten Analyse von HLKS-Planungsunterlagen und Generierung von Ingenieur-Offerten.

## Projektstruktur

```
.
├── backend/          # FastAPI Backend
├── frontend/         # Next.js Frontend
├── database/         # PostgreSQL Schema & Migrations
├── docker/           # Docker-Konfigurationen
└── docs/             # Dokumentation
```

## Module

1. **Datenaufnahme (Intake)**: Datei-Upload, Klassifikation, Speicherung
2. **Datenextraktion (Extraction)**: Parser für Excel, Word, PDF, IFC, OCR
3. **Validierung**: Konsistenzprüfungen, YAML-Abgleich, Fragenliste
4. **Berichtsgenerierung**: RMB-Offerte, Risikoanalyse, WBS-Timeline, RACI-Matrix

## Technologie-Stack

### Backend
- FastAPI (Python Web Framework)
- PostgreSQL mit JSONB & pgvector
- Celery für asynchrone Tasks
- S3-kompatibler Objektspeicher

### Frontend
- Next.js (React)
- TypeScript

### Parser & Tools
- openpyxl / pandas (Excel)
- python-docx (Word)
- pdfplumber / Camelot (PDF)
- IfcOpenShell (IFC/BIM)
- Tesseract OCR + OpenCV
- spaCy (NLP)

### Berichte
- python-docx (Word-Dokumente)
- ReportLab (PDF mit Grafiken)

## Setup

Siehe `docs/SETUP.md` für detaillierte Installationsanleitung.

## Entwicklung

```bash
# Backend starten
cd backend
uvicorn main:app --reload

# Frontend starten
cd frontend
npm run dev
```

## Lizenz

Proprietär - RMB Ingenieurbüro
