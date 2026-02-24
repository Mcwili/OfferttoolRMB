import { useCallback, useState, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { filesApi } from '../services/api';
import './FileUpload.css';

interface ProjectFileUploadProps {
  projectId: number;
  onUploadSuccess?: () => void;
  onClose?: () => void;
}

const ProjectFileUpload = ({ projectId, onUploadSuccess, onClose }: ProjectFileUploadProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
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
    noClick: false,
    noKeyboard: false,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
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
      // Lade alle Dateien hoch
      const uploadPromises = files.map(async (file) => {
        try {
          setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
          
          const result = await filesApi.upload(file, projectId);
          
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
        // Schließe nach kurzer Verzögerung
        setTimeout(() => {
          if (onClose) {
            onClose();
          }
        }, 1500);
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
    }
  };

  return (
    <div className="project-file-upload-modal">
      <div className="project-file-upload-content glass">
        <div className="project-file-upload-header">
          <h3>Dateien zum Projekt hinzufügen</h3>
          {onClose && (
            <button className="close-btn" onClick={onClose} title="Schließen">
              <svg width="20" height="20" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 4L4 12M4 4l8 8"/>
              </svg>
            </button>
          )}
        </div>

        <div
          {...getRootProps()}
          className={`dropzone ${isDragActive ? 'active' : ''}`}
        >
          <input {...getInputProps()} />
          <div className="dropzone-content">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            <p className="dropzone-text">
              {isDragActive
                ? 'Dateien hier ablegen...'
                : 'Dateien hier ablegen oder klicken zum Auswählen'}
            </p>
            <p className="dropzone-hint">
              Unterstützt: PDF, Excel, Word, IFC, Bilder, ZIP
            </p>
          </div>
        </div>

        {files.length > 0 && (
          <div className="files-list">
            <h4>Ausgewählte Dateien ({files.length})</h4>
            <div className="files-grid">
              {files.map((file, index) => (
                <div key={index} className="file-item glass-strong">
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{(file.size / 1024).toFixed(1)} KB</span>
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
                    className="remove-file-btn"
                    onClick={() => removeFile(index)}
                    disabled={uploading}
                    title="Entfernen"
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 4L4 12M4 4l8 8"/>
                    </svg>
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

        <div className="upload-actions">
          <button
            onClick={uploadFiles}
            disabled={uploading || files.length === 0}
            className="upload-btn glass-strong"
            type="button"
          >
            {uploading 
              ? 'Wird hochgeladen...' 
              : `${files.length > 0 ? `${files.length} Datei(en)` : ''} hochladen`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProjectFileUpload;
