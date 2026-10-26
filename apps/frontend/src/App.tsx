import { useState, useEffect } from 'react';
import { Workshop } from './components/Workshop';
import { createSession } from './lib/api';
import './index.css';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Auto-create session on mount
  useEffect(() => {
    const init = async () => {
      try {
        const session = await createSession({
          customer_name: 'Discovery Session',
        });
        setSessionId(session.session_id);
      } catch {
        setError('Could not connect to ASA. Is the backend running?');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-surface border border-border mb-4">
            <svg className="w-7 h-7 text-primary animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm">Connecting to ASA...</p>
        </div>
      </div>
    );
  }

  if (error || !sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-sm">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-surface border border-border mb-4">
            <svg className="w-7 h-7 text-danger" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <p className="text-text-secondary text-sm mb-4">{error || 'Something went wrong'}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-[12px] text-sm font-medium text-background"
            style={{ background: 'linear-gradient(90deg, #FF9900, #F47C20)' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <Workshop
      sessionId={sessionId}
      onReset={() => window.location.reload()}
    />
  );
}

export default App;
