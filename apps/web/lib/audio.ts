/**
 * Browser Audio Processing Engine & WebSocket Stream Manager.
 * Manages MediaRecorder microphone streaming, WebSocket connection to /ws/audio,
 * and Web Audio API AudioContext binary audio decoding & playback.
 */

export type SiriOrbState = "idle" | "listening" | "processing" | "speaking";

export interface AudioStreamCallbacks {
  onStateChange?: (state: SiriOrbState) => void;
  onTranscription?: (text: string) => void;
  onResponseText?: (text: string) => void;
  onError?: (err: string) => void;
}

export class AudioStreamManager {
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private socket: WebSocket | null = null;
  private mediaStream: MediaStream | null = null;
  private callbacks: AudioStreamCallbacks = {};

  constructor(callbacks: AudioStreamCallbacks = {}) {
    this.callbacks = callbacks;
  }

  /**
   * Connect to backend audio streaming WebSocket at /ws/audio.
   */
  public connect(url?: string): void {
    const wsUrl = url || process.env.NEXT_PUBLIC_AGENT_AUDIO_WS_URL || "ws://localhost:8000/ws/audio";
    
    try {
      this.socket = new WebSocket(wsUrl);
      this.socket.binaryType = "arraybuffer";

      this.socket.onopen = () => {
        console.log("Connected to Audio Streaming WebSocket at /ws/audio");
      };

      this.socket.onmessage = async (event) => {
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "state_change") {
              this.callbacks.onStateChange?.(data.state as SiriOrbState);
            } else if (data.type === "transcription") {
              this.callbacks.onTranscription?.(data.text);
            } else if (data.type === "text_response") {
              this.callbacks.onResponseText?.(data.text);
            } else if (data.type === "error") {
              this.callbacks.onError?.(data.message);
            }
          } catch (e) {
            console.error("Error parsing JSON WebSocket message:", e);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // Binary audio chunk received from server Edge-TTS -> Decode and play via AudioContext
          await this.playAudioBuffer(event.data);
        }
      };

      this.socket.onerror = (err) => {
        console.warn("WebSocket error:", err);
      };

      this.socket.onclose = () => {
        console.log("Audio WebSocket disconnected.");
      };
    } catch (e) {
      console.error("Failed to establish WebSocket connection:", e);
    }
  }

  /**
   * Start microphone capture using MediaRecorder and stream sliced chunks to server.
   */
  public async startStreaming(): Promise<boolean> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType: "audio/webm" });

      const chunks: Blob[] = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        const fullBlob = new Blob(chunks, { type: "audio/webm" });
        const arrayBuffer = await fullBlob.arrayBuffer();

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.callbacks.onStateChange?.("processing");
          this.socket.send(arrayBuffer);
        }
      };

      this.mediaRecorder.start();
      this.callbacks.onStateChange?.("listening");
      return true;
    } catch (err) {
      console.error("Microphone access error:", err);
      this.callbacks.onError?.("Microphone permission denied.");
      return false;
    }
  }

  /**
   * Stop microphone capture and trigger chunk payload transmission.
   */
  public stopStreaming(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }

  /**
   * Decode binary arrayBuffer using Web Audio API AudioContext and play sound.
   */
  private async playAudioBuffer(buffer: ArrayBuffer): Promise<void> {
    try {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      }

      this.callbacks.onStateChange?.("speaking");
      const decodedData = await this.audioContext.decodeAudioData(buffer.slice(0));
      const source = this.audioContext.createBufferSource();
      source.buffer = decodedData;
      source.connect(this.audioContext.destination);

      source.onended = () => {
        this.callbacks.onStateChange?.("idle");
      };

      source.start(0);
    } catch (e) {
      console.warn("Audio decoding error:", e);
      this.callbacks.onStateChange?.("idle");
    }
  }

  /**
   * Close WebSocket connection and cleanup resources.
   */
  public disconnect(): void {
    this.stopStreaming();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}
