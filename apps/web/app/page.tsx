"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Plus, Square, X, MicOff, LayoutDashboard } from "lucide-react";
import SiriOrb from "@/components/ui/siri-orb";
import { AudioStreamManager, SiriOrbState } from "@/lib/audio";
import CalendarWidget from "@/components/CalendarWidget";
import EmployeeStack, { AGENT_EMPLOYEES } from "@/components/EmployeeStack";
import AgentTodoList from "@/components/AgentTodoList";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

// Suggestion chips per agent
const AGENT_SUGGESTIONS: Record<string, string[]> = {
  research_agent: [
    "Show all discovered leads",
    "Scrape new businesses in Standerton",
    "Find companies missing websites",
    "Export contact directory",
  ],
  email_agent: [
    "Review pending email pitches",
    "Generate proposal for Auto Repair",
    "Dispatch approved emails now",
    "Check outbox queue status",
  ],
  reports_agent: [
    "Show this week's analytics",
    "Export PDF report",
    "Summarise lead conversion rates",
    "Compare week-on-week performance",
  ],
  project_manager: [
    "Check subagent system status",
    "Audit all running agent threads",
    "Restart idle agents",
    "Show error logs from last 24h",
  ],
};

const renderFormattedText = (text: string) => {
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    const isBullet = line.trim().startsWith("- ") || line.trim().startsWith("• ");
    const content = isBullet ? line.trim().replace(/^[-•]\s*/, "") : line;

    const parts = content.split(/(\*\*.*?\*\*|\[.*?\]\(.*?\))/g);
    const parsed = parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} style={{ fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("[") && part.includes("](") && part.endsWith(")")) {
        const match = part.match(/^\[(.*?)\]\((.*?)\)$/);
        if (match) {
          return (
            <a key={i} href={match[2]} target="_blank" rel="noopener noreferrer" style={{ color: "#ec4899", textDecoration: "underline" }}>
              {match[1]}
            </a>
          );
        }
      }
      return part;
    });

    if (isBullet) {
      return (
        <div key={idx} style={{ display: "flex", gap: 8, marginLeft: 6, marginTop: 3 }}>
          <span style={{ color: "#ec4899" }}>•</span>
          <div>{parsed}</div>
        </div>
      );
    }
    return <div key={idx} style={{ minHeight: line.trim() ? "auto" : "0.4em" }}>{parsed}</div>;
  });
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);

  // Voice / Full-screen White Orb Live mode state
  const [voiceActive, setVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [liveResponse, setLiveResponse] = useState("");

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const activeAgent = AGENT_EMPLOYEES.find((a) => a.id === activeAgentId);

  const handleSelectAgent = (id: string) => {
    setActiveAgentId(id);
    setMessages([]);
  };

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startVoiceMode = async () => {
    setVoiceActive(true);
    setOrbState("listening");

    const manager = new AudioStreamManager({
      onStateChange: (s) => setOrbState(s),
      onTranscription: (t) => setTranscription(t),
      onResponseText: (r) => setLiveResponse(r),
      onError: (err) => {
        console.error("Audio stream error:", err);
        stopVoiceMode();
      },
    });
    audioManagerRef.current = manager;
    const connected = await manager.connect();
    if (!connected) {
      console.warn("Could not connect to audio WebSocket.");
      stopVoiceMode();
      return;
    }
    const ok = await manager.startStreaming();
    if (!ok) stopVoiceMode();
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    audioManagerRef.current?.setMuted(nextMuted);
  };

  const stopVoiceMode = () => {
    audioManagerRef.current?.disconnect();
    audioManagerRef.current = null;
    setVoiceActive(false);
    setOrbState("idle");
    setTranscription("");
    setLiveResponse("");
  };

  const handleSend = async (text?: string) => {
    const userText = (text || inputValue).trim();
    if (!userText || loading) return;
    setInputValue("");
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        sender: "user",
        text: userText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: userText,
          user_id: "web_user",
          thread_id: activeAgentId ?? "default",
        }),
      });
      const data = await res.json();
      clearTimeout(timeoutId);
      const reply = data.response || data.message || data.detail || "No response from agent.";
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: reply,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: (err instanceof DOMException && err.name === "AbortError")
            ? "The agent took too long to respond. The backend may still be processing — try again."
            : "Could not reach the agent backend. Make sure it is running on port 8000.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "hidden" }}>
      {voiceActive ? (
        /* ── FULL-SCREEN WHITE ORB LIVE SPEECH MODE ── */
        <div style={{ position: "fixed", inset: 0, zIndex: 1000, background: "#ffffff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 32, color: "#0f172a" }}>
          <SiriOrb size={220} animationDuration={12} />

          <div style={{ textAlign: "center", maxWidth: 500 }}>
            <p style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#ec4899", fontWeight: 700, margin: "0 0 6px" }}>
              {orbState === "listening"
                ? "Listening, pause for 3 seconds to send..."
                : orbState === "speaking"
                  ? "Agent is speaking..."
                  : "Processing..."}
            </p>
            {transcription && <p style={{ fontSize: 16, color: "#0f172a", fontWeight: 500, margin: "6px 0" }}>&#34;{transcription}&#34;</p>}
            {liveResponse && <p style={{ fontSize: 14, color: "#64748b", fontStyle: "italic", margin: "6px 0" }}>{liveResponse}</p>}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button onClick={toggleMute} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 999, background: isMuted ? "#fee2e2" : "#f1f5f9", color: isMuted ? "#dc2626" : "#334155", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
              <MicOff size={16} /><span>{isMuted ? "Unmute Mic" : "Mute Mic"}</span>
            </button>
            <button onClick={stopVoiceMode} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 24px", borderRadius: 999, background: "#ec4899", color: "#ffffff", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, boxShadow: "0 4px 14px rgba(236,72,153,0.4)" }}>
              <X size={16} /><span>Close</span>
            </button>
          </div>
        </div>
      ) : (
        /* ── CLEAN MINIMAL MAIN HUB ── */
        <div className="dashboard-container" style={{ backgroundImage: "linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url('/gemini-bg.png')", backgroundSize: "cover", backgroundPosition: "center", color: "#1e293b" }}>
          {/* Header */}
          <header style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px" }}>
            <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>my_agent</span>
            <Link href="/dashboard" style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a", background: "#ffffff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
              <LayoutDashboard size={14} />Admin Dashboard
            </Link>
          </header>

          <main className="dashboard-main-grid">
            {/* LEFT: Calendar + Employee Roster */}
            <div style={{ display: "flex", flexDirection: "column", gap: "clamp(6px, 1.2vh, 14px)", overflow: "hidden", height: "100%" }}>
              <CalendarWidget />
              <EmployeeStack activeAgentId={activeAgentId ?? ""} onSelectAgent={handleSelectAgent} />
            </div>

            {/* CENTER: Hero + Prompt Capsule + Suggestion Chips */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: messages.length === 0 ? "center" : "flex-start", position: "relative", height: "100%", overflowY: "auto", paddingRight: 4, paddingTop: messages.length > 0 ? 20 : 0 }}>

              {messages.length === 0 ? (
                <div style={{ textAlign: "center", marginBottom: 28, maxWidth: 600 }}>
                  <h1 style={{ fontSize: 38, fontWeight: 400, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 8px" }}>
                    What's next, sir?
                  </h1>
                  <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                    {activeAgent
                      ? <>Interacting with <strong style={{ color: "#ec4899" }}>{activeAgent.name}</strong>. Ask a question or click the Orb for speech mode.</>
                      : "Select an agent from AI Employees to get started."}
                  </p>
                </div>
              ) : (
                /* Message Stream */
                <div style={{ width: "100%", maxWidth: 640, flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 20 }}>
                  {messages.map((msg) => (
                    <div key={msg.id} style={{ display: "flex", justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                      <div style={{ maxWidth: "80%", padding: "12px 16px", fontSize: 13, lineHeight: 1.6, borderRadius: 18, background: msg.sender === "user" ? "#0f172a" : "#ffffff", color: msg.sender === "user" ? "#ffffff" : "#0f172a", border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 2px 10px rgba(0,0,0,0.04)" }}>
                        <div>{renderFormattedText(msg.text)}</div>
                      </div>
                    </div>
                  ))}
                  {loading && <div style={{ fontSize: 13, color: "#64748b" }}>{activeAgent?.name ?? "Agent"} is thinking...</div>}
                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* Prompt Capsule */}
              <div style={{ width: "100%", maxWidth: 600 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#ffffff", borderRadius: 999, padding: "8px 12px 8px 18px", boxShadow: "0 10px 30px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.05)", border: "1px solid rgba(226,232,240,0.9)" }}>
                  <button style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
                    <Plus size={20} />
                  </button>
                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSend(); } }}
                    placeholder={activeAgent ? `Ask ${activeAgent.name}...` : "Select an agent to begin..."}
                    style={{ flex: 1, border: "none", outline: "none", fontSize: 14, color: "#0f172a", background: "transparent", fontFamily: "inherit" }}
                  />
                  <button
                    onClick={startVoiceMode}
                    title="Speech mode"
                    style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: 2, borderRadius: "50%", transition: "transform 150ms" }}
                    onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                  >
                    <SiriOrb size={24} animationDuration={20} />
                  </button>
                </div>
              </div>

              {/* SUGGESTION CHIPS — shown only when agent selected and no messages yet */}
              {messages.length === 0 && activeAgentId && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 600, marginTop: 18 }}>
                  {(AGENT_SUGGESTIONS[activeAgentId] ?? []).map((chip) => (
                    <button
                      key={chip}
                      onClick={() => handleSend(chip)}
                      style={{ padding: "6px 14px", fontSize: 12, fontWeight: 500, background: "rgba(255,255,255,0.6)", backdropFilter: "blur(8px)", border: "1px solid rgba(226,232,240,0.9)", borderRadius: 999, cursor: "pointer", color: "#334155", transition: "all 150ms ease" }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#ec4899"; (e.currentTarget as HTMLButtonElement).style.color = "#ec4899"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(226,232,240,0.9)"; (e.currentTarget as HTMLButtonElement).style.color = "#334155"; }}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* RIGHT: Daily To-Do List */}
            <div style={{ height: "100%", overflow: "hidden" }}>
              <AgentTodoList activeAgentId={activeAgentId ?? ""} activeAgentName={activeAgent?.name ?? ""} />
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
