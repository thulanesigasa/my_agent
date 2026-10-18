"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUp, ArrowUpRight, Check, ChevronDown, Copy, Headphones, Menu, Mic, Plus, Search, ShieldCheck, Sparkles, Square, Volume2, X } from "lucide-react";
import { BrowserVoice, VoiceState } from "@/lib/browser-voice";
import { AudioStreamManager } from "@/lib/audio";
import styles from "./chat.module.css";

type Message = { id: string; role: "user" | "assistant"; text: string; voice?: boolean };
const agents = [
  { id: "project_manager", name: "Elevate", role: "Your coordinator", mark: "E", prompt: "What would you like to move forward?", suggestions: ["Summarise my outreach progress", "What needs my attention?", "Help me plan my next research batch"] },
  { id: "research_agent", name: "Research", role: "Find the right businesses", mark: "R", prompt: "Let's find your next opportunity.", suggestions: ["Help me research local businesses", "Explain automatic qualification", "What evidence does a lead need?"] },
  { id: "email_agent", name: "Outreach", role: "Thoughtful conversations", mark: "O", prompt: "Let's start a good conversation.", suggestions: ["Help me improve a website proposal", "Explain the email approval process", "Help me respond to a business enquiry"] },
  { id: "reports_agent", name: "Reports", role: "Understand your progress", mark: "↗", prompt: "Make sense of the work so far.", suggestions: ["Help me understand reply rates", "Explain the weekly outreach report", "What counts as a confirmed outcome?"] },
];

function Formatted({ text }: { text: string }) {
  return <div className={styles.messageText}>{text.split(/(\[[^\]\n]+\]\([^)\s]+\)|\*\*[^*]+\*\*)/g).map((part, i) => {
    const match = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
    if (match) {
      const href = match[2];
      if (/^https?:\/\//i.test(href) || /^\/[^/]/.test(href)) return <a key={i} href={href} target={href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">{match[1]}</a>;
    }
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    return <span key={i}>{part}</span>;
  })}</div>;
}

