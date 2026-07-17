/**
 * Voice client — REST API + Browser Speech Synthesis + Browser Speech Recognition.
 *
 * Works entirely over HTTPS (no WebSocket needed):
 * - STT: Browser SpeechRecognition API (Chrome)
 * - Messages: Same REST API as chat (/v1/sessions/{id}/messages)
 * - TTS: Browser SpeechSynthesis API
 *
 * Turn-taking:
 * - User speaks → 5 second silence → text sent to API
 * - ASA responds → browser speaks the response
 * - After speech ends → listen again
 */

import { sendMessage, createSession } from './api';

export type VoiceStatus = 'idle' | 'connecting' | 'live' | 'processing' | 'done' | 'error';

export interface VoiceCallbacks {
  onStatusChange: (status: VoiceStatus) => void;
  onTranscript: (role: 'user' | 'agent', text: string) => void;
  onAudioLevel: (level: number) => void;
  onDigest: (data: any) => void;
  onError: (message: string) => void;
}

export class VoiceClient {
  private recognition: any = null;
  private callbacks: VoiceCallbacks;
  private status: VoiceStatus = 'idle';
  private isMuted = false;
  private sessionId: string | null = null;
  private pendingText = '';
  private sendTimer: any = null;
  private speaking = false;

  constructor(callbacks: VoiceCallbacks) {
    this.callbacks = callbacks;
  }

  get currentStatus() { return this.status; }
  get muted() { return this.isMuted; }

  async start(): Promise<void> {
    this.setStatus('connecting');

    // Create a session for this voice call
    try {
      const session = await createSession({ customer_name: 'Voice Session' });
      this.sessionId = session.session_id;
    } catch {
      this.callbacks.onError('Cannot connect to ASA backend.');
      this.setStatus('error');
      return;
    }

    this.setStatus('live');

    // Speak greeting
    const greeting = "Hello, I'm ASA, your Autonomous Solutions Architect. Tell me about your organisation and what's driving this cloud initiative.";
    this.callbacks.onTranscript('agent', greeting);
    await this.speak(greeting);

    // Start listening
    this.startSTT();
  }

  toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (this.isMuted) {
      this.stopSTT();
    } else if (!this.speaking) {
      this.startSTT();
    }
    return this.isMuted;
  }

  hangup(): void {
    this.stopSTT();
    this.flushPendingText();
    window.speechSynthesis.cancel();
    this.setStatus('done');
    this.callbacks.onDigest({ summary: 'Voice session ended.' });
  }

  // ── Speech-to-Text ──

  private startSTT(): void {
    if (this.isMuted || this.speaking) return;

    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      this.callbacks.onError('Speech recognition requires Chrome.');
      return;
    }
    if (this.recognition) return;

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
          // 3 second debounce — fast enough to feel responsive, long enough for pauses
          if (this.sendTimer) clearTimeout(this.sendTimer);
          this.sendTimer = setTimeout(() => this.flushPendingText(), 3000);
        }
      }
    };

    this.recognition.onerror = (e: any) => {
      if (e.error !== 'no-speech' && e.error !== 'aborted') {
        console.warn('STT error:', e.error);
      }
    };

    this.recognition.onend = () => {
      this.recognition = null;
      if (this.status === 'live' && !this.isMuted && !this.speaking) {
        setTimeout(() => this.startSTT(), 300);
      }
    };

    try { this.recognition.start(); } catch { /* already started */ }
  }

  private stopSTT(): void {
    if (this.recognition) {
      try { this.recognition.abort(); } catch {}
      this.recognition = null;
    }
  }

  private async flushPendingText(): Promise<void> {
    if (this.sendTimer) { clearTimeout(this.sendTimer); this.sendTimer = null; }
    if (!this.pendingText || !this.sessionId) return;

    const text = this.pendingText;
    this.pendingText = '';

    this.callbacks.onTranscript('user', text);
    this.stopSTT();
    this.setStatus('processing');

    try {
      const response = await sendMessage(this.sessionId, text);
      this.callbacks.onTranscript('agent', response.content);
      this.setStatus('live');
      await this.speak(response.content);
      // Resume listening after speaking
      this.startSTT();
    } catch {
      this.callbacks.onError('Failed to get response.');
      this.setStatus('live');
      this.startSTT();
    }
  }

  // ── Text-to-Speech (Amazon Polly via backend) ──

  private speak(text: string): Promise<void> {
    return new Promise(async (resolve) => {
      this.speaking = true;
      this.stopSTT();

      try {
        // Call Polly TTS endpoint — returns MP3 audio
        const apiBase = (import.meta as any).env?.VITE_API_URL || 'https://tdj9q54rxg.execute-api.eu-west-1.amazonaws.com/v1';
        const baseUrl = apiBase.replace('/v1', '');
        const encoded = encodeURIComponent(text.slice(0, 2000));
        const response = await fetch(`${baseUrl}/v1/tts?text=${encoded}&voice=Matthew`);
        
        if (response.ok) {
          const audioBlob = await response.blob();
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            this.speaking = false;
            resolve();
          };
          audio.onerror = () => {
            URL.revokeObjectURL(audioUrl);
            this.speaking = false;
            resolve();
          };
          
          await audio.play();
          return;
        }
      } catch (e) {
        console.warn('Polly TTS failed, falling back to browser speech:', e);
      }

      // Fallback to browser speech synthesis if Polly fails
      const clean = text.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/---/g, '').replace(/\n+/g, '. ').replace(/[#*`]/g, '');
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.0;
      utterance.onend = () => { this.speaking = false; resolve(); };
      utterance.onerror = () => { this.speaking = false; resolve(); };
      window.speechSynthesis.speak(utterance);
    });
  }

  private setStatus(status: VoiceStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }
}
