/**
 * Voice client — real-time bidirectional audio call.
 *
 * Protocol (mirrors vox-brief):
 * - Captures mic audio via ScriptProcessor → PCM 16-bit 16kHz → base64
 * - Sends audio chunks over WebSocket to backend
 * - Receives audio chunks back and plays them
 * - Receives transcripts for live display
 *
 * Fallback: If WebSocket fails (e.g. on Lambda), uses browser
 * SpeechRecognition + sends text via transcript_input message.
 */

const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

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
  private mediaStream: MediaStream | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private recognition: any = null;
  private callbacks: VoiceCallbacks;
  private status: VoiceStatus = 'idle';
  private nextPlayTime = 0;
  private isMuted = false;
  private scheduledSources: AudioBufferSourceNode[] = [];
  private useSTTFallback = false;

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks;
  }

  get currentStatus() { return this.status; }
  get muted() { return this.isMuted; }

  async start(): Promise<void> {
    this.setStatus('connecting');

    try {
      // Request mic access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      this.audioCtx = new AudioContext();
    } catch {
      this.callbacks.onError('Microphone access denied.');
      this.setStatus('idle');
      return;
    }

    // Determine WebSocket URL
    const wsUrl = this.getWsUrl();

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.ws!.send(JSON.stringify({ type: 'start' }));
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        this.handleMessage(msg);
      } catch { /* ignore non-JSON */ }
    };

    this.ws.onerror = () => {
      this.callbacks.onError('Voice connection error. Ensure the backend is running locally.');
      this.cleanup();
      this.setStatus('error');
    };

    this.ws.onclose = () => {
      if (this.status === 'live') {
        this.setStatus('done');
      }
      this.cleanup();
    };
  }

  toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    return this.isMuted;
  }

  hangup(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'hangup' }));
    }
    this.stopCapture();
    this.setStatus('processing');
  }

  private getWsUrl(): string {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return `ws://${window.location.host}/ws/call`;
    }
    // Production: connect to local backend (user must be running it)
    // This is for the hackathon demo
    return `ws://localhost:8000/ws/call`;
  }

  private handleMessage(msg: { type: string; [key: string]: any }): void {
    switch (msg.type) {
      case 'status':
        this.handleStatus(msg.state);
        break;
      case 'audio':
        this.playAudioChunk(msg.data);
        break;
      case 'transcript':
        this.callbacks.onTranscript(msg.role, msg.text);
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
        this.startCapture();
        // Also start STT fallback if available
        this.startSTTFallback();
        break;
      case 'processing':
        this.setStatus('processing');
        this.stopCapture();
        break;
      case 'done':
        this.setStatus('done');
        this.cleanup();
        break;
    }
  }

  // ── Audio Capture ──

  private startCapture(): void {
    if (!this.audioCtx || !this.mediaStream) return;

    const src = this.audioCtx.createMediaStreamSource(this.mediaStream);
    this.scriptProcessor = this.audioCtx.createScriptProcessor(BUFFER_SIZE, 1, 1);

    this.scriptProcessor.onaudioprocess = (e) => {
      if (this.isMuted || this.status !== 'live' || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;

      const raw = e.inputBuffer.getChannelData(0);

      // Calculate audio level for visualization
      let sum = 0;
      for (let i = 0; i < raw.length; i++) sum += raw[i] * raw[i];
      this.callbacks.onAudioLevel(Math.sqrt(sum / raw.length));

      // Downsample and send
      const ds = this.downsample(raw, this.audioCtx!.sampleRate, SAMPLE_RATE);
      const pcm = this.float32ToInt16(ds);
      const b64 = this.arrayBufferToBase64(pcm.buffer as ArrayBuffer);
      this.ws!.send(JSON.stringify({ type: 'audio', data: b64 }));
    };

    src.connect(this.scriptProcessor);
    this.scriptProcessor.connect(this.audioCtx.destination);
  }

  private stopCapture(): void {
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor.onaudioprocess = null;
      this.scriptProcessor = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
    this.stopSTTFallback();
  }

  // ── STT Fallback (sends text when audio processing isn't handled server-side) ──

  private startSTTFallback(): void {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    this.useSTTFallback = true;
    this.recognition = new SR();
    this.recognition.continuous = true;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = (event: any) => {
      const last = event.results[event.results.length - 1];
      if (last.isFinal) {
        const text = last[0].transcript.trim();
        if (text && this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'transcript_input', text }));
        }
      }
    };

    this.recognition.onend = () => {
      if (this.status === 'live' && this.useSTTFallback) {
        try { this.recognition.start(); } catch { /* ignore */ }
      }
    };

    try { this.recognition.start(); } catch { /* ignore */ }
  }

  private stopSTTFallback(): void {
    this.useSTTFallback = false;
    if (this.recognition) {
      try { this.recognition.abort(); } catch { /* ignore */ }
      this.recognition = null;
    }
  }

  // ── Audio Playback ──

  private playAudioChunk(b64: string): void {
    if (!this.audioCtx) return;

    const int16 = this.base64ToInt16Array(b64);
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
    };
  }

  // ── Utilities ──

  private downsample(buf: Float32Array, fromRate: number, toRate: number): Float32Array {
    if (fromRate === toRate) return buf;
    const ratio = fromRate / toRate;
    const out = new Float32Array(Math.floor(buf.length / ratio));
    for (let i = 0; i < out.length; i++) out[i] = buf[Math.floor(i * ratio)];
    return out;
  }

  private float32ToInt16(float32: Float32Array): Int16Array {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const x = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = x < 0 ? x * 0x8000 : x * 0x7FFF;
    }
    return int16;
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  private base64ToInt16Array(b64: string): Int16Array {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Int16Array(bytes.buffer);
  }

  private setStatus(status: VoiceStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }

  private cleanup(): void {
    this.stopCapture();
    for (const s of this.scheduledSources) {
      try { s.stop(); } catch { /* ignore */ }
    }
    this.scheduledSources = [];
    this.nextPlayTime = 0;
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
