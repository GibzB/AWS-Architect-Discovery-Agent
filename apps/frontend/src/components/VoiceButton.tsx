import { useState, useCallback, useRef } from 'react';
import { VoiceClient, type VoiceStatus } from '../lib/voice';

interface VoiceButtonProps {
  sessionId: string;
  onTranscript: (role: 'user' | 'assistant', text: string) => void;
}

export function VoiceButton({ sessionId, onTranscript }: VoiceButtonProps) {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [error, setError] = useState('');
  const [muted, setMuted] = useState(false);
  const clientRef = useRef<VoiceClient | null>(null);

  const handleStart = useCallback(async () => {
    setError('');
    const client = new VoiceClient({
      onStatusChange: (s) => setStatus(s),
      onTranscript: (role, text) => {
        const mappedRole = role === 'agent' ? 'assistant' : 'user';
        onTranscript(mappedRole as 'user' | 'assistant', text);
      },
      onAudioLevel: () => {},
      onDigest: () => {},
      onError: (msg) => setError(msg),
    });
    clientRef.current = client;
    await client.start();
  }, [sessionId, onTranscript]);

  const handleHangup = useCallback(() => {
    clientRef.current?.hangup();
  }, []);

  const handleMute = useCallback(() => {
    if (clientRef.current) {
      const newMuted = clientRef.current.toggleMute();
      setMuted(newMuted);
    }
  }, []);

  const isActive = status === 'live' || status === 'connecting';
  const isProcessing = status === 'processing';

  // Idle / Error / Done state — show start button
  if (!isActive && !isProcessing) {
    return (
      <div className="flex flex-col items-center gap-1">
        <button
          onClick={handleStart}
          className="flex items-center gap-2 px-3 py-2.5 rounded-[12px] border border-border
            bg-surface-light hover:border-primary/30 transition-all duration-200"
          title="Start voice conversation"
        >
          <svg className="w-4 h-4 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="2" width="6" height="11" rx="3" />
            <path d="M5 10a7 7 0 0014 0" />
            <line x1="12" y1="19" x2="12" y2="22" />
          </svg>
          <span className="text-xs font-medium text-muted">Voice</span>
        </button>
        {error && <p className="text-[10px] text-danger max-w-[180px] text-center">{error}</p>}
      </div>
    );
  }

  // Processing state
  if (isProcessing) {
    return (
      <div className="flex items-center gap-2 px-3 py-2.5 rounded-[12px] border border-border bg-surface-light">
        <svg className="w-4 h-4 text-primary animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <span className="text-xs font-medium text-muted">Processing...</span>
      </div>
    );
  }

  // Live / Connecting state — show mute + hangup
  return (
    <div className="flex items-center gap-2">
      {/* Mute button */}
      <button
        onClick={handleMute}
        className={`flex items-center gap-1.5 px-3 py-2.5 rounded-[12px] border transition-all duration-200 text-xs font-medium
          ${muted
            ? 'border-warning/40 bg-warning/10 text-warning'
            : 'border-border bg-surface-light text-muted hover:border-primary/30'
          }`}
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="2" width="6" height="11" rx="3" />
          <path d="M5 10a7 7 0 0014 0" />
          {muted && <line x1="3" y1="3" x2="21" y2="21" />}
        </svg>
        {muted ? 'Unmute' : 'Mute'}
      </button>

      {/* Live indicator */}
      <div className="flex items-center gap-1.5 px-2">
        <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
        <span className="text-[10px] text-success font-medium">LIVE</span>
      </div>

      {/* Hangup button */}
      <button
        onClick={handleHangup}
        className="flex items-center gap-1.5 px-3 py-2.5 rounded-[12px] border border-danger/30
          bg-danger/10 text-danger hover:bg-danger/20 transition-all duration-200 text-xs font-medium"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z"/>
        </svg>
        Hang Up
      </button>
    </div>
  );
}
