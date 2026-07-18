import { useState, useRef, useCallback } from 'react';
import { createSession, sendMessage } from './lib/api';
import './index.css';

type AppState = 'idle' | 'connecting' | 'live' | 'processing' | 'done' | 'error';
type Scenario = 'startup' | 'sme' | 'enterprise';

interface TranscriptLine {
  role: 'agent' | 'user';
  text: string;
}

const SCENARIOS: Record<Scenario, { name: string; subtitle: string; context: string; greeting: string }> = {
  startup: {
    name: 'Startups / Micro',
    subtitle: 'Discover Local Gems',
    context: 'a startup or micro-business with a lean team and early-stage product',
    greeting: "Hi there! I'm ASA. I work with startups like yours to design cloud architectures that scale without breaking the bank. Tell me — what does your company do and what are you building?",
  },
  sme: {
    name: 'SMEs',
    subtitle: 'Fast Rising Brands',
    context: 'a growing SME scaling operations with an established product and expanding team',
    greeting: "Hello! I'm ASA, your solutions architect. I help growing businesses design scalable, secure cloud platforms. Tell me about your company — what do you do, how big is the team, and what's driving your move to cloud?",
  },
  enterprise: {
    name: 'Enterprise',
    subtitle: 'Trusted & Established',
    context: 'a large enterprise or multinational with complex operations and strict compliance needs',
    greeting: "Good afternoon. I'm ASA, your solutions architect. I specialise in enterprise cloud transformations with a focus on compliance, resilience, and scalability. Tell me about your organisation and what's driving this initiative.",
  },
};

