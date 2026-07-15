import { useState, useCallback, useRef } from 'react';
import { VoiceClient, type VoiceStatus } from '../lib/voice';

interface VoiceButtonProps {
  sessionId: string;
  onTranscript: (role: 'user' | 'assistant', text: string) => void;
}

const STATUS_CONFIG: Record<VoiceStatus, { label: string; pulse: boolean }> = {
  idle: { label: 'Voice', pulse: false },
  connecting: { label: 'Starting...', pulse: true },
  ready: { label: 'Ready', pulse: false },
  listening: { label: 'Listening...', pulse: true },
  thinking: { label: 'Thinking...', pulse: true },
  speaking: { label: 'Speaking...', pulse: true },
  done: { label: 'Done', pulse: false },
};

export function VoiceButton({ sessionId, onTranscript }: VoiceButtonProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [error, setError] = useState('');
  const clientRef = useRef<VoiceClient | null>(null);

  const handleToggle = useCallback(async () => {
    if (status === 'idle' || status === 'done') {
      setError('');
      const client = new VoiceClient(sessionId, {
        onStatusChange: (s) => setStatus(s),
        onTranscript: (role, text) => onTranscript(role, text),
        onError: (msg) => setError(msg),
      });
      clientRef.current = client;
      await client.start();
    } else {
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
    <div className="flex flex-col items-center gap-1">
      <button
        onClick={handleToggle}
        className={`relative flex items-center gap-2 px-3 py-2.5 rounded-[12px] border transition-all duration-200
          ${isActive
            ? 'border-primary/40 bg-primary/10'
            : 'border-border bg-surface-light hover:border-primary/30'
          }`}
        title={isActive ? 'Stop voice' : 'Start voice conversation'}
      >
        {/* Pulse ring */}
        {config.pulse && (
          <span className="absolute inset-0 rounded-[12px] animate-ping opacity-15 border border-primary" />
        )}

        {/* Mic icon */}
        <svg
          className={`w-4 h-4 ${isActive ? 'text-primary' : 'text-muted'}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0014 0" />
          <line x1="12" y1="19" x2="12" y2="22" />
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
        <p className="text-[10px] text-danger max-w-[150px] text-center">{error}</p>
      )}
    </div>
  );
}
