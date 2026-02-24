import { useState, useEffect, useMemo } from 'react';
import FileUpload from './components/FileUpload';
import ProjectFileUpload from './components/ProjectFileUpload';
import IFCViewer from './components/IFCViewer';
import { projectsApi, settingsApi, filesApi, legalReviewApi, questionListApi } from './services/api';
import type { Project } from './services/api';
import './App.css';

type SortField = 'date' | 'name' | 'number' | 'location' | 'status';

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortAscending, setSortAscending] = useState(false); // false = neueste zuerst
  const [, setSelectedProjectId] = useState<number | null>(null);
  const [projectDetailsModal, setProjectDetailsModal] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [chatgptApiKey, setChatgptApiKey] = useState('');
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [apiKeySaved, setApiKeySaved] = useState(false);
  const [legalReviewLoading, setLegalReviewLoading] = useState(false);
  const [legalReviewStep, setLegalReviewStep] = useState<string | null>(null);
  const [legalReviewPrompt, setLegalReviewPrompt] = useState('');
  const [legalReviewResults, setLegalReviewResults] = useState<any>(null);
  const [legalReviewResultsLoading, setLegalReviewResultsLoading] = useState(false);
  const [promptLoading, setPromptLoading] = useState(false);
  const [promptSaved, setPromptSaved] = useState(false);
  const [templateStatus, setTemplateStatus] = useState<{exists: boolean; filename?: string; size?: number; modified?: string} | null>(null);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [questionListLoading, setQuestionListLoading] = useState(false);
  const [questionListStep, setQuestionListStep] = useState<string | null>(null);
  const [questionListPrompt, setQuestionListPrompt] = useState('');
  const [questionListPromptLoading, setQuestionListPromptLoading] = useState(false);
  const [questionListPromptSaved, setQuestionListPromptSaved] = useState(false);
  const [questionListTemplateStatus, setQuestionListTemplateStatus] = useState<{exists: boolean; filename?: string; size?: number; modified?: string} | null>(null);
  const [questionListTemplateLoading, setQuestionListTemplateLoading] = useState(false);
  const [showProjectFileUpload, setShowProjectFileUpload] = useState(false);
  const [showIFCViewer, setShowIFCViewer] = useState(false);
  const [selectedIFCFile, setSelectedIFCFile] = useState<{ id: number; filename: string } | null>(null);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.getAll();
      setProjects(data);
    } catch (error: any) {
      console.error('Fehler beim Laden der Projekte:', error);
      // Wenn Backend nicht erreichbar, zeige leere Liste
      setProjects([]);
      // Kein Error-State hier, da das Backend möglicherweise noch nicht läuft
    } finally {
      setLoading(false);
    }
  };

  const loadChatgptApiKey = async () => {
    try {
      const setting = await settingsApi.get('chatgpt_api_key');
      setChatgptApiKey(setting.value || '');
    } catch (error: any) {
      // Wenn Setting nicht existiert, ist das ok
      if (error.response?.status !== 404) {
        console.error('Fehler beim Laden des API-Keys:', error);
      }
      setChatgptApiKey('');
    }
  };

  // Standard-Prompt (muss mit Backend übereinstimmen)
  // Hinweis: Der vollständige Prompt wird vom Backend geladen, dies ist nur eine Vorschau
  const DEFAULT_LEGAL_REVIEW_PROMPT = `Rolle
Du bist ein spezialisierter Vertrags und Risikoanalyst für schweizer Ingenieur und Haustechnik Planungsfirmen. Dein Fokus liegt auf HLKS, Gebäudetechnik, Generalplaner und Fachplanerverträgen. Du denkst aus Sicht der Auftragnehmerseite. Dein Auftraggeber ist RMB Engineering, eine Haustechnik Planungsfirma in der Schweiz.

Aufgabe
Prüfe die nachfolgenden Offertunterlagen VOLLSTÄNDIG und ABSCHLIESSEND auf kritische, unklare oder nachteilige vertragliche Inhalte für RMB Engineering. Der Schwerpunkt liegt auf Planungsvertragsentwürfen, Vertragsbedingungen, AGB, Zusatzbedingungen, Haftungsklauseln, Vergütungsmodellen, Terminvorgaben, Koordinationspflichten und Risikoübertragungen.

KRITISCH WICHTIG - ABSCHLIESSENDE PRÜFUNG:
- Du musst ALLE problematischen Punkte identifizieren, nicht nur die wichtigsten oder eine Auswahl
- KEINE Zusammenfassung oder Gruppierung - jeder einzelne problematische Punkt muss separat aufgeführt werden
- Die Prüfung soll abschliessend sein - auch wenn das Ergebnis sehr umfangreich wird (50+ Punkte sind möglich und erwünscht)
- Gehe ZEILE FÜR ZEILE durch alle Dokumente
- Prüfe jeden Absatz, jede Klausel, jede Bedingung einzeln

Du musst alle Unterlagen vollständig lesen, auch wenn sie umfangreich sind. Falls mehrere Dokumente vorhanden sind, bewerte sie gesamthaft und systematisch durch - Dokument für Dokument, Absatz für Absatz.

Bewertungsschwerpunkte - DETAILLIERTE CHECKLISTE
Prüfe insbesondere, aber nicht ausschliesslich, folgende Themen systematisch:

1. HAFTUNG UND VERANTWORTUNG
- Unbegrenzte oder übermässige Haftung
- Haftung für Leistungen Dritter
- Haftung für Kosten, Termine oder Betrieb
- Abweichungen von SIA Normen
- Haftungsdauer und Verjährung
- Haftung für Planungsfehler ohne Verschulden
- Haftung für versteckte Mängel
- Haftung für Umweltschäden oder Altlasten

2. LEISTUNGSUMFANG
- Unklare oder offene Leistungsbeschriebe
- Versteckte Zusatzleistungen
- Koordinations- und Gesamtverantwortung
- Bauherrenvertretung oder GU ähnliche Pflichten
- Leistungen ohne klare Honorierung
- Unklare Abgrenzung zwischen Planungsphasen
- Leistungen, die über den Standard hinausgehen

3. HONORIERUNG UND VERGÜTUNG
- Pauschalhonorare mit offenem Leistungsumfang
- Fehlende Regelungen zu Zusatzleistungen
- Abhängigkeit von Projektfortschritt oder Baukosten
- Zahlungsziele, Rückbehalte, Abzüge
- Honorar bei Projektabbruch oder Kündigung
- Unklare Honorarberechnungsgrundlage

4. TERMINE UND VERZUG
- Verbindliche Termine ohne Abgrenzung
- Konventionalstrafen
- Verantwortung für Verzögerungen Dritter
- Unklare Terminvereinbarungen
- Termine ohne Berücksichtigung von Genehmigungsverfahren

5. RECHTE UND PFLICHTEN
- Kündigungsrechte des Auftraggebers
- Einseitige Vertragsänderungen
- Dokumentations- und Reportingpflichten
- Versicherungsanforderungen über Standard
- Geheimhaltungspflichten ohne zeitliche Begrenzung
- Nutzungsrechte an Planungsunterlagen

6. RECHTLICHES
- Gerichtsstand und anwendbares Recht
- Abweichungen von schweizer Standardverträgen
- Unklare Rangordnung der Vertragsdokumente
- Schiedsgerichtsvereinbarungen
- Abweichungen von gesetzlichen Bestimmungen

Ausgabeformat - WICHTIG: JSON-Format
Deine Antwort MUSS IMMER als gültiges JSON-Objekt erfolgen. Kein zusätzlicher Text, keine Erklärungen, nur das JSON-Objekt.

Das JSON-Format ist exakt wie folgt definiert:
{
  "allgemeine_einschaetzung": "Kurze Gesamtbeurteilung der Unterlagen aus Sicht von RMB Engineering. Fokus auf Gesamtrisiko.",
  "kritische_punkte": [
    {
      "nummer": 1,
      "titel": "Kurzer, prägnanter Titel des Risikos",
      "zitat": "Exakter Wortlaut aus den Unterlagen (vollständiges Zitat)",
      "beurteilung": "Fachliche Einschätzung, warum dieser Punkt für RMB Engineering kritisch, unklar oder nachteilig ist. Bezug auf typische Praxis in der Schweiz und SIA Normen, ohne Paragraphen zu zitieren.",
      "risiko_rating": "rot",
      "empfehlung": "Konkrete Handlungsempfehlung für RMB Engineering (z.B. Anpassung verlangen, präzisieren, streichen, akzeptabel mit Vorbehalt)"
    }
  ]
}

Wichtige Regeln für JSON-Ausgabe:
- Die Antwort muss ein gültiges JSON-Objekt sein
- "risiko_rating" muss exakt einer der Werte sein: "rot", "orange" oder "grün"
- "nummer" muss eine fortlaufende Zahl sein, beginnend bei 1
- Jeder Punkt in "kritische_punkte" muss alle Felder enthalten
- Keine zusätzlichen Felder, keine Kommentare, nur das JSON-Objekt
- Alle Textfelder müssen als Strings formatiert sein
- Mehrzeilige Texte bleiben als Strings erhalten

Wichtige Regeln für die Analyse:
- Nummerierung immer fortlaufend beginnen bei 1
- Jeder Punkt darf nur ein Thema behandeln
- Keine Vermischung mehrerer Risiken in einem Punkt
- Keine juristischen Floskeln, klare und praxisnahe Sprache
- Keine Absicherung zugunsten des Auftraggebers formulieren
- Denke strikt aus Sicht von RMB Engineering
- Falls etwas unklar ist, bewerte es als Risiko
- Falls etwas fehlt, das üblich wäre, weise explizit darauf hin

Farblogik
rot = wesentliches Risiko mit möglich grossem finanziellem oder haftungsrechtlichem Schaden
orange = relevantes Risiko, das verhandelt oder präzisiert werden sollte
grün = geringes Risiko oder marktüblich, Hinweis reicht

Start
Beginne mit der Analyse, sobald die Unterlagen eingefügt werden. Gib NUR das JSON-Objekt zurück, keine zusätzlichen Erklärungen.`;

  const loadLegalReviewPrompt = async () => {
    try {
      const setting = await settingsApi.get('legal_review_prompt');
      setLegalReviewPrompt(setting.value || DEFAULT_LEGAL_REVIEW_PROMPT);
    } catch (error: any) {
      // Wenn Setting nicht existiert, verwende Standard-Prompt
      if (error.response?.status === 404) {
        setLegalReviewPrompt(DEFAULT_LEGAL_REVIEW_PROMPT);
      } else {
        console.error('Fehler beim Laden des Prompts:', error);
        setLegalReviewPrompt(DEFAULT_LEGAL_REVIEW_PROMPT);
      }
    }
  };

  const loadTemplateStatus = async () => {
    try {
      setTemplateLoading(true);
      const status = await settingsApi.getLegalReviewTemplateStatus();
      setTemplateStatus(status);
    } catch (error: any) {
      console.error('Fehler beim Laden des Template-Status:', error);
      setTemplateStatus({ exists: false });
    } finally {
      setTemplateLoading(false);
    }
  };

  const saveLegalReviewPrompt = async () => {
    setPromptLoading(true);
    setPromptSaved(false);
    try {
      if (legalReviewPrompt.trim() === '') {
        // Wenn leer, lösche die Einstellung, damit Standard-Prompt verwendet wird
        try {
          await settingsApi.delete('legal_review_prompt');
        } catch (deleteError: any) {
          // Wenn Setting nicht existiert, ist das ok
          if (deleteError.response?.status !== 404) {
            throw deleteError;
          }
        }
      } else {
        // Speichere den benutzerdefinierten Prompt
        await settingsApi.update('legal_review_prompt', {
          value: legalReviewPrompt.trim(),
          description: 'Prompt für die rechtliche Prüfung von Offertunterlagen'
        });
      }
      setPromptSaved(true);
      setTimeout(() => setPromptSaved(false), 3000);
    } catch (error: any) {
      console.error('Fehler beim Speichern des Prompts:', error);
      alert('Fehler beim Speichern des Prompts: ' + (error.response?.data?.detail || error.message));
    } finally {
      setPromptLoading(false);
    }
  };

  const saveChatgptApiKey = async () => {
    setApiKeyLoading(true);
    setApiKeySaved(false);
    try {
      await settingsApi.update('chatgpt_api_key', {
        value: chatgptApiKey,
        description: 'ChatGPT API-Key für AI-Anwendungen'
      });
      setApiKeySaved(true);
      setTimeout(() => setApiKeySaved(false), 3000);
    } catch (error: any) {
      console.error('Fehler beim Speichern des API-Keys:', error);
      alert('Fehler beim Speichern des API-Keys: ' + (error.response?.data?.detail || error.message));
    } finally {
      setApiKeyLoading(false);
    }
  };

  // Standard-Prompt für Frageliste (muss mit Backend übereinstimmen)
  const DEFAULT_QUESTION_LIST_PROMPT = `Du bist ein erfahrener Schweizer Ingenieurberater im Bereich HLKS und Fachkoordination mit sehr guter Kenntnis der SIA-Ordnungen und der üblichen Honoraroffertenpraxis.

Deine Aufgabe ist es, die zur Verfügung gestellten Projektunterlagen kritisch zu prüfen mit dem Ziel, eine Honorarofferte zu erstellen. Die Offerte kann nur erstellt werden, wenn alle notwendigen Grundlagen klar, widerspruchsfrei und ausreichend definiert sind.

Gehe strukturiert vor und prüfe die Unterlagen insbesondere in folgenden Punkten:

Leistungsumfang
Prüfe, ob der Leistungsumfang klar beschrieben ist oder ob er Interpretationsspielraum enthält.
Erkenne fehlende, unklare oder widersprüchliche Leistungsbeschriebe.
Beurteile, ob der Umfang realistisch zu den angegebenen Projektzielen passt.

Gewerke
Prüfe, für welche Gewerke Leistungen erwartet werden.
Berücksichtige mindestens folgende Gewerke:
Heizung
Kälte
Sanitär
Lüftung
Sprinkler
Fachkoordination
Andere Gewerke, falls implizit oder explizit erwähnt

Identifiziere fehlende Zuordnungen, Mehrdeutigkeiten oder implizite Annahmen.
Prüfe, ob Zusatzgewerke eindeutig als solche deklariert sind.

SIA-Phasen
Prüfe für jedes Gewerk, welche SIA-Phasen beauftragt sind oder erwartet werden.
Berücksichtige folgende Phasen:
SIA 31 Vorprojekt
SIA 32 Bauprojekt
SIA 33 Bewilligung
SIA 41 Ausschreibung
SIA 51 Ausführungsplanung
SIA 52 Realisierung
SIA 53 Abnahmen

Identifiziere fehlende Phasenangaben, widersprüchliche Aussagen oder unklare Abgrenzungen.
Prüfe, ob Phasen ausgelassen wurden und ob dies begründet ist.

Zusatzleistungen
Prüfe, ob Zusatzleistungen klar als solche definiert sind oder implizit erwartet werden.
Typische Zusatzleistungen können sein:
Sprinklerplanung
Erweiterte Fachbauleitung
Leistungen für weitere Gewerke
Besondere Nachweise, Simulationen, Studien oder Konzepte

Zeige auf, wo Zusatzleistungen vermischt oder nicht sauber abgegrenzt sind.

Projektgrundlagen
Prüfe, ob folgende Grundlagen ausreichend vorhanden sind oder fehlen:
Projektbeschrieb
Nutzungsangaben
Flächen, Volumen oder Kennwerte
Qualitäts- und Nachhaltigkeitsanforderungen
Schnittstellen zu anderen Planern
Terminvorgaben

Risiken und Unklarheiten
Identifiziere Risiken für den Auftragnehmer aufgrund unklarer oder fehlender Angaben.
Beurteile, wo Nachforderungen, Mehraufwand oder Streitpotenzial entstehen können.

Ergebnis

Erstelle als Resultat eine strukturierte Frageliste an den Auftraggeber.
Die Frageliste soll:
klar und präzise formuliert sein
nach Themen gegliedert sein
nur offene oder unklare Punkte enthalten
keine Annahmen treffen
keine Lösungen vorschlagen

Ziel ist es, mit dieser Frageliste alle offenen Punkte zu klären, damit eine transparente, faire und belastbare Honorarofferte erstellt werden kann.

Ausgabeformat - WICHTIG: JSON-Format
Deine Antwort MUSS IMMER als gültiges JSON-Objekt erfolgen. Kein zusätzlicher Text, keine Erklärungen, nur das JSON-Objekt.

Das JSON-Format ist exakt wie folgt definiert:
{
  "zusammenfassung": "Kurze Zusammenfassung der offenen Punkte und der wichtigsten Fragen",
  "fragen": [
    {
      "nummer": 1,
      "kategorie": "Leistungsumfang",
      "frage": "Ist der Leistungsumfang für die HLKS-Planung klar definiert?",
      "begruendung": "Im Dokument wird nur allgemein von 'Planungsleistungen' gesprochen, ohne konkrete Aufgaben zu benennen.",
      "prioritaet": "hoch"
    }
  ]
}

Wichtige Regeln für JSON-Ausgabe:
- Die Antwort muss ein gültiges JSON-Objekt sein
- "prioritaet" muss exakt einer der Werte sein: "hoch", "mittel" oder "niedrig"
- "nummer" muss eine fortlaufende Zahl sein, beginnend bei 1
- "kategorie" sollte eine der folgenden sein: "Leistungsumfang", "Gewerke", "SIA-Phasen", "Zusatzleistungen", "Projektgrundlagen", "Risiken und Unklarheiten" oder eine passende andere Kategorie
- Jede Frage in "fragen" muss alle Felder enthalten
- Keine zusätzlichen Felder, keine Kommentare, nur das JSON-Objekt
- Alle Textfelder müssen als Strings formatiert sein
- Mehrzeilige Texte bleiben als Strings erhalten

Gib NUR das JSON-Objekt zurück, keine zusätzlichen Erklärungen.`;

  const loadQuestionListPrompt = async () => {
    try {
      const setting = await settingsApi.get('question_list_prompt');
      setQuestionListPrompt(setting.value || DEFAULT_QUESTION_LIST_PROMPT);
    } catch (error: any) {
      // Wenn Setting nicht existiert, verwende Standard-Prompt
      if (error.response?.status === 404) {
        setQuestionListPrompt(DEFAULT_QUESTION_LIST_PROMPT);
      } else {
        console.error('Fehler beim Laden des Frageliste-Prompts:', error);
        setQuestionListPrompt(DEFAULT_QUESTION_LIST_PROMPT);
      }
    }
  };

  const loadQuestionListTemplateStatus = async () => {
    try {
      setQuestionListTemplateLoading(true);
      const status = await settingsApi.getQuestionListTemplateStatus();
      setQuestionListTemplateStatus(status);
    } catch (error: any) {
      console.error('Fehler beim Laden des Frageliste-Template-Status:', error);
      setQuestionListTemplateStatus({ exists: false });
    } finally {
      setQuestionListTemplateLoading(false);
    }
  };

  const saveQuestionListPrompt = async () => {
    setQuestionListPromptLoading(true);
    setQuestionListPromptSaved(false);
    try {
      if (questionListPrompt.trim() === '') {
        // Wenn leer, lösche die Einstellung, damit Standard-Prompt verwendet wird
        try {
          await settingsApi.delete('question_list_prompt');
        } catch (deleteError: any) {
          // Wenn Setting nicht existiert, ist das ok
          if (deleteError.response?.status !== 404) {
            throw deleteError;
          }
        }
      } else {
        // Speichere den benutzerdefinierten Prompt
        await settingsApi.update('question_list_prompt', {
          value: questionListPrompt.trim(),
          description: 'Prompt für die Frageliste-Generierung'
        });
      }
      setQuestionListPromptSaved(true);
      setTimeout(() => setQuestionListPromptSaved(false), 3000);
    } catch (error: any) {
      console.error('Fehler beim Speichern des Frageliste-Prompts:', error);
      alert('Fehler beim Speichern des Prompts: ' + (error.response?.data?.detail || error.message));
    } finally {
      setQuestionListPromptLoading(false);
    }
  };

  const loadLegalReviewResults = async (projectId: number) => {
    try {
      setLegalReviewResultsLoading(true);
      const results = await legalReviewApi.getResults(projectId);
      if (results.latest) {
        setLegalReviewResults(results.latest);
      } else {
        setLegalReviewResults(null);
      }
    } catch (error: any) {
      console.error('Fehler beim Laden der Prüfungsergebnisse:', error);
      setLegalReviewResults(null);
    } finally {
      setLegalReviewResultsLoading(false);
    }
  };

  useEffect(() => {
    if (showSettings) {
      loadChatgptApiKey();
      loadLegalReviewPrompt();
      loadTemplateStatus();
      loadQuestionListPrompt();
      loadQuestionListTemplateStatus();
    }
  }, [showSettings]);

  useEffect(() => {
    if (projectDetailsModal?.project?.id) {
      loadLegalReviewResults(projectDetailsModal.project.id);
    } else {
      setLegalReviewResults(null);
    }
  }, [projectDetailsModal?.project?.id]);

  // Polling für Projekte mit Status "processing"
  useEffect(() => {
    const hasProcessingProjects = projects.some(p => p.status === 'processing');
    
    if (hasProcessingProjects) {
      // Starte Polling alle 5 Sekunden
      const interval = setInterval(() => {
        loadProjects();
      }, 5000);
      
      return () => {
        clearInterval(interval);
      };
    }
  }, [projects]);

  useEffect(() => {
    loadProjects();
  }, []);

  // Extrahiere Projektnummer aus description
  const extractProjectNumber = (description?: string): string => {
    if (!description) return '';
    const match = description.match(/Projektnummer:\s*(.+)/);
    return match ? match[1].trim() : '';
  };

  // Sortiere Projekte
  const sortedProjects = useMemo(() => {
    const sorted = [...projects];
    sorted.sort((a, b) => {
      let comparison = 0;
      
      switch (sortField) {
        case 'date':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name, 'de-DE');
          break;
        case 'number':
          const numA = extractProjectNumber(a.description);
          const numB = extractProjectNumber(b.description);
          comparison = numA.localeCompare(numB, 'de-DE');
          break;
        case 'location':
          const locA = a.standort || '';
          const locB = b.standort || '';
          comparison = locA.localeCompare(locB, 'de-DE');
          break;
        case 'status':
          comparison = a.status.localeCompare(b.status, 'de-DE');
          break;
      }
      
      return sortAscending ? comparison : -comparison;
    });
    return sorted;
  }, [projects, sortField, sortAscending]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAscending(!sortAscending);
    } else {
      setSortField(field);
      // Standard-Sortierung: Datum absteigend (neueste zuerst), andere aufsteigend
      setSortAscending(field === 'date' ? false : true);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-content">
      <div>
            <h1 className="title">HLKS Offert-Tool</h1>
            <p className="subtitle">
              Intelligente Offerte-Generierung aus Planungsunterlagen
        </p>
      </div>
          <button 
            className="settings-btn"
            onClick={() => setShowSettings(true)}
            title="Einstellungen"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M 12 2 L 13 2 L 13 5 L 15 5 L 15 7 L 13 7 L 13 5 L 11 5 L 11 7 L 9 7 L 9 5 L 11 5 L 11 2 L 12 2 Z M 12 22 L 13 22 L 13 19 L 15 19 L 15 17 L 13 17 L 13 19 L 11 19 L 11 17 L 9 17 L 9 19 L 11 19 L 11 22 L 12 22 Z M 2 12 L 2 13 L 5 13 L 5 15 L 7 15 L 7 13 L 5 13 L 5 11 L 7 11 L 7 9 L 5 9 L 5 11 L 2 11 L 2 12 Z M 22 12 L 22 13 L 19 13 L 19 15 L 17 15 L 17 13 L 19 13 L 19 11 L 17 11 L 17 9 L 19 9 L 19 11 L 22 11 L 22 12 Z M 5 5 L 6.5 5 L 8 6.5 L 8 8 L 6.5 8 L 5 6.5 L 5 5 Z M 19 5 L 17.5 5 L 16 6.5 L 16 8 L 17.5 8 L 19 6.5 L 19 5 Z M 5 19 L 6.5 19 L 8 17.5 L 8 16 L 6.5 16 L 5 17.5 L 5 19 Z M 19 19 L 17.5 19 L 16 17.5 L 16 16 L 17.5 16 L 19 17.5 L 19 19 Z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
          </button>
        </div>
      </header>

      <main className="main-content">
        <section className="upload-section">
          <FileUpload onUploadSuccess={loadProjects} />
        </section>

        {projects.length > 0 && (
          <section className="projects-section">
            <div className="projects-header">
              <h2 className="section-title">Projekte</h2>
            </div>
            <div className="projects-table-container glass">
              <table className="projects-table">
                <thead>
                  <tr>
                    <th 
                      className={`sortable-header ${sortField === 'name' ? 'active' : ''}`}
                      onClick={() => handleSort('name')}
                    >
                      Projektname
                      {sortField === 'name' && (sortAscending ? ' ↑' : ' ↓')}
                    </th>
                    <th 
                      className={`sortable-header ${sortField === 'number' ? 'active' : ''}`}
                      onClick={() => handleSort('number')}
                    >
                      Projektnummer
                      {sortField === 'number' && (sortAscending ? ' ↑' : ' ↓')}
                    </th>
                    <th 
                      className={`sortable-header ${sortField === 'location' ? 'active' : ''}`}
                      onClick={() => handleSort('location')}
                    >
                      Standort
                      {sortField === 'location' && (sortAscending ? ' ↑' : ' ↓')}
                    </th>
                    <th 
                      className={`sortable-header ${sortField === 'status' ? 'active' : ''}`}
                      onClick={() => handleSort('status')}
                    >
                      Status
                      {sortField === 'status' && (sortAscending ? ' ↑' : ' ↓')}
                    </th>
                    <th 
                      className={`sortable-header ${sortField === 'date' ? 'active' : ''}`}
                      onClick={() => handleSort('date')}
                    >
                      Datum
                      {sortField === 'date' && (sortAscending ? ' ↑' : ' ↓')}
                    </th>
                    <th className="extraction-header">Extrahiert</th>
                    <th className="actions-header" style={{ width: '4rem', textAlign: 'center' }}>Aktionen</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedProjects.map((project) => {
                    return (
                        <tr 
                          key={project.id}
                          className="project-row"
                          onClick={async () => {
                            setSelectedProjectId(project.id);
                            setLoadingDetails(true);
                            setProjectDetailsModal(null); // Reset vor dem Laden
                            try {
                              const details = await projectsApi.getDetails(project.id);
                              const extractedData = await projectsApi.getExtractedDataByFile(project.id);
                              // Sicherstellen, dass die Datenstruktur korrekt ist
                              const modalData = {
                                ...details,
                                project: details?.project || null,
                                files: Array.isArray(details?.files) ? details.files : [],
                                extractedDataByFile: extractedData || { files: [] }
                              };
                              setProjectDetailsModal(modalData);
                            } catch (error: any) {
                              console.error('Fehler beim Laden der Projekt-Details:', error);
                              const errorMessage = error.response?.data?.detail || error.message || 'Unbekannter Fehler';
                              alert('Fehler beim Laden der Projekt-Details: ' + errorMessage);
                              setProjectDetailsModal(null);
                            } finally {
                              setLoadingDetails(false);
                            }
                          }}
                        >
                          <td className="project-name">{project.name}</td>
                          <td className="project-number">
                            {extractProjectNumber(project.description) || '-'}
                          </td>
                          <td className="project-location">{project.standort || '-'}</td>
                          <td>
                            <span className={`project-status status-${project.status}`}>
                              {project.status}
                            </span>
                          </td>
                          <td className="project-date">
                            {new Date(project.created_at).toLocaleDateString('de-DE', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric'
                            })}
                          </td>
                          <td className="extraction-cell">
                            {project.status === 'processing' && (
                              <div className="extraction-status extraction-spinner">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                  <circle
                                    cx="8"
                                    cy="8"
                                    r="6"
                                    stroke="#007aff"
                                    strokeWidth="2"
                                    strokeDasharray="37.7"
                                    strokeDashoffset="9.4"
                                    strokeLinecap="round"
                                  />
                                </svg>
                              </div>
                            )}
                            {project.status === 'validated' && (
                              <div className="extraction-status extraction-success">
                                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                  <path
                                    d="M3 8 L6 11 L13 4"
                                    stroke="#34c759"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                </svg>
                              </div>
                            )}
                          </td>
                          <td className="actions-cell" style={{ textAlign: 'center', padding: '0.7rem 0.875rem' }}>
                            <button
                              className="project-delete-btn"
                              onClick={async (e) => {
                                e.stopPropagation(); // Verhindert das Öffnen des Detail-Modals
                                if (window.confirm(`Soll das Projekt "${project.name}" wirklich gelöscht werden?`)) {
                                  try {
                                    await projectsApi.delete(project.id);
                                    loadProjects(); // Projekte neu laden
                                  } catch (error: any) {
                                    console.error('Fehler beim Löschen des Projekts:', error);
                                    alert('Fehler beim Löschen des Projekts: ' + (error.response?.data?.detail || error.message));
                                  }
                                }
                              }}
                              title="Projekt löschen"
                            >
                              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M3 6h10M5 6v8a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1V6M7 3h2a1 1 0 0 0 1-1V1a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1z"/>
                              </svg>
                            </button>
                          </td>
                        </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {loading && (
          <div className="loading glass">
            <p>Lade Projekte...</p>
          </div>
        )}
      </main>

      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Einstellungen</h2>
              <button className="modal-close" onClick={() => setShowSettings(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="settings-content">
                <div className="settings-section">
                  <h3>ChatGPT API</h3>
                  <p className="settings-description">
                    Geben Sie hier Ihren ChatGPT API-Key ein. Dieser wird verschlüsselt gespeichert 
                    und bei allen AI-Anwendungen in dieser App verwendet.
                  </p>
                  <div className="settings-input-group">
                    <label htmlFor="chatgpt-api-key">API-Key</label>
                    <input
                      id="chatgpt-api-key"
                      type="password"
                      className="settings-input"
                      placeholder="sk-..."
                      value={chatgptApiKey}
                      onChange={(e) => setChatgptApiKey(e.target.value)}
                    />
                    <button
                      className="settings-save-btn"
                      onClick={saveChatgptApiKey}
                      disabled={apiKeyLoading}
                    >
                      {apiKeyLoading ? 'Speichere...' : 'Speichern'}
                    </button>
                    {apiKeySaved && (
                      <span className="settings-saved-indicator">✓ Gespeichert</span>
                    )}
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Rechtliche Prüfung - Prompt</h3>
                  <p className="settings-description">
                    Passen Sie hier den Prompt für die rechtliche Prüfung an. Dieser Prompt wird an die AI gesendet,
                    um die Offertunterlagen zu analysieren. Wenn kein Prompt gespeichert ist, wird der Standard-Prompt verwendet.
                    Sie können den Standard-Prompt laden, indem Sie das Feld leer lassen und speichern, oder den Standard-Prompt manuell eingeben.
                  </p>
                  <div className="settings-input-group">
                    <label htmlFor="legal-review-prompt">Prompt</label>
                    <textarea
                      id="legal-review-prompt"
                      className="settings-textarea"
                      placeholder="Standard-Prompt wird angezeigt..."
                      value={legalReviewPrompt}
                      onChange={(e) => setLegalReviewPrompt(e.target.value)}
                      rows={20}
                    />
                    <div style={{ display: 'flex', gap: '0.7rem', alignItems: 'center', marginTop: '0.7rem' }}>
                      <button
                        className="settings-save-btn"
                        onClick={saveLegalReviewPrompt}
                        disabled={promptLoading}
                      >
                        {promptLoading ? 'Speichere...' : 'Speichern'}
                      </button>
                      {promptSaved && (
                        <span className="settings-saved-indicator">✓ Gespeichert</span>
                      )}
                    </div>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.7rem', fontStyle: 'italic' }}>
                      Hinweis: Wenn das Feld leer ist und Sie speichern, wird der Standard-Prompt verwendet. 
                      Um einen benutzerdefinierten Prompt zu verwenden, geben Sie ihn hier ein und speichern Sie ihn.
                    </p>
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Rechtliche Prüfung - Word-Vorlage</h3>
                  <p className="settings-description">
                    Laden Sie hier die Word-Vorlage für die rechtliche Prüfung hoch. Diese Vorlage wird für alle generierten 
                    rechtlichen Prüfungen verwendet. Die Vorlage sollte im Format "RMB A4 hoch.docx" sein.
                  </p>
                  <div className="settings-input-group">
                    <label htmlFor="legal-review-template">Word-Vorlage (.docx)</label>
                    <input
                      id="legal-review-template"
                      type="file"
                      accept=".docx"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          if (!file.name.endsWith('.docx')) {
                            alert('Bitte wählen Sie eine .docx Datei aus');
                            return;
                          }
                          try {
                            await settingsApi.uploadLegalReviewTemplate(file);
                            alert('Vorlage erfolgreich hochgeladen!');
                            e.target.value = ''; // Reset input
                            // Status neu laden
                            await loadTemplateStatus();
                          } catch (error: any) {
                            console.error('Fehler beim Hochladen der Vorlage:', error);
                            alert('Fehler beim Hochladen der Vorlage: ' + (error.response?.data?.detail || error.message));
                          }
                        }
                      }}
                      style={{
                        padding: '0.7rem',
                        background: 'rgba(255, 255, 255, 0.1)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '7px',
                        color: 'var(--text-primary)',
                        fontSize: '0.875rem',
                        width: '100%',
                        cursor: 'pointer'
                      }}
                    />
                    {templateLoading ? (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.7rem' }}>
                        Prüfe Status...
                      </p>
                    ) : templateStatus?.exists ? (
                      <div style={{ 
                        marginTop: '0.7rem', 
                        padding: '0.7rem', 
                        background: 'rgba(52, 199, 89, 0.2)', 
                        border: '1px solid rgba(52, 199, 89, 0.4)', 
                        borderRadius: '7px',
                        fontSize: '0.75rem'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#34c759', fontWeight: 600 }}>
                          <span>✓</span>
                          <span>Vorlage erfolgreich hinterlegt</span>
                        </div>
                        {templateStatus.filename && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Datei: {templateStatus.filename}
                          </div>
                        )}
                        {templateStatus.size && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Größe: {(templateStatus.size / 1024).toFixed(1)} KB
                          </div>
                        )}
                        {templateStatus.modified && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Geändert: {new Date(templateStatus.modified).toLocaleString('de-DE')}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p style={{ 
                        fontSize: '0.75rem', 
                        color: 'rgba(255, 59, 48, 0.9)', 
                        marginTop: '0.7rem',
                        padding: '0.7rem',
                        background: 'rgba(255, 59, 48, 0.1)',
                        border: '1px solid rgba(255, 59, 48, 0.3)',
                        borderRadius: '7px'
                      }}>
                        ⚠ Keine Vorlage hinterlegt. Bitte laden Sie eine Word-Vorlage (.docx) hoch.
                      </p>
                    )}
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.7rem', fontStyle: 'italic' }}>
                      Die hochgeladene Vorlage ersetzt die Standard-Vorlage "RMB A4 hoch.docx" im Vorlagen-Verzeichnis.
                    </p>
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Frageliste - Prompt</h3>
                  <p className="settings-description">
                    Passen Sie hier den Prompt für die Frageliste-Generierung an. Dieser Prompt wird an die AI gesendet,
                    um die Projektunterlagen zu analysieren und eine strukturierte Frageliste zu erstellen. Wenn kein Prompt gespeichert ist, wird der Standard-Prompt verwendet.
                  </p>
                  <div className="settings-input-group">
                    <label htmlFor="question-list-prompt">Prompt</label>
                    <textarea
                      id="question-list-prompt"
                      className="settings-textarea"
                      placeholder="Standard-Prompt wird angezeigt..."
                      value={questionListPrompt}
                      onChange={(e) => setQuestionListPrompt(e.target.value)}
                      rows={20}
                    />
                    <div style={{ display: 'flex', gap: '0.7rem', alignItems: 'center', marginTop: '0.7rem' }}>
                      <button
                        className="settings-save-btn"
                        onClick={saveQuestionListPrompt}
                        disabled={questionListPromptLoading}
                      >
                        {questionListPromptLoading ? 'Speichere...' : 'Speichern'}
                      </button>
                      {questionListPromptSaved && (
                        <span className="settings-saved-indicator">✓ Gespeichert</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="settings-section">
                  <h3>Frageliste - Word-Vorlage</h3>
                  <p className="settings-description">
                    Laden Sie hier eine benutzerdefinierte Word-Vorlage (.docx) für die Frageliste hoch.
                    Die hochgeladene Vorlage ersetzt die Standard-Vorlage "Frageliste Vorlage.docx" im Vorlagen-Verzeichnis.
                  </p>
                  <div className="settings-input-group">
                    <label htmlFor="question-list-template">Vorlage hochladen</label>
                    <input
                      id="question-list-template"
                      type="file"
                      accept=".docx"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          if (!file.name.endsWith('.docx')) {
                            alert('Bitte wählen Sie eine .docx Datei aus');
                            return;
                          }
                          try {
                            await settingsApi.uploadQuestionListTemplate(file);
                            alert('Vorlage erfolgreich hochgeladen!');
                            e.target.value = '';
                            loadQuestionListTemplateStatus();
                          } catch (error: any) {
                            console.error('Fehler beim Hochladen der Vorlage:', error);
                            alert('Fehler beim Hochladen der Vorlage: ' + (error.response?.data?.detail || error.message));
                          }
                        }
                      }}
                      style={{
                        padding: '0.7rem',
                        background: 'rgba(255, 255, 255, 0.1)',
                        border: '1px solid rgba(255, 255, 255, 0.3)',
                        borderRadius: '7px',
                        color: 'var(--text-primary)',
                        fontSize: '0.875rem',
                        width: '100%',
                        cursor: 'pointer'
                      }}
                    />
                    {questionListTemplateLoading ? (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.7rem' }}>
                        Prüfe Status...
                      </p>
                    ) : questionListTemplateStatus?.exists ? (
                      <div style={{ 
                        marginTop: '0.7rem', 
                        padding: '0.7rem', 
                        background: 'rgba(52, 199, 89, 0.2)', 
                        border: '1px solid rgba(52, 199, 89, 0.4)', 
                        borderRadius: '7px',
                        fontSize: '0.75rem'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#34c759', fontWeight: 600 }}>
                          <span>✓</span>
                          <span>Vorlage erfolgreich hinterlegt</span>
                        </div>
                        {questionListTemplateStatus.filename && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Datei: {questionListTemplateStatus.filename}
                          </div>
                        )}
                        {questionListTemplateStatus.size && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Größe: {(questionListTemplateStatus.size / 1024).toFixed(1)} KB
                          </div>
                        )}
                        {questionListTemplateStatus.modified && (
                          <div style={{ marginTop: '0.35rem', color: 'var(--text-secondary)' }}>
                            Geändert: {new Date(questionListTemplateStatus.modified).toLocaleString('de-DE')}
                          </div>
                        )}
                      </div>
                    ) : (
                      <p style={{ 
                        fontSize: '0.75rem', 
                        color: 'rgba(255, 59, 48, 0.9)', 
                        marginTop: '0.7rem',
                        padding: '0.7rem',
                        background: 'rgba(255, 59, 48, 0.1)',
                        border: '1px solid rgba(255, 59, 48, 0.3)',
                        borderRadius: '7px'
                      }}>
                        ⚠ Keine Vorlage hinterlegt. Bitte laden Sie eine Word-Vorlage (.docx) hoch.
                      </p>
                    )}
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.7rem', fontStyle: 'italic' }}>
                      Die hochgeladene Vorlage ersetzt die Standard-Vorlage "Frageliste Vorlage.docx" im Vorlagen-Verzeichnis.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {projectDetailsModal && (
        <div className="project-details-modal-overlay" onClick={() => {
          setProjectDetailsModal(null);
          setSelectedProjectId(null);
        }}>
          <div className="project-details-modal-content glass" onClick={(e) => e.stopPropagation()}>
            {loadingDetails ? (
              <div className="loading-details">Lade Details...</div>
            ) : (
              <>
                <div className="project-details-header">
                  <h2 className="project-details-title">{projectDetailsModal.project?.name || 'Projekt-Details'}</h2>
                  <button className="project-details-close" onClick={() => {
                    setProjectDetailsModal(null);
                    setSelectedProjectId(null);
                  }}>×</button>
                </div>
                <div className="project-details-info">
                  <div className="project-info-item">
                    <strong>Projektnummer:</strong> {extractProjectNumber(projectDetailsModal.project?.description) || '-'}
                  </div>
                  <div className="project-info-item">
                    <strong>Standort:</strong> {projectDetailsModal.project?.standort || '-'}
                  </div>
                  <div className="project-info-item">
                    <strong>Status:</strong> <span className={`project-status status-${projectDetailsModal.project?.status}`}>
                      {projectDetailsModal.project?.status}
                    </span>
                  </div>
                  <div className="project-info-item">
                    <strong>Erstellt:</strong> {projectDetailsModal.project?.created_at ? new Date(projectDetailsModal.project.created_at).toLocaleDateString('de-DE') : '-'}
                  </div>
                </div>

                <div className="project-details-section">
                  <h3 className="section-title">Aktionen</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
                    <button
                      className="legal-review-btn"
                      onClick={async () => {
                        if (!projectDetailsModal?.project?.id) return;
                        setLegalReviewLoading(true);
                        setLegalReviewStep('initializing');
                        try {
                          // Schritt 1: Text wird extrahiert
                          setLegalReviewStep('extracting');
                          await new Promise(resolve => setTimeout(resolve, 500)); // Kurze Verzögerung für UX
                          
                          // Schritt 2: Prompt wird geladen
                          setLegalReviewStep('loading_prompt');
                          await new Promise(resolve => setTimeout(resolve, 300));
                          
                          // Schritt 3: AI-Analyse läuft (dieser Schritt dauert am längsten)
                          setLegalReviewStep('ai_analysis');
                          
                          // API-Call starten
                          const result = await legalReviewApi.start(projectDetailsModal.project.id, true);
                          
                          // Schritt 4: Word-Dokument wird generiert
                          setLegalReviewStep('generating_document');
                          await new Promise(resolve => setTimeout(resolve, 500));
                          
                          // Schritt 5: Datei wird gespeichert
                          setLegalReviewStep('saving');
                          await new Promise(resolve => setTimeout(resolve, 300));
                          
                          if (result && result.success) {
                            // Schritt 6: Fertig
                            setLegalReviewStep('completed');
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Prüfungsergebnisse speichern
                            if (result.analysis_result) {
                              setLegalReviewResults(result.analysis_result);
                            }
                            
                            alert('Rechtliche Prüfung erfolgreich abgeschlossen! Das Word-Dokument wurde dem Projekt hinzugefügt.');
                            // Projekt-Details neu laden, um die neue Datei anzuzeigen
                            const details = await projectsApi.getDetails(projectDetailsModal.project.id);
                            const extractedData = await projectsApi.getExtractedDataByFile(projectDetailsModal.project.id);
                            setProjectDetailsModal({
                              ...details,
                              extractedDataByFile: extractedData
                            });
                          } else {
                            alert('Rechtliche Prüfung fehlgeschlagen: ' + (result?.message || 'Unbekannter Fehler'));
                          }
                        } catch (error: any) {
                          console.error('Fehler bei der rechtlichen Prüfung:', error);
                          setLegalReviewStep('error');
                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unbekannter Fehler';
                          alert('Fehler bei der rechtlichen Prüfung: ' + errorMessage);
                        } finally {
                          setLegalReviewLoading(false);
                          setLegalReviewStep(null);
                        }
                      }}
                      disabled={legalReviewLoading}
                    >
                      {legalReviewLoading ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', justifyContent: 'center' }}>
                          <span className="legal-review-spinner">⏳</span>
                          <span>{legalReviewStep === 'extracting' ? 'Text wird extrahiert...' :
                                 legalReviewStep === 'loading_prompt' ? 'Prompt wird geladen...' :
                                 legalReviewStep === 'ai_analysis' ? 'AI-Analyse läuft...' :
                                 legalReviewStep === 'generating_document' ? 'Word-Dokument wird generiert...' :
                                 legalReviewStep === 'saving' ? 'Datei wird gespeichert...' :
                                 legalReviewStep === 'completed' ? 'Fertig!' :
                                 legalReviewStep === 'error' ? 'Fehler aufgetreten' :
                                 'Prüfung läuft...'}</span>
                        </span>
                      ) : 'Rechtliche Prüfung starten'}
                    </button>
                    <button
                      className="question-list-btn"
                      onClick={async () => {
                        if (!projectDetailsModal?.project?.id) return;
                        setQuestionListLoading(true);
                        setQuestionListStep('initializing');
                        try {
                          // Schritt 1: Text wird extrahiert
                          setQuestionListStep('extracting');
                          await new Promise(resolve => setTimeout(resolve, 500));
                          
                          // Schritt 2: Prompt wird geladen
                          setQuestionListStep('loading_prompt');
                          await new Promise(resolve => setTimeout(resolve, 300));
                          
                          // Schritt 3: AI-Analyse läuft
                          setQuestionListStep('ai_analysis');
                          
                          // API-Call starten
                          const result = await questionListApi.start(projectDetailsModal.project.id);
                          
                          // Schritt 4: Word-Dokument wird generiert
                          setQuestionListStep('generating_document');
                          await new Promise(resolve => setTimeout(resolve, 500));
                          
                          // Schritt 5: Datei wird gespeichert
                          setQuestionListStep('saving');
                          await new Promise(resolve => setTimeout(resolve, 300));
                          
                          if (result && result.success) {
                            // Schritt 6: Fertig
                            setQuestionListStep('completed');
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            alert('Frageliste erfolgreich generiert! Das Word-Dokument wurde dem Projekt hinzugefügt.');
                            // Projekt-Details neu laden, um die neue Datei anzuzeigen
                            const details = await projectsApi.getDetails(projectDetailsModal.project.id);
                            const extractedData = await projectsApi.getExtractedDataByFile(projectDetailsModal.project.id);
                            setProjectDetailsModal({
                              ...details,
                              extractedDataByFile: extractedData
                            });
                          } else {
                            alert('Frageliste-Generierung fehlgeschlagen: ' + (result?.message || 'Unbekannter Fehler'));
                          }
                        } catch (error: any) {
                          console.error('Fehler bei der Frageliste-Generierung:', error);
                          setQuestionListStep('error');
                          const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Unbekannter Fehler';
                          alert('Fehler bei der Frageliste-Generierung: ' + errorMessage);
                        } finally {
                          setQuestionListLoading(false);
                          setQuestionListStep(null);
                        }
                      }}
                      disabled={questionListLoading}
                    >
                      {questionListLoading ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', justifyContent: 'center' }}>
                          <span className="question-list-spinner">⏳</span>
                          <span>{questionListStep === 'extracting' ? 'Text wird extrahiert...' :
                                 questionListStep === 'loading_prompt' ? 'Prompt wird geladen...' :
                                 questionListStep === 'ai_analysis' ? 'AI-Analyse läuft...' :
                                 questionListStep === 'generating_document' ? 'Word-Dokument wird generiert...' :
                                 questionListStep === 'saving' ? 'Datei wird gespeichert...' :
                                 questionListStep === 'completed' ? 'Fertig!' :
                                 questionListStep === 'error' ? 'Fehler aufgetreten' :
                                 'Generierung läuft...'}</span>
                        </span>
                      ) : 'Frageliste generieren'}
                    </button>
                    {legalReviewLoading && legalReviewStep && (
                      <div style={{ 
                        marginTop: '0.7rem', 
                        padding: '0.7rem', 
                        background: 'rgba(255, 255, 255, 0.1)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)', 
                        borderRadius: '7px',
                        fontSize: '0.75rem'
                      }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: legalReviewStep === 'extracting' ? 'var(--text-primary)' : (['loading_prompt', 'ai_analysis', 'generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{legalReviewStep === 'extracting' ? '⏳' : (['loading_prompt', 'ai_analysis', 'generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '✓' : '○')}</span>
                            <span>Text wird extrahiert...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: legalReviewStep === 'loading_prompt' ? 'var(--text-primary)' : (['ai_analysis', 'generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{legalReviewStep === 'loading_prompt' ? '⏳' : (['ai_analysis', 'generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '✓' : '○')}</span>
                            <span>Prompt wird geladen...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: legalReviewStep === 'ai_analysis' ? 'var(--text-primary)' : (['generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{legalReviewStep === 'ai_analysis' ? '⏳' : (['generating_document', 'saving', 'completed'].includes(legalReviewStep) ? '✓' : '○')}</span>
                            <span>AI-Analyse läuft...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: legalReviewStep === 'generating_document' ? 'var(--text-primary)' : (['saving', 'completed'].includes(legalReviewStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{legalReviewStep === 'generating_document' ? '⏳' : (['saving', 'completed'].includes(legalReviewStep) ? '✓' : '○')}</span>
                            <span>Word-Dokument wird generiert...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: legalReviewStep === 'saving' ? 'var(--text-primary)' : (legalReviewStep === 'completed' ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{legalReviewStep === 'saving' ? '⏳' : (legalReviewStep === 'completed' ? '✓' : '○')}</span>
                            <span>Datei wird gespeichert...</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {questionListLoading && questionListStep && (
                      <div style={{ 
                        marginTop: '0.7rem', 
                        padding: '0.7rem', 
                        background: 'rgba(255, 255, 255, 0.1)', 
                        border: '1px solid rgba(255, 255, 255, 0.2)', 
                        borderRadius: '7px',
                        fontSize: '0.75rem'
                      }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: questionListStep === 'extracting' ? 'var(--text-primary)' : (['loading_prompt', 'ai_analysis', 'generating_document', 'saving', 'completed'].includes(questionListStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{questionListStep === 'extracting' ? '⏳' : (['loading_prompt', 'ai_analysis', 'generating_document', 'saving', 'completed'].includes(questionListStep) ? '✓' : '○')}</span>
                            <span>Text wird extrahiert...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: questionListStep === 'loading_prompt' ? 'var(--text-primary)' : (['ai_analysis', 'generating_document', 'saving', 'completed'].includes(questionListStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{questionListStep === 'loading_prompt' ? '⏳' : (['ai_analysis', 'generating_document', 'saving', 'completed'].includes(questionListStep) ? '✓' : '○')}</span>
                            <span>Prompt wird geladen...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: questionListStep === 'ai_analysis' ? 'var(--text-primary)' : (['generating_document', 'saving', 'completed'].includes(questionListStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{questionListStep === 'ai_analysis' ? '⏳' : (['generating_document', 'saving', 'completed'].includes(questionListStep) ? '✓' : '○')}</span>
                            <span>AI-Analyse läuft...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: questionListStep === 'generating_document' ? 'var(--text-primary)' : (['saving', 'completed'].includes(questionListStep) ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{questionListStep === 'generating_document' ? '⏳' : (['saving', 'completed'].includes(questionListStep) ? '✓' : '○')}</span>
                            <span>Word-Dokument wird generiert...</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: questionListStep === 'saving' ? 'var(--text-primary)' : (questionListStep === 'completed' ? '#34c759' : 'var(--text-secondary)') }}>
                            <span>{questionListStep === 'saving' ? '⏳' : (questionListStep === 'completed' ? '✓' : '○')}</span>
                            <span>Datei wird gespeichert...</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Rechtliche Prüfung Ergebnisse */}
                {legalReviewResults && (
                  <div className="project-details-section">
                    <h3 className="section-title">Rechtliche Prüfung</h3>
                    {legalReviewResultsLoading ? (
                      <div className="loading-details">Lade Prüfungsergebnisse...</div>
                    ) : legalReviewResults.kritische_punkte && legalReviewResults.kritische_punkte.length > 0 ? (
                      <div className="legal-review-results">
                        {legalReviewResults.allgemeine_einschaetzung && (
                          <div className="legal-review-summary">
                            <h4 className="section-subtitle">Allgemeine Einschätzung</h4>
                            <p>{legalReviewResults.allgemeine_einschaetzung}</p>
                          </div>
                        )}
                        <div className="legal-review-points">
                          <h4 className="section-subtitle">Kritische Punkte ({legalReviewResults.kritische_punkte.length})</h4>
                          {legalReviewResults.kritische_punkte.map((punkt: any) => {
                            const rating = punkt.risiko_rating?.toLowerCase() || 'grün';
                            const ratingClass = `risk-rating-${rating}`;
                            return (
                              <div key={punkt.nummer} className="legal-review-point">
                                <div className="legal-review-point-header">
                                  <span className="legal-review-point-number">[{punkt.nummer}]</span>
                                  <h5 className="legal-review-point-title">{punkt.titel}</h5>
                                  <span className={`legal-review-rating ${ratingClass}`}>{rating.toUpperCase()}</span>
                                </div>
                                {punkt.zitat && (
                                  <div className="legal-review-quote">
                                    <strong>Zitat:</strong>
                                    {punkt.quelle_datei && (
                                      <span className="legal-review-source">
                                        {' '}(Quelle: {punkt.quelle_datei}
                                        {punkt.quelle_paragraph && `, Absatz ${punkt.quelle_paragraph}`})
                                      </span>
                                    )}
                                    <div className="legal-review-quote-text">{punkt.zitat}</div>
                                  </div>
                                )}
                                {punkt.beurteilung && (
                                  <div className="legal-review-assessment">
                                    <strong>Beurteilung:</strong> {punkt.beurteilung}
                                  </div>
                                )}
                                {punkt.empfehlung && (
                                  <div className="legal-review-recommendation">
                                    <strong>Empfehlung:</strong> {punkt.empfehlung}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <p className="no-data">Keine Prüfungsergebnisse verfügbar. Bitte starten Sie eine rechtliche Prüfung.</p>
                    )}
                  </div>
                )}

                <div className="project-details-section">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.7rem' }}>
                    <h3 className="section-title">Hochgeladene Dateien</h3>
                    <button
                      className="add-files-btn glass-strong"
                      onClick={() => setShowProjectFileUpload(true)}
                      title="Dateien hinzufügen"
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M8 2v12M2 8h12"/>
                      </svg>
                      Dateien hinzufügen
                    </button>
                  </div>
                  <div className="files-table-container">
                    {projectDetailsModal?.files && Array.isArray(projectDetailsModal.files) && projectDetailsModal.files.length > 0 ? (
                      <table className="files-table">
                        <thead>
                          <tr>
                            <th>Dateiname</th>
                            <th>Typ</th>
                            <th>Größe</th>
                            <th>Datum</th>
                            <th>Extrahiert</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {projectDetailsModal.files.filter((file: any) => file && file.id).map((file: any) => {
                            try {
                              const extractedData = projectDetailsModal.extractedDataByFile?.files?.find((f: any) => f?.file_id === file.id);
                              const stats = extractedData?.extracted_data || {};
                              const totalEntities = (stats.raeume?.length || 0) + 
                                                   (stats.anlagen?.length || 0) + 
                                                   (stats.geraete?.length || 0) + 
                                                   (stats.anforderungen?.length || 0) + 
                                                   (stats.termine?.length || 0) + 
                                                   (stats.leistungen?.length || 0);
                              
                              // Prüfe auch auf full_text (wichtig für Word-Dateien)
                              const hasFullText = stats.full_text && (
                                (Array.isArray(stats.full_text) && stats.full_text.length > 0) ||
                                (typeof stats.full_text === 'string' && stats.full_text.trim().length > 0)
                              );
                              
                              // const hasExtractedData = totalEntities > 0 || hasFullText; // Nicht verwendet
                              
                              // Prüfe, ob es ein generierter Report ist
                              const isGeneratedReport = file.document_type === 'rechtliche_pruefung' || 
                                                       file.document_type === 'frageliste' ||
                                                       file.original_filename?.startsWith('rechtliche_pruefung') ||
                                                       file.original_filename?.startsWith('report_') ||
                                                       file.original_filename?.includes('Frageliste');
                              
                              return (
                                <tr 
                                  key={file.id} 
                                  className={isGeneratedReport ? 'generated-report-row' : ''}
                                  onClick={(e) => {
                                    // Nur öffnen wenn nicht auf Button geklickt wurde
                                    if ((e.target as HTMLElement).closest('button')) {
                                      return;
                                    }
                                    if (file.file_type === 'IFC') {
                                      setSelectedIFCFile({ id: file.id, filename: file.original_filename || 'IFC-Datei' });
                                      setShowIFCViewer(true);
                                    }
                                  }}
                                  style={{ cursor: file.file_type === 'IFC' ? 'pointer' : 'default' }}
                                >
                                <td className="file-name-cell">
                                  <span className="file-icon-silhouette">
                                    {file.file_type === 'Excel' ? (
                                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <rect x="2" y="2" width="12" height="12" rx="1"/>
                                        <path d="M5 2v12M9 2v12M2 5h12M2 9h12"/>
                                      </svg>
                                    ) : file.file_type === 'Word' ? (
                                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <rect x="2" y="2" width="12" height="12" rx="1"/>
                                        <path d="M5 5h6M5 8h6M5 11h4"/>
                                      </svg>
                                    ) : file.file_type === 'PDF' ? (
                                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <rect x="2" y="2" width="12" height="12" rx="1"/>
                                        <path d="M5 5h6M5 8h6M5 11h4"/>
                                      </svg>
                                    ) : (
                                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M3 3h10v10H3z"/>
                                        <path d="M5 3v10M11 3v10M3 5h10M3 11h10"/>
                                      </svg>
                                    )}
                                  </span>
                                  <span className="file-name-text">{file.original_filename || 'Unbekannte Datei'}</span>
                                  {isGeneratedReport && (
                                    <span className="generated-report-badge" title="Generierter Report">
                                      📄 Report
                                    </span>
                                  )}
                                </td>
                                <td className="file-type-cell">{file.file_type || '-'}</td>
                                <td className="file-size-cell">{file.file_size ? ((file.file_size / 1024).toFixed(1) + ' KB') : '-'}</td>
                                <td className="file-date-cell">
                                  {file.upload_date ? new Date(file.upload_date).toLocaleDateString('de-DE') : '-'}
                                </td>
                                <td className="file-extracted-cell">
                                  {file.processed ? (
                                    <span className="extraction-status-badge">
                                      {totalEntities > 0 ? (
                                        <>
                                          {stats.raeume?.length > 0 && <span>R:{stats.raeume.length}</span>}
                                          {stats.anlagen?.length > 0 && <span>A:{stats.anlagen.length}</span>}
                                          {stats.geraete?.length > 0 && <span>G:{stats.geraete.length}</span>}
                                        </>
                                      ) : hasFullText ? (
                                        <span className="extraction-success-icon" title="Text extrahiert">✓ Text</span>
                                      ) : (
                                        <span className="extraction-success-icon">✓</span>
                                      )}
                                    </span>
                                  ) : (
                                    <span className="extraction-pending">-</span>
                                  )}
                                </td>
                                <td className="file-action-cell">
                                  <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                                    <button 
                                      className="file-download-btn-small"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                          await filesApi.download(file.id, file.original_filename || 'datei');
                                        } catch (error) {
                                          console.error('Fehler beim Download:', error);
                                          alert('Fehler beim Download der Datei');
                                        }
                                      }}
                                      title="Download"
                                    >
                                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                      <path d="M8 2v8M5 7l3 3 3-3M2 13h12"/>
                                    </svg>
                                  </button>
                                    <button 
                                      className="file-delete-btn-small"
                                      onClick={async (e) => {
                                        e.stopPropagation();
                                        if (window.confirm(`Möchten Sie die Datei "${file.original_filename || 'Unbekannte Datei'}" wirklich löschen?`)) {
                                          try {
                                            await filesApi.delete(file.id);
                                            // Projekt-Details neu laden, um die Dateiliste zu aktualisieren
                                            if (projectDetailsModal?.project?.id) {
                                              const details = await projectsApi.getDetails(projectDetailsModal.project.id);
                                              const extractedData = await projectsApi.getExtractedDataByFile(projectDetailsModal.project.id);
                                              setProjectDetailsModal({
                                                ...details,
                                                extractedDataByFile: extractedData
                                              });
                                            }
                                          } catch (error) {
                                            console.error('Fehler beim Löschen:', error);
                                            alert('Fehler beim Löschen der Datei');
                                          }
                                        }
                                      }}
                                      title="Löschen"
                                    >
                                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                        <path d="M3 4h10M6 4V2a1 1 0 011-1h2a1 1 0 011 1v2M5 4v10a1 1 0 001 1h4a1 1 0 001-1V4M8 7v4M6 7v4M10 7v4"/>
                                      </svg>
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            );
                            } catch (error) {
                              console.error('Fehler beim Rendern der Datei:', error, file);
                              return (
                                <tr key={file.id || Math.random()}>
                                  <td colSpan={6} style={{ color: 'red', padding: '0.7rem' }}>
                                    Fehler beim Laden der Datei: {file.original_filename || 'Unbekannt'}
                                  </td>
                                </tr>
                              );
                            }
                          })}
                        </tbody>
                      </table>
                    ) : (
                      <p className="no-data">Keine Dateien vorhanden</p>
                    )}
                  </div>
                </div>

                <div className="project-details-section">
                  <h3 className="section-title">Extrahierte Daten (nach Datei)</h3>
                  {projectDetailsModal.extractedDataByFile?.files && projectDetailsModal.extractedDataByFile.files.length > 0 ? (
                    <div className="extracted-data-by-file">
                      {projectDetailsModal.extractedDataByFile.files.map((fileData: any) => {
                        const ed = fileData.extracted_data || {};
                        const entityTypes = [
                          { key: 'raeume', label: 'Räume', data: ed.raeume || [] },
                          { key: 'anlagen', label: 'Anlagen', data: ed.anlagen || [] },
                          { key: 'geraete', label: 'Geräte', data: ed.geraete || [] },
                          { key: 'anforderungen', label: 'Anforderungen', data: ed.anforderungen || [] },
                          { key: 'termine', label: 'Termine', data: ed.termine || [] },
                          { key: 'leistungen', label: 'Leistungen', data: ed.leistungen || [] },
                        ].filter(et => et.data.length > 0);
                        
                        const hasRawTables = ed.raw_tables && ed.raw_tables.length > 0;
                        const hasFullText = ed.full_text && ed.full_text.length > 0;
                        const hasMetadata = ed.metadata && Object.keys(ed.metadata).length > 0;

                        return (
                          <div key={fileData.file_id} className="file-data-section">
                            <h4 className="file-data-title">
                              <span className="file-icon-silhouette">
                                {fileData.file_type === 'Excel' ? (
                                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <rect x="2" y="2" width="12" height="12" rx="1"/>
                                    <path d="M5 2v12M9 2v12M2 5h12M2 9h12"/>
                                  </svg>
                                ) : fileData.file_type === 'Word' ? (
                                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <rect x="2" y="2" width="12" height="12" rx="1"/>
                                    <path d="M5 5h6M5 8h6M5 11h4"/>
                                  </svg>
                                ) : fileData.file_type === 'PDF' ? (
                                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <rect x="2" y="2" width="12" height="12" rx="1"/>
                                    <path d="M5 5h6M5 8h6M5 11h4"/>
                                  </svg>
                                ) : (
                                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <path d="M3 3h10v10H3z"/>
                                    <path d="M5 3v10M11 3v10M3 5h10M3 11h10"/>
                                  </svg>
                                )}
                              </span>
                              {fileData.filename}
                            </h4>
                            {entityTypes.length > 0 ? (
                              <details className="entity-types-container" open>
                                <summary className="entity-types-summary">Strukturierte Daten ({entityTypes.reduce((sum, et) => sum + et.data.length, 0)} Einträge)</summary>
                                <div className="entity-type-tabs">
                                  {entityTypes.map((et) => (
                                    <details key={et.key} className="entity-type-section">
                                      <summary className="entity-type-title">{et.label} ({et.data.length})</summary>
                                      <div className="entity-table" style={{ marginTop: '0.49rem' }}>
                                        <table>
                                          <thead>
                                            <tr>
                                              {Object.keys(et.data[0] || {}).filter(k => k !== 'quelle').map(key => (
                                                <th key={key}>{key}</th>
                                              ))}
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {et.data.slice(0, 10).map((entity: any, idx: number) => (
                                              <tr key={idx}>
                                                {Object.keys(entity).filter(k => k !== 'quelle').map(key => (
                                                  <td key={key} title={String(entity[key] || '-')}>{String(entity[key] || '-')}</td>
                                                ))}
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                        {et.data.length > 10 && (
                                          <p className="more-data-indicator">... und {et.data.length - 10} weitere</p>
                                        )}
                                      </div>
                                    </details>
                                  ))}
                                </div>
                              </details>
                            ) : (
                              <p className="no-data">Keine strukturierten Daten extrahiert</p>
                            )}
                            
                            {/* Raw Tables Anzeige */}
                            {hasRawTables && (
                              <details className="raw-tables-section">
                                <summary className="section-subtitle">Rohtabellen ({ed.raw_tables.length})</summary>
                                <div style={{ marginTop: '0.35rem' }}>
                                  {ed.raw_tables.map((table: any, tableIdx: number) => (
                                    <details key={tableIdx} className="raw-table-item">
                                      <summary>
                                        Tabelle {tableIdx + 1}: {table.sheet_name || 'Unbekannt'} 
                                        ({table.row_count || 0} Zeilen, {table.column_count || 0} Spalten)
                                      </summary>
                                      {table.headers && table.rows && (
                                        <div className="raw-table-content">
                                          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                                            <table className="entity-table">
                                              <thead>
                                                <tr>
                                                  {table.headers.map((header: string, hIdx: number) => (
                                                    <th key={hIdx}>{header}</th>
                                                  ))}
                                                </tr>
                                              </thead>
                                              <tbody>
                                                {table.rows.slice(0, 50).map((row: any, rIdx: number) => (
                                                  <tr key={rIdx}>
                                                    {table.headers.map((header: string, cIdx: number) => (
                                                      <td key={cIdx}>{String(row[header] || '')}</td>
                                                    ))}
                                                  </tr>
                                                ))}
                                              </tbody>
                                            </table>
                                          </div>
                                          {table.rows.length > 50 && (
                                            <p className="more-data-indicator">... und {table.rows.length - 50} weitere Zeilen</p>
                                          )}
                                        </div>
                                      )}
                                    </details>
                                  ))}
                                </div>
                              </details>
                            )}
                            
                            {/* Full Text Anzeige */}
                            {hasFullText && (
                              <details className="full-text-section">
                                <summary className="section-subtitle">Unstrukturierter Text ({ed.full_text.length} Einträge)</summary>
                                <div className="full-text-content" style={{ marginTop: '0.35rem' }}>
                                  {ed.full_text.map((textEntry: any, textIdx: number) => {
                                    const quelle = textEntry.quelle || {};
                                    const datei = quelle.datei || textEntry.datei;
                                    const absatz = quelle.absatz;
                                    const blatt = quelle.blatt || textEntry.sheet;
                                    const zelle = quelle.cell_reference || textEntry.cell_reference;
                                    const zeile = quelle.zeile;
                                    
                                    return (
                                      <div key={textIdx} className="full-text-item">
                                        <div className="full-text-meta">
                                          {datei && <span className="source-file">Datei: {datei}</span>}
                                          {absatz !== undefined && absatz !== null && <span className="source-paragraph">Absatz: {absatz + 1}</span>}
                                          {blatt && <span className="source-sheet">Blatt: {blatt}</span>}
                                          {zelle && <span className="source-cell">Zelle: {zelle}</span>}
                                          {zeile !== undefined && zeile !== null && <span className="source-row">Zeile: {zeile + 1}</span>}
                                        </div>
                                        <div className="full-text-body">{textEntry.content || textEntry}</div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </details>
                            )}
                            
                            {/* Metadata Anzeige */}
                            {hasMetadata && (
                              <div className="metadata-section">
                                <h5 className="section-subtitle">Metadaten</h5>
                                <details className="metadata-details">
                                  <summary>Metadaten anzeigen</summary>
                                  <pre className="metadata-content">
                                    {JSON.stringify(ed.metadata, null, 2)}
                                  </pre>
                                </details>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="no-data">Keine extrahierten Daten vorhanden</p>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {showProjectFileUpload && projectDetailsModal?.project?.id && (
        <ProjectFileUpload
          projectId={projectDetailsModal.project.id}
          onUploadSuccess={async () => {
            // Projekt-Details neu laden
            if (projectDetailsModal?.project?.id) {
              const details = await projectsApi.getDetails(projectDetailsModal.project.id);
              const extractedData = await projectsApi.getExtractedDataByFile(projectDetailsModal.project.id);
              setProjectDetailsModal({
                ...details,
                extractedDataByFile: extractedData
              });
            }
            setShowProjectFileUpload(false);
          }}
          onClose={() => setShowProjectFileUpload(false)}
        />
      )}

      {showIFCViewer && selectedIFCFile && (
        <IFCViewer
          fileId={selectedIFCFile.id}
          filename={selectedIFCFile.filename}
          onClose={() => {
            setShowIFCViewer(false);
            setSelectedIFCFile(null);
          }}
        />
      )}
    </div>
  );
}

export default App;