export default function Home() {
  const [active, setActive] = useState("project_manager");
  const [conversations, setConversations] = useState<Record<string, Message[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [voice, setVoice] = useState(false);
  const [wake, setWake] = useState(false);
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [supported, setSupported] = useState(false);
  const [copied, setCopied] = useState("");
  const browser = useRef<BrowserVoice | null>(null);
  const server = useRef<AudioStreamManager | null>(null);
  const request = useRef<AbortController | null>(null);
  const pending = useRef(false);
  const voiceOn = useRef(false);
  const activeRef = useRef(active);
  const threads = useRef<Record<string, string>>({});
  const bottom = useRef<HTMLDivElement>(null);
  const sendRef = useRef<(text: string, spoken?: boolean) => Promise<void>>(async () => {});
  const agent = agents.find((a) => a.id === active)!;
  const messages = conversations[active] || [];
  function thread(id: string) { return threads.current[id] ||= `${id}_${crypto.randomUUID()}`; }
  function append(id: string, role: Message["role"], text: string, spoken = false) {
    setConversations((old) => ({ ...old, [id]: [...(old[id] || []), { id: crypto.randomUUID(), role, text, voice: spoken }] }));
  }
  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length, busy, transcript]);
  useEffect(() => {
    setSupported(BrowserVoice.supported());
    const manager = new BrowserVoice({
      state: setState, transcript: setTranscript,
      activated: () => { voiceOn.current = true; setVoice(true); setError(""); },
      final: (text) => { setTranscript(""); void sendRef.current(text, true); },
      error: (message) => { setError(message); setVoice(false); setWake(false); voiceOn.current = false; manager.setWake(false); manager.stop(); },
    });
    browser.current = manager;
    return () => { manager.dispose(); server.current?.disconnect(); request.current?.abort(); };
  }, []);
  function stopVoice() {
    voiceOn.current = false; setVoice(false); setTranscript("");
    server.current?.disconnect(); server.current = null; browser.current?.stop();
  }
  async function startVoice() {
    if (busy) return;
    setError(""); voiceOn.current = true; setVoice(true);
    if (BrowserVoice.supported()) { try { browser.current?.start(); } catch (e) { stopVoice(); setError(e instanceof Error ? e.message : "Could not start voice."); } return; }
    const workspace = activeRef.current;
    const manager = new AudioStreamManager({
      onStateChange: setState,
      onTranscription: (text) => { if (voiceOn.current) append(workspace, "user", text, true); },
      onResponseText: (text) => { if (voiceOn.current) append(workspace, "assistant", text, true); },
      onError: (message) => { setError(message); stopVoice(); },
    });
    server.current = manager;
    const connected = await manager.connect(undefined, thread(workspace));
    if (server.current !== manager || !voiceOn.current) { manager.disconnect(); return; }
    if (!connected || !(await manager.startStreaming())) { stopVoice(); setError("Server voice could not start. Check microphone access and backend voice configuration. Text chat remains available."); }
  }
  async function send(text: string, spoken = false) {
    const value = text.trim();
    if (!value || pending.current) return;
    pending.current = true; setBusy(true); setError(""); setInput("");
    const workspace = activeRef.current;
    append(workspace, "user", value, spoken);
    browser.current?.processing();
    const controller = new AbortController(); request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      const res = await fetch("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal, body: JSON.stringify({ message: value, user_id: "web_user", thread_id: thread(workspace) }) });
      const data = await res.json();
      if (!res.ok || data.status === "error") throw new Error(data.response || data.message || data.detail || `Request failed (${res.status})`);
      const answer = typeof data.response === "string" ? data.response : typeof data.message === "string" ? data.message : "The backend returned no response text.";
      append(workspace, "assistant", answer, spoken);
      if (voiceOn.current) browser.current?.speak(answer); else browser.current?.resume();
    } catch (e) {
      setError(controller.signal.aborted ? "Stopped waiting for this response. The backend may still finish; check Approvals before repeating an action." : e instanceof Error ? e.message : "Could not reach the agent. Check that your backend is running.");
      stopVoice(); browser.current?.resume();
    } finally { clearTimeout(timeout); pending.current = false; setBusy(false); request.current = null; }
  }
  sendRef.current = send;
  function select(id: string) { if (busy || voice) return; setActive(id); activeRef.current = id; setMobileOpen(false); setError(""); setInput(""); }
  function newChat() { if (busy || voice) return; threads.current[active] = `${active}_${crypto.randomUUID()}`; setConversations((old) => ({ ...old, [active]: [] })); setError(""); setInput(""); }
  function toggleWake() {
    try { browser.current?.setWake(!wake); setWake(!wake); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Wake phrase unavailable."); }
  }
  function submit(e: FormEvent) { e.preventDefault(); void send(input); }
  const status = state === "standby" ? 'Listening for “elevate agent”' : state === "listening" ? "Listening to you" : state === "speaking" ? "Speaking" : busy || state === "processing" ? "Thinking" : "Ready when you are";
  return <div className={styles.app}>
    {mobileOpen && <button className={styles.scrim} aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`${styles.sidebar} ${mobileOpen ? styles.open : ""}`}>
      <Link href="/" className={styles.brand}><span className={styles.brandMark}><Sparkles size={21} /></span><span>elevate<span className={styles.brandSub}>agen / your AI team</span></span></Link>
      <button className={styles.newChat} onClick={newChat} disabled={busy || voice}><Plus size={17} /> New conversation <span>↗</span></button>
      <div className={styles.sectionLabel}>YOUR AGENT SPACES</div>
      <nav className={styles.agentList} aria-label="Agent spaces">{agents.map((a) => <button key={a.id} aria-pressed={active === a.id} disabled={busy || voice} onClick={() => select(a.id)} className={active === a.id ? styles.agentActive : styles.agentButton}><span className={styles.agentMark}>{a.mark}</span><span><strong>{a.name}</strong><small>{a.role}</small></span>{active === a.id && <span className={styles.activeDot} />}</button>)}</nav>
      <div className={styles.sidebarBottom}><div className={styles.wakeCard}><span className={styles.sectionLabel}>A LITTLE MORE HANDS-FREE</span><p>Say <strong>“elevate agent”</strong><br />to start a conversation.</p><button onClick={toggleWake} disabled={!supported || busy || voice} className={wake ? styles.wakeOn : styles.wakeButton}><Mic size={14} />{wake ? "Wake listening on" : "Enable wake phrase"}</button><small>Opt-in microphone access. Double-clap desktop launch is kept.</small></div><Link href="/dashboard" className={styles.dashboardLink}><ShieldCheck size={16} /> Outreach workspace <ArrowUpRight size={15} /></Link><div className={styles.profile}><span>TS</span><div>TS Industries<small>Local agent workspace</small></div><span className={styles.profileDot} /></div></div>
    </aside>
    <main className={styles.main}>
      <header className={styles.header}><div className={styles.headerLeft}><button className={styles.mobileMenu} aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={21} /></button><span>{agent.name}</span><ChevronDown size={14} /><span className={styles.headerDivider} /><span className={styles.headerCaption}>A conversation with your team</span></div><Link href="/dashboard?tab=approvals" className={styles.approvals}><ShieldCheck size={15} /> Approvals <ArrowUpRight size={14} /></Link></header>
      <div className={styles.scrollArea}>
        {!messages.length ? <section className={styles.welcome}><div className={styles.orbit}><span /><Sparkles size={35} strokeWidth={1.3} /></div><div className={styles.eyebrow}>LESS BUSYWORK. MORE POSSIBILITY.</div><h1>{agent.prompt}</h1><p>Talk it through, make a plan, or put your agents to work.<br className={styles.desktopBreak} /> Start with a message. Take it further with your voice.</p><div className={styles.suggestions}>{agent.suggestions.map((suggestion, i) => <button key={suggestion} onClick={() => void send(suggestion)} disabled={busy}><span>{i === 0 ? <Search size={17} /> : i === 1 ? <Sparkles size={17} /> : <ArrowUpRight size={17} />}</span>{suggestion}<ArrowUpRight size={14} /></button>)}</div></section> : <div className={styles.messages} aria-live="polite" aria-relevant="additions">{messages.map((message) => <article key={message.id} className={message.role === "user" ? styles.userMessage : styles.assistantMessage}>{message.role === "assistant" && <span className={styles.replyMark}><Sparkles size={17} /></span>}<div className={styles.messageBody}><div className={styles.messageMeta}>{message.role === "user" ? "You" : agent.name}{message.voice && <Mic size={11} />}</div><Formatted text={message.text} />{message.role === "assistant" && <div className={styles.messageActions}><button aria-label="Copy response" onClick={() => { void navigator.clipboard.writeText(message.text).then(() => { setCopied(message.id); setTimeout(() => setCopied(""), 1800); }).catch(() => setError("Clipboard access unavailable. Select and copy the response text.")); }}>{copied === message.id ? <Check size={14} /> : <Copy size={14} />}</button><button aria-label="Read response aloud" disabled={busy || voice} onClick={() => browser.current?.speak(message.text)}><Volume2 size={14} /></button></div>}</div></article>)}{busy && <div className={styles.thinking} role="status"><span /><span /><span /> Working on your message</div>}<div ref={bottom} /></div>}
      </div>
      <div className={styles.composerArea}>
        {error && <div className={styles.error} role="alert">{error}<button aria-label="Dismiss error" onClick={() => setError("")}><X size={15} /></button></div>}
        {(voice || wake || state === "speaking") && <div className={styles.voiceBar}><span className={styles.voicePulse} /><span>{status}{transcript ? ` · ${transcript}` : ""}</span>{state === "speaking" && <button onClick={() => { server.current?.interrupt(); browser.current?.resume(); window.speechSynthesis?.cancel(); }}>Interrupt</button>}{voice && <button onClick={stopVoice}>End voice <X size={13} /></button>}</div>}
        <form className={styles.composer} onSubmit={submit}><label className={styles.inputLabel} htmlFor="chat-message">Message {agent.name}</label><textarea disabled={voice && !supported} id="chat-message" aria-label={`Message ${agent.name}`} value={input} maxLength={20000} placeholder={`Message ${agent.name}…`} rows={2} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!busy) void send(input); } }} /><div className={styles.composerBottom}><div className={styles.composerTools}><button type="button" title={voice ? "End voice conversation" : "Start voice conversation"} aria-label={voice ? "End voice conversation" : "Start voice conversation"} className={voice ? styles.voiceButtonActive : styles.voiceButton} disabled={busy} onClick={() => voice ? stopVoice() : void startVoice()}><Headphones size={17} /> <span>{voice ? "Voice on" : "Voice conversation"}</span></button><span className={styles.modelLabel}>elevate agent</span></div>{busy ? <button type="button" className={styles.send} aria-label="Stop waiting" onClick={() => request.current?.abort()}><Square size={15} fill="currentColor" /></button> : <button type="submit" className={styles.send} aria-label="Send message" disabled={!input.trim() || (voice && !supported)}><ArrowUp size={19} /></button>}</div></form>
        <div className={styles.footerNote}><span>Text or voice. One conversation.</span><span>Outgoing emails always need your approval.</span></div>
      </div>
    </main>
  </div>;
}
