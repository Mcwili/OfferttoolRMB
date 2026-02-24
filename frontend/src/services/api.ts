import axios from 'axios';

// Verwende direkte Verbindung, da Vite-Proxy Probleme verursacht
// In Production: direkte URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.DEV ? 'http://localhost:8000/api' : 'http://localhost:8000/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 Minuten Timeout für AI-Analysen und Datei-Uploads
});

// Request Interceptor für besseres Error-Handling
api.interceptors.request.use(
  (config) => {
    // Logging für Debugging
    console.log('API Request:', {
      url: config.url,
      baseURL: config.baseURL,
      fullURL: `${config.baseURL}${config.url}`,
      method: config.method,
      headers: config.headers
    });
    return config;
  },
  (error) => {
    console.error('Request Interceptor Error:', error);
    return Promise.reject(error);
  }
);

// Response Interceptor für besseres Error-Handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Detailliertes Error-Logging für Debugging
    console.error('API Error Details:', {
      message: error.message,
      code: error.code,
      name: error.name,
      config: error.config ? {
        url: error.config.url,
        baseURL: error.config.baseURL,
        method: error.config.method,
        headers: error.config.headers
      } : null,
      response: error.response ? {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data
      } : null,
      request: error.request ? {
        readyState: error.request.readyState,
        status: error.request.status,
        statusText: error.request.statusText
      } : null
    });
    
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout - Backend antwortet nicht';
    } else if (!error.response) {
      if (error.code === 'ERR_NETWORK' || error.message?.includes('Failed to fetch')) {
        error.message = `Netzwerkfehler: Backend nicht erreichbar. Bitte prüfe:\n- Backend läuft auf http://localhost:8000\n- Keine Firewall blockiert die Verbindung\n- Browser-Konsole für weitere Details öffnen (F12)`;
      } else {
        error.message = 'Backend nicht erreichbar. Bitte stelle sicher, dass das Backend auf http://localhost:8000 läuft.';
      }
    }
    return Promise.reject(error);
  }
);

export interface Project {
  id: number;
  name: string;
  description?: string;
  standort?: string;
  status: string;
  created_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  standort?: string;
}

export interface FileUploadResponse {
  id: number;
  project_id: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  upload_date: string;
  document_type?: string | null;
  discipline?: string | null;
  revision?: string | null;
  processed: boolean;
}

// Projects API
export const projectsApi = {
  getAll: async (): Promise<Project[]> => {
    const response = await api.get('/v1/projects/');
    return response.data;
  },

  getById: async (id: number): Promise<Project> => {
    const response = await api.get(`/v1/projects/${id}`);
    return response.data;
  },

  getDetails: async (id: number): Promise<any> => {
    const response = await api.get(`/v1/projects/${id}/details`);
    return response.data;
  },

  getExtractedDataByFile: async (id: number): Promise<any> => {
    const response = await api.get(`/v1/projects/${id}/extracted-data-by-file`);
    return response.data;
  },

  create: async (project: ProjectCreate): Promise<Project> => {
    const response = await api.post('/v1/projects/', project);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/v1/projects/${id}`);
  },
};

// Files API
export const filesApi = {
  upload: async (
    file: File,
    projectId: number,
    _documentType?: string,
    _discipline?: string
  ): Promise<FileUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    // project_id ist im URL-Path, nicht im FormData
    // document_type und discipline werden vom Backend automatisch erkannt

    const response = await api.post(`/v1/files/upload/${projectId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    // Backend gibt UploadResponse zurück mit files-Array
    // Wir nehmen die erste Datei aus dem Array
    const result = response.data.files?.[0] || response.data;
    return result;
  },

  getById: async (id: number): Promise<any> => {
    const response = await api.get(`/v1/files/${id}`);
    return response.data;
  },

  download: async (fileId: number, filename: string): Promise<void> => {
    const response = await api.get(`/v1/files/${fileId}/download`, {
      responseType: 'blob',
    });
    
    // Blob erstellen und Download triggern
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  delete: async (fileId: number): Promise<void> => {
    await api.delete(`/v1/files/${fileId}`);
  },

  getFileAsBlob: async (fileId: number, onProgress?: (progress: number) => void): Promise<Blob> => {
    const startTime = Date.now();
    console.log(`[API] Starting blob download for file ${fileId}`);
    
    try {
      const response = await api.get(`/v1/files/${fileId}/download`, {
        responseType: 'blob',
        timeout: 600000, // 10 Minuten Timeout für große IFC-Dateien
        onDownloadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(percentCompleted);
            console.log(`[API] Download progress: ${percentCompleted}% (${progressEvent.loaded}/${progressEvent.total} bytes)`);
          } else if (onProgress) {
            // Wenn total nicht verfügbar ist, verwende loaded als Indikator
            console.log(`[API] Download progress: ${progressEvent.loaded} bytes loaded (total unknown)`);
          }
        },
      });
      
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      const blob = response.data;
      
      console.log(`[API] Blob download completed`, {
        fileId,
        blobSize: blob.size,
        blobType: blob.type,
        duration: `${duration}s`,
        responseStatus: response.status,
        responseHeaders: {
          contentType: response.headers['content-type'],
          contentLength: response.headers['content-length']
        }
      });
      
      // Validate blob
      if (!(blob instanceof Blob)) {
        throw new Error(`Unerwarteter Response-Typ: ${typeof blob}, erwartet: Blob`);
      }
      
      if (blob.size === 0) {
        throw new Error('Downloadierte Datei ist leer');
      }
      
      return blob;
    } catch (error: any) {
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;
      
      console.error(`[API] Blob download failed`, {
        fileId,
        duration: `${duration}s`,
        error: {
          message: error?.message,
          code: error?.code,
          name: error?.name,
          response: error?.response ? {
            status: error.response.status,
            statusText: error.response.statusText,
            headers: error.response.headers,
            dataType: typeof error.response.data,
            dataSize: error.response.data instanceof Blob ? error.response.data.size : 'N/A'
          } : null,
          request: error?.request ? {
            readyState: error.request.readyState,
            status: error.request.status
          } : null
        }
      });
      
      // Verbesserte Fehlermeldungen
      if (error?.code === 'ECONNABORTED') {
        throw new Error(`Download-Timeout nach ${duration}s. Die Datei ist möglicherweise zu groß oder das Backend antwortet nicht.`);
      } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Failed to fetch')) {
        throw new Error(`Netzwerkfehler: Backend nicht erreichbar oder Verbindung abgebrochen. Bitte prüfe:\n- Backend läuft auf http://localhost:8000\n- Keine Firewall blockiert die Verbindung\n- Browser-Konsole für Details (F12)`);
      } else if (error?.response) {
        const status = error.response.status;
        const statusText = error.response.statusText;
        let detail = '';
        
        // Versuche Fehlerdetails aus der Response zu extrahieren
        if (error.response.data instanceof Blob) {
          // Wenn es ein Blob ist, versuche es als Text zu lesen
          try {
            const text = await error.response.data.text();
            detail = text.substring(0, 200);
          } catch {
            detail = 'Fehlerdetails konnten nicht gelesen werden';
          }
        } else if (typeof error.response.data === 'string') {
          detail = error.response.data.substring(0, 200);
        } else if (error.response.data?.detail) {
          detail = error.response.data.detail;
        }
        
        throw new Error(`Backend-Fehler ${status} ${statusText}${detail ? `: ${detail}` : ''}`);
      }
      
      throw error;
    }
  },
};

