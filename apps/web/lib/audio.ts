/**
 * Web Audio API recorder and speech playback utilities.
 * Handles microphone recording, real-time volume analyzer, base64 encoding,
 * and audio playback of Edge-TTS voice payloads.
 */

export class AudioRecorderManager {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private stream: MediaStream | null = null;
  private animFrameId: number | null = null;

  async startRecording(onVolumeChange?: (level: number) => void): Promise<boolean> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.start();

      // Audio level analyzer for SiriOrb reactive animation
      if (onVolumeChange) {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const source = this.audioContext.createMediaStreamSource(this.stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        const updateVolume = () => {
          if (!this.analyser) return;
          this.analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          const normalized = Math.min(1.0, avg / 128.0);
          onVolumeChange(normalized);
          this.animFrameId = requestAnimationFrame(updateVolume);
        };
        updateVolume();
      }

      return true;
    } catch (err) {
      console.error("Failed to access microphone:", err);
      return false;
    }
  }

  async stopRecording(): Promise<string> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve("");
        return;
      }

      this.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
          const base64Audio = reader.result as string;
          resolve(base64Audio);
        };

        this.cleanup();
      };

      this.mediaRecorder.stop();
    });
  }

  private cleanup() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

/**
 * Play base64 audio string synthesized by Edge-TTS.
 */
export async function playBase64Audio(base64Data: string): Promise<void> {
  if (!base64Data) return;
  try {
    const audioUrl = base64Data.startsWith("data:")
      ? base64Data
      : `data:audio/mp3;base64,${base64Data}`;
    const audio = new Audio(audioUrl);
    await audio.play();
  } catch (e) {
    console.warn("Failed to auto-play response audio:", e);
  }
}
