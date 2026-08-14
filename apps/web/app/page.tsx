"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Plus, Square, X, MicOff, LayoutDashboard, Bot, User, Sparkles } from "lucide-react";
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

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState<string>("research_agent");

  // Voice / Full-screen White Orb Live mode state
  const [voiceActive, setVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [liveResponse, setLiveResponse] = useState("");
  const [micError, setMicError] = useState<string | null>(null);

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const activeAgent = AGENT_EMPLOYEES.find((a) => a.id === activeAgentId) || AGENT_EMPLOYEES[0];

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startVoiceMode = async () => {
    setMicError(null);
    setVoiceActive(true);
    setOrbState("listening");

    const manager = new AudioStreamManager({
      onStateChange: (newState) => setOrbState(newState),
      onTranscription: (userText) => setTranscription(userText),
      onResponseText: (agentText) => setLiveResponse(agentText),
      onError: (err) => {
        setMicError(err);
        setVoiceActive(false);
      },
    });

    audioManagerRef.current = manager;
    manager.connect();
    const ok = await manager.startStreaming();
    if (!ok) {
      setVoiceActive(false);
    }
  };

  const stopVoiceMode = () => {
    if (audioManagerRef.current) {
      audioManagerRef.current.disconnect();
      audioManagerRef.current = null;
    }
    setVoiceActive(false);
    setOrbState("idle");
    setTranscription("");
    setLiveResponse("");
  };

  const handleSendText = () => {
    if (!inputValue.trim() || loading) return;
    const userText = inputValue.trim();
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

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: `[${activeAgent.name}] Received: "${userText}". Task processed in Standerton lead pipeline.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setLoading(false);
    }, 1000);
  };

  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "hidden" }}>
      {voiceActive ? (
        /* ── FULL-SCREEN WHITE ORB LIVE SPEECH MODE ── */
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "#ffffff",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-between",
          padding: "40px 24px", color: "#0f172a",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", maxWidth: 800 }}>
            <span style={{ fontWeight: 700, fontSize: 18, color: "#0f172a" }}>my_agent · Live Voice</span>
            <button
              onClick={stopVoiceMode}
              style={{
                background: "rgba(0,0,0,0.05)", border: "none", borderRadius: "50%",
                width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: "#64748b",
              }}
            >
              <X size={18} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, margin: "auto" }}>
            <SiriOrb size={220} animationDuration={12} />

            <div style={{ textAlign: "center", maxWidth: 500 }}>
              <p style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#ec4899", fontWeight: 700, margin: "0 0 6px" }}>
                {orbState === "listening" ? "Listening to your voice..." : orbState === "speaking" ? "Agent is speaking..." : "Processing..."}
              </p>

              {transcription && (
                <p style={{ fontSize: 16, color: "#0f172a", fontWeight: 500, margin: "6px 0" }}>
                  "{transcription}"
                </p>
              )}

              {liveResponse && (
                <p style={{ fontSize: 14, color: "#64748b", fontStyle: "italic", margin: "6px 0" }}>
                  {liveResponse}
                </p>
              )}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button
              onClick={() => setIsMuted(!isMuted)}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 20px", borderRadius: 999,
                background: isMuted ? "#fee2e2" : "#f1f5f9",
                color: isMuted ? "#dc2626" : "#334155",
                border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
              }}
            >
              <MicOff size={16} />
              <span>{isMuted ? "Unmute Mic" : "Mute Mic"}</span>
            </button>

            <button
              onClick={stopVoiceMode}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 24px", borderRadius: 999,
                background: "#ec4899", color: "#ffffff",
                border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
                boxShadow: "0 4px 14px rgba(236, 72, 153, 0.4)",
              }}
            >
              <Square size={14} fill="#ffffff" />
              <span>Click to Interrupt</span>
            </button>
          </div>
        </div>
      ) : (
        /* ── PURE CLEAN MINIMAL MAIN HUB UI MATCHING USER SCREENSHOT 1:1 ── */
        <div className="dashboard-container" style={{
          backgroundImage: "linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url('/gemini-bg.png')",
          backgroundSize: "cover", backgroundPosition: "center",
          color: "#1e293b",
        }}>
          {/* Top Bar Header */}
          <header style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>my_agent</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Link
                href="/dashboard"
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a",
                  background: "#ffffff", border: "1px solid rgba(0,0,0,0.1)",
                  borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                }}
              >
                <LayoutDashboard size={14} />
                Admin Dashboard
              </Link>
            </div>
          </header>

          {/* Main Responsive 3-Column Layout Container */}
          <main className="dashboard-main-grid">
            {/* ── LEFT COLUMN (Top: Calendar | Bottom: Employee Roster) ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: "clamp(6px, 1.2vh, 14px)", overflow: "hidden", height: "100%" }}>
              <CalendarWidget />
              <EmployeeStack activeAgentId={activeAgentId} onSelectAgent={setActiveAgentId} />
            </div>

            {/* ── CENTER COLUMN (Pure Minimal Assistant Input Capsule) ── */}
            <div style={{
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              position: "relative", height: "100%", overflowY: "auto",
              paddingRight: 4,
            }}>
              {messages.length === 0 ? (
                /* Centered Hero Title & Subtitle Matching Screenshot 1:1 */
                <div style={{ textAlign: "center", marginBottom: 32, maxWidth: 600 }}>
                  <h1 style={{ fontSize: 38, fontWeight: 400, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 8px" }}>
                    What's next, sir?
                  </h1>
                  <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                    Interacting with <strong style={{ color: "#ec4899" }}>{activeAgent.name}</strong>. Ask a question or click the Orb for speech mode.
                  </p>
                </div>
              ) : (
                /* Message Stream */
                <div style={{ width: "100%", maxWidth: 640, flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 20 }}>
                  {messages.map((msg) => (
                    <div key={msg.id} style={{ display: "flex", gap: 10, justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                      <div style={{
                        maxWidth: "80%", padding: "12px 16px", fontSize: 13, lineHeight: 1.6,
                        borderRadius: 18,
                        background: msg.sender === "user" ? "#0f172a" : "#ffffff",
                        color: msg.sender === "user" ? "#ffffff" : "#0f172a",
                        border: "1px solid rgba(0,0,0,0.08)",
                        boxShadow: "0 2px 10px rgba(0,0,0,0.04)",
                      }}>
                        <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <span style={{ fontSize: 13, color: "#64748b" }}>{activeAgent.name} is thinking...</span>
                    </div>
                  )}
                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* Floating Input Bar with Glowing Pink Voice Orb */}
              <div style={{ width: "100%", maxWidth: 600, position: "relative" }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 12,
                  background: "#ffffff", borderRadius: 999,
                  padding: "8px 12px 8px 18px",
                  boxShadow: "0 10px 30px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.05)",
                  border: "1px solid rgba(226, 232, 240, 0.9)",
                }}>
                  <button title="Add attachment" style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
                    <Plus size={20} />
                  </button>

                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleSendText();
                      }
                    }}
                    placeholder={`Ask ${activeAgent.name}...`}
                    style={{
                      flex: 1, border: "none", outline: "none",
                      fontSize: 14, color: "#0f172a", background: "transparent",
                      fontFamily: "inherit",
                    }}
                  />

                  <button
                    onClick={startVoiceMode}
                    title="Click to switch to speech mode"
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      padding: 2, borderRadius: "50%", transition: "transform 150ms",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                  >
                    <SiriOrb size={24} animationDuration={20} />
                  </button>
                </div>
              </div>
            </div>

            {/* ── RIGHT COLUMN (Right Box: Daily To-Do List) ── */}
            <div style={{ height: "100%", overflow: "hidden" }}>
              <AgentTodoList activeAgentId={activeAgentId} activeAgentName={activeAgent.name} />
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
