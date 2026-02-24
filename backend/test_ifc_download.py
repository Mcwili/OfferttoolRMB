"""
Test-Skript für IFC-Datei-Download
Testet den Download-Endpunkt und identifiziert mögliche Probleme
"""

import requests
import time
import sys
import os
from pathlib import Path

# API Base URL
API_BASE_URL = "http://localhost:8000/api/v1"

def test_file_download(file_id: int, output_path: str = None):
    """
    Testet den Download einer Datei
    
    Args:
        file_id: ID der Datei zum Download
        output_path: Optionaler Pfad zum Speichern der Datei
    """
    print(f"\n{'='*60}")
    print(f"Test: Download von Datei {file_id}")
    print(f"{'='*60}\n")
    
    url = f"{API_BASE_URL}/files/{file_id}/download"
    
    print(f"URL: {url}")
    print(f"Starte Download...\n")
    
    start_time = time.time()
    downloaded_bytes = 0
    chunks_received = 0
    
    try:
        # Request mit Streaming
        response = requests.get(
            url,
            stream=True,
            timeout=600  # 10 Minuten Timeout
        )
        
        # Prüfe Status-Code
        print(f"Status Code: {response.status_code}")
        print(f"Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print()
        
        if response.status_code != 200:
            print(f"[ERROR] FEHLER: Status Code {response.status_code}")
            print(f"Response Text: {response.text[:500]}")
            return False
        
        # Lade Datei in Chunks
        content_length = response.headers.get('Content-Length')
        if content_length:
            total_size = int(content_length)
            print(f"Erwartete Größe: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
        else:
            total_size = None
            print(f"Erwartete Größe: Unbekannt (kein Content-Length Header)")
        
        print(f"\nLade Datei...")
        
        chunks = []
        last_progress_time = time.time()
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
                downloaded_bytes += len(chunk)
                chunks_received += 1
                
                # Progress-Anzeige alle 0.5 Sekunden
                current_time = time.time()
                if current_time - last_progress_time >= 0.5:
                    elapsed = current_time - start_time
                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                    
                    if total_size:
                        percent = (downloaded_bytes / total_size) * 100
                        remaining = total_size - downloaded_bytes
                        eta = remaining / speed if speed > 0 else 0
                        print(f"  Progress: {percent:.1f}% ({downloaded_bytes:,}/{total_size:,} bytes) "
                              f"Speed: {speed / 1024 / 1024:.2f} MB/s ETA: {eta:.1f}s")
                    else:
                        print(f"  Progress: {downloaded_bytes:,} bytes "
                              f"Speed: {speed / 1024 / 1024:.2f} MB/s")
                    
                    last_progress_time = current_time
        
        # Zusammenfügen aller Chunks
        file_content = b''.join(chunks)
        duration = time.time() - start_time
        
        print(f"\n[OK] Download abgeschlossen!")
        print(f"  Dauer: {duration:.2f} Sekunden")
        print(f"  Größe: {downloaded_bytes:,} bytes ({downloaded_bytes / 1024 / 1024:.2f} MB)")
        print(f"  Chunks: {chunks_received}")
        print(f"  Durchschnittliche Geschwindigkeit: {downloaded_bytes / duration / 1024 / 1024:.2f} MB/s")
        
        if total_size and downloaded_bytes != total_size:
            print(f"⚠️  WARNUNG: Größe stimmt nicht überein!")
            print(f"  Erwartet: {total_size:,} bytes")
            print(f"  Erhalten: {downloaded_bytes:,} bytes")
            print(f"  Differenz: {abs(total_size - downloaded_bytes):,} bytes")
        
        # Validiere Datei-Inhalt
        print(f"\nValidiere Datei-Inhalt...")
        
        if len(file_content) == 0:
            print(f"[ERROR] FEHLER: Datei ist leer!")
            return False
        
        # Prüfe auf IFC-Marker (IFC-Dateien beginnen oft mit bestimmten Zeichen)
        if file_content.startswith(b'ISO-10303-21'):
            print(f"[OK] IFC-Datei erkannt (ISO-10303-21 Header)")
        elif file_content.startswith(b'IFC'):
            print(f"[OK] IFC-Datei erkannt (IFC Header)")
        else:
            # Prüfe auf Text-Encoding
            try:
                text_start = file_content[:100].decode('utf-8', errors='ignore')
                if 'ISO-10303-21' in text_start or 'IFC' in text_start:
                    print(f"[OK] IFC-Datei erkannt (Text-Header)")
                else:
                    print(f"⚠️  Unbekanntes Dateiformat (beginnt mit: {text_start[:50]}...)")
            except:
                print(f"⚠️  Datei scheint binär zu sein")
        
        # Speichere Datei falls gewünscht
        if output_path:
            print(f"\nSpeichere Datei nach: {output_path}")
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(file_content)
            print(f"[OK] Datei gespeichert")
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"[ERROR] FEHLER: Timeout nach {time.time() - start_time:.2f} Sekunden")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] FEHLER: Verbindungsfehler")
        print(f"  {str(e)}")
        print(f"\nBitte prüfe:")
        print(f"  - Backend läuft auf http://localhost:8000")
        print(f"  - Keine Firewall blockiert die Verbindung")
        return False
    except Exception as e:
        print(f"[ERROR] FEHLER: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"\nTraceback:")
        print(traceback.format_exc())
        return False


def list_files(project_id: int = None):
    """Listet alle Dateien auf (optional gefiltert nach Projekt)"""
    if project_id:
        url = f"{API_BASE_URL}/files/project/{project_id}"
    else:
        # Wir können nicht alle Dateien auflisten, brauchen ein Projekt
        print("Bitte gib eine Projekt-ID an")
        return []
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            files = response.json()
            print(f"\nGefundene Dateien:")
            for file in files:
                print(f"  ID: {file['id']:4d} | {file['original_filename']:40s} | "
                      f"Typ: {file['file_type']:10s} | Größe: {file.get('file_size', 'N/A')}")
            return files
        else:
            print(f"❌ Fehler beim Abrufen der Dateien: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
        return []


if __name__ == "__main__":
    print("IFC-Download Test-Skript")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\nVerwendung:")
        print(f"  python {sys.argv[0]} <file_id> [output_path]")
        print(f"  python {sys.argv[0]} --list <project_id>")
        print("\nBeispiele:")
        print(f"  python {sys.argv[0]} 1")
        print(f"  python {sys.argv[0]} 1 output.ifc")
        print(f"  python {sys.argv[0]} --list 1")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        if len(sys.argv) < 3:
            print("Bitte gib eine Projekt-ID an")
            sys.exit(1)
        project_id = int(sys.argv[2])
        list_files(project_id)
    else:
        file_id = int(sys.argv[1])
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        success = test_file_download(file_id, output_path)
        sys.exit(0 if success else 1)