// Extraction API
export const extractionApi = {
  start: async (projectId: number): Promise<any> => {
    const response = await api.post(`/v1/extraction/project/${projectId}`, {});
    return response.data;
  },
};

// Legal Review API
export interface LegalReviewResponse {
  success: boolean;
  message: string;
  file: FileUploadResponse | null;
  analysis_result?: any;
}

export interface LegalReviewResults {
  legal_review_results: Array<{
    created_at: string;
    analysis_result: any;
  }>;
  latest: any | null;
}

export const legalReviewApi = {
  start: async (projectId: number, returnAnalysis: boolean = true): Promise<LegalReviewResponse> => {
    const response = await api.post(`/v1/legal-review/project/${projectId}/start?return_analysis=${returnAnalysis}`);
    return response.data;
  },
  getResults: async (projectId: number): Promise<LegalReviewResults> => {
    const response = await api.get(`/v1/legal-review/project/${projectId}/results`);
    return response.data;
  },
};

// Question List API
export interface QuestionListResponse {
  success: boolean;
  message: string;
  file: FileUploadResponse | null;
}

export const questionListApi = {
  start: async (projectId: number): Promise<QuestionListResponse> => {
    const response = await api.post(`/v1/question-list/project/${projectId}/start`);
    return response.data;
  },
};

// Settings API
export interface Setting {
  key: string;
  value: string | null;
  description: string | null;
}

export interface SettingUpdate {
  value: string;
  description?: string;
}

export const settingsApi = {
  getAll: async (): Promise<Setting[]> => {
    const response = await api.get('/v1/settings/');
    return response.data;
  },

  get: async (key: string): Promise<Setting> => {
    const response = await api.get(`/v1/settings/${key}`);
    return response.data;
  },

  update: async (key: string, update: SettingUpdate): Promise<Setting> => {
    const response = await api.put(`/v1/settings/${key}`, update);
    return response.data;
  },

  delete: async (key: string): Promise<void> => {
    await api.delete(`/v1/settings/${key}`);
  },

  uploadLegalReviewTemplate: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/v1/settings/legal-review-template/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getLegalReviewTemplateStatus: async (): Promise<any> => {
    const response = await api.get('/v1/settings/legal-review-template/status');
    return response.data;
  },

  uploadQuestionListTemplate: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/v1/settings/question-list-template/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getQuestionListTemplateStatus: async (): Promise<any> => {
    const response = await api.get('/v1/settings/question-list-template/status');
    return response.data;
  },
};

export default api;
