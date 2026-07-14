import { useState, useCallback, useRef } from 'react';
import { VoiceClient, type VoiceStatus } from '../lib/voice';

interface VoiceButtonProps {
  sessionId: string;
  onTranscript: (role: 'user' | 'assistant', text: string) => void;
}

const STATUS_CONFIG: Record<VoiceStatus, { label: string; color: string; pulse: boolean }> = {
  idle: { label: 'Start Voice', color: 'bg-surface-light', pulse: false },
  connecting: { label: 'Connecting...', color: 'bg-warning/20', pulse: true },
  ready: { label: 'Listening...', color: 'bg-success/20', pulse: true },
  listening: { label: 'Listening...', color: 'bg-success/20', pulse: true },
  thinking: { label: 'Thinking...', color: 'bg-info/20', pulse: true },
  speaking: { label: 'Speaking...', color: 'bg-primary/20', pulse: true },
  done: { label: 'Session Ended', color: 'bg-surface-light', pulse: false },
};

export function VoiceButton({ sessionId, onTranscript }: VoiceButtonProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [error, setError] = useState<string>('');
  const clientRef = useRef<VoiceClient | null>(null);

  const handleToggle = useCallback(async () => {
    if (status === 'idle' || status === 'done') {
      // Start voice session
      setError('');
      const client = new VoiceClient(sessionId, {
        onStatusChange: (s) => setStatus(s),
        onTranscript: (role, text) => onTranscript(role, text),
        onAgentTrace: () => {},
        onError: (msg) => setError(msg),
      });
      clientRef.current = client;
      await client.start();
    } else {
      // Stop voice session
      if (clientRef.current) {
        await clientRef.current.stop();
        clientRef.current = null;
      }
      setStatus('idle');
    }
  }, [status, sessionId, onTranscript]);

  const config = STATUS_CONFIG[status];
  const isActive = status !== 'idle' && status !== 'done';

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleToggle}
        className={`relative flex items-center gap-2 px-4 py-2.5 rounded-[12px] border transition-all duration-200
          ${isActive
            ? 'border-primary/30 hover:border-primary/50'
            : 'border-border hover:border-primary/30'
          } ${config.color}`}
      >
        {/* Pulse ring */}
        {config.pulse && (
          <span className="absolute inset-0 rounded-[12px] animate-ping opacity-20 border border-primary" />
        )}

        {/* Mic icon */}
        <svg
          className={`w-4 h-4 ${isActive ? 'text-primary' : 'text-muted'}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          {isActive ? (
            <>
              <rect x="9" y="2" width="6" height="11" rx="3" />
              <path d="M5 10a7 7 0 0014 0" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </>
          ) : (
            <>
              <rect x="9" y="2" width="6" height="11" rx="3" />
              <path d="M5 10a7 7 0 0014 0" />
              <line x1="12" y1="19" x2="12" y2="22" />
              <line x1="8" y1="22" x2="16" y2="22" />
            </>
          )}
        </svg>

        <span className={`text-xs font-medium ${isActive ? 'text-text' : 'text-muted'}`}>
          {config.label}
        </span>

        {/* Stop indicator */}
        {isActive && (
          <span className="w-2 h-2 rounded-sm bg-danger" />
        )}
      </button>

      {error && (
        <p className="text-[10px] text-danger">{error}</p>
      )}
    </div>
  );
}
