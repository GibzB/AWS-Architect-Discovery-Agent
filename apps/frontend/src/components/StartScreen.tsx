import { useState } from 'react';
import { createSession } from '../lib/api';

interface StartScreenProps {
  onSessionCreated: (sessionId: string, customerName: string) => void;
}

export function StartScreen({ onSessionCreated }: StartScreenProps) {
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    setError('');

    try {
      const session = await createSession({
        customer_name: name.trim(),
        customer_industry: industry.trim() || undefined,
      });
      onSessionCreated(session.session_id, name.trim());
    } catch (err) {
      setError('Failed to start session. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #050B16 0%, #0D1626 55%, #172335 100%)' }}>
      <div className="w-full max-w-md">
        {/* Logo / Identity */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface mb-6 border border-border">
            <svg className="w-8 h-8 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold font-heading text-text mb-2">Atlas</h1>
          <p className="text-text-secondary text-sm">AI Solutions Architect</p>
          <p className="text-muted text-xs mt-1">Cloud Discovery Workshop</p>
        </div>

        {/* Form Card */}
        <div className="bg-surface rounded-[16px] border border-border p-8 shadow-[0_8px_30px_rgba(0,0,0,0.35)]">
          <div className="mb-6">
            <p className="text-text-secondary text-sm leading-relaxed">
              I'll guide you through a structured discovery workshop to understand your
              business objectives and design an implementation-ready cloud architecture.
            </p>
          </div>

          <form onSubmit={handleStart} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted uppercase tracking-wider mb-2">
                Organisation Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Acme Corp"
                className="w-full px-4 py-3 rounded-[10px] bg-background border border-border
                  text-text placeholder:text-disabled text-sm
                  focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
                  transition-colors duration-200"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted uppercase tracking-wider mb-2">
                Industry <span className="text-disabled">(optional)</span>
              </label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. Fintech, Healthcare, SaaS"
                className="w-full px-4 py-3 rounded-[10px] bg-background border border-border
                  text-text placeholder:text-disabled text-sm
                  focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30
                  transition-colors duration-200"
              />
            </div>

            {error && (
              <p className="text-danger text-xs">{error}</p>
            )}

            <button
              type="submit"
              disabled={!name.trim() || loading}
              className="w-full py-3 rounded-[12px] font-medium text-sm text-background
                disabled:opacity-40 disabled:cursor-not-allowed
                transition-all duration-200 hover:shadow-[0_15px_40px_rgba(255,153,0,0.12)]
                active:scale-[0.98]"
              style={{
                background: 'linear-gradient(90deg, #FF9900, #F47C20)',
              }}
            >
              {loading ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Initialising...
                </span>
              ) : (
                'Start Discovery Workshop'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-disabled text-xs mt-6">
          Powered by Amazon Bedrock · Nova Pro · AgentCore
        </p>
      </div>
    </div>
  );
}
