-- PostgreSQL Initialisierung für HLKS Planungsanalyse Tool
-- Erstellt Datenbank-Schema und aktiviert Extensions

-- pgvector Extension für Vektorsuche (falls benötigt)
CREATE EXTENSION IF NOT EXISTS vector;

-- Indizes für JSONB-Felder (für schnelle Abfragen im project_data.data_json)
-- Diese werden später via Alembic Migrations erstellt, hier nur als Beispiel:

-- Beispiel-Index für häufige JSON-Abfragen:
-- CREATE INDEX idx_project_data_raeume ON project_data USING GIN ((data_json -> 'raeume'));
-- CREATE INDEX idx_project_data_anlagen ON project_data USING GIN ((data_json -> 'anlagen'));

-- Kommentar: Die eigentlichen Tabellen werden via SQLAlchemy Models und Alembic erstellt
