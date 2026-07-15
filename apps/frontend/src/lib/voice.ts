/**
 * Voice client — WebSocket + Polly TTS + Browser STT.
 *
 * Flow:
 * 1. Connect WebSocket to /ws/call
 * 2. Server sends greeting audio (Polly)
 * 3. After audio finishes, browser STT starts listening
 * 4. User speaks → 5 second silence → accumulated text sent to server
 * 5. Server processes through agent pipeline → sends response audio
 * 6. Repeat until hangup
 *
 * Turn-taking:
 * - STT pauses while server audio is playing
 * - 5-second debounce ensures user can finish their thought
 * - STT resumes after last audio chunk finishes playing
 */

const SAMPLE_RATE = 16000;

export type VoiceStatus = 'idle' | 'connecting' | 'live' | 'processing' | 'done' | 'error';

export interface VoiceCallbacks {
  onStatusChange: (status: VoiceStatus) => void;
  onTranscript: (role: 'user' | 'agent', text: string) => void;
  onAudioLevel: (level: number) => void;
  onDigest: (data: any) => void;
  onError: (message: string) => void;
}

export class VoiceClient {
  private ws: WebSocket | null = null;
  private audioCtx: AudioContext | null = null;
  private recognition: any = null;
  private callbacks: VoiceCallbacks;
  private status: VoiceStatus = 'idle';
  private nextPlayTime = 0;
  private isMuted = false;
  private scheduledSources: AudioBufferSourceNode[] = [];
  private pendingText = '';
  private sendTimer: any = null;
  private isPlaying = false;

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks;
  }

  get currentStatus() { return this.status; }
  get muted() { return this.isMuted; }

  async start(): Promise<void> {
    this.setStatus('connecting');

    this.audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });

    const wsUrl = this.getWsUrl();
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.ws!.send(JSON.stringify({ type: 'start' }));
    };

    this.ws.onmessage = (ev) => {
      try {
        this.handleMessage(JSON.parse(ev.data));
      } catch { /* ignore */ }
    };

    this.ws.onerror = () => {
      // If WebSocket fails (e.g. on Amplify/Lambda), show helpful message
      const isRemote = !['localhost', '127.0.0.1'].includes(window.location.hostname);
      if (isRemote) {
        this.callbacks.onError('Voice requires the local backend. Run: make backend');
      } else {
        this.callbacks.onError('Voice connection failed. Is the backend running?');
      }
      this.cleanup();
      this.setStatus('error');
    };

    this.ws.onclose = () => {
      if (this.status === 'live') this.setStatus('done');
      this.cleanup();
    };
  }

  toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stopSTT();
    } else if (!this.isPlaying) {
      this.startSTT();
    }
    return this.isMuted;
  }

  hangup(): void {
    this.clearAudioQueue();
    this.stopSTT();
    // Send any pending text first
    this.flushPendingText();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'hangup' }));
    }
    this.setStatus('processing');
  }

  // ── Message Handler ──

  private handleMessage(msg: { type: string; [key: string]: any }): void {
    switch (msg.type) {
      case 'status':
        this.handleStatus(msg.state);
        break;
      case 'audio':
        this.isPlaying = true;
        this.stopSTT(); // Don't listen while ASA speaks
        this.playAudioChunk(msg.data);
        break;
      case 'transcript':
        this.callbacks.onTranscript(msg.role, msg.text);
        if (msg.role === 'agent') {
          // After agent transcript, audio will follow then STT resumes
        }
        break;
      case 'digest':
        this.callbacks.onDigest(msg.data);
        this.setStatus('done');
        break;
      case 'error':
        this.callbacks.onError(msg.message);
        this.setStatus('error');
        break;
    }
  }

  private handleStatus(state: string): void {
    switch (state) {
      case 'connecting':
        this.setStatus('connecting');
        break;
      case 'live':
        this.setStatus('live');
        // STT will start after greeting audio finishes
        break;
      case 'processing':
        this.setStatus('processing');
        this.stopSTT();
        break;
      case 'done':
        this.setStatus('done');
        this.cleanup();
        break;
    }
  }

  // ── STT (Browser Speech Recognition) ──

  private startSTT(): void {
    if (this.isMuted || this.isPlaying) return;

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      this.callbacks.onError('Speech recognition not supported. Use Chrome.');
      return;
    }

    if (this.recognition) return; // Already running

    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = (event: any) => {
      const last = event.results[event.results.length - 1];
      if (last.isFinal) {
        const text = last[0].transcript.trim();
        if (text) {
          this.pendingText += (this.pendingText ? ' ' : '') + text;
          // Reset 5-second timer
          if (this.sendTimer) clearTimeout(this.sendTimer);
          this.sendTimer = setTimeout(() => this.flushPendingText(), 5000);
        }
      }
    };

    this.recognition.onerror = (event: any) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        console.warn('STT error:', event.error);
      }
    };

    this.recognition.onend = () => {
      this.recognition = null;
      // Restart if we should still be listening
      if (this.status === 'live' && !this.isMuted && !this.isPlaying) {
        setTimeout(() => this.startSTT(), 300);
      }
    };

    try {
      this.recognition.start();
    } catch { /* ignore - might already be started */ }
  }

  private stopSTT(): void {
    if (this.recognition) {
      try { this.recognition.abort(); } catch { /* ignore */ }
      this.recognition = null;
    }
  }

  private flushPendingText(): void {
    if (this.sendTimer) { clearTimeout(this.sendTimer); this.sendTimer = null; }
    if (this.pendingText && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'transcript_input', text: this.pendingText }));
      this.pendingText = '';
    }
  }

  // ── Audio Playback ──

  private playAudioChunk(b64: string): void {
    if (!this.audioCtx) return;

    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768.0;

    const buffer = this.audioCtx.createBuffer(1, float32.length, SAMPLE_RATE);
    buffer.copyToChannel(float32, 0);

    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);

    const now = this.audioCtx.currentTime;
    if (this.nextPlayTime < now) this.nextPlayTime = now + 0.05;
    source.start(this.nextPlayTime);
    this.nextPlayTime += buffer.duration;

    this.scheduledSources.push(source);
    source.onended = () => {
      this.scheduledSources = this.scheduledSources.filter(s => s !== source);
      // When all audio finished playing, resume STT
      if (this.scheduledSources.length === 0) {
        this.isPlaying = false;
        // Wait 1 second after audio ends before listening
        setTimeout(() => {
          if (this.status === 'live' && !this.isMuted) {
            this.startSTT();
          }
        }, 1000);
      }
    };
  }

  private clearAudioQueue(): void {
    for (const s of this.scheduledSources) {
      try { s.stop(); } catch { /* ignore */ }
    }
    this.scheduledSources = [];
    this.nextPlayTime = 0;
    this.isPlaying = false;
  }

  // ── Utilities ──

  private getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/call`;
  }

  private setStatus(status: VoiceStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }

  private cleanup(): void {
    this.stopSTT();
    this.clearAudioQueue();
    if (this.sendTimer) { clearTimeout(this.sendTimer); this.sendTimer = null; }
    if (this.audioCtx) { this.audioCtx.close(); this.audioCtx = null; }
    if (this.ws) { this.ws.close(); this.ws = null; }
    this.pendingText = '';
  }
}
