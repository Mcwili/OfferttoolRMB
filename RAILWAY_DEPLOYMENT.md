# Railway Deployment – Anleitung

## Schnellstart

1. Projekt auf Railway verbinden (GitHub-Repo)
2. **Volume hinzufügen** (für persistente Daten, siehe unten)
3. Optional: Umgebungsvariablen setzen
4. Deploy starten

---

## Persistente Daten (wichtig)

Ohne Volume gehen alle Daten bei jedem Neustart verloren.

### Volume einrichten

1. Im Railway-Dashboard: **Rechtsklick auf den Service** → **Add Volume**
2. **Mount Path:** `/app/data`
3. Volume mit dem Service verbinden

Damit bleiben erhalten:
- SQLite-Datenbank (Projekte, Einstellungen, API-Key)
- Hochgeladene Dateien
- Uploads von Vorlagen (rechtliche Prüfung, Frageliste)

---

## Optionale Umgebungsvariablen

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `DATABASE_URL` | PostgreSQL statt SQLite (falls PostgreSQL-Add-on verwendet wird) | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Starker Zufallswert für zukünftige Auth-Features | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Zusätzliche Origins bei eigener Domain | `https://meine-domain.ch` |

---

## PostgreSQL (optional)

Für mehr Datenbankleistung und Skalierung:

1. Projekt: **Add Plugin** → **PostgreSQL**
2. Variable `DATABASE_URL` wird automatisch gesetzt
3. Vor dem ersten Start: Migrationen laufen (Tabellen werden automatisch erstellt)

---

## Funktionen

- **OCR**: Tesseract ist im Image enthalten (gescannte PDFs/Bilder)
- **Vorlagen**: Speicherort `/app/data/Vorlagen` (persistent mit Volume)
- **API-Key**: Speicherung in der Datenbank
