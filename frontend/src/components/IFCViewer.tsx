import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { filesApi } from '../services/api';
import './IFCViewer.css';

interface IFCViewerProps {
  fileId: number;
  filename: string;
  onClose: () => void;
}

const IFCViewer = ({ fileId, filename, onClose }: IFCViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const ifcLoaderRef = useRef<any>(null);
  const modelRef = useRef<THREE.Group | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(0);

  useEffect(() => {
    // Debug-Mode Logging: Schreibe direkt in Log-Datei via Server-Endpoint und Backend-API
    const writeDebugLog = (location: string, message: string, hypothesisId: string, data?: any) => {
      const logEntry = {location,message,data:data||{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId};
      // #region agent log
      // Versuche Server-Endpoint (Debug-Mode)
      fetch('http://127.0.0.1:7243/ingest/461f330f-a3db-4054-ad59-c1077cc77e55',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logEntry)}).catch(()=>{});
      // Fallback: Backend-API
      const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      fetch(`${apiBaseUrl}/v1/debug-logs-direct`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(logEntry)}).catch(()=>{});
      // #endregion
      console.log(`[${hypothesisId}] ${message}`, data);
    };
    
    // #region agent log
    writeDebugLog('IFCViewer.tsx:27', 'IFCViewer component mounted', 'A', { fileId, filename });
    // #endregion
    
    const initializeViewer = async () => {
      // #region agent log
      writeDebugLog('IFCViewer.tsx:28', 'initializeViewer started', 'A', { containerRef: !!containerRef.current });
      // #endregion
      console.log('IFCViewer useEffect started', { containerRef: !!containerRef.current });
      
      if (!containerRef.current) {
        console.error('Container ref is null');
        return;
      }
      
      // Hilfsfunktion: Stelle sicher, dass ALLE Geometrien eine boundingSphere haben
      // Dies verhindert "Cannot read properties of undefined (reading 'boundingSphere')" Fehler
      const ensureAllGeometriesHaveBounds = (obj: THREE.Object3D) => {
        obj.traverse((child) => {
          if (child instanceof THREE.Mesh && child.geometry) {
            const geometry = child.geometry;
            
            // Für BufferGeometry
            if (geometry instanceof THREE.BufferGeometry) {
              // Stelle sicher, dass boundingBox existiert
              if (!geometry.boundingBox) {
                try {
                  if (geometry.attributes && geometry.attributes.position && 
                      geometry.attributes.position.count > 0 && 
                      geometry.attributes.position.array && 
                      geometry.attributes.position.array.length > 0) {
                    geometry.computeBoundingBox();
                  } else {
                    geometry.boundingBox = new THREE.Box3();
                  }
                } catch (e) {
                  geometry.boundingBox = new THREE.Box3();
                }
              }
              
              // Stelle sicher, dass boundingSphere existiert - KRITISCH!
              if (!geometry.boundingSphere) {
                try {
                  if (geometry.attributes && geometry.attributes.position && 
                      geometry.attributes.position.count > 0 && 
                      geometry.attributes.position.array && 
                      geometry.attributes.position.array.length > 0) {
                    geometry.computeBoundingSphere();
                  } else {
                    // Erstelle leere Sphere als Fallback
                    geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                  }
                } catch (e) {
                  // Erstelle leere Sphere als Fallback - MUSS vorhanden sein!
                  geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                }
              }
              
              // Zusätzliche Sicherheit: Prüfe ob boundingSphere wirklich existiert
              if (!geometry.boundingSphere) {
                geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
              }
            } else {
              // Für andere Geometrie-Typen
              try {
                if (typeof (geometry as any).computeBoundingBox === 'function' && !(geometry as any).boundingBox) {
                  (geometry as any).computeBoundingBox();
                }
                if (typeof (geometry as any).computeBoundingSphere === 'function' && !(geometry as any).boundingSphere) {
                  (geometry as any).computeBoundingSphere();
                }
                // Stelle sicher, dass boundingSphere existiert
                if (!(geometry as any).boundingSphere) {
                  (geometry as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                }
              } catch (e) {
                if (!(geometry as any).boundingSphere) {
                  (geometry as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                }
              }
            }
          }
        });
      };
      
      // Dynamically import IFCLoader
      let IFCLoaderClass: any;
      try {
        const module = await import('web-ifc-three/IFCLoader');
        IFCLoaderClass = module.default || module.IFCLoader || module;
        console.log('IFCLoader imported:', typeof IFCLoaderClass, IFCLoaderClass);
      } catch (e: any) {
        console.error('Failed to import IFCLoader:', e);
        setError(`Fehler beim Importieren des IFC Loaders: ${e?.message || e}`);
        setLoading(false);
        return;
      }
      
      // Check if IFCLoader is a constructor function
      if (!IFCLoaderClass) {
        console.error('IFCLoader is null/undefined');
        setError('IFC Loader konnte nicht geladen werden. IFCLoader ist null.');
        setLoading(false);
        return;
      }
      
      if (typeof IFCLoaderClass !== 'function') {
        console.error('IFCLoader is not a constructor', { IFCLoaderClass, type: typeof IFCLoaderClass });
        setError(`IFC Loader konnte nicht geladen werden. IFCLoader ist ${typeof IFCLoaderClass} statt einer Funktion. Bitte prüfen Sie die Browser-Konsole für Details.`);
        setLoading(false);
        return;
      }
      
      // Scene Setup
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf0f0f0);
      sceneRef.current = scene;

      // Camera Setup
      const camera = new THREE.PerspectiveCamera(
        75,
        containerRef.current.clientWidth / containerRef.current.clientHeight,
        0.1,
        1000
      );
      camera.position.set(10, 10, 10);
      cameraRef.current = camera;

      // Renderer Setup
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
      renderer.setPixelRatio(window.devicePixelRatio);
      containerRef.current.appendChild(renderer.domElement);
      rendererRef.current = renderer;
      
      // #region agent log
      const gl = renderer.getContext();
      writeDebugLog('IFCViewer.tsx:187', 'Renderer initialization', 'D', {
        hasWebGLContext: !!gl,
        webglVersion: gl ? gl.getParameter(gl.VERSION) : null,
        canvasWidth: containerRef.current.clientWidth,
        canvasHeight: containerRef.current.clientHeight,
        rendererType: renderer.constructor.name
      });
      // #endregion

      // Controls Setup
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.minDistance = 1;
      controls.maxDistance = 500;
      controlsRef.current = controls;

      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      scene.add(ambientLight);

      const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.5);
      directionalLight1.position.set(10, 10, 5);
      scene.add(directionalLight1);

      const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
      directionalLight2.position.set(-10, 5, -5);
      scene.add(directionalLight2);

      // Axes Helper
      const axesHelper = new THREE.AxesHelper(5);
      scene.add(axesHelper);

      // IFC Loader Setup
      let ifcLoader: any;
      try {
        ifcLoader = new IFCLoaderClass();
        
        // Set WASM path - critical for web-ifc to work
        // Verwende lokale WASM-Datei aus public/wasm/ (kopiert von node_modules/web-ifc)
        // Die Datei ist über http://localhost:3000/wasm/web-ifc.wasm erreichbar
        const wasmPath = '/wasm/'; // Relativer Pfad zu public/wasm/
        
        console.log('Setting WASM path:', wasmPath);
        console.log('IFC Loader methods:', Object.keys(ifcLoader));
        console.log('IFC Manager available:', !!ifcLoader.ifcManager);
        
        // Versuche verschiedene Methoden, um WASM-Pfad zu setzen
        let wasmPathSet = false;
        
        // Methode 1: ifcManager.setWasmPath() (bevorzugt)
        if (ifcLoader.ifcManager && typeof ifcLoader.ifcManager.setWasmPath === 'function') {
          try {
            // setWasmPath kann async sein, daher await verwenden
            // Zweiter Parameter: false = lokaler Pfad, true = CDN
            const result = ifcLoader.ifcManager.setWasmPath(wasmPath, false);
            if (result instanceof Promise) {
              await result;
            }
            console.log('WASM path set via ifcManager.setWasmPath');
            wasmPathSet = true;
          } catch (e: any) {
            console.warn('Failed to set WASM path via ifcManager.setWasmPath:', e);
          }
        }
        
        // Methode 2: ifcLoader.setWasmPath()
        if (!wasmPathSet && typeof ifcLoader.setWasmPath === 'function') {
          try {
            // Zweiter Parameter: false = lokaler Pfad, true = CDN
            const result = ifcLoader.setWasmPath(wasmPath, false);
            if (result instanceof Promise) {
              await result;
            }
            console.log('WASM path set via setWasmPath');
            wasmPathSet = true;
          } catch (e: any) {
            console.warn('Failed to set WASM path via setWasmPath:', e);
          }
        }
        
        // Methode 3: Direkte Eigenschaft
        if (!wasmPathSet && ifcLoader.wasmPath !== undefined) {
          ifcLoader.wasmPath = wasmPath;
          console.log('WASM path set via wasmPath property');
          wasmPathSet = true;
        }
        
        if (!wasmPathSet) {
          console.warn('WARNUNG: Konnte WASM-Pfad nicht setzen. Verfügbare Methoden:', Object.keys(ifcLoader));
          console.warn('IFC Manager methods:', ifcLoader.ifcManager ? Object.keys(ifcLoader.ifcManager) : 'N/A');
        }
        
        ifcLoaderRef.current = ifcLoader;
        console.log('IFC Loader initialized successfully', {
          wasmPathSet,
          wasmPath,
          hasSetWasmPath: typeof ifcLoader.setWasmPath === 'function',
          hasIfcManager: !!ifcLoader.ifcManager,
          hasIfcManagerSetWasmPath: !!(ifcLoader.ifcManager && typeof ifcLoader.ifcManager.setWasmPath === 'function')
        });
      } catch (err: any) {
        console.error('Fehler beim Initialisieren des IFC Loaders:', err);
        setError(`Fehler beim Initialisieren des IFC Loaders: ${err?.message || err}`);
        setLoading(false);
        return;
      }

      // Load IFC File
      const loadIFCFile = async () => {
        if (!ifcLoader) {
          setError('IFC Loader ist nicht initialisiert');
          setLoading(false);
          return;
        }

        const debugLog: Array<{ timestamp: string; message: string; data?: any }> = [];
        const addDebugLog = (message: string, data?: any) => {
          const timestamp = new Date().toISOString();
          const logEntry = {
            timestamp,
            message,
            data: data ? (typeof data === 'object' ? data : { value: data }) : undefined
          };
          debugLog.push(logEntry);
          const consoleEntry = `[IFCViewer Debug] ${message}${data ? `: ${JSON.stringify(data)}` : ''}`;
          console.log(consoleEntry);
        };
        
        // Funktion zum Speichern der Debug-Logs
        const saveDebugLogs = async () => {
          const logData = {
            fileId,
            filename,
            timestamp: new Date().toISOString(),
            logs: debugLog,
            summary: {
              totalLogs: debugLog.length,
              errors: debugLog.filter(log => log.message.toLowerCase().includes('error') || log.message.toLowerCase().includes('failed')).length,
              warnings: debugLog.filter(log => log.message.toLowerCase().includes('warning') || log.message.toLowerCase().includes('warn')).length
            }
          };
          
          const jsonString = JSON.stringify(logData, null, 2);
          const filename_download = `ifc-viewer-debug-${fileId}-${Date.now()}.json`;
          
          // 1. Erstelle JSON-Datei und lade sie herunter (für Benutzer)
          try {
            const blob = new Blob([jsonString], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename_download;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            console.log(`[DEBUG] Debug-Logs wurden als ${filename_download} heruntergeladen`);
          } catch (downloadError: any) {
            console.error('[DEBUG] Fehler beim Herunterladen der Debug-Logs:', downloadError);
          }
          
          // 2. Sende auch an Backend zum Speichern im Projekt-Verzeichnis (für AI-Zugriff)
          try {
            const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
            console.log(`[DEBUG] Sende Debug-Logs an Backend: ${apiBaseUrl}/v1/debug-logs`);
            
            const response = await fetch(`${apiBaseUrl}/v1/debug-logs`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: jsonString
            });
            
            if (response.ok) {
              const result = await response.json();
              console.log(`[DEBUG] ✅ Debug-Logs wurden im Backend gespeichert: ${result.file_path}`);
              addDebugLog('Debug-Logs erfolgreich im Backend gespeichert', { file_path: result.file_path });
            } else {
              const errorText = await response.text();
              console.warn(`[DEBUG] ⚠️ Backend konnte Debug-Logs nicht speichern: ${response.status} ${response.statusText}`, errorText);
              addDebugLog('WARNING: Backend konnte Debug-Logs nicht speichern', { 
                status: response.status, 
                statusText: response.statusText,
                error: errorText.substring(0, 200)
              });
            }
          } catch (e: any) {
            console.error('[DEBUG] ❌ Fehler beim Senden der Debug-Logs an Backend:', e?.message || e);
            addDebugLog('ERROR: Fehler beim Senden der Debug-Logs an Backend', { 
              error: e?.message || String(e),
              errorType: e?.name
            });
          }
        };

        try {
          console.log('[IFCViewer] Starting loadIFCFile', { fileId, filename });
          setLoading(true);
          setError(null);
          setLoadingProgress(0);
          addDebugLog('Starting IFC file load', { fileId, filename });
          console.log('[IFCViewer] Loading state set, calling filesApi.getFileAsBlob');

          // Download file as blob first
          addDebugLog('Starting blob download');
          console.log('[IFCViewer] Starting blob download');
          let fileBlob: Blob;
          try {
            fileBlob = await filesApi.getFileAsBlob(fileId, (progress) => {
              // Progress callback: 0-60% für Download
              const progressPercent = Math.min(60, progress);
              setLoadingProgress(progressPercent);
              addDebugLog(`Download progress: ${progressPercent}%`);
            });
            addDebugLog('Blob download completed', { 
              blobSize: fileBlob.size, 
              blobType: fileBlob.type 
            });
          } catch (downloadError: any) {
            addDebugLog('Blob download failed', {
              error: downloadError?.message,
              errorType: downloadError?.name,
              errorCode: downloadError?.code,
              response: downloadError?.response ? {
                status: downloadError.response.status,
                statusText: downloadError.response.statusText,
                data: typeof downloadError.response.data === 'string' 
                  ? downloadError.response.data.substring(0, 200) 
                  : downloadError.response.data
              } : null
            });
            throw new Error(`Download fehlgeschlagen: ${downloadError?.message || 'Unbekannter Fehler'}`);
          }
          
          setLoadingProgress(65);
          addDebugLog('Converting blob to ArrayBuffer');
          
          // Convert blob to ArrayBuffer
          let arrayBuffer: ArrayBuffer;
          try {
            arrayBuffer = await fileBlob.arrayBuffer();
            addDebugLog('ArrayBuffer created', { 
              byteLength: arrayBuffer.byteLength,
              expectedSize: fileBlob.size 
            });
            
            // Validate ArrayBuffer
            if (arrayBuffer.byteLength === 0) {
              throw new Error('ArrayBuffer ist leer');
            }
            if (arrayBuffer.byteLength !== fileBlob.size) {
              addDebugLog('WARNING: ArrayBuffer size mismatch', {
                blobSize: fileBlob.size,
                arrayBufferSize: arrayBuffer.byteLength
              });
            }
          } catch (bufferError: any) {
            addDebugLog('ArrayBuffer conversion failed', {
              error: bufferError?.message,
              errorType: bufferError?.name
            });
            throw new Error(`Fehler beim Konvertieren der Datei: ${bufferError?.message || 'Unbekannter Fehler'}`);
          }
          
          setLoadingProgress(75);
          
          // web-ifc-three IFCLoader benötigt eine URL
          let model: THREE.Group;
          let blobUrl: string | null = null;
          
          try {
            // Prüfe verfügbare Methoden
            addDebugLog('Checking available methods', {
              arrayBufferSize: arrayBuffer.byteLength,
              ifcLoaderMethods: Object.keys(ifcLoader),
              hasLoadMethod: typeof ifcLoader.load === 'function',
              ifcManagerMethods: ifcLoader.ifcManager ? Object.keys(ifcLoader.ifcManager) : [],
              ifcManagerAvailable: !!ifcLoader.ifcManager
            });
            
            setLoadingProgress(80);
            
            // Versuche verschiedene Methoden zum Laden der IFC-Datei
            // Methode 1: Direkte API-URL (sollte am zuverlässigsten sein)
            // WICHTIG: Verwende absolute URL, nicht Proxy-URL, da ifcLoader.load() möglicherweise
            // Probleme mit dem Vite-Proxy hat
            const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
            const fileUrl = `${apiBaseUrl}/v1/files/${fileId}/download`;
            
            addDebugLog('Using direct API URL method', { 
              fileUrl,
              envViteApiUrl: import.meta.env.VITE_API_URL,
              envDev: import.meta.env.DEV,
              windowLocation: window.location.origin
            });
            
            model = await new Promise<THREE.Group>((resolve, reject) => {
              const timeout = setTimeout(() => {
                reject(new Error('Timeout beim Laden der IFC-Datei (5 Minuten überschritten)'));
              }, 300000); // 5 Minuten Timeout
              
              // Prüfe ob load() existiert
              if (typeof ifcLoader.load !== 'function') {
                clearTimeout(timeout);
                reject(new Error(`ifcLoader.load ist keine Funktion. Verfügbare Methoden: ${Object.keys(ifcLoader).join(', ')}`));
                return;
              }
              
              addDebugLog('Calling ifcLoader.load()', { fileUrl });
              
              try {
                ifcLoader.load(
                  fileUrl,
                  (ifcModel: any) => {
                    clearTimeout(timeout);
                    
                    // Detaillierte Analyse des zurückgegebenen Modells
                    const modelAnalysis: any = {
                      modelType: typeof ifcModel,
                      isGroup: ifcModel instanceof THREE.Group,
                      isObject3D: ifcModel instanceof THREE.Object3D,
                      isMesh: ifcModel instanceof THREE.Mesh,
                      constructor: ifcModel?.constructor?.name,
                      modelKeys: Object.keys(ifcModel || {}),
                      hasMesh: !!(ifcModel as any).mesh,
                      hasModel: !!(ifcModel as any).model,
                      hasScene: !!(ifcModel as any).scene,
                      children: ifcModel instanceof THREE.Object3D ? ifcModel.children.length : 'N/A',
                      visible: ifcModel instanceof THREE.Object3D ? ifcModel.visible : 'N/A'
                    };
                    
                    // Prüfe rekursiv nach Meshes
                    if (ifcModel instanceof THREE.Object3D) {
                      let meshCount = 0;
                      ifcModel.traverse((child) => {
                        if (child instanceof THREE.Mesh) {
                          meshCount++;
                        }
                      });
                      modelAnalysis.totalMeshes = meshCount;
                    }
                    
                    addDebugLog('IFC model loaded successfully', modelAnalysis);
                    
                    // #region agent log
                    writeDebugLog('IFCViewer.tsx:530', 'IFC model loaded from loader', 'A', {
                      modelType: typeof ifcModel,
                      isGroup: ifcModel instanceof THREE.Group,
                      isMesh: ifcModel instanceof THREE.Mesh,
                      constructor: ifcModel?.constructor?.name,
                      visible: ifcModel instanceof THREE.Object3D ? ifcModel.visible : 'N/A',
                      children: ifcModel instanceof THREE.Object3D ? ifcModel.children.length : 'N/A',
                      totalMeshes: modelAnalysis.totalMeshes || 0
                    });
                    // #endregion
                    
                    let group: THREE.Group;
                    
                    // Prüfe verschiedene mögliche Strukturen
                    // WICHTIG: IFCModel erweitert THREE.Mesh und hat sowohl geometry/material als auch ein mesh Property
                    // Die Logs zeigen: IFCModel selbst hat Geometrie (571532 Vertices)!
                    if (ifcModel instanceof THREE.Group) {
                      group = ifcModel;
                      addDebugLog('Model is THREE.Group');
                    } else if (ifcModel instanceof THREE.Mesh || (ifcModel as any).constructor.name === 'IFCModel') {
                      // IFCModel erweitert THREE.Mesh - verwende es direkt!
                      // WICHTIG: Verwende das IFCModel selbst, nicht das mesh Property!
                      group = new THREE.Group();
                      
                      // Stelle sicher, dass das IFCModel sichtbar ist und korrekt konfiguriert ist
                      ifcModel.visible = true;
                      ifcModel.frustumCulled = false; // WICHTIG: Deaktiviere Frustum Culling für Debugging
                      ifcModel.updateMatrix();
                      ifcModel.updateMatrixWorld(true);
                      
                      // KRITISCH: Stelle sicher, dass die Geometrie korrekt kompiliert wird
                      // Three.js benötigt eine explizite Kompilierung der Geometrie-Gruppen
                      if (ifcModel.geometry && ifcModel.geometry instanceof THREE.BufferGeometry) {
                        const geometry = ifcModel.geometry;
                        // Erzwinge Neuberechnung der Bounding-Boxen für alle Gruppen
                        if (geometry.groups && geometry.groups.length > 0) {
                          // WICHTIG: Erstelle neue Gruppen-Array, um sicherzustellen, dass Three.js die Änderungen erkennt
                          const groupsCopy = geometry.groups.map((g: any) => ({
                            start: g.start,
                            count: g.count,
                            materialIndex: g.materialIndex
                          }));
                          geometry.groups = groupsCopy;
                          
                          geometry.computeBoundingBox();
                          geometry.computeBoundingSphere();
                          // Markiere Geometrie als geändert, damit Three.js sie neu kompiliert
                          (geometry as any).needsUpdate = true;
                          // Stelle sicher, dass alle Attribute aktualisiert werden
                          if (geometry.attributes.position) {
                            geometry.attributes.position.needsUpdate = true;
                          }
                          if (geometry.index) {
                            (geometry.index as any).needsUpdate = true;
                          }
                        }
                      }
                      
                      // KRITISCH: Prüfe Geometrie auf Material-Indizes
                      if (ifcModel.geometry && ifcModel.geometry instanceof THREE.BufferGeometry) {
                        const geometry = ifcModel.geometry;
                        const hasMaterialIndex = geometry.attributes && (geometry as any).groups && (geometry as any).groups.length > 0;
                        
                        // #region agent log
                        try {
                          writeDebugLog('IFCViewer.tsx:440', 'Geometry analysis start', 'B', {
                            hasGroups: hasMaterialIndex,
                            groupsCount: hasMaterialIndex ? (geometry as any).groups.length : 0,
                            vertices: geometry.attributes?.position?.count || 0,
                            hasIndex: !!geometry.index,
                            indexCount: geometry.index ? geometry.index.count : 0
                          });
                        } catch (e) {
                          console.warn('Error in writeDebugLog:', e);
                        }
                        // #endregion
                        
                        addDebugLog('Geometry analysis', {
                          hasGroups: hasMaterialIndex,
                          groupsCount: hasMaterialIndex ? (geometry as any).groups.length : 0,
                          groups: hasMaterialIndex ? (geometry as any).groups.map((g: any) => ({
                            start: g.start,
                            count: g.count,
                            materialIndex: g.materialIndex
                          })) : null,
                          vertices: geometry.attributes?.position?.count || 0,
                          hasIndex: !!geometry.index,
                          indexCount: geometry.index ? geometry.index.count : 0
                        });
                        
                        // Prüfe Index-Buffer auf Gültigkeit (Hypothese B)
                        if (geometry.index) {
                          const indexArray = geometry.index.array as Uint16Array | Uint32Array;
                          const maxIndex = Math.max(...Array.from(indexArray.slice(0, Math.min(100, indexArray.length))));
                          const vertexCount = geometry.attributes?.position?.count || 0;
                          
                          // #region agent log
                          try {
                            writeDebugLog('IFCViewer.tsx:460', 'Index buffer validation', 'B', {
                              maxIndexSample: maxIndex,
                              vertexCount,
                              indexCount: indexArray.length,
                              isValid: maxIndex < vertexCount
                            });
                          } catch (e) {
                            console.warn('Error in writeDebugLog:', e);
                          }
                          // #endregion
                          
                          if (maxIndex >= vertexCount) {
                            console.error('[IFCViewer] ⚠️ Index-Buffer enthält ungültige Indizes!', { maxIndex, vertexCount });
                            addDebugLog('ERROR: Invalid index buffer', { maxIndex, vertexCount });
                          }
                        }
                        
                        // Stelle sicher, dass die Geometrie nicht leer ist
                        if (!geometry.attributes || !geometry.attributes.position || geometry.attributes.position.count === 0) {
                          console.error('[IFCViewer] ⚠️ Geometrie hat keine Vertices!');
                          addDebugLog('ERROR: Geometry has no vertices');
                        }
                      }
                      
                      // Stelle sicher, dass Materialien korrekt sind
                      // KRITISCH: Material-Arrays müssen alle Materialien haben!
                      if (ifcModel.material) {
                        if (Array.isArray(ifcModel.material)) {
                          // Material-Array: Stelle sicher, dass alle Materialien vorhanden und sichtbar sind
                          let materialFixed = false;
                          const fixedMaterials = ifcModel.material.map((mat: any, idx: number) => {
                            if (!mat) {
                              console.warn(`[IFCViewer] Material ${idx} ist null/undefined, erstelle Standard-Material`);
                              materialFixed = true;
                              const defaultMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                              defaultMat.visible = true;
                              defaultMat.transparent = false;
                              defaultMat.opacity = 1;
                              return defaultMat;
                            }
                            mat.visible = true;
                            if (mat.transparent !== undefined) mat.transparent = false;
                            if (mat.opacity !== undefined && mat.opacity < 1) mat.opacity = 1;
                            // Stelle sicher, dass Material nicht frustumCulled ist
                            if ((mat as any).frustumCulled !== undefined) {
                              (mat as any).frustumCulled = false;
                            }
                            return mat;
                          });
                          
                          if (materialFixed) {
                            ifcModel.material = fixedMaterials;
                            addDebugLog('Material-Array korrigiert (null-Materialien ersetzt)', {
                              originalLength: ifcModel.material.length,
                              fixedLength: fixedMaterials.length
                            });
                          }
                          
                          // KRITISCH: Wenn Geometrie Material-Gruppen hat, prüfe ob Indizes gültig sind
                          if (ifcModel.geometry && (ifcModel.geometry as any).groups) {
                            const groups = (ifcModel.geometry as any).groups;
                            let invalidIndices = 0;
                            let groupsFixed = false;
                            const materialIndexMap: number[] = [];
                            
                            // Finde maximale Material-Index-Anforderung
                            let maxMaterialIndex = -1;
                            groups.forEach((group: any) => {
                              if (group.materialIndex > maxMaterialIndex) {
                                maxMaterialIndex = group.materialIndex;
                              }
                            });
                            
                            // Stelle sicher, dass Material-Array groß genug ist
                            if (maxMaterialIndex >= fixedMaterials.length) {
                              console.warn(`[IFCViewer] Material-Array zu klein (${fixedMaterials.length}), erweitere auf ${maxMaterialIndex + 1}`);
                              while (fixedMaterials.length <= maxMaterialIndex) {
                                const defaultMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                                defaultMat.visible = true;
                                defaultMat.transparent = false;
                                defaultMat.opacity = 1;
                                defaultMat.side = THREE.FrontSide;
                                fixedMaterials.push(defaultMat);
                              }
                              groupsFixed = true;
                            }
                            
                            // Korrigiere ungültige Material-Indizes
                            groups.forEach((group: any, idx: number) => {
                              materialIndexMap.push(group.materialIndex);
                              if (group.materialIndex < 0 || group.materialIndex >= fixedMaterials.length) {
                                invalidIndices++;
                                const correctedIndex = Math.max(0, Math.min(group.materialIndex, fixedMaterials.length - 1));
                                console.warn(`[IFCViewer] Korrigiere ungültigen Material-Index: ${group.materialIndex} -> ${correctedIndex}`);
                                group.materialIndex = correctedIndex;
                                groupsFixed = true;
                              }
                            });
                            
                            // Wenn Gruppen korrigiert wurden, aktualisiere die Geometrie
                            if (groupsFixed) {
                              (ifcModel.geometry as any).groups = groups;
                              ifcModel.material = fixedMaterials;
                              // Erzwinge Geometrie-Update
                              if (ifcModel.geometry && ifcModel.geometry.attributes && ifcModel.geometry.attributes.position && ifcModel.geometry.attributes.position.count > 0) {
                                ifcModel.geometry.computeBoundingBox();
                                ifcModel.geometry.computeBoundingSphere();
                              }
                              addDebugLog('Material-Indizes korrigiert', {
                                invalidIndicesFixed: invalidIndices,
                                materialArrayLength: fixedMaterials.length,
                                groupsCount: groups.length
                              });
                            }
                            
                            // #region agent log
                            try {
                              writeDebugLog('IFCViewer.tsx:500', 'Material groups validation', 'C', {
                                groupsCount: groups.length,
                                materialArrayLength: fixedMaterials.length,
                                invalidIndices,
                                groupsFixed,
                                materialIndices: materialIndexMap,
                                groups: groups.map((g: any) => ({ start: g.start, count: g.count, materialIndex: g.materialIndex }))
                              });
                            } catch (e) {
                              console.warn('Error in writeDebugLog:', e);
                            }
                            // #endregion
                            
                            if (invalidIndices > 0 && !groupsFixed) {
                              addDebugLog('WARNING: Invalid material indices found', {
                                invalidIndices,
                                materialArrayLength: fixedMaterials.length,
                                groupsCount: groups.length
                              });
                            }
                          }
                          
                          // KRITISCH: Stelle sicher, dass alle Materialien wirklich sichtbar und nicht transparent sind
                          fixedMaterials.forEach((mat: any, idx: number) => {
                            if (mat) {
                              // KRITISCH: Stelle sicher, dass Material eine sichtbare Farbe hat
                              if (!mat.color || (mat.color.getHex && mat.color.getHex() === 0x000000)) {
                                console.warn(`[IFCViewer] Material ${idx} hat keine Farbe oder ist schwarz, setze Standard-Farbe`);
                                if (!mat.color) {
                                  mat.color = new THREE.Color(0xcccccc);
                                } else {
                                  mat.color.setHex(0xcccccc);
                                }
                              }
                              
                              // Erzwinge explizite Eigenschaften
                              mat.visible = true;
                              mat.transparent = false;
                              mat.opacity = 1.0;
                              mat.side = THREE.FrontSide; // Stelle sicher, dass beide Seiten gerendert werden
                              
                              // Stelle sicher, dass Material nicht disposed ist
                              if (mat.needsUpdate !== undefined) {
                                mat.needsUpdate = true;
                              }
                              
                              // Prüfe Material auf WebGL-Kompatibilität (Hypothese A)
                              const gl = rendererRef.current ? (rendererRef.current as any).getContext() : null;
                              const hasShaderError = mat.onBeforeCompile ? true : false;
                              const materialType = mat.constructor.name;
                              const materialColor = mat.color ? (mat.color.getHex ? mat.color.getHex() : mat.color) : null;
                              const materialColorRgb = mat.color ? (mat.color.r !== undefined ? {r: mat.color.r, g: mat.color.g, b: mat.color.b} : null) : null;
                              
                              // #region agent log
                              try {
                                writeDebugLog('IFCViewer.tsx:520', 'Material WebGL compatibility check', 'A', {
                                  materialIndex: idx,
                                  materialType,
                                  visible: mat.visible,
                                  transparent: mat.transparent,
                                  opacity: mat.opacity,
                                  hasShaderError,
                                  hasWebGLContext: !!gl,
                                  colorHex: materialColor,
                                  colorRgb: materialColorRgb,
                                  hasColor: !!mat.color
                                });
                              } catch (e) {
                                console.warn('Error in writeDebugLog:', e);
                              }
                              // #endregion
                              
                              // Logge Material-Status für Debugging
                              addDebugLog(`Material ${idx} configured`, {
                                type: mat.constructor.name,
                                visible: mat.visible,
                                transparent: mat.transparent,
                                opacity: mat.opacity,
                                side: mat.side,
                                color: mat.color ? mat.color.getHex() : null
                              });
                            }
                          });
                          
                          // KRITISCH: Stelle sicher, dass Material-Array korrekt gesetzt ist
                          ifcModel.material = fixedMaterials;
                          
                          // KRITISCH: Erzwinge Material-Update für alle Materialien
                          fixedMaterials.forEach((mat: any) => {
                            if (mat) {
                              mat.visible = true;
                              mat.transparent = false;
                              mat.opacity = 1.0;
                              mat.side = THREE.FrontSide;
                              if (mat.needsUpdate !== undefined) {
                                mat.needsUpdate = true;
                              }
                            }
                          });
                          
                          // KRITISCH: Stelle sicher, dass Geometrie-Gruppen korrekt mit Materialien verknüpft sind
                          // Wenn Geometrie-Gruppen vorhanden sind, müssen sie mit dem Material-Array übereinstimmen
                          if (ifcModel.geometry && (ifcModel.geometry as any).groups) {
                            const geometry = ifcModel.geometry;
                            const groups = (geometry as any).groups;
                            const totalTriangles = groups.reduce((sum: number, group: any) => sum + group.count, 0);
                            
                            // Stelle sicher, dass Geometrie kompiliert ist
                            if (geometry.attributes && geometry.attributes.position && geometry.attributes.position.count > 0) {
                              try {
                                geometry.computeBoundingBox();
                                geometry.computeBoundingSphere();
                              } catch (e) {
                                console.warn('[IFCViewer] Fehler beim Kompilieren der Geometrie:', e);
                              }
                            }
                            
                            // Stelle sicher, dass Geometrie-Attribute aktualisiert werden
                            if (geometry.attributes && geometry.attributes.position) {
                              if (geometry.attributes.position.needsUpdate !== undefined) {
                                geometry.attributes.position.needsUpdate = true;
                              }
                            }
                            if (geometry.index && (geometry.index as any).needsUpdate !== undefined) {
                              (geometry.index as any).needsUpdate = true;
                            }
                            
                            // #region agent log
                            try {
                              writeDebugLog('IFCViewer.tsx:545', 'Geometry groups material linking', 'C', {
                                groupsCount: groups.length,
                                materialArrayLength: fixedMaterials.length,
                                totalTriangles,
                                groups: groups.map((g: any) => ({
                                  start: g.start,
                                  count: g.count,
                                  materialIndex: g.materialIndex,
                                  hasMaterial: g.materialIndex >= 0 && g.materialIndex < fixedMaterials.length,
                                  materialType: g.materialIndex >= 0 && g.materialIndex < fixedMaterials.length ? fixedMaterials[g.materialIndex]?.constructor.name : 'none'
                                }))
                              });
                            } catch (e) {
                              console.warn('Error in writeDebugLog:', e);
                            }
                            // #endregion
                            
                            // Stelle sicher, dass alle Gruppen gültige Material-Indizes haben
                            let hasInvalidGroups = false;
                            let groupsCorrected = false;
                            
                            // Finde maximale Material-Index-Anforderung
                            let maxMaterialIndex = -1;
                            groups.forEach((group: any) => {
                              if (group.materialIndex > maxMaterialIndex) {
                                maxMaterialIndex = group.materialIndex;
                              }
                            });
                            
                            // Stelle sicher, dass Material-Array groß genug ist
                            if (maxMaterialIndex >= fixedMaterials.length) {
                              console.warn(`[IFCViewer] Material-Array zu klein (${fixedMaterials.length}), erweitere auf ${maxMaterialIndex + 1}`);
                              while (fixedMaterials.length <= maxMaterialIndex) {
                                const defaultMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                                defaultMat.visible = true;
                                defaultMat.transparent = false;
                                defaultMat.opacity = 1;
                                defaultMat.side = THREE.FrontSide;
                                if (defaultMat.needsUpdate !== undefined) {
                                  defaultMat.needsUpdate = true;
                                }
                                fixedMaterials.push(defaultMat);
                              }
                              ifcModel.material = fixedMaterials;
                              groupsCorrected = true;
                            }
                            
                            groups.forEach((group: any, idx: number) => {
                              if (group.materialIndex < 0 || group.materialIndex >= fixedMaterials.length) {
                                hasInvalidGroups = true;
                                const correctedIndex = Math.max(0, Math.min(group.materialIndex, fixedMaterials.length - 1));
                                console.warn(`[IFCViewer] Korrigiere ungültigen Material-Index in Gruppe ${idx}: ${group.materialIndex} -> ${correctedIndex}`);
                                group.materialIndex = correctedIndex;
                                groupsCorrected = true;
                              }
                              if (group.count === 0) {
                                hasInvalidGroups = true;
                                console.warn(`[IFCViewer] ⚠️ Gruppe ${idx} hat 0 Triangles: start=${group.start}, count=${group.count}`);
                              }
                            });
                            
                            // Wenn Gruppen korrigiert wurden, aktualisiere die Geometrie
                            if (groupsCorrected) {
                              (ifcModel.geometry as any).groups = groups;
                              if (ifcModel.geometry && ifcModel.geometry.attributes && ifcModel.geometry.attributes.position && ifcModel.geometry.attributes.position.count > 0) {
                                ifcModel.geometry.computeBoundingBox();
                                ifcModel.geometry.computeBoundingSphere();
                              }
                              addDebugLog('Geometrie-Gruppen korrigiert', {
                                groupsCount: groups.length,
                                materialArrayLength: fixedMaterials.length
                              });
                            }
                            
                            if (hasInvalidGroups && !groupsCorrected) {
                              console.error('[IFCViewer] ⚠️ Geometrie-Gruppen haben ungültige Material-Indizes oder 0 Triangles!');
                              addDebugLog('ERROR: Invalid geometry groups', {
                                groupsCount: groups.length,
                                materialArrayLength: fixedMaterials.length
                              });
                            }
                          }
                        } else {
                          // Einzelnes Material
                          ifcModel.material.visible = true;
                          if ((ifcModel.material as any).transparent !== undefined) {
                            (ifcModel.material as any).transparent = false;
                          }
                          if ((ifcModel.material as any).opacity !== undefined && (ifcModel.material as any).opacity < 1) {
                            (ifcModel.material as any).opacity = 1;
                          }
                        }
                      } else {
                        // Kein Material vorhanden - erstelle Standard-Material
                        console.warn('[IFCViewer] IFCModel hat kein Material, erstelle Standard-Material');
                        const defaultMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                        defaultMat.visible = true;
                        defaultMat.transparent = false;
                        defaultMat.opacity = 1;
                        ifcModel.material = defaultMat;
                        addDebugLog('Standard-Material erstellt für IFCModel');
                      }
                      
                      group.add(ifcModel);
                      addDebugLog('IFCModel added directly to group', {
                        meshType: ifcModel.constructor.name,
                        isIFCModel: (ifcModel as any).constructor.name === 'IFCModel',
                        isTHREEMesh: ifcModel instanceof THREE.Mesh,
                        meshGeometry: ifcModel.geometry ? {
                          vertices: ifcModel.geometry.attributes?.position?.count || 0,
                          type: ifcModel.geometry.type,
                          hasAttributes: !!ifcModel.geometry.attributes,
                          hasGroups: !!(ifcModel.geometry as any).groups,
                          groupsCount: (ifcModel.geometry as any).groups ? (ifcModel.geometry as any).groups.length : 0
                        } : null,
                        meshMaterial: ifcModel.material ? {
                          type: Array.isArray(ifcModel.material) ? 'Array' : ifcModel.material.constructor.name,
                          isArray: Array.isArray(ifcModel.material),
                          arrayLength: Array.isArray(ifcModel.material) ? ifcModel.material.length : 1
                        } : null,
                        hasMeshProperty: !!(ifcModel as any).mesh,
                        meshPropertyType: (ifcModel as any).mesh ? (ifcModel as any).mesh.constructor.name : 'none',
                        frustumCulled: ifcModel.frustumCulled
                      });
                    } else if (ifcModel instanceof THREE.Mesh) {
                      // Direkt ein Mesh (aber kein IFCModel mit mesh Property)
                      group = new THREE.Group();
                      // Stelle sicher, dass Matrix aktualisiert wird
                      ifcModel.updateMatrix();
                      ifcModel.updateMatrixWorld(true);
                      group.add(ifcModel);
                      addDebugLog('Model is THREE.Mesh, wrapped in Group');
                    } else if ((ifcModel as any).model && (ifcModel as any).model instanceof THREE.Object3D) {
                      group = new THREE.Group();
                      group.add((ifcModel as any).model);
                      addDebugLog('Model created from model property');
                    } else if ((ifcModel as any).scene && (ifcModel as any).scene instanceof THREE.Scene) {
                      // Wenn eine Scene zurückgegeben wird, füge alle Objekte hinzu
                      group = new THREE.Group();
                      (ifcModel as any).scene.children.forEach((child: THREE.Object3D) => {
                        group.add(child.clone());
                      });
                      addDebugLog('Model created from scene property');
                    } else if (ifcModel instanceof THREE.Object3D) {
                      group = new THREE.Group();
                      group.add(ifcModel);
                      addDebugLog('Model created from Object3D');
                    } else {
                      // Fallback: Versuche direkt hinzuzufügen
                      group = new THREE.Group();
                      if (ifcModel) {
                        group.add(ifcModel as any);
                      }
                      addDebugLog('Model added directly (unknown structure)', {
                        ifcModelType: typeof ifcModel,
                        ifcModelValue: String(ifcModel).substring(0, 200)
                      });
                    }
                    
                    // Stelle sicher, dass das Modell sichtbar ist und Matrix aktualisiert wird
                    group.visible = true;
                    group.updateMatrix();
                    group.updateMatrixWorld(true);
                    
                    // Zähle alle Meshes und prüfe Materialien
                    let meshCount = 0;
                    let materialIssues = 0;
                    
                    group.traverse((child) => {
                      child.visible = true;
                      child.updateMatrix();
                      
                      if (child instanceof THREE.Mesh) {
                        meshCount++;
                        
                        // KRITISCH: Prüfe Materialien
                        if (!child.material) {
                          console.warn('[IFCViewer] Mesh hat kein Material:', child);
                          materialIssues++;
                          // Erstelle ein Standard-Material falls keines vorhanden
                          child.material = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                        } else if (Array.isArray(child.material)) {
                          // Material-Array
                          if (child.material.length === 0) {
                            console.warn('[IFCViewer] Mesh hat leeres Material-Array:', child);
                            materialIssues++;
                            child.material = [new THREE.MeshStandardMaterial({ color: 0xcccccc })];
                          } else {
                            child.material.forEach((mat, idx) => {
                              if (!mat) {
                                console.warn(`[IFCViewer] Material ${idx} ist null/undefined`);
                                child.material[idx] = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                                materialIssues++;
                              } else {
                                mat.visible = true;
                                if ((mat as any).transparent !== undefined) {
                                  (mat as any).transparent = false;
                                }
                                if ((mat as any).opacity !== undefined && (mat as any).opacity < 1) {
                                  (mat as any).opacity = 1;
                                }
                                // Stelle sicher, dass Material nicht frustumCulled ist
                                if ((mat as any).frustumCulled !== undefined) {
                                  (mat as any).frustumCulled = true;
                                }
                              }
                            });
                          }
                        } else {
                          // Einzelnes Material
                          child.material.visible = true;
                          if ((child.material as any).transparent !== undefined) {
                            (child.material as any).transparent = false;
                          }
                          if ((child.material as any).opacity !== undefined && (child.material as any).opacity < 1) {
                            (child.material as any).opacity = 1;
                          }
                        }
                        
                        // Stelle sicher, dass Geometry vorhanden ist und korrekt ist
                        if (!child.geometry) {
                          console.warn('[IFCViewer] Mesh hat keine Geometrie:', child);
                        } else if (!child.geometry.attributes || !child.geometry.attributes.position) {
                          console.warn('[IFCViewer] Mesh-Geometrie hat keine Position-Attribute:', child.geometry);
                        } else if (child.geometry.attributes.position.count === 0) {
                          console.warn('[IFCViewer] Mesh-Geometrie hat keine Vertices:', child);
                        } else {
                          // Stelle sicher, dass Geometry nicht frustumCulled ist (für Debugging deaktiviert)
                          child.frustumCulled = false;
                          child.matrixAutoUpdate = true;
                        }
                      }
                    });
                    
                    if (materialIssues > 0) {
                      addDebugLog('WARNING: Material-Probleme gefunden', {
                        materialIssues,
                        meshCount
                      });
                    }
                    
                    // Zusätzliche Prüfung: Stelle sicher, dass alle Meshes korrekt konfiguriert sind
                    group.traverse((child) => {
                      if (child instanceof THREE.Mesh) {
                        // Stelle sicher, dass Materialien korrekt sind
                        if (child.material) {
                          if (Array.isArray(child.material)) {
                            // Prüfe jedes Material im Array
                            child.material.forEach((mat: any, idx: number) => {
                              if (!mat) {
                                console.warn(`[IFCViewer] Material ${idx} ist null/undefined, erstelle Standard-Material`);
                                child.material[idx] = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                                materialIssues++;
                              } else {
                                mat.visible = true;
                                if (mat.transparent !== undefined) mat.transparent = false;
                                if (mat.opacity !== undefined && mat.opacity < 1) mat.opacity = 1;
                              }
                            });
                          } else {
                            child.material.visible = true;
                            if ((child.material as any).transparent !== undefined) {
                              (child.material as any).transparent = false;
                            }
                            if ((child.material as any).opacity !== undefined && (child.material as any).opacity < 1) {
                              (child.material as any).opacity = 1;
                            }
                          }
                        }
                        
                        // Stelle sicher, dass Geometry vorhanden ist
                        if (!child.geometry || !child.geometry.attributes || !child.geometry.attributes.position) {
                          console.warn('[IFCViewer] Mesh hat keine gültige Geometrie:', child);
                        }
                      }
                    });
                    
                    addDebugLog('Model created successfully', {
                      modelChildren: group.children.length,
                      modelType: group.constructor.name,
                      modelVisible: group.visible,
                      totalMeshes: (() => {
                        let count = 0;
                        group.traverse((child) => {
                          if (child instanceof THREE.Mesh) count++;
                        });
                        return count;
                      })()
                    });
                    
                    resolve(group);
                  },
                  (progress: any) => {
                    if (progress && progress.total) {
                      const percent = Math.round((progress.loaded / progress.total) * 100);
                      setLoadingProgress(Math.min(95, 80 + (percent * 0.15)));
                      addDebugLog(`Load progress: ${percent}% (${progress.loaded}/${progress.total} bytes)`);
                    } else if (progress && progress.loaded) {
                      // Wenn total nicht verfügbar ist
                      const estimatedPercent = Math.round((progress.loaded / arrayBuffer.byteLength) * 100);
                      setLoadingProgress(Math.min(95, 80 + Math.round(estimatedPercent * 0.15)));
                      addDebugLog(`Load progress: ${progress.loaded} bytes loaded (estimated ${estimatedPercent}%)`);
                    }
                  },
                  (error: any) => {
                    clearTimeout(timeout);
                    addDebugLog('IFC Loader error callback', {
                      error: error?.message,
                      errorType: error?.name,
                      errorStack: error?.stack?.substring(0, 500),
                      errorString: String(error),
                      errorKeys: error ? Object.keys(error) : []
                    });
                    reject(error);
                  }
                );
              } catch (loadCallError: any) {
                clearTimeout(timeout);
                addDebugLog('Error calling ifcLoader.load()', {
                  error: loadCallError?.message,
                  errorType: loadCallError?.name,
                  errorStack: loadCallError?.stack?.substring(0, 500)
                });
                reject(loadCallError);
              }
            });
            
            setLoadingProgress(95);
            addDebugLog('IFC file loading completed successfully');
            
            modelRef.current = model;
            
            // Debug: Prüfe Modell-Struktur vor dem Hinzufügen
            addDebugLog('Model structure before adding to scene', {
              modelType: model.constructor.name,
              childrenCount: model.children.length,
              visible: model.visible,
              position: { x: model.position.x, y: model.position.y, z: model.position.z },
              scale: { x: model.scale.x, y: model.scale.y, z: model.scale.z },
              rotation: { x: model.rotation.x, y: model.rotation.y, z: model.rotation.z }
            });
            
            // Zähle alle Meshes im Modell
            let meshCount = 0;
            let totalVertices = 0;
            let meshesWithoutMaterial = 0;
            let meshesWithoutGeometry = 0;
            let meshesInvisible = 0;
            model.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                meshCount++;
                if (!child.material) {
                  meshesWithoutMaterial++;
                }
                if (!child.geometry) {
                  meshesWithoutGeometry++;
                }
                if (!child.visible) {
                  meshesInvisible++;
                }
                if (child.geometry) {
                  const geometry = child.geometry;
                  if (geometry.attributes && geometry.attributes.position) {
                    totalVertices += geometry.attributes.position.count;
                  }
                }
              }
            });
            
            addDebugLog('Model geometry stats', {
              meshCount,
              totalVertices,
              hasGeometry: meshCount > 0,
              meshesWithoutMaterial,
              meshesWithoutGeometry,
              meshesInvisible
            });
            
            // #region agent log
            writeDebugLog('IFCViewer.tsx:1210', 'Model mesh validation', 'L', {
              meshCount,
              totalVertices,
              meshesWithoutMaterial,
              meshesWithoutGeometry,
              meshesInvisible,
              modelVisible: model.visible,
              modelChildren: model.children.length
            });
            // #endregion
            
            if (meshCount === 0) {
              console.warn('WARNUNG: Modell hat keine Meshes! Das Modell wird möglicherweise nicht angezeigt.');
              // #region agent log
              writeDebugLog('IFCViewer.tsx:1165', 'Model has no meshes', 'A', {
                meshCount: 0,
                totalVertices: 0,
                modelChildren: model.children.length,
                allChildren: model.children.map((child, idx) => ({
                  index: idx,
                  type: child.constructor.name,
                  visible: child.visible,
                  children: child.children.length
                }))
              });
              // #endregion
              addDebugLog('WARNING: Model has no meshes', {
                allChildren: model.children.map((child, idx) => ({
                  index: idx,
                  type: child.constructor.name,
                  visible: child.visible,
                  children: child.children.length
                }))
              });
            } else {
              // #region agent log
              writeDebugLog('IFCViewer.tsx:1165', 'Model loaded successfully', 'A', {
                meshCount,
                totalVertices,
                modelType: model.constructor.name,
                modelVisible: model.visible,
                modelChildren: model.children.length
              });
              // #endregion
            }
            
            // Stelle sicher, dass Modell-Matrix aktualisiert wird, bevor es zur Szene hinzugefügt wird
            model.updateMatrix();
            model.updateMatrixWorld(true);
            
            scene.add(model);
            
            // #region agent log
            writeDebugLog('IFCViewer.tsx:1181', 'Model added to scene', 'A', {
              sceneChildren: scene.children.length,
              modelVisible: model.visible,
              modelChildren: model.children.length,
              modelType: model.constructor.name,
              modelPosition: { x: model.position.x, y: model.position.y, z: model.position.z }
            });
            // #endregion
            
            // Erzwinge Matrix-Update für alle Objekte in der Szene
            scene.updateMatrixWorld(true);
            
            addDebugLog('Model added to scene', {
              sceneChildren: scene.children.length,
              sceneObjects: scene.children.map((child, idx) => ({
                index: idx,
                type: child.constructor.name,
                visible: child.visible
              })),
              modelMatrixWorld: model.matrixWorld ? 'set' : 'not set'
            });

            // KRITISCH: Stelle sicher, dass ALLE Geometrien eine boundingSphere haben
            // Dies muss VOR setFromObject() passieren, da Three.js intern darauf zugreift
            const ensureAllGeometriesHaveBounds = (obj: THREE.Object3D) => {
              obj.traverse((child) => {
                if (child instanceof THREE.Mesh && child.geometry) {
                  const geometry = child.geometry;
                  
                  // Für BufferGeometry
                  if (geometry instanceof THREE.BufferGeometry) {
                    // Stelle sicher, dass boundingBox existiert
                    if (!geometry.boundingBox) {
                      try {
                        if (geometry.attributes && geometry.attributes.position && 
                            geometry.attributes.position.count > 0 && 
                            geometry.attributes.position.array && 
                            geometry.attributes.position.array.length > 0) {
                          geometry.computeBoundingBox();
                        } else {
                          geometry.boundingBox = new THREE.Box3();
                        }
                      } catch (e) {
                        console.warn('[IFCViewer] Fehler beim Erstellen boundingBox:', e);
                        geometry.boundingBox = new THREE.Box3();
                      }
                    }
                    
                    // Stelle sicher, dass boundingSphere existiert - KRITISCH!
                    if (!geometry.boundingSphere) {
                      try {
                        if (geometry.attributes && geometry.attributes.position && 
                            geometry.attributes.position.count > 0 && 
                            geometry.attributes.position.array && 
                            geometry.attributes.position.array.length > 0) {
                          geometry.computeBoundingSphere();
                        } else {
                          // Erstelle leere Sphere als Fallback
                          geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                        }
                      } catch (e) {
                        console.warn('[IFCViewer] Fehler beim Erstellen boundingSphere:', e);
                        // Erstelle leere Sphere als Fallback - MUSS vorhanden sein!
                        geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                      }
                    }
                    
                    // Zusätzliche Sicherheit: Prüfe ob boundingSphere wirklich existiert
                    if (!geometry.boundingSphere) {
                      console.error('[IFCViewer] KRITISCH: boundingSphere konnte nicht erstellt werden!');
                      geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                    }
                  } else {
                    // Für andere Geometrie-Typen
                    try {
                      if (typeof (geometry as any).computeBoundingBox === 'function' && !(geometry as any).boundingBox) {
                        (geometry as any).computeBoundingBox();
                      }
                      if (typeof (geometry as any).computeBoundingSphere === 'function' && !(geometry as any).boundingSphere) {
                        (geometry as any).computeBoundingSphere();
                      }
                      // Stelle sicher, dass boundingSphere existiert
                      if (!(geometry as any).boundingSphere) {
                        (geometry as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                      }
                    } catch (e) {
                      console.warn('[IFCViewer] Fehler beim Erstellen boundingSphere für nicht-BufferGeometry:', e);
                      if (!(geometry as any).boundingSphere) {
                        (geometry as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                      }
                    }
                  }
                }
                
                // Stelle auch sicher, dass Object3D-Objekte (wie Groups) eine boundingSphere haben
                // Dies ist wichtig für frustum.intersectsObject(), das rekursiv auf alle Objekte zugreift
                if (child instanceof THREE.Object3D && !(child instanceof THREE.Mesh)) {
                  // Für Groups und andere Object3D-Objekte
                  if (!(child as any).boundingSphere) {
                    try {
                      // Versuche boundingSphere aus Geometrien der Children zu berechnen
                      const tempBox = new THREE.Box3();
                      let hasGeometry = false;
                      
                      child.traverse((grandChild) => {
                        if (grandChild instanceof THREE.Mesh && grandChild.geometry) {
                          const grandGeometry = grandChild.geometry;
                          if (grandGeometry instanceof THREE.BufferGeometry && grandGeometry.boundingBox) {
                            tempBox.expandByBox(grandGeometry.boundingBox);
                            hasGeometry = true;
                          }
                        }
                      });
                      
                      if (hasGeometry && !tempBox.isEmpty()) {
                        const center = tempBox.getCenter(new THREE.Vector3());
                        const size = tempBox.getSize(new THREE.Vector3());
                        const radius = Math.max(size.x, size.y, size.z) / 2;
                        (child as any).boundingSphere = new THREE.Sphere(center, radius);
                      } else {
                        (child as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                      }
                    } catch (e) {
                      (child as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                    }
                  }
                }
              });
            };
            
            // Fit camera to model
            // Stelle sicher, dass alle Geometrien kompiliert sind, bevor Bounding Box berechnet wird
            ensureAllGeometriesHaveBounds(model);
            
            // Stelle auch sicher, dass das Modell selbst (Group) eine boundingSphere hat
            // Dies ist wichtig für frustum.intersectsObject() später
            if (model instanceof THREE.Group && !(model as any).boundingSphere) {
              try {
                const tempBox = new THREE.Box3();
                let hasGeometry = false;
                
                model.traverse((child) => {
                  if (child instanceof THREE.Mesh && child.geometry) {
                    const geometry = child.geometry;
                    if (geometry instanceof THREE.BufferGeometry && geometry.boundingBox) {
                      tempBox.expandByBox(geometry.boundingBox);
                      hasGeometry = true;
                    }
                  }
                });
                
                if (hasGeometry && !tempBox.isEmpty()) {
                  const center = tempBox.getCenter(new THREE.Vector3());
                  const size = tempBox.getSize(new THREE.Vector3());
                  const radius = Math.max(size.x, size.y, size.z) / 2;
                  (model as any).boundingSphere = new THREE.Sphere(center, radius);
                } else {
                  (model as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                }
              } catch (e) {
                console.warn('[IFCViewer] Fehler beim Erstellen boundingSphere für Group:', e);
                (model as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
              }
            }
            
            // Stelle auch sicher, dass das Modell selbst (Group) eine boundingSphere hat
            // Dies ist wichtig für frustum.intersectsObject() später
            if (model instanceof THREE.Group && !(model as any).boundingSphere) {
              try {
                const tempBox = new THREE.Box3();
                tempBox.setFromObject(model);
                if (!tempBox.isEmpty()) {
                  const center = tempBox.getCenter(new THREE.Vector3());
                  const size = tempBox.getSize(new THREE.Vector3());
                  const radius = Math.max(size.x, size.y, size.z) / 2;
                  (model as any).boundingSphere = new THREE.Sphere(center, radius);
                } else {
                  (model as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
                }
              } catch (e) {
                console.warn('[IFCViewer] Fehler beim Erstellen boundingSphere für Group:', e);
                (model as any).boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
              }
            }
            
            const box = new THREE.Box3();
            try {
              // Versuche Bounding Box zu berechnen
              box.setFromObject(model);
            } catch (e: any) {
              console.error('[IFCViewer] Fehler beim Berechnen der Bounding Box des Modells:', e);
              console.error('[IFCViewer] Fehler-Details:', {
                errorMessage: e?.message,
                errorStack: e?.stack,
                modelType: model?.constructor?.name,
                modelChildren: model?.children?.length,
                modelVisible: model?.visible
              });
              
              // Versuche manuell Bounding Box zu berechnen, falls setFromObject fehlschlägt
              try {
                let hasValidGeometry = false;
                const tempBox = new THREE.Box3();
                model.traverse((child) => {
                  if (child instanceof THREE.Mesh && child.geometry) {
                    const geometry = child.geometry;
                    if (geometry instanceof THREE.BufferGeometry) {
                      if (geometry.boundingBox) {
                        tempBox.expandByBox(geometry.boundingBox);
                        hasValidGeometry = true;
                      } else if (geometry.attributes && geometry.attributes.position && geometry.attributes.position.count > 0) {
                        try {
                          geometry.computeBoundingBox();
                          if (geometry.boundingBox) {
                            tempBox.expandByBox(geometry.boundingBox);
                            hasValidGeometry = true;
                          }
                        } catch (e2) {
                          console.warn('[IFCViewer] Konnte Bounding Box für Mesh nicht berechnen:', e2);
                        }
                      }
                    }
                  }
                });
                
                if (hasValidGeometry && !tempBox.isEmpty()) {
                  box.copy(tempBox);
                  console.log('[IFCViewer] Bounding Box manuell berechnet:', box);
                } else {
                  throw new Error('Keine gültige Geometrie gefunden');
                }
              } catch (manualError) {
                console.error('[IFCViewer] Auch manuelle Bounding Box Berechnung fehlgeschlagen:', manualError);
                // Verwende Standard-Position bei Fehler
                if (cameraRef.current) {
                  cameraRef.current.position.set(10, 10, 10);
                  cameraRef.current.lookAt(0, 0, 0);
                }
                if (controlsRef.current) {
                  controlsRef.current.target.set(0, 0, 0);
                  controlsRef.current.update();
                }
                setLoadingProgress(100);
                setLoading(false);
                addDebugLog('IFC file loading completed (with bounding box error)', { 
                  error: String(e),
                  manualError: String(manualError)
                });
                return;
              }
            }
            
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            
            addDebugLog('Model bounding box', {
              min: { x: box.min.x, y: box.min.y, z: box.min.z },
              max: { x: box.max.x, y: box.max.y, z: box.max.z },
              center: { x: center.x, y: center.y, z: center.z },
              size: { x: size.x, y: size.y, z: size.z },
              isEmpty: box.isEmpty()
            });
            
            // Wenn Bounding Box leer ist, verwende Standard-Position
            if (box.isEmpty() || size.x === 0 && size.y === 0 && size.z === 0) {
              console.warn('WARNUNG: Bounding Box ist leer! Verwende Standard-Kamera-Position.');
              if (cameraRef.current) {
                cameraRef.current.position.set(10, 10, 10);
                cameraRef.current.lookAt(0, 0, 0);
              }
              if (controlsRef.current) {
                controlsRef.current.target.set(0, 0, 0);
              }
            } else {
              if (!cameraRef.current || !controlsRef.current) {
                console.error('[IFCViewer] Kamera oder Controls nicht verfügbar!');
                return;
              }
              
              const camera = cameraRef.current;
              const controls = controlsRef.current;
              
              const maxDim = Math.max(size.x, size.y, size.z);
              const fov = camera.fov * (Math.PI / 180);
              let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
              cameraZ *= 1.5; // Add some padding
              
              camera.position.set(center.x, center.y, center.z + cameraZ);
              camera.lookAt(center);
              controls.target.copy(center);
              
              // #region agent log
              writeDebugLog('IFCViewer.tsx:1445', 'Camera positioned', 'C', {
                cameraPosition: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
                cameraTarget: { x: controls.target.x, y: controls.target.y, z: controls.target.z },
                modelCenter: { x: center.x, y: center.y, z: center.z },
                modelSize: { x: size.x, y: size.y, z: size.z },
                maxDim,
                cameraZ,
                cameraFov: camera.fov
              });
              // #endregion
              
              addDebugLog('Camera positioned', {
                position: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
                target: { x: controls.target.x, y: controls.target.y, z: controls.target.z },
                maxDim,
                cameraZ
              });
            }
            
            if (controlsRef.current) {
              controlsRef.current.update();
            }
            
            setLoadingProgress(100);
            setLoading(false);
            addDebugLog('IFC file loading completed successfully');
            
            // KRITISCH: Finale Überprüfung und Korrektur aller Meshes
            // Dies muss NACH dem Hinzufügen zur Szene UND nach der Kamera-Positionierung passieren
            console.log('[IFCViewer] Starte finale Überprüfung aller Meshes...');
            
            // Stelle sicher, dass alle Geometrien und Materialien korrekt konfiguriert sind
            model.traverse((child) => {
              if (child instanceof THREE.Mesh) {
                // Stelle sicher, dass Mesh sichtbar ist
                child.visible = true;
                child.frustumCulled = false;
                child.updateMatrix();
                child.updateMatrixWorld(true);
                
                // Stelle sicher, dass Materialien korrekt sind
                if (child.material) {
                  if (Array.isArray(child.material)) {
                    child.material.forEach((mat: any) => {
                      if (mat) {
                        // KRITISCH: Stelle sicher, dass Material eine sichtbare Farbe hat
                        if (!mat.color || (mat.color.getHex && mat.color.getHex() === 0x000000)) {
                          if (!mat.color) {
                            mat.color = new THREE.Color(0xcccccc);
                          } else {
                            mat.color.setHex(0xcccccc);
                          }
                        }
                        
                        mat.visible = true;
                        mat.transparent = false;
                        mat.opacity = 1.0;
                        mat.side = THREE.FrontSide;
                        if (mat.needsUpdate !== undefined) {
                          mat.needsUpdate = true;
                        }
                      }
                    });
                  } else {
                    // KRITISCH: Stelle sicher, dass Material eine sichtbare Farbe hat
                    if (!child.material.color || (child.material.color.getHex && child.material.color.getHex() === 0x000000)) {
                      if (!child.material.color) {
                        child.material.color = new THREE.Color(0xcccccc);
                      } else {
                        child.material.color.setHex(0xcccccc);
                      }
                    }
                    
                    child.material.visible = true;
                    (child.material as any).transparent = false;
                    (child.material as any).opacity = 1.0;
                    (child.material as any).side = THREE.FrontSide;
                    if ((child.material as any).needsUpdate !== undefined) {
                      (child.material as any).needsUpdate = true;
                    }
                  }
                }
                
                // Stelle sicher, dass Geometrie kompiliert ist
                if (child.geometry && child.geometry instanceof THREE.BufferGeometry) {
                  const geometry = child.geometry;
                  
                  // Stelle sicher, dass Geometrie kompiliert wird
                  if (geometry.attributes && geometry.attributes.position && geometry.attributes.position.count > 0) {
                    try {
                      geometry.computeBoundingBox();
                      geometry.computeBoundingSphere();
                    } catch (e) {
                      console.warn('[IFCViewer] Fehler beim Kompilieren der Geometrie:', e);
                    }
                    
                    // Stelle sicher, dass Geometrie-Attribute aktualisiert werden
                    if (geometry.attributes.position.needsUpdate !== undefined) {
                      geometry.attributes.position.needsUpdate = true;
                    }
                    if (geometry.index && (geometry.index as any).needsUpdate !== undefined) {
                      (geometry.index as any).needsUpdate = true;
                    }
                    
                    // KRITISCH: Markiere Geometrie als geändert, damit Three.js sie neu kompiliert
                    // Dies ist wichtig für das Rendering, auch wenn keine Gruppen vorhanden sind
                    (geometry as any).needsUpdate = true;
                    
                    // Stelle sicher, dass Geometrie-Gruppen korrekt mit Materialien verknüpft sind
                    if (geometry.groups && geometry.groups.length > 0 && Array.isArray(child.material)) {
                      const groups = geometry.groups;
                      let materialArray = child.material;
                      
                      // KRITISCH: Prüfe, ob Material-Array groß genug ist für alle Gruppen
                      let maxMaterialIndex = -1;
                      groups.forEach((group: any) => {
                        if (group.materialIndex > maxMaterialIndex) {
                          maxMaterialIndex = group.materialIndex;
                        }
                      });
                      
                      // Stelle sicher, dass Material-Array groß genug ist
                      if (maxMaterialIndex >= materialArray.length) {
                        console.warn(`[IFCViewer] Material-Array zu klein: ${materialArray.length}, benötigt: ${maxMaterialIndex + 1}`);
                        while (materialArray.length <= maxMaterialIndex) {
                          const defaultMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                          defaultMat.visible = true;
                          defaultMat.transparent = false;
                          defaultMat.opacity = 1.0;
                          defaultMat.side = THREE.FrontSide;
                          if (defaultMat.needsUpdate !== undefined) {
                            defaultMat.needsUpdate = true;
                          }
                          materialArray.push(defaultMat);
                        }
                        child.material = materialArray;
                      }
                      
                      // Prüfe und korrigiere Material-Indizes
                      let needsUpdate = false;
                      groups.forEach((group: any) => {
                        if (group.materialIndex < 0 || group.materialIndex >= materialArray.length) {
                          const correctedIndex = Math.max(0, Math.min(group.materialIndex, materialArray.length - 1));
                          console.warn(`[IFCViewer] Korrigiere Material-Index in Gruppe: ${group.materialIndex} -> ${correctedIndex}`);
                          group.materialIndex = correctedIndex;
                          needsUpdate = true;
                        }
                      });
                      
                      // Stelle sicher, dass alle Materialien korrekt sind
                      materialArray.forEach((mat: any, idx: number) => {
                        if (mat) {
                          // KRITISCH: Stelle sicher, dass Material eine sichtbare Farbe hat
                          if (!mat.color || (mat.color.getHex && mat.color.getHex() === 0x000000)) {
                            console.warn(`[IFCViewer] Material ${idx} hat keine Farbe oder ist schwarz, setze Standard-Farbe`);
                            if (!mat.color) {
                              mat.color = new THREE.Color(0xcccccc);
                            } else {
                              mat.color.setHex(0xcccccc);
                            }
                            needsUpdate = true;
                          }
                          
                          mat.visible = true;
                          mat.transparent = false;
                          mat.opacity = 1.0;
                          mat.side = THREE.FrontSide;
                          if (mat.needsUpdate !== undefined) {
                            mat.needsUpdate = true;
                          }
                        } else {
                          console.warn(`[IFCViewer] Material ${idx} ist null, erstelle Standard-Material`);
                          materialArray[idx] = new THREE.MeshStandardMaterial({ color: 0xcccccc });
                          materialArray[idx].visible = true;
                          materialArray[idx].transparent = false;
                          materialArray[idx].opacity = 1.0;
                          materialArray[idx].side = THREE.FrontSide;
                          if (materialArray[idx].needsUpdate !== undefined) {
                            materialArray[idx].needsUpdate = true;
                          }
                          needsUpdate = true;
                        }
                      });
                      
                      // KRITISCH: Erstelle IMMER neue Gruppen-Array, um sicherzustellen, dass Three.js die Änderungen erkennt
                      // Dies ist wichtig, auch wenn keine Änderungen vorgenommen wurden, da Three.js möglicherweise
                      // die Gruppen nicht korrekt erkennt, wenn sie nicht neu zugewiesen werden
                      const newGroups = groups.map((g: any) => ({
                        start: g.start,
                        count: g.count,
                        materialIndex: g.materialIndex
                      }));
                      // WICHTIG: Setze groups auf leeres Array und dann auf neue Gruppen, um Three.js zu zwingen, sie neu zu verarbeiten
                      geometry.groups = [];
                      geometry.groups = newGroups;
                      
                      // Stelle sicher, dass Material-Array korrekt zugewiesen ist
                      child.material = materialArray;
                      
                      // Erzwinge Geometrie-Update - dies ist kritisch für das Rendering
                      geometry.computeBoundingBox();
                      geometry.computeBoundingSphere();
                      
                      // Stelle sicher, dass Geometrie-Attribute aktualisiert werden
                      if (geometry.attributes.position.needsUpdate !== undefined) {
                        geometry.attributes.position.needsUpdate = true;
                      }
                      if (geometry.index && (geometry.index as any).needsUpdate !== undefined) {
                        (geometry.index as any).needsUpdate = true;
                      }
                      
                      // KRITISCH: Markiere Geometrie als geändert, damit Three.js sie neu kompiliert
                      (geometry as any).needsUpdate = true;
                      
                      // KRITISCH: Erzwinge Material-Update für alle Materialien
                      materialArray.forEach((mat: any) => {
                        if (mat && mat.needsUpdate !== undefined) {
                          mat.needsUpdate = true;
                        }
                      });
                      
                      console.log('[IFCViewer] Geometrie-Gruppen aktualisiert und Geometrie neu kompiliert', {
                        groupsCount: groups.length,
                        materialArrayLength: materialArray.length,
                        maxMaterialIndex
                      });
                    } else if (geometry.groups && geometry.groups.length > 0 && !Array.isArray(child.material)) {
                      // Geometrie hat Gruppen, aber Material ist kein Array - das ist ein Problem!
                      console.error('[IFCViewer] ⚠️ Geometrie hat Gruppen, aber Material ist kein Array!', {
                        groupsCount: geometry.groups.length,
                        materialType: typeof child.material,
                        materialIsArray: Array.isArray(child.material)
                      });
                      
                      // Konvertiere einzelnes Material zu Array
                      const singleMaterial = child.material as THREE.Material;
                      const materialArray: THREE.Material[] = [];
                      
                      // Erstelle Material-Array mit genügend Materialien für alle Gruppen
                      let maxMaterialIndex = -1;
                      geometry.groups.forEach((group: any) => {
                        if (group.materialIndex > maxMaterialIndex) {
                          maxMaterialIndex = group.materialIndex;
                        }
                      });
                      
                      for (let i = 0; i <= maxMaterialIndex; i++) {
                        materialArray.push(singleMaterial.clone());
                      }
                      
                      child.material = materialArray;
                      
                      // Erstelle neue Gruppen-Array
                      geometry.groups = geometry.groups.map((g: any) => ({
                        start: g.start,
                        count: g.count,
                        materialIndex: g.materialIndex
                      }));
                      
                      // Erzwinge Geometrie-Update
                      geometry.computeBoundingBox();
                      geometry.computeBoundingSphere();
                      (geometry as any).needsUpdate = true;
                      
                      console.log('[IFCViewer] Material von Einzel-Material zu Array konvertiert', {
                        groupsCount: geometry.groups.length,
                        materialArrayLength: materialArray.length
                      });
                    }
                  }
                }
              }
            });
          
            // Erzwinge erneuten Render nach allen Korrekturen
            // KRITISCH: Führe mehrere Render-Zyklen durch, um sicherzustellen, dass alle Updates verarbeitet werden
            if (rendererRef.current && sceneRef.current && cameraRef.current) {
              sceneRef.current.updateMatrixWorld(true);
              rendererRef.current.info.reset();
              
              // Erster Render: Initialisiert die Geometrie
              rendererRef.current.render(sceneRef.current, cameraRef.current);
              
              // Zweiter Render: Stellt sicher, dass alle Material-Updates verarbeitet werden
              rendererRef.current.render(sceneRef.current, cameraRef.current);
              
              // Dritter Render: Finale Statistiken
              rendererRef.current.render(sceneRef.current, cameraRef.current);
              
              const finalStats = rendererRef.current.info;
              
              // Prüfe, ob Modell im Sichtfeld ist
              const frustum = new THREE.Frustum();
              const matrix = new THREE.Matrix4().multiplyMatrices(
                cameraRef.current.projectionMatrix,
                cameraRef.current.matrixWorldInverse
              );
              frustum.setFromProjectionMatrix(matrix);
              
              let modelInFrustum = false;
              let modelBoundingBox: THREE.Box3 | null = null;
              try {
                const box = new THREE.Box3();
                box.setFromObject(model);
                modelBoundingBox = box;
                modelInFrustum = frustum.intersectsBox(box);
              } catch (e) {
                console.warn('[IFCViewer] Konnte Frustum-Check nicht durchführen:', e);
              }
              
              // Prüfe Materialien auf Farben
              const materialColors: any[] = [];
              model.traverse((child) => {
                if (child instanceof THREE.Mesh && child.material) {
                  const materials = Array.isArray(child.material) ? child.material : [child.material];
                  materials.forEach((mat: any, idx: number) => {
                    if (mat && mat.color) {
                      const colorHex = mat.color.getHex ? mat.color.getHex() : null;
                      const colorRgb = mat.color.r !== undefined ? {r: mat.color.r, g: mat.color.g, b: mat.color.b} : null;
                      const emission = mat.emission ? (mat.emission.getHex ? mat.emission.getHex() : null) : null;
                      const brightness = colorRgb ? (colorRgb.r + colorRgb.g + colorRgb.b) / 3 : null;
                      materialColors.push({
                        materialIndex: idx,
                        colorHex,
                        colorRgb,
                        emission,
                        brightness,
                        visible: mat.visible,
                        transparent: mat.transparent,
                        opacity: mat.opacity,
                        materialType: mat.constructor.name
                      });
                    }
                  });
                }
              });
              
              // Prüfe Canvas und Renderer-Status
              const canvas = rendererRef.current?.domElement;
              const canvasVisible = canvas ? (canvas.offsetWidth > 0 && canvas.offsetHeight > 0) : false;
              const canvasStyle = canvas ? window.getComputedStyle(canvas) : null;
              const rendererInfo = rendererRef.current ? {
                domElement: !!rendererRef.current.domElement,
                domElementWidth: rendererRef.current.domElement?.width || 0,
                domElementHeight: rendererRef.current.domElement?.height || 0,
                pixelRatio: rendererRef.current.getPixelRatio(),
                shadowMapEnabled: rendererRef.current.shadowMap.enabled
              } : null;
              
              // KRITISCH: Stelle sicher, dass Kamera-Position aktualisiert ist
              // OrbitControls kann die Kamera-Position nach controls.update() ändern
              if (controlsRef.current) {
                controlsRef.current.update();
              }
              if (cameraRef.current) {
                cameraRef.current.updateMatrixWorld(true);
              }
              
              // Berechne Distanz zwischen Kamera und Modell
              const cameraToModelDistance = modelBoundingBox && cameraRef.current ? 
                cameraRef.current.position.distanceTo(modelBoundingBox.getCenter(new THREE.Vector3())) : null;
              
              // Prüfe, ob Modell im Near/Far-Plane der Kamera ist
              const modelInCameraRange = modelBoundingBox && cameraRef.current ? 
                (cameraToModelDistance! >= cameraRef.current.near && cameraToModelDistance! <= cameraRef.current.far) : null;
              
              // KRITISCH: Prüfe, ob Modell wirklich in der Scene ist
              const modelInScene = sceneRef.current.children.some(c => c === model);
              if (!modelInScene) {
                console.error('[IFCViewer] ⚠️ WARNUNG: Modell ist nicht in der Scene beim Post-fix render stats!');
                console.error('[IFCViewer] Scene children:', sceneRef.current.children.map(c => c.constructor.name));
                console.error('[IFCViewer] Model type:', model.constructor.name);
                // Versuche Modell zur Scene hinzuzufügen, falls es fehlt
                if (!sceneRef.current.children.includes(model)) {
                  console.warn('[IFCViewer] Füge Modell zur Scene hinzu...');
                  sceneRef.current.add(model);
                  sceneRef.current.updateMatrixWorld(true);
                  // Erzwinge erneuten Render nach Hinzufügen
                  rendererRef.current?.render(sceneRef.current, cameraRef.current!);
                }
              }
              
              // #region agent log
              writeDebugLog('IFCViewer.tsx:1687', 'Post-fix render stats', 'B', {
                renderCalls: finalStats.render.calls,
                renderTriangles: finalStats.render.triangles,
                geometries: finalStats.memory.geometries,
                sceneChildren: sceneRef.current.children.length,
                modelInScene: sceneRef.current.children.some(c => c === model),
                modelVisible: model.visible,
                modelInFrustum,
                modelInCameraRange,
                cameraToModelDistance,
                cameraNear: cameraRef.current?.near || 0,
                cameraFar: cameraRef.current?.far || 0,
                cameraFov: cameraRef.current?.fov || 0,
                modelBoundingBox: modelBoundingBox ? {
                  min: {x: modelBoundingBox.min.x, y: modelBoundingBox.min.y, z: modelBoundingBox.min.z},
                  max: {x: modelBoundingBox.max.x, y: modelBoundingBox.max.y, z: modelBoundingBox.max.z},
                  center: modelBoundingBox.getCenter(new THREE.Vector3()),
                  size: modelBoundingBox.getSize(new THREE.Vector3())
                } : null,
                cameraPosition: cameraRef.current ? {
                  x: cameraRef.current.position.x,
                  y: cameraRef.current.position.y,
                  z: cameraRef.current.position.z
                } : {x: 0, y: 0, z: 0},
                cameraTarget: controlsRef.current ? {
                  x: controlsRef.current.target.x,
                  y: controlsRef.current.target.y,
                  z: controlsRef.current.target.z
                } : {x: 0, y: 0, z: 0},
                materialColors: materialColors.slice(0, 10), // Erste 10 Materialien
                canvasVisible,
                canvasStyle: canvasStyle ? {
                  display: canvasStyle.display,
                  visibility: canvasStyle.visibility,
                  opacity: canvasStyle.opacity,
                  width: canvasStyle.width,
                  height: canvasStyle.height
                } : null,
                rendererInfo
              });
              // #endregion
              
              console.log('[IFCViewer] Final Render Stats nach Korrekturen:', {
                renderCalls: finalStats.render.calls,
                renderTriangles: finalStats.render.triangles,
                geometries: finalStats.memory.geometries
              });
              
              if (finalStats.render.triangles === 0) {
                console.error('[IFCViewer] ⚠️ WARNUNG: Immer noch keine Triangles nach Korrekturen!');
                addDebugLog('ERROR: Still no triangles after fixes', {
                  renderCalls: finalStats.render.calls,
                  geometries: finalStats.memory.geometries
                });
              }
            }
            
            // Prüfe WebGL-Kontext (Hypothese D)
            const gl = (rendererRef.current as any).getContext();
            const webglInfo = gl ? {
              version: gl.getParameter(gl.VERSION),
              vendor: gl.getParameter(gl.VENDOR),
              renderer: gl.getParameter(gl.RENDERER),
              maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
              maxVertexAttribs: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
              maxVertexUniforms: gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),
              maxFragmentUniforms: gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS)
            } : null;
            
            // Prüfe WebGL-Fehler (Hypothese D)
            const webglErrors: string[] = [];
            if (gl) {
              const error = gl.getError();
              if (error !== gl.NO_ERROR) {
                webglErrors.push(`WebGL error: ${error}`);
              }
            }
            
            // #region agent log
            writeDebugLog('IFCViewer.tsx:1065', 'WebGL context check', 'D', {
              hasWebGLContext: !!gl,
              webglInfo,
              rendererInitialized: !!rendererRef.current,
              webglErrors,
              hasErrors: webglErrors.length > 0
            });
            // #endregion
            
            if (webglErrors.length > 0) {
              console.error('[IFCViewer] WebGL-Fehler gefunden:', webglErrors);
              addDebugLog('ERROR: WebGL errors detected', { errors: webglErrors });
            }
          } catch (loadError: any) {
            // Cleanup Blob URL bei Fehler
            if (blobUrl) {
              URL.revokeObjectURL(blobUrl);
              blobUrl = null;
            }
            
            addDebugLog('Error loading IFC file (catch block)', {
              error: loadError?.message,
              errorType: loadError?.name,
              errorStack: loadError?.stack?.substring(0, 500),
              errorString: String(loadError)
            });
            
            // Fallback: Versuche Blob-URL Methode
            addDebugLog('Trying fallback method with Blob URL');
            
            try {
              // Konvertiere ArrayBuffer zu Blob und erstelle Blob-URL
              const blob = new Blob([arrayBuffer], { type: 'application/octet-stream' });
              blobUrl = URL.createObjectURL(blob);
              addDebugLog('Blob URL created for fallback', { blobUrl, blobSize: blob.size });
              
              model = await new Promise<THREE.Group>((resolve, reject) => {
                const timeout = setTimeout(() => {
                  if (blobUrl) URL.revokeObjectURL(blobUrl);
                  reject(new Error('Timeout beim Laden der IFC-Datei (Fallback-Methode)'));
                }, 300000); // 5 Minuten Timeout
                
                ifcLoader.load(
                  blobUrl!,
                  (ifcModel: any) => {
                    clearTimeout(timeout);
                    if (blobUrl) URL.revokeObjectURL(blobUrl);
                    addDebugLog('IFC model loaded via Blob URL', {
                      modelType: typeof ifcModel,
                      isGroup: ifcModel instanceof THREE.Group
                    });
                    let group: THREE.Group;
                    if (ifcModel instanceof THREE.Group) {
                      group = ifcModel;
                    } else if (ifcModel.mesh) {
                      group = new THREE.Group();
                      group.add(ifcModel.mesh);
                    } else if (ifcModel instanceof THREE.Object3D) {
                      group = new THREE.Group();
                      group.add(ifcModel);
                    } else {
                      group = new THREE.Group();
                      group.add(ifcModel);
                    }
                    resolve(group);
                  },
                  (progress: any) => {
                    if (progress && progress.total) {
                      const percent = Math.round((progress.loaded / progress.total) * 100);
                      setLoadingProgress(Math.min(95, 80 + (percent * 0.15)));
                      addDebugLog(`Fallback load progress: ${percent}%`);
                    }
                  },
                  (error: any) => {
                    clearTimeout(timeout);
                    if (blobUrl) URL.revokeObjectURL(blobUrl);
                    addDebugLog('IFC Loader Blob URL error', {
                      error: error?.message,
                      errorType: error?.name
                    });
                    reject(error);
                  }
                );
              });
              addDebugLog('Fallback method succeeded');
            } catch (fallbackError: any) {
              if (blobUrl) {
                URL.revokeObjectURL(blobUrl);
                blobUrl = null;
              }
              addDebugLog('Fallback method also failed', {
                error: fallbackError?.message,
                errorType: fallbackError?.name
              });
              throw new Error(`Fehler beim Laden der IFC-Datei: ${loadError?.message || 'Unbekannter Fehler'}. Fallback ebenfalls fehlgeschlagen: ${fallbackError?.message || 'Unbekannter Fehler'}`);
            }
          }
          
          // Log all debug messages to console for troubleshooting
          console.log('=== IFC Viewer Debug Log ===');
          debugLog.forEach(log => console.log(`[${log.timestamp}] ${log.message}`, log.data || ''));
          console.log('=== End Debug Log ===');
          
          // Speichere Debug-Logs nach erfolgreichem Laden
          await saveDebugLogs();
        } catch (err: any) {
          console.error('Fehler beim Laden der IFC-Datei:', err);
          console.error('=== IFC Viewer Debug Log ===');
          debugLog.forEach(log => console.log(`[${log.timestamp}] ${log.message}`, log.data || ''));
          console.error('=== End Debug Log ===');
          
          // Speichere Debug-Logs auch bei Fehler
          await saveDebugLogs();
          
          // Detaillierte Fehlermeldung
          let errorMessage = 'Fehler beim Laden der IFC-Datei';
          if (err?.message) {
            errorMessage = err.message;
          } else if (err?.response) {
            errorMessage = `Backend-Fehler: ${err.response.status} ${err.response.statusText}`;
          } else if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Failed to fetch')) {
            errorMessage = 'Netzwerkfehler: Backend nicht erreichbar oder Verbindung abgebrochen. Bitte prüfe:\n- Backend läuft auf http://localhost:8000\n- Datei ist nicht zu groß\n- Browser-Konsole für Details (F12)';
          }
          
          setError(errorMessage);
          setLoading(false);
        }
      };
      
      // Starte Ladevorgang mit Fehlerbehandlung
      loadIFCFile().catch((err: any) => {
        console.error('[IFCViewer] Fehler beim Laden der IFC-Datei:', err);
        let errorMessage = 'Fehler beim Laden der IFC-Datei';
        if (err?.message) {
          errorMessage = err.message;
        } else if (err?.response) {
          errorMessage = `Backend-Fehler: ${err.response.status} ${err.response.statusText}`;
        } else if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Failed to fetch')) {
          errorMessage = 'Netzwerkfehler: Backend nicht erreichbar oder Verbindung abgebrochen. Bitte prüfe:\n- Backend läuft auf http://localhost:8000\n- Datei ist nicht zu groß\n- Browser-Konsole für Details (F12)';
        }
        setError(errorMessage);
        setLoading(false);
      });

      // Animation Loop
      let frameCount = 0;
      const animate = () => {
        requestAnimationFrame(animate);
        frameCount++;
        
        // Log alle 60 Frames (ca. 1x pro Sekunde bei 60fps)
        if (frameCount % 60 === 0) {
          const renderStats = rendererRef.current ? rendererRef.current.info : null;
          const canvas = rendererRef.current?.domElement;
          const canvasVisible = canvas ? (canvas.offsetWidth > 0 && canvas.offsetHeight > 0) : false;
          
          // Prüfe Modell-Position relativ zur Kamera
          let modelDistance = null;
          let modelInView = false;
          let modelInScene = false;
          let modelMaterialInfo: any = null;
          if (modelRef.current && cameraRef.current && sceneRef.current) {
            try {
              // Prüfe, ob Modell in Scene ist (Hypothese L)
              modelInScene = sceneRef.current.children.some(c => c === modelRef.current);
              
              const box = new THREE.Box3();
              box.setFromObject(modelRef.current);
              const modelCenter = box.getCenter(new THREE.Vector3());
              modelDistance = cameraRef.current.position.distanceTo(modelCenter);
              
              const frustum = new THREE.Frustum();
              const matrix = new THREE.Matrix4().multiplyMatrices(
                cameraRef.current.projectionMatrix,
                cameraRef.current.matrixWorldInverse
              );
              frustum.setFromProjectionMatrix(matrix);
              modelInView = frustum.intersectsBox(box);
              
              // Prüfe Materialien auf Opacity/Transparenz (Hypothese I)
              const materials: any[] = [];
              modelRef.current.traverse((child) => {
                if (child instanceof THREE.Mesh && child.material) {
                  const mats = Array.isArray(child.material) ? child.material : [child.material];
                  mats.forEach((mat: any) => {
                    if (mat) {
                      materials.push({
                        type: mat.constructor.name,
                        visible: mat.visible,
                        transparent: mat.transparent,
                        opacity: mat.opacity,
                        color: mat.color ? mat.color.getHex() : null,
                        side: mat.side
                      });
                    }
                  });
                }
              });
              modelMaterialInfo = {
                totalMaterials: materials.length,
                transparentMaterials: materials.filter(m => m.transparent).length,
                invisibleMaterials: materials.filter(m => !m.visible).length,
                lowOpacityMaterials: materials.filter(m => m.opacity < 0.1).length,
                sampleMaterials: materials.slice(0, 5)
              };
            } catch (e) {
              // Ignore errors
            }
          }
          
          // Prüfe Scene-Background (Hypothese J)
          const sceneBackground = sceneRef.current?.background;
          const sceneBackgroundInfo = sceneBackground ? {
            isColor: sceneBackground instanceof THREE.Color,
            colorHex: sceneBackground instanceof THREE.Color ? sceneBackground.getHex() : null,
            colorRgb: sceneBackground instanceof THREE.Color ? {
              r: sceneBackground.r,
              g: sceneBackground.g,
              b: sceneBackground.b
            } : null
          } : null;
          
          // #region agent log
          writeDebugLog('IFCViewer.tsx:1873', 'Render loop frame', 'E', {
            frameCount,
            sceneChildren: sceneRef.current?.children.length || 0,
            cameraPosition: cameraRef.current ? {
              x: cameraRef.current.position.x,
              y: cameraRef.current.position.y,
              z: cameraRef.current.position.z
            } : null,
            cameraTarget: controlsRef.current ? {
              x: controlsRef.current.target.x,
              y: controlsRef.current.target.y,
              z: controlsRef.current.target.z
            } : null,
            modelVisible: modelRef.current?.visible || false,
            modelChildren: modelRef.current?.children.length || 0,
            modelInScene,
            modelDistance,
            modelInView,
            renderCalls: renderStats?.render.calls || 0,
            renderTriangles: renderStats?.render.triangles || 0,
            canvasVisible,
            canvasSize: canvas ? {
              width: canvas.width,
              height: canvas.height,
              offsetWidth: canvas.offsetWidth,
              offsetHeight: canvas.offsetHeight
            } : null,
            modelMaterialInfo,
            sceneBackgroundInfo
          });
          // #endregion
          console.log(`[IFCViewer] Render loop running (Frame ${frameCount})`, {
            sceneChildren: sceneRef.current?.children.length || 0,
            cameraPosition: cameraRef.current ? {
              x: cameraRef.current.position.x,
              y: cameraRef.current.position.y,
              z: cameraRef.current.position.z
            } : null,
            modelVisible: modelRef.current?.visible || false,
            modelChildren: modelRef.current?.children.length || 0
          });
        }
        
        if (controlsRef.current) {
          controlsRef.current.update();
        }
        if (rendererRef.current && sceneRef.current && cameraRef.current) {
          // Stelle sicher, dass die Kamera-Matrix aktualisiert ist
          cameraRef.current.updateMatrixWorld(true);
          sceneRef.current.updateMatrixWorld(true);
          rendererRef.current.render(sceneRef.current, cameraRef.current);
        }
      };
      animate();
      
      console.log('Animation loop started');

      // Handle Window Resize
      const handleResize = () => {
        if (!containerRef.current || !cameraRef.current || !rendererRef.current) return;
        cameraRef.current.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight;
        cameraRef.current.updateProjectionMatrix();
        rendererRef.current.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
      };
      window.addEventListener('resize', handleResize);

      // Store cleanup function
      cleanupRef.current = () => {
        window.removeEventListener('resize', handleResize);
        if (controlsRef.current) {
          controlsRef.current.dispose();
        }
        if (rendererRef.current) {
          rendererRef.current.dispose();
        }
        if (ifcLoaderRef.current && ifcLoaderRef.current.ifcManager) {
          ifcLoaderRef.current.ifcManager.dispose();
        }
      };
    };
    
    // Initialize viewer
    initializeViewer();

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, [fileId]);

  const handleResetView = () => {
    if (!modelRef.current || !cameraRef.current || !controlsRef.current) return;

    // Stelle sicher, dass ALLE Geometrien eine boundingSphere haben
    modelRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh && child.geometry) {
        const geometry = child.geometry;
        if (geometry instanceof THREE.BufferGeometry) {
          if (!geometry.boundingBox) {
            try {
              if (geometry.attributes?.position?.count > 0) {
                geometry.computeBoundingBox();
              } else {
                geometry.boundingBox = new THREE.Box3();
              }
            } catch (e) {
              geometry.boundingBox = new THREE.Box3();
            }
          }
          if (!geometry.boundingSphere) {
            try {
              if (geometry.attributes?.position?.count > 0) {
                geometry.computeBoundingSphere();
              } else {
                geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
              }
            } catch (e) {
              geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
            }
          }
        }
      }
    });

    const box = new THREE.Box3();
    try {
      box.setFromObject(modelRef.current);
    } catch (e) {
      console.error('[IFCViewer] Fehler beim Berechnen der Bounding Box (reset view):', e);
      return;
    }

    if (box.isEmpty()) {
      console.warn('[IFCViewer] Bounding Box ist leer, kann View nicht zurücksetzen');
      return;
    }

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const distance = maxDim * 2;

    cameraRef.current.position.set(
      center.x + distance,
      center.y + distance,
      center.z + distance
    );
    cameraRef.current.lookAt(center);
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
  };

  const handleFitToScreen = () => {
    if (!modelRef.current || !cameraRef.current || !controlsRef.current || !containerRef.current) return;

    // Stelle sicher, dass ALLE Geometrien eine boundingSphere haben
    modelRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh && child.geometry) {
        const geometry = child.geometry;
        if (geometry instanceof THREE.BufferGeometry) {
          if (!geometry.boundingBox) {
            try {
              if (geometry.attributes?.position?.count > 0) {
                geometry.computeBoundingBox();
              } else {
                geometry.boundingBox = new THREE.Box3();
              }
            } catch (e) {
              geometry.boundingBox = new THREE.Box3();
            }
          }
          if (!geometry.boundingSphere) {
            try {
              if (geometry.attributes?.position?.count > 0) {
                geometry.computeBoundingSphere();
              } else {
                geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
              }
            } catch (e) {
              geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 0);
            }
          }
        }
      }
    });

    const box = new THREE.Box3();
    try {
      box.setFromObject(modelRef.current);
    } catch (e) {
      console.error('[IFCViewer] Fehler beim Berechnen der Bounding Box (fit to screen):', e);
      return;
    }

    if (box.isEmpty()) {
      console.warn('[IFCViewer] Bounding Box ist leer, kann View nicht anpassen');
      return;
    }

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = cameraRef.current.fov * (Math.PI / 180);
    const distance = maxDim / (2 * Math.tan(fov / 2));

    cameraRef.current.position.set(
      center.x + distance,
      center.y + distance,
      center.z + distance
    );
    cameraRef.current.lookAt(center);
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
  };

  return (
    <div className="ifc-viewer-overlay" onClick={onClose}>
      <div className="ifc-viewer-content glass" onClick={(e) => e.stopPropagation()}>
        <div className="ifc-viewer-header">
          <h3 className="ifc-viewer-title">IFC Viewer: {filename}</h3>
          <button className="ifc-viewer-close" onClick={onClose} title="Schließen">
            ×
          </button>
        </div>

        <div className="ifc-viewer-toolbar">
          <button className="ifc-viewer-btn" onClick={handleResetView} title="Ansicht zurücksetzen">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 8a5 5 0 0 1 5-5v2M13 8a5 5 0 0 1-5 5v-2M8 3v2M8 11v2"/>
            </svg>
            Reset View
          </button>
          <button className="ifc-viewer-btn" onClick={handleFitToScreen} title="Modell zentrieren">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="2" width="12" height="12" rx="1"/>
              <path d="M6 6h4v4H6z"/>
            </svg>
            Fit to Screen
          </button>
          <div className="ifc-viewer-info">
            <span>Navigation: Links-Drag = Rotate | Rechts-Drag = Pan | Scroll = Zoom</span>
          </div>
        </div>

        <div className="ifc-viewer-container" ref={containerRef}>
          {loading && (
            <div className="ifc-viewer-loading">
              <div className="ifc-viewer-loading-spinner"></div>
              <p>Lade IFC-Datei... {loadingProgress}%</p>
            </div>
          )}
          {error && (
            <div className="ifc-viewer-error">
              <span>⚠️</span>
              <p>{error}</p>
              <button className="ifc-viewer-btn" onClick={onClose}>Schließen</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default IFCViewer;
