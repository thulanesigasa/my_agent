/** Browser speech is opt-in. Wake activation is not speaker authentication. */
export type VoiceState = "idle" | "standby" | "listening" | "processing" | "speaking";
type Result = { isFinal: boolean; 0: { transcript: string } };
type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { resultIndex: number; results: ArrayLike<Result> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null;
  start(): void; abort(): void;
};
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
export function wakeCommand(text: string): string | null {
  const match = /\belevate\s+agent\b[\s,.!?;:]*/i.exec(text);
  return match ? text.slice(match.index + match[0].length).trim() : null;
}

export class BrowserVoice {
  private recognition: Recognition | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private wake = false;
  private conversation = false;
  private busy = false;
  private disposed = false;
  private generation = 0;
  constructor(private callbacks: { state: (state: VoiceState) => void; transcript: (text: string) => void; final: (text: string) => void; activated: () => void; error: (message: string) => void }) {}
  static supported(): boolean { return typeof window !== "undefined" && !!((window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition); }
  private cancelRecognition() {
    this.generation++;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const old = this.recognition; this.recognition = null;
    if (old) { old.onend = null; old.onresult = null; old.onerror = null; old.abort(); }
  }
  setWake(enabled: boolean) {
    if (enabled && !BrowserVoice.supported()) throw new Error("Wake phrase recognition is unavailable in this browser. Use the voice button or text chat.");
    this.wake = enabled;
    if (!this.conversation && !this.busy) { this.cancelRecognition(); this.listen(); }
  }
  start() {
    if (!BrowserVoice.supported()) throw new Error("Browser speech recognition is unavailable.");
    this.conversation = true; this.busy = false;
    window.speechSynthesis?.cancel(); this.cancelRecognition(); this.listen();
  }
  stop() {
    this.conversation = false; this.busy = false;
    window.speechSynthesis?.cancel(); this.cancelRecognition(); this.listen();
  }
  processing() { this.busy = true; this.cancelRecognition(); this.callbacks.state("processing"); }
  resume() { this.busy = false; this.cancelRecognition(); this.listen(); }
  speak(text: string) {
    this.busy = true; this.cancelRecognition();
    if (!("speechSynthesis" in window)) { this.resume(); return; }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/[*#`]/g, "").slice(0, 8000));
    utterance.lang = "en-ZA";
    const generation = this.generation;
    utterance.onend = () => { if (!this.disposed && this.generation === generation) this.resume(); };
    utterance.onerror = () => { if (!this.disposed && this.generation === generation) { this.callbacks.error("Speech playback failed. The text response is still available."); this.resume(); } };
    this.callbacks.state("speaking"); window.speechSynthesis.speak(utterance);
  }
  private listen() {
    if (this.disposed || this.busy || (!this.wake && !this.conversation)) { if (!this.busy) this.callbacks.state("idle"); return; }
    const Constructor = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!Constructor) return;
    const recognition = new Constructor(); this.recognition = recognition;
    const generation = this.generation;
    const current = () => !this.disposed && generation === this.generation && this.recognition === recognition;
    recognition.lang = "en-ZA"; recognition.continuous = false; recognition.interimResults = true;
    this.callbacks.state(this.conversation ? "listening" : "standby");
    recognition.onresult = (event) => {
      if (!current()) return;
      let final = "", interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) final += result[0].transcript + " "; else interim += result[0].transcript;
      }
      if (this.conversation) this.callbacks.transcript(interim || final.trim());
      if (!final.trim()) return;
      if (!this.conversation) {
        const command = wakeCommand(final);
        if (command === null) return;
        this.conversation = true; this.callbacks.activated(); this.cancelRecognition();
        if (!command) { this.listen(); return; }
        this.processing(); this.callbacks.final(command);
      } else { this.processing(); this.callbacks.final(final.trim()); }
    };
    recognition.onerror = (event) => {
      if (!current() || event.error === "aborted" || event.error === "no-speech") return;
      this.wake = false; this.conversation = false; this.busy = false; this.cancelRecognition(); this.callbacks.state("idle");
      this.callbacks.error(event.error === "not-allowed" || event.error === "service-not-allowed" ? "Microphone or speech permission was denied. Allow it in your browser, then enable voice again." : `Speech recognition stopped (${event.error}). Text chat is still available.`);
    };
    recognition.onend = () => {
      if (!current()) return;
      this.recognition = null;
      this.timer = setTimeout(() => { this.timer = null; this.listen(); }, 400);
    };
    try { recognition.start(); } catch { this.callbacks.error("Could not start speech recognition. Try enabling voice again."); this.wake = false; this.conversation = false; this.cancelRecognition(); this.callbacks.state("idle"); }
  }
  dispose() { this.disposed = true; this.wake = false; this.conversation = false; this.cancelRecognition(); window.speechSynthesis?.cancel(); }
}
