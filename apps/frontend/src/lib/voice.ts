/**
 * Voice client — manages WebSocket connection, speech recognition, and audio playback.
 *
 * Architecture:
 * - STT: Browser Web Speech API (SpeechRecognition)
 * - TTS: Amazon Polly via backend WebSocket (PCM 16-bit 16kHz)
 * - Transport: WebSocket to /v1/sessions/{id}/voice
 */

export interface VoiceCallbacks {
  onStatusChange: (status: VoiceStatus) => void;
  onTranscript: (role: 'user' | 'assistant', text: string) => void;
  onAgentTrace: (trace: Record<string, unknown>) => void;
  onError: (message: string) => void;
}

export type VoiceStatus = 'idle' | 'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking' | 'done';

export class VoiceClient {
  private ws: WebSocket | null = null;
  private recognition: any = null;
  private audioCtx: AudioContext | null = null;
  private callbacks: VoiceCallbacks;
  private sessionId: string;
  private status: VoiceStatus = 'idle';
  private audioQueue: Float32Array[] = [];
  private isPlaying = false;

  constructor(sessionId: string, callbacks: VoiceCallbacks) {
    this.sessionId = sessionId;
    this.callbacks = callbacks;
  }

  get currentStatus(): VoiceStatus {
    return this.status;
  }

  get playing(): boolean {
    return this.isPlaying;
  }

  async start(): Promise<void> {
    this.setStatus('connecting');

    // Initialize audio context
    this.audioCtx = new AudioContext({ sampleRate: 16000 });

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/v1/sessions/${this.sessionId}/voice`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.ws!.send(JSON.stringify({ type: 'start' }));
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };

    this.ws.onerror = () => {
      this.callbacks.onError('Voice connection failed');
      this.setStatus('idle');
    };

    this.ws.onclose = () => {
      this.setStatus('idle');
      this.stopRecognition();
    };
  }

  async stop(): Promise<void> {
    this.stopRecognition();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'hangup' }));
    }
    this.cleanup();
  }

  private handleMessage(msg: { type: string; [key: string]: unknown }): void {
    switch (msg.type) {
      case 'status':
        this.handleStatus(msg.state as string);
        break;
      case 'text':
        this.callbacks.onTranscript('assistant', msg.content as string);
        break;
      case 'audio':
        this.queueAudio(msg.data as string);
        break;
      case 'audio_end':
        this.playQueuedAudio();
        break;
      case 'agent_trace':
        this.callbacks.onAgentTrace(msg.data as Record<string, unknown>);
        break;
      case 'error':
        this.callbacks.onError(msg.message as string);
        break;
    }
  }

  private handleStatus(state: string): void {
    switch (state) {
      case 'ready':
        this.setStatus('ready');
        this.startRecognition();
        break;
      case 'thinking':
        this.setStatus('thinking');
        this.stopRecognition();
        break;
      case 'speaking':
        this.setStatus('speaking');
        break;
      case 'done':
        this.setStatus('done');
        this.cleanup();
        break;
    }
  }

  private startRecognition(): void {
    // Use Web Speech API
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.callbacks.onError('Speech recognition not supported in this browser. Use Chrome.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = (event: any) => {
      const lastResult = event.results[event.results.length - 1];
      if (lastResult.isFinal) {
        const text = lastResult[0].transcript.trim();
        if (text) {
          this.callbacks.onTranscript('user', text);
          this.setStatus('thinking');
          this.stopRecognition();
          // Send to backend
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'transcript', text }));
          }
        }
      }
    };

    this.recognition.onerror = (event: any) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        this.callbacks.onError(`Speech recognition error: ${event.error}`);
      }
    };

    this.recognition.onend = () => {
      // Restart recognition if we're still in ready state
      if (this.status === 'ready' || this.status === 'listening') {
        try {
          this.recognition?.start();
        } catch { /* ignore */ }
      }
    };

    try {
      this.recognition.start();
      this.setStatus('listening');
    } catch (e) {
      this.callbacks.onError('Could not start speech recognition');
    }
  }

  private stopRecognition(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch { /* ignore */ }
      this.recognition = null;
    }
  }

  private queueAudio(base64Data: string): void {
    // Decode base64 to PCM 16-bit samples
    const binaryStr = atob(base64Data);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }

    // Convert Int16 PCM to Float32
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    this.audioQueue.push(float32);
  }

  private async playQueuedAudio(): Promise<void> {
    if (!this.audioCtx || this.audioQueue.length === 0) {
      // No audio to play, go back to listening
      this.isPlaying = false;
      this.setStatus('ready');
      this.startRecognition();
      return;
    }

    this.isPlaying = true;

    // Concatenate all chunks
    const totalLength = this.audioQueue.reduce((sum, arr) => sum + arr.length, 0);
    const combined = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.audioQueue) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    this.audioQueue = [];

    // Play via AudioContext
    const buffer = this.audioCtx.createBuffer(1, combined.length, 16000);
    buffer.getChannelData(0).set(combined);

    const source = this.audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioCtx.destination);

    source.onended = () => {
      this.isPlaying = false;
      // After speaking, go back to listening
      this.setStatus('ready');
      this.startRecognition();
    };

    source.start();
  }

  private setStatus(status: VoiceStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }

  private cleanup(): void {
    this.stopRecognition();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }
    this.audioQueue = [];
    this.isPlaying = false;
  }
}
