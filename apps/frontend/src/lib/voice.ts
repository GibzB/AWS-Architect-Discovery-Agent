/**
 * Voice client — browser-native speech recognition + speech synthesis.
 *
 * Architecture (no WebSocket needed):
 * - STT: Web Speech API (SpeechRecognition) — runs entirely in browser
 * - TTS: Web Speech Synthesis API — runs entirely in browser
 * - Messages sent via the same REST API as chat
 */

import { sendMessage, type SendMessageResponse } from './api';

export interface VoiceCallbacks {
  onStatusChange: (status: VoiceStatus) => void;
  onTranscript: (role: 'user' | 'assistant', text: string) => void;
  onError: (message: string) => void;
}

export type VoiceStatus = 'idle' | 'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking' | 'done';

export class VoiceClient {
  private recognition: any = null;
  private callbacks: VoiceCallbacks;
  private sessionId: string;
  private status: VoiceStatus = 'idle';
  private active = false;

  constructor(sessionId: string, callbacks: VoiceCallbacks) {
    this.sessionId = sessionId;
    this.callbacks = callbacks;
  }

  get currentStatus(): VoiceStatus {
    return this.status;
  }

  async start(): Promise<void> {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.callbacks.onError('Speech recognition not supported. Use Chrome.');
      return;
    }

    this.active = true;
    this.setStatus('ready');

    // Speak the greeting
    this.speak("Hello, I'm ASA. Tell me about your cloud initiative.");
  }

  async stop(): Promise<void> {
    this.active = false;
    this.stopRecognition();
    window.speechSynthesis.cancel();
    this.setStatus('idle');
  }

  private startRecognition(): void {
    if (!this.active) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = async (event: any) => {
      const text = event.results[0][0].transcript.trim();
      if (text && this.active) {
        this.callbacks.onTranscript('user', text);
        this.setStatus('thinking');
        await this.processMessage(text);
      }
    };

    this.recognition.onerror = (event: any) => {
      if (event.error === 'no-speech' || event.error === 'aborted') {
        // Restart listening
        if (this.active) {
          setTimeout(() => this.startRecognition(), 300);
        }
        return;
      }
      this.callbacks.onError(`Speech error: ${event.error}`);
    };

    this.recognition.onend = () => {
      // Restart if we're still in listening mode
      if (this.active && this.status === 'listening') {
        setTimeout(() => this.startRecognition(), 300);
      }
    };

    try {
      this.recognition.start();
      this.setStatus('listening');
    } catch {
      // Already started or permission denied
      if (this.active) {
        setTimeout(() => this.startRecognition(), 500);
      }
    }
  }

  private stopRecognition(): void {
    if (this.recognition) {
      try { this.recognition.abort(); } catch { /* ignore */ }
      this.recognition = null;
    }
  }

  private async processMessage(text: string): Promise<void> {
    try {
      const response: SendMessageResponse = await sendMessage(this.sessionId, text);
      this.callbacks.onTranscript('assistant', response.content);

      // Speak the response
      if (this.active) {
        this.speak(response.content);
      }
    } catch (err) {
      this.callbacks.onError('Failed to get response from ASA.');
      if (this.active) {
        this.setStatus('listening');
        this.startRecognition();
      }
    }
  }

  private speak(text: string): void {
    this.setStatus('speaking');
    window.speechSynthesis.cancel();

    // Clean markdown formatting for speech
    const cleanText = text
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/---/g, '')
      .replace(/\n+/g, '. ')
      .replace(/[#*`]/g, '');

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Prefer a natural-sounding voice
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Daniel') || v.name.includes('Google UK English Male') ||
      v.name.includes('Alex') || v.name.includes('Samantha')
    );
    if (preferred) utterance.voice = preferred;

    utterance.onend = () => {
      if (this.active) {
        this.setStatus('listening');
        this.startRecognition();
      }
    };

    utterance.onerror = () => {
      if (this.active) {
        this.setStatus('listening');
        this.startRecognition();
      }
    };

    window.speechSynthesis.speak(utterance);
  }

  private setStatus(status: VoiceStatus): void {
    this.status = status;
    this.callbacks.onStatusChange(status);
  }
}
