# Frontend Debugging - Weiße Seite

## ✅ Was wurde gemacht

1. **TypeScript-Fehler behoben**:
   - Type-Imports korrigiert
   - Ungenutzte Variablen entfernt
   - Build funktioniert jetzt

2. **Backend gestartet**: Läuft auf Port 8000

3. **Fehlerbehandlung verbessert**: App zeigt jetzt auch ohne Backend etwas an

## 🔍 Debugging-Schritte

### Schritt 1: Browser-Konsole prüfen
1. Öffne http://localhost:3000
2. Drücke **F12** (Entwicklertools)
3. Gehe zum Tab **Console**
4. Prüfe auf rote Fehlermeldungen

### Schritt 2: Network-Tab prüfen
1. Im Entwicklertools zum Tab **Network**
2. Lade die Seite neu (F5)
3. Prüfe ob alle Dateien geladen werden:
   - `main.tsx`
   - `index.css`
   - `App.css`
   - `FileUpload.css`

### Schritt 3: Hard Refresh
- **Windows/Linux**: `Ctrl + Shift + R` oder `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`

### Schritt 4: Cache leeren
1. Entwicklertools öffnen (F12)
2. Rechtsklick auf Reload-Button
3. "Empty Cache and Hard Reload" wählen

## 🐛 Häufige Probleme

### Problem 1: "Cannot find module"
**Lösung**: Stelle sicher, dass alle Dateien vorhanden sind:
- `src/components/FileUpload.tsx`
- `src/services/api.ts`
- `src/App.tsx`
- `src/index.css`

### Problem 2: CORS-Fehler
**Lösung**: Backend muss laufen und CORS muss konfiguriert sein (ist bereits gemacht)

### Problem 3: React rendert nicht
**Lösung**: Prüfe ob `main.tsx` korrekt ist und `#root` Element existiert

## 🔧 Manuelle Prüfung

Öffne die Browser-Konsole und führe aus:
```javascript
// Prüfe ob React geladen ist
console.log(window.React);

// Prüfe ob root-Element existiert
console.log(document.getElementById('root'));

// Prüfe ob Backend erreichbar ist
fetch('http://localhost:8000/')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

## 📝 Nächste Schritte

1. Öffne http://localhost:3000
2. Öffne Entwicklertools (F12)
3. Prüfe Console auf Fehler
4. Teile die Fehlermeldungen mit mir

## ✅ Erwartetes Verhalten

Wenn alles funktioniert, solltest du sehen:
- Titel: "HLKS Planungsanalyse"
- Untertitel: "Automatisierte Analyse von Planungsunterlagen"
- Upload-Bereich mit Glassmorphism-Effekt
- Projektname-Eingabefeld