function App() {
  const [state, setState] = useState<AppState>('idle');
  const [scenario, setScenario] = useState<Scenario>('startup');
  const [, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [statusText, setStatusText] = useState('Choose your business category, then talk with ASA.');
  const [waveActive, setWaveActive] = useState(false);
  const [micGlow, setMicGlow] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const [digest, setDigest] = useState<any>(null);
  const [pendingDisplay, setPendingDisplay] = useState('');
  const [chatInput, setChatInput] = useState('');

  const stateRef = useRef<AppState>('idle');
  const sessionRef = useRef<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const pendingTextRef = useRef('');
  const speakingRef = useRef(false);

  const updateState = (s: AppState) => { stateRef.current = s; setState(s); };

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch TTS audio from Polly (returns prepared HTMLAudioElement or falls back to browser TTS)
  const fetchTTS = useCallback(async (text: string): Promise<HTMLAudioElement | 'browser-fallback'> => {
    try {
      const apiBase = (import.meta as any).env?.VITE_API_URL || 'https://tdj9q54rxg.execute-api.eu-west-1.amazonaws.com/v1';
      const baseUrl = apiBase.replace('/v1', '');
      const encoded = encodeURIComponent(text.slice(0, 2000));
      const response = await fetch(`${baseUrl}/v1/tts?text=${encoded}&voice=Matthew`);

      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        // Store the object URL on the element for cleanup
        (audio as any)._objectUrl = url;
        return audio;
      } else {
        return 'browser-fallback';
      }
    } catch {
      return 'browser-fallback';
    }
  }, []);

  // Play a prepared audio element (or browser fallback)
  const playAudio = useCallback(async (audio: HTMLAudioElement | 'browser-fallback', text: string): Promise<void> => {
    speakingRef.current = true;
    setWaveActive(true);
    setMicGlow(false);
    setStatusText('ASA is speaking...');

    if (audio !== 'browser-fallback' && stateRef.current === 'live') {
      const url = (audio as any)._objectUrl as string | undefined;
      audioRef.current = audio;
      await new Promise<void>((resolve) => {
        audio.onended = () => { if (url) URL.revokeObjectURL(url); audioRef.current = null; resolve(); };
        audio.onerror = () => { if (url) URL.revokeObjectURL(url); audioRef.current = null; resolve(); };
        if (stateRef.current !== 'live') { if (url) URL.revokeObjectURL(url); audioRef.current = null; resolve(); return; }
        audio.play().catch(() => { if (url) URL.revokeObjectURL(url); audioRef.current = null; resolve(); });
      });
    } else if (stateRef.current === 'live') {
      // Browser speechSynthesis fallback
      await new Promise<void>((resolve) => {
        const u = new SpeechSynthesisUtterance(text);
        u.rate = 1.0;
        u.onend = () => resolve();
        u.onerror = () => resolve();
        window.speechSynthesis.speak(u);
      });
    }

    speakingRef.current = false;
    setWaveActive(false);
    audioRef.current = null;

    // 3 second pause then enable mic (only if still live)
    if (stateRef.current === 'live') {
      setStatusText('Get ready to speak...');
      setTimeout(() => {
        if (stateRef.current === 'live' && !speakingRef.current) {
          setMicGlow(true);
          setStatusText('Speak now — mic is active.');
          startListening();
        }
      }, 3000);
    }
  }, []);

  const lastSpeechTimeRef = useRef<number>(0);
  const silenceCheckRef = useRef<any>(null);

  // STT
  const startListening = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setStatusText('Speech recognition requires Chrome browser.');
      return;
    }
    if (recognitionRef.current) return;

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      // ANY result (interim or final) means user is still talking
      lastSpeechTimeRef.current = Date.now();

      let interim = '';
      let finalText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += t + ' ';
        } else {
          interim += t;
        }
      }

      // Show what user is saying in real-time
      if (interim) {
        setPendingDisplay(pendingTextRef.current + ' ' + interim);
      }

      if (finalText.trim()) {
        pendingTextRef.current += (pendingTextRef.current ? ' ' : '') + finalText.trim();
        setPendingDisplay(pendingTextRef.current);
      }

      // Start/restart the silence checker (polls every 500ms)
      if (!silenceCheckRef.current) {
        silenceCheckRef.current = setInterval(() => {
          const silenceMs = Date.now() - lastSpeechTimeRef.current;
          if (silenceMs >= 5000 && pendingTextRef.current) {
            // 5 seconds of silence — user is done talking
            clearInterval(silenceCheckRef.current);
            silenceCheckRef.current = null;
            flushText();
          }
        }, 500);
      }
    };

    recognition.onend = () => {
      recognitionRef.current = null;
      // If there's pending text and recognition ended (e.g. network timeout),
      // wait the full 5 seconds of silence before flushing
      if (stateRef.current === 'live' && !speakingRef.current) {
        setTimeout(() => startListening(), 300);
      }
    };

    recognition.onerror = () => {};

    try {
      recognition.start();
      recognitionRef.current = recognition;
      lastSpeechTimeRef.current = Date.now(); // reset on start
    } catch {}
  }, []);

  const stopListening = useCallback(() => {
    setMicGlow(false);
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
      recognitionRef.current = null;
    }
    if (silenceCheckRef.current) {
      clearInterval(silenceCheckRef.current);
      silenceCheckRef.current = null;
    }
  }, []);

  const flushText = useCallback(async () => {
    if (silenceCheckRef.current) { clearInterval(silenceCheckRef.current); silenceCheckRef.current = null; }
    if (!pendingTextRef.current || !sessionRef.current) return;

    const text = pendingTextRef.current;
    pendingTextRef.current = '';
    setPendingDisplay('');

    stopListening();
    setMicGlow(false);
    updateState('processing');
    setStatusText('ASA is thinking...');
    setTranscript(prev => [...prev, { role: 'user', text }]);

    try {
      const response = await sendMessage(sessionRef.current, text);
      // Start TTS fetch immediately, before updating UI
      const audioPromise = fetchTTS(response.content);
      setTranscript(prev => [...prev, { role: 'agent', text: response.content }]);
      setQuestionCount(prev => prev + 1);
      updateState('live');
      // Audio should be ready (or nearly ready) by now
      const audio = await audioPromise;
      await playAudio(audio, response.content);
    } catch {
      setStatusText('Connection error. Try speaking again.');
      updateState('live');
      setMicGlow(true);
      startListening();
    }
  }, [fetchTTS, playAudio, stopListening, startListening]);

  // Send text message via chat input
  const handleChatSend = async () => {
    const text = chatInput.trim();
    if (!text || !sessionRef.current) return;

    setChatInput('');
    stopListening();
    setMicGlow(false);
    updateState('processing');
    setStatusText('ASA is thinking...');
    setTranscript(prev => [...prev, { role: 'user', text }]);

    try {
      const response = await sendMessage(sessionRef.current, text);
      const audioPromise = fetchTTS(response.content);
      setTranscript(prev => [...prev, { role: 'agent', text: response.content }]);
      setQuestionCount(prev => prev + 1);
      updateState('live');
      const audio = await audioPromise;
      await playAudio(audio, response.content);
    } catch {
      setStatusText('Connection error. Try again.');
      updateState('live');
      setMicGlow(true);
      startListening();
    }
  };

  // Start call
  const handleStart = async () => {
    updateState('connecting');
    setStatusText('Connecting to ASA...');
    setTranscript([]);
    setQuestionCount(0);
    setDigest(null);
    setPendingDisplay('');

    try {
      const session = await createSession({ customer_name: 'Voice Session' });
      setSessionId(session.session_id);
      sessionRef.current = session.session_id;

      updateState('live');

      const greeting = SCENARIOS[scenario].greeting;

      // Start TTS fetch immediately (in parallel with typewriter)
      const audioPromise = fetchTTS(greeting);

      // Typewriter effect — populate text as audio loads
      setTranscript([{ role: 'agent', text: '' }]);
      const words = greeting.split(' ');
      const wordDelay = Math.min(150, 2500 / words.length); // spread across ~2.5s
      for (let i = 0; i < words.length; i++) {
        if (stateRef.current !== 'live') break;
        await new Promise(r => setTimeout(r, wordDelay));
        setTranscript([{ role: 'agent', text: words.slice(0, i + 1).join(' ') }]);
      }

      // Send scenario context silently to backend
      await sendMessage(session.session_id, `[Context: The customer is ${SCENARIOS[scenario].context}. Tailor questions accordingly.]`);

      // Audio should be fetched by now — play immediately
      const audio = await audioPromise;
      await playAudio(audio, greeting);
    } catch {
      updateState('error');
      setStatusText('Could not connect to ASA. Please try again.');
    }
  };

  // Hangup — immediately stop everything and go back to start
  const handleHangup = () => {
    // Stop all audio immediately
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    window.speechSynthesis.cancel();
    speakingRef.current = false;

    stopListening();
    pendingTextRef.current = '';
    setPendingDisplay('');
    setWaveActive(false);
    setMicGlow(false);

    // Reset to idle immediately
    updateState('idle');
    setStatusText('Choose your business category, then talk with ASA.');
    setTranscript([]);
    setQuestionCount(0);
    setDigest(null);
  };

  const isIdle = state === 'idle' || state === 'error' || state === 'done';
  const isLive = state === 'live' || state === 'connecting' || state === 'processing';

  return (
    <div className="min-h-screen bg-background text-text">
      {/* Header */}
      <header className="border-b border-border bg-surface/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-sm font-bold text-white">A</div>
            <span className="font-semibold text-text tracking-tight">ASA</span>
            {sessionRef.current && (
              <span className="text-[10px] text-disabled font-mono ml-2">
                {sessionRef.current.slice(0, 8)}
              </span>
            )}
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
            <div className={`w-20 h-20 rounded-full bg-background border-2 flex items-center justify-center transition-all duration-500
              ${micGlow ? 'mic-active border-success' : 'border-border'}`}>
              <div className={`waveform ${waveActive ? 'active' : ''}`}>
                {[...Array(7)].map((_, i) => <div key={i} className="waveform-bar" />)}
              </div>
            </div>
          </div>

          <h2 className="text-lg font-semibold text-text">ASA</h2>
          <p className="text-muted text-sm mt-0.5 mb-4">Solutions Architect Discovery</p>

          {/* Status */}
          <p className="text-sm text-text-secondary mb-6">{statusText}</p>

          {/* Pending speech display (shows what user is saying) */}
          {pendingDisplay && isLive && (
            <div className="mb-4 px-4 py-2 bg-info/10 border border-info/20 rounded-xl text-sm text-info text-left">
              <span className="text-[10px] text-info/60 uppercase font-medium">You're saying:</span>
              <p className="mt-1">{pendingDisplay}</p>
            </div>
          )}

          {/* Scenario Picker (idle only) */}
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

          {/* Start Button */}
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
              <div className="text-xs text-muted bg-background px-3 py-1.5 rounded-full border border-border">
                Q{questionCount + 1}
              </div>
            </div>
          )}

          {/* Done state with no digest yet */}
          {state === 'done' && !digest && (
            <div className="inline-flex items-center gap-2 text-muted text-sm px-5 py-2.5 rounded-full border border-border bg-surface-light">
              <svg className="w-4 h-4 text-success" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              Preparing your digest...
            </div>
          )}
        </div>

        {/* Transcript */}
        {transcript.length > 0 && (
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border flex items-center justify-between">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">Transcript</span>
              {isLive && <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />}
            </div>
            <div className="p-5 space-y-3 max-h-80 overflow-y-auto text-sm">
              {transcript.map((line, i) => (
                <div key={i} className="flex gap-3">
                  <span className={`font-medium shrink-0 w-8 text-right text-[11px] uppercase mt-0.5
                    ${line.role === 'agent' ? 'text-primary' : 'text-info'}`}>
                    {line.role === 'agent' ? 'ASA' : 'You'}
                  </span>
                  <span className="text-text-secondary leading-relaxed">{line.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chat text input — available during call */}
        {isLive && (
          <div className="bg-surface border border-border rounded-2xl p-4">
            <div className="flex gap-3 items-end">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleChatSend(); } }}
                placeholder="Or type your response here..."
                className="flex-1 px-4 py-2.5 rounded-xl bg-background border border-border text-text text-sm
                  placeholder:text-disabled focus:outline-none focus:border-primary/40 transition-colors"
                disabled={state === 'processing'}
              />
              <button
                onClick={handleChatSend}
                disabled={!chatInput.trim() || state === 'processing'}
                className="px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-medium
                  disabled:opacity-30 disabled:cursor-not-allowed hover:bg-brand-500 active:scale-95 transition-all"
              >
                Send
              </button>
            </div>
          </div>
        )}

        {/* Digest */}
        {digest && (
          <div className="space-y-4">
            <div className="bg-surface border border-border rounded-2xl p-6">
              <h3 className="text-base font-semibold text-text mb-3">Session Summary</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{digest.summary}</p>
            </div>

            {digest.highlights?.length > 0 && (
              <div className="bg-surface border border-border rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-primary uppercase tracking-wider mb-3">What We Gathered</h3>
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
                onClick={() => { updateState('idle'); setDigest(null); setTranscript([]); setPendingDisplay(''); }}
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
