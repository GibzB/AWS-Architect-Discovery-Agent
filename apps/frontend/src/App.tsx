import { useState, useRef } from 'react';
import { createSession, sendMessage } from './lib/api';
import './index.css';

type AppState = 'idle' | 'connecting' | 'live' | 'processing' | 'done' | 'error';
type Scenario = 'startup' | 'sme' | 'enterprise';

interface TranscriptLine {
  role: 'agent' | 'user';
  text: string;
}

const SCENARIOS: Record<Scenario, { name: string; subtitle: string; context: string }> = {
  startup: {
    name: 'Startups / Micro',
    subtitle: 'Discover Local Gems',
    context: 'a startup or micro-business (1-10 employees, early stage, lean budget)',
  },
  sme: {
    name: 'Small & Medium Enterprises',
    subtitle: 'Fast Rising Brands',
    context: 'a small or medium enterprise (10-500 employees, growing revenue, scaling operations)',
  },
  enterprise: {
    name: 'Enterprise & Multinational',
    subtitle: 'Trusted & Established',
    context: 'a large enterprise or multinational corporation (500+ employees, complex operations, global presence)',
  },
};

function App() {
  const [state, setState] = useState<AppState>('idle');
  const [scenario, setScenario] = useState<Scenario>('startup');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [statusText, setStatusText] = useState('Choose your business category, then talk with ASA.');
  const [waveActive, setWaveActive] = useState(false);
  const [micGlow, setMicGlow] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [digest, setDigest] = useState<any>(null);

  const recognitionRef = useRef<any>(null);
  const pendingTextRef = useRef('');
  const sendTimerRef = useRef<any>(null);
  const speakingRef = useRef(false);

  // TTS via Polly
  const speak = async (text: string): Promise<void> => {
    speakingRef.current = true;
    setWaveActive(true);
    setMicGlow(false);

    try {
      const apiBase = (import.meta as any).env?.VITE_API_URL || 'https://tdj9q54rxg.execute-api.eu-west-1.amazonaws.com/v1';
      const baseUrl = apiBase.replace('/v1', '');
      const encoded = encodeURIComponent(text.slice(0, 2000));
      const response = await fetch(`${baseUrl}/v1/tts?text=${encoded}&voice=Matthew`);

      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);

        await new Promise<void>((resolve) => {
          audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
          audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
          audio.play();
        });
      }
    } catch (e) {
      // Fallback to browser TTS
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      await new Promise<void>((resolve) => {
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      });
    }

    speakingRef.current = false;
    setWaveActive(false);

    // After speaking, wait 2-3 seconds then enable mic (green glow)
    setTimeout(() => {
      if (state === 'live') {
        setMicGlow(true);
        startListening();
      }
    }, 2500);
  };

  // STT
  const startListening = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR || recognitionRef.current) return;

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      const last = event.results[event.results.length - 1];
      if (last.isFinal) {
        const text = last[0].transcript.trim();
        if (text) {
          pendingTextRef.current += (pendingTextRef.current ? ' ' : '') + text;
          // Reset 5-second timer
          if (sendTimerRef.current) clearTimeout(sendTimerRef.current);
          sendTimerRef.current = setTimeout(() => flushText(), 5000);
        }
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      // Restart if still live and not speaking
      if (state === 'live' && !speakingRef.current) {
        setTimeout(() => startListening(), 300);
      }
    };

    recognition.onerror = () => {};

    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch {}
  };

  const stopListening = () => {
    setMicGlow(false);
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }
  };

  const flushText = async () => {
    if (sendTimerRef.current) { clearTimeout(sendTimerRef.current); sendTimerRef.current = null; }
    if (!pendingTextRef.current || !sessionId) return;

    const text = pendingTextRef.current;
    pendingTextRef.current = '';

    // Stop listening while processing
    stopListening();
    setMicGlow(false);
    setState('processing');
    setStatusText('ASA is analysing your response...');
    setTranscript(prev => [...prev, { role: 'user', text }]);

    try {
      const response = await sendMessage(sessionId, text);
      setTranscript(prev => [...prev, { role: 'agent', text: response.content }]);
      setQuestionCount(prev => prev + 1);
      setState('live');
      setStatusText('ASA is responding...');
      await speak(response.content);
      setStatusText('Your turn — speak when the mic glows green.');
    } catch {
      setStatusText('Error getting response. Try again.');
      setState('live');
      setMicGlow(true);
      startListening();
    }
  };

  // Start call
  const handleStart = async () => {
    setState('connecting');
    setStatusText('Connecting to ASA...');
    setTranscript([]);
    setQuestionCount(0);
    setDigest(null);

    try {
      const session = await createSession({ customer_name: 'Voice Session' });
      setSessionId(session.session_id);

      setState('live');
      setStatusText('ASA is greeting you...');

      const greeting = `Good afternoon. I'm ASA, your Autonomous Solutions Architect. I'll guide you through today's cloud discovery workshop. My role is to understand your business objectives, identify technical constraints, evaluate risks, and work with my specialist colleagues to produce an implementation-ready architecture. I understand you're ${SCENARIOS[scenario].context}. Let's begin — tell me what your company does, who your users are, and what's driving this cloud initiative.`;

      setTranscript([{ role: 'agent', text: greeting }]);

      // Also send scenario context to backend
      await sendMessage(session.session_id, `[System context: The customer is ${SCENARIOS[scenario].context}]`);

      await speak(greeting);
      setStatusText('Your turn — speak when the mic glows green.');
    } catch {
      setState('error');
      setStatusText('Could not connect to ASA. Please try again.');
    }
  };

  // Hangup
  const handleHangup = () => {
    stopListening();
    if (sendTimerRef.current) clearTimeout(sendTimerRef.current);
    if (pendingTextRef.current) flushText();

    setState('done');
    setStatusText('Call ended. Your discovery report is being prepared.');
    setWaveActive(false);
    setMicGlow(false);

    setDigest({
      summary: `Discovery session completed with ${questionCount} exchanges. ASA gathered requirements for ${SCENARIOS[scenario].name} architecture.`,
      highlights: transcript.filter(t => t.role === 'user').map(t => t.text).slice(0, 5),
      action_items: ['Architecture design in progress', 'Report will be delivered to your email'],
    });
  };

  const isIdle = state === 'idle' || state === 'done' || state === 'error';
  const isLive = state === 'live' || state === 'connecting' || state === 'processing';

  return (
    <div className="min-h-screen bg-background text-text">
      {/* Header */}
      <header className="border-b border-border bg-surface/60 backdrop-blur">
        <div className="max-w-3xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-sm font-bold text-white">A</div>
            <span className="font-semibold text-text tracking-tight">ASA</span>
          </div>
          <span className="text-xs text-muted hidden sm:block">Autonomous Solutions Architect</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 py-8 space-y-5">
        {/* Agent Card */}
        <div className="bg-surface border border-border rounded-2xl p-8 text-center">
          {/* Waveform Avatar */}
          <div className="relative inline-flex items-center justify-center mb-6">
            {state === 'connecting' && (
              <div className="pulse-ring absolute w-24 h-24 rounded-full border-2 border-brand-500" />
            )}
            <div className={`w-20 h-20 rounded-full bg-background border-2 flex items-center justify-center transition-all duration-300
              ${micGlow ? 'mic-active border-success' : 'border-border'}`}>
              <div className={`waveform ${waveActive ? 'active' : ''}`}>
                {[...Array(7)].map((_, i) => <div key={i} className="waveform-bar" />)}
              </div>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-text">ASA</h2>
          <p className="text-muted text-sm mt-0.5 mb-6">Solutions Architect Discovery</p>

          {/* Status */}
          <p className="text-sm text-text-secondary mb-6">{statusText}</p>

          {/* Scenario Picker (idle) */}
          {isIdle && !digest && (
            <div className="grid grid-cols-3 gap-3 mb-6 text-left">
              {(Object.entries(SCENARIOS) as [Scenario, typeof SCENARIOS[Scenario]][]).map(([key, val]) => (
                <button
                  key={key}
                  onClick={() => setScenario(key)}
                  className={`scenario-card flex flex-col gap-1 p-3 rounded-xl border-2 transition-all text-left
                    ${scenario === key ? 'selected' : ''}`}
                >
                  <span className="text-xs font-bold tracking-wide text-text">{val.name}</span>
                  <span className="text-xs text-muted opacity-60">{val.subtitle}</span>
                </button>
              ))}
            </div>
          )}

          {/* Start Button (idle) */}
          {isIdle && !digest && (
            <button
              onClick={handleStart}
              className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-500 active:scale-95
                text-white font-medium px-8 py-3 rounded-full transition-all shadow-lg shadow-brand-900/40"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z"/>
              </svg>
              Talk with Agent
            </button>
          )}

          {/* In-call controls */}
          {isLive && (
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={handleHangup}
                className="flex items-center gap-2 bg-danger/20 hover:bg-danger/30 text-danger text-sm px-5 py-2.5 rounded-full border border-danger/30 transition-all"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z"/>
                </svg>
                Hang Up
              </button>
              {/* Question counter */}
              <div className="text-xs text-muted bg-background px-3 py-1.5 rounded-full border border-border">
                Q{questionCount + 1}
              </div>
            </div>
          )}

          {/* Call ended */}
          {state === 'done' && !digest && (
            <div className="inline-flex items-center gap-2 text-muted text-sm px-5 py-2.5 rounded-full border border-border bg-surface-light">
              <svg className="w-4 h-4 text-success" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              Call ended — preparing your digest
            </div>
          )}
        </div>

        {/* Transcript Card */}
        {transcript.length > 0 && (
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border flex items-center justify-between">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">Live Transcript</span>
              {isLive && <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />}
            </div>
            <div className="p-5 space-y-3 max-h-72 overflow-y-auto text-sm">
              {transcript.map((line, i) => (
                <div key={i} className="flex gap-2">
                  <span className={`font-medium shrink-0 w-10 text-right ${line.role === 'agent' ? 'transcript-agent' : 'transcript-user'}`}>
                    {line.role === 'agent' ? 'ASA' : 'You'}
                  </span>
                  <span className="transcript-text leading-snug">{line.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Digest Card */}
        {digest && (
          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-2xl p-6">
              <h3 className="text-base font-semibold text-text mb-3">Call Summary</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{digest.summary}</p>
            </div>

            {digest.highlights?.length > 0 && (
              <div className="bg-surface border border-border rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-3">Key Points Gathered</h3>
                <ul className="space-y-2 text-sm text-text-secondary">
                  {digest.highlights.map((h: string, i: number) => (
                    <li key={i} className="flex gap-2"><span className="text-primary shrink-0">✦</span>{h}</li>
                  ))}
                </ul>
              </div>
            )}

            {digest.action_items?.length > 0 && (
              <div className="bg-surface border border-border rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-warning uppercase tracking-wider mb-3">Next Steps</h3>
                <ul className="space-y-2 text-sm text-text-secondary">
                  {digest.action_items.map((a: string, i: number) => (
                    <li key={i} className="flex gap-2"><span className="text-warning shrink-0">→</span>{a}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="text-center pt-2">
              <button
                onClick={() => { setState('idle'); setDigest(null); setTranscript([]); }}
                className="inline-flex items-center gap-2 bg-surface-light hover:bg-border text-text-secondary text-sm px-6 py-2.5 rounded-full border border-border transition-all"
              >
                Start a new session
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
