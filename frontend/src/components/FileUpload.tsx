import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { filesApi, projectsApi } from '../services/api';
import type { ProjectCreate } from '../services/api';
import './FileUpload.css';

interface FileUploadProps {
  onUploadSuccess?: () => void;
}

const FileUpload = ({ onUploadSuccess }: FileUploadProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [projectName, setProjectName] = useState('');
  const [projectNummer, setProjectNummer] = useState('');
  const [projectStandort, setProjectStandort] = useState('');
  const [textContent, setTextContent] = useState('');
  const [projectId, setProjectId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/ifc': ['.ifc'],
      'image/*': ['.jpg', '.jpeg', '.png', '.tiff'],
      'application/zip': ['.zip'],
    },
    multiple: true,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const createProject = async (): Promise<number> => {
    if (!projectName.trim()) {
      throw new Error('Projektname ist erforderlich');
    }

    try {
      const projectData: ProjectCreate = {
        name: projectName,
        description: projectNummer ? `Projektnummer: ${projectNummer}` : undefined,
        standort: projectStandort || undefined,
      };

      const project = await projectsApi.create(projectData);
      return project.id;
    } catch (err: any) {
      if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        throw new Error('Backend nicht erreichbar. Bitte stelle sicher, dass das Backend auf http://localhost:8000 läuft.');
      }
      throw err;
    }
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      setError('Bitte wähle mindestens eine Datei aus');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress({});

    try {
      // Erstelle Projekt falls noch nicht vorhanden
      let currentProjectId = projectId;
      if (!currentProjectId) {
        currentProjectId = await createProject();
        setProjectId(currentProjectId);
      }

      // Lade alle Dateien hoch
      const uploadPromises = files.map(async (file) => {
        try {
          setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
          
          const result = await filesApi.upload(file, currentProjectId!);
          
          setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
          return { success: true, file: file.name, result };
        } catch (err: any) {
          console.error('Upload-Fehler für', file.name, ':', err);
          return {
            success: false,
            file: file.name,
            error: err.response?.data?.detail || err.message || 'Upload fehlgeschlagen',
          };
        }
      });

      const results = await Promise.all(uploadPromises);
      const failed = results.filter((r) => !r.success);

      if (failed.length > 0) {
        setError(
          `${failed.length} Datei(en) konnten nicht hochgeladen werden: ${failed.map((f) => f.file).join(', ')}`
        );
      } else {
        setSuccess(`${files.length} Datei(en) erfolgreich hochgeladen!`);
        setFiles([]);
        if (onUploadSuccess) {
          onUploadSuccess();
        }
      }
    } catch (err: any) {
      let errorMessage = 'Ein Fehler ist aufgetreten';
      
      if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        errorMessage = 'Backend nicht erreichbar. Bitte stelle sicher, dass das Backend auf http://localhost:8000 läuft.';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setUploading(false);
      setTimeout(() => {
        setUploadProgress({});
        setSuccess(null);
      }, 3000);
    }
  };

  return (
    <div className="file-upload-container glass">
      <div className="upload-header">
        <h3 className="section-title">Dateien hochladen</h3>
        <p className="upload-description">
          Ziehe Dateien hierher oder klicke zum Auswählen
        </p>
      </div>

      {!projectId && (
        <div className="project-form">
          <div className="form-group">
            <label htmlFor="project-name">Projektname *</label>
            <input
              id="project-name"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="z.B. Bürogebäude Zürich"
              className="glass-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="project-nummer">Projektnummer</label>
            <input
              id="project-nummer"
              type="text"
              value={projectNummer}
              onChange={(e) => setProjectNummer(e.target.value)}
              placeholder="z.B. PROJ-2024-001"
              className="glass-input"
            />
          </div>
          <div className="form-group">
            <label htmlFor="project-standort">Standort</label>
            <input
              id="project-standort"
              type="text"
              value={projectStandort}
              onChange={(e) => setProjectStandort(e.target.value)}
              placeholder="z.B. Zürich"
              className="glass-input"
            />
          </div>
        </div>
      )}

      {projectId && (
        <div className="project-info glass-strong">
          <div className="project-info-main">
            <span className="project-label">Projekt:</span>
            <span className="project-name">{projectName}</span>
            {projectNummer && (
              <span className="project-nummer">({projectNummer})</span>
            )}
          </div>
          <button
            onClick={() => {
              setProjectId(null);
              setProjectName('');
              setProjectNummer('');
              setProjectStandort('');
              setTextContent('');
            }}
            className="change-project-btn"
          >
            Ändern
          </button>
        </div>
      )}

      <div className="text-input-section">
        <label htmlFor="text-content" className="text-input-label">
          Textinhalt eingeben
        </label>
        <textarea
          id="text-content"
          className="text-input glass-input"
          placeholder="Fügen Sie hier Textinhalte direkt ein oder kopieren Sie Inhalte aus anderen Dokumenten..."
          value={textContent}
          onChange={(e) => setTextContent(e.target.value)}
          rows={8}
        />
      </div>

      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${files.length > 0 ? 'has-files' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="dropzone-content">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="upload-icon"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          {isDragActive ? (
            <p className="dropzone-text">Dateien hier ablegen...</p>
          ) : (
            <p className="dropzone-text">
              Ziehe Dateien hierher oder <span className="link-text">klicke zum Auswählen</span>
            </p>
          )}
          <p className="dropzone-hint">
            Unterstützt: PDF, Excel, Word, IFC, Bilder, ZIP
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="files-list">
          <div className="files-header">
            <span className="files-count">{files.length} Datei(en) ausgewählt</span>
            <button onClick={() => setFiles([])} className="clear-btn">
              Alle entfernen
            </button>
          </div>
          <div className="files-grid">
            {files.map((file, index) => (
              <div key={index} className="file-item glass-strong">
                <div className="file-info">
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>
                {uploadProgress[file.name] !== undefined && (
                  <div className="upload-progress">
                    <div
                      className="progress-bar"
                      style={{ width: `${uploadProgress[file.name]}%` }}
                    />
                  </div>
                )}
                <button
                  onClick={() => removeFile(index)}
                  className="remove-btn"
                  disabled={uploading}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="message error glass-strong">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="message success glass-strong">
          <span>✓</span>
          <span>{success}</span>
        </div>
      )}

      {(files.length > 0 || textContent.trim()) && (
        <>
          {!projectName.trim() && (
            <div className="message warning glass-strong">
              <span>ℹ️</span>
              <span>Bitte gib einen Projektnamen ein, um fortzufahren</span>
            </div>
          )}
          <button
            onClick={uploadFiles}
            disabled={uploading || !projectName.trim() || (files.length === 0 && !textContent.trim())}
            className="upload-btn glass-strong"
            type="button"
          >
            {uploading 
              ? 'Wird hochgeladen...' 
              : `${files.length > 0 ? `${files.length} Datei(en)` : ''}${files.length > 0 && textContent.trim() ? ' und ' : ''}${textContent.trim() ? 'Text' : ''} hochladen`}
          </button>
        </>
      )}
    </div>
  );
};

export default FileUpload;
