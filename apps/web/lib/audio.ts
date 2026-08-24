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

export async function playBase64Audio(base64Data: string): Promise<void> {
  try {
    const binaryString = atob(base64Data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const decodedData = await audioContext.decodeAudioData(bytes.buffer);
    const source = audioContext.createBufferSource();
    source.buffer = decodedData;
    source.connect(audioContext.destination);
    source.start(0);
  } catch (e) {
    console.warn("Error playing base64 audio:", e);
  }
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
   * Resolves true when socket reaches WebSocket.OPEN.
   */
  public async connect(url?: string): Promise<boolean> {
    const wsUrl =
      url ||
      process.env.NEXT_PUBLIC_AGENT_AUDIO_WS_URL ||
      "ws://127.0.0.1:8000/ws/audio";

    return new Promise<boolean>((resolve) => {
      try {
        this.socket = new WebSocket(wsUrl);
        this.socket.binaryType = "arraybuffer";

        const timeoutId = setTimeout(() => {
          console.warn("WebSocket connection timeout to", wsUrl);
          resolve(false);
        }, 5000);

        this.socket.onopen = () => {
          clearTimeout(timeoutId);
          console.log("Connected to Audio Streaming WebSocket at", wsUrl);
          resolve(true);
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
            // Binary audio chunk received from server -> Decode and play via Web Audio API
            await this.playAudioBuffer(event.data);
          }
        };

        this.socket.onerror = (err) => {
          clearTimeout(timeoutId);
          console.warn("WebSocket error:", err);
          resolve(false);
        };

        this.socket.onclose = () => {
          console.log("Audio WebSocket disconnected.");
        };
      } catch (e) {
        console.error("Failed to establish WebSocket connection:", e);
        resolve(false);
      }
    });
  }

  /**
   * Start microphone capture using MediaRecorder and collect audio chunks.
   */
  public async startStreaming(): Promise<boolean> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      let mimeType = "audio/webm";
      if (!MediaRecorder.isTypeSupported("audio/webm")) {
        if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
          mimeType = "audio/ogg";
        } else {
          mimeType = "";
        }
      }

      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);

      const chunks: Blob[] = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        const fullBlob = new Blob(chunks, { type: mimeType || "audio/webm" });
        const arrayBuffer = await fullBlob.arrayBuffer();

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          this.callbacks.onStateChange?.("processing");
          this.socket.send(arrayBuffer);
        } else {
          console.warn("Cannot send audio: WebSocket is not open.");
        }
      };

      this.mediaRecorder.start();
      this.callbacks.onStateChange?.("listening");
      return true;
    } catch (err: any) {
      console.warn("Microphone access error:", err);
      const errMsg =
        err?.name === "NotAllowedError"
          ? "Microphone access blocked. Please allow microphone permission in your browser settings."
          : "Could not access microphone.";
      this.callbacks.onError?.(errMsg);
      return false;
    }
  }

  /**
   * Stop recording and transmit captured audio over the open WebSocket.
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
