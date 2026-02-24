// Test-Version zum Debuggen
import './index.css';
import './App.css';

function App() {
  return (
    <div style={{ padding: '2rem', minHeight: '100vh', background: 'linear-gradient(135deg, #f5f5f7 0%, #ffffff 100%)' }}>
      <h1 style={{ color: '#1d1d1f', fontSize: '3rem', marginBottom: '1rem' }}>
        HLKS Planungsanalyse
      </h1>
      <p style={{ color: '#6e6e73', fontSize: '1.25rem' }}>
        Automatisierte Analyse von Planungsunterlagen
      </p>
      <div style={{ 
        marginTop: '2rem', 
        padding: '2rem', 
        background: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(20px)',
        borderRadius: '24px',
        border: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <h2 style={{ color: '#1d1d1f', marginBottom: '1rem' }}>Test</h2>
        <p style={{ color: '#6e6e73' }}>Wenn du das siehst, funktioniert React!</p>
      </div>
    </div>
  );
}

export default App;
