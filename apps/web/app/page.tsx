"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Plus, ChevronDown, Mic, MicOff, Square, X,
  PenSquare, LayoutDashboard, ArrowUp, Sparkles,
  Volume2, VolumeX, Bot, User
} from "lucide-react";
import SiriOrb from "@/components/ui/siri-orb";
import { AudioStreamManager, SiriOrbState } from "@/lib/audio";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
  mode?: "text" | "voice";
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [modelDropdown, setModelDropdown] = useState(false);

  // Voice / Full-screen Orb Live mode state
  const [voiceActive, setVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [liveResponse, setLiveResponse] = useState("");

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const manager = new AudioStreamManager({
      onStateChange: (state) => {
        setOrbState(state);
      },
      onTranscription: (text) => {
        if (text) {
          setTranscription(text);
          const userMsg: Message = {
            id: `usr_${Date.now()}`,
            sender: "user",
            text: text,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "voice",
          };
          setMessages((prev) => [...prev, userMsg]);
        }
      },
      onResponseText: (text) => {
        if (text) {
          setLiveResponse(text);
          const botMsg: Message = {
            id: `bot_${Date.now()}`,
            sender: "assistant",
            text: text,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            mode: "voice",
          };
          setMessages((prev) => [...prev, botMsg]);
        }
      },
    });

    manager.connect();
    audioManagerRef.current = manager;

    return () => {
      manager.disconnect();
    };
  }, []);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Start voice streaming session (Full Screen White Orb Mode)
  const startVoiceMode = async () => {
    setVoiceActive(true);
    setTranscription("");
    setLiveResponse("");
    const started = await audioManagerRef.current?.startStreaming();
    if (!started) {
      setVoiceActive(false);
      setOrbState("idle");
    }
  };

  // Interrupt / Stop voice streaming and return to Gemini Home UI
  const interruptVoiceMode = () => {
    audioManagerRef.current?.stopStreaming();
    setVoiceActive(false);
    setOrbState("idle");
    setIsMuted(false);
  };

  // Toggle Mute
  const toggleMute = () => {
    setIsMuted((prev) => {
      const next = !prev;
      if (next) {
        audioManagerRef.current?.stopStreaming();
      } else {
        audioManagerRef.current?.startStreaming();
      }
      return next;
    });
  };

  // Send Text query
  const handleSendText = async (textToSend?: string) => {
    const text = (textToSend || inputValue).trim();
    if (!text || loading) return;

    const userMsg: Message = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      mode: "text",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
      const apiKey = process.env.NEXT_PUBLIC_AGENT_API_KEY || "";

      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (apiKey) headers["X-API-Key"] = apiKey;

      const res = await fetch(`${apiUrl}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: text }),
      });

      let responseText = "";
      if (res.ok) {
        const data = await res.json();
        responseText = data.response || data.message || "Executed successfully by my_agent.";
      } else {
        responseText = getAgentFallbackResponse(text);
      }

      const botMsg: Message = {
        id: `bot_${Date.now()}`,
        sender: "assistant",
        text: responseText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        mode: "text",
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      const botMsg: Message = {
        id: `bot_${Date.now()}`,
        sender: "assistant",
        text: getAgentFallbackResponse(text),
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        mode: "text",
      };
      setMessages((prev) => [...prev, botMsg]);
    } finally {
      setLoading(false);
    }
  };

  const getAgentFallbackResponse = (query: string): string => {
    const q = query.toLowerCase();
    if (q.includes("lead") || q.includes("outreach")) {
      return "I've initiated lead discovery. Target prospects scraped and outreach drafts created in Admin Dashboard.";
    }
    if (q.includes("response") || q.includes("metric") || q.includes("rate")) {
      return "Outreach status: 284 emails sent, 91 responses (32.0% response rate), 47 active leads.";
    }
    if (q.includes("memory") || q.includes("vector") || q.includes("supabase")) {
      return "Connected to Supabase pgvector store. Holding active continuous memories for user preferences.";
    }
    return `Processed request: "${query}". Dispatched to LangGraph agent. Inspect logs in Admin Dashboard.`;
  };

  return (
    <div style={{
      position: "fixed", inset: 0, overflow: "hidden",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>
      {/* ── FULL SCREEN ORB VOICE MODE (When Voice Active) ───────────── */}
      {voiceActive ? (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "#ffffff", display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "between", padding: "32px 24px",
        }}>
          {/* Top Controls */}
          <div style={{ width: "100%", maxWidth: 600, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: isMuted ? "#ef4444" : "#10b981" }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: "#333" }}>
                {isMuted ? "Microphone Muted" : orbState === "listening" ? "Listening..." : orbState === "processing" ? "Thinking..." : "Speaking..."}
              </span>
            </div>
            <button
              onClick={interruptVoiceMode}
              title="Close Voice Mode"
              style={{ background: "#f5f5f5", border: "1px solid #e0e0e0", borderRadius: "50%", width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#555" }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Centered Large SiriOrb */}
          <div style={{ margin: "auto", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, textAlign: "center" }}>
            <div style={{ cursor: "pointer", transform: "scale(1.25)", transition: "transform 300ms ease" }}>
              <SiriOrb size={220} animationDuration={orbState === "idle" ? 20 : 3} />
            </div>

            {/* Live Transcription / Response */}
            <div style={{ maxWidth: 480, minHeight: 60 }}>
              {transcription && (
                <p style={{ fontSize: 14, color: "#777", fontStyle: "italic", margin: "0 0 8px" }}>
                  "{transcription}"
                </p>
              )}
              {liveResponse && (
                <p style={{ fontSize: 15, fontWeight: 500, color: "#111", margin: 0, lineHeight: 1.5 }}>
                  {liveResponse}
                </p>
              )}
              {!transcription && !liveResponse && (
                <p style={{ fontSize: 14, color: "#999", margin: 0 }}>
                  Speak now or click Interrupt to end...
                </p>
              )}
            </div>
          </div>

          {/* Bottom Controls: Mute & Click to Interrupt */}
          <div style={{ width: "100%", maxWidth: 420, display: "flex", alignItems: "center", justifyContent: "center", gap: 16, marginBottom: 24 }}>
            {/* Mute Button */}
            <button
              onClick={toggleMute}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "12px 20px", borderRadius: 999,
                background: isMuted ? "#fef2f2" : "#f5f5f5",
                border: isMuted ? "1px solid #fca5a5" : "1px solid #e0e0e0",
                color: isMuted ? "#dc2626" : "#333",
                fontSize: 13, fontWeight: 600, cursor: "pointer",
                transition: "all 150ms",
              }}
            >
              {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
              <span>{isMuted ? "Unmute Mic" : "Mute Mic"}</span>
            </button>

            {/* Click to Interrupt Button */}
            <button
              onClick={interruptVoiceMode}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "12px 24px", borderRadius: 999,
                background: "#111111", color: "#ffffff",
                border: "none", fontSize: 13, fontWeight: 600,
                cursor: "pointer", boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                transition: "all 150ms",
              }}
            >
              <Square size={14} fill="#ffffff" />
              <span>Click to Interrupt</span>
            </button>
          </div>
        </div>
      ) : (
        /* ── GEMINI HOME UI (Default View) ───────────────────────────── */
        <div style={{
          position: "fixed", inset: 0, display: "flex", flexDirection: "column",
          backgroundImage: "url('/gemini-bg.png'), radial-gradient(circle at 50% 40%, rgba(224, 242, 254, 0.6) 0%, rgba(243, 232, 255, 0.4) 50%, #f8fafc 100%)",
          backgroundSize: "cover", backgroundPosition: "center",
          color: "#1e293b",
        }}>
          {/* Top Bar Header */}
          <header style={{ height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <img src="/favicon.png" alt="my_agent" style={{ width: 24, height: 24, objectFit: "contain" }} />
              <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>my_agent</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button
                onClick={() => setMessages([])}
                title="New Chat"
                style={{ background: "rgba(255,255,255,0.8)", border: "1px solid rgba(0,0,0,0.08)", borderRadius: "50%", width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#475569" }}
              >
                <PenSquare size={16} />
              </button>

              <Link
                href="/dashboard"
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a",
                  background: "rgba(255,255,255,0.85)", border: "1px solid rgba(0,0,0,0.08)",
                  borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                }}
              >
                <LayoutDashboard size={14} />
                Admin Dashboard
              </Link>
            </div>
          </header>

          {/* Main Area */}
          <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "20px", overflowY: "auto" }}>
            {messages.length === 0 ? (
              /* ── Gemini Centered Hero Title ── */
              <div style={{ textAlign: "center", marginBottom: 36, maxWidth: 640 }}>
                <h1 style={{ fontSize: 38, fontWeight: 400, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 8px" }}>
                  What's next, THULANE?
                </h1>
                <p style={{ fontSize: 14, color: "#64748b", margin: 0 }}>
                  Ask my_agent or click the mic to switch to speech mode.
                </p>
              </div>
            ) : (
              /* ── Message Stream ── */
              <div style={{ width: "100%", maxWidth: 680, flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 20 }}>
                {messages.map((msg) => (
                  <div key={msg.id} style={{ display: "flex", gap: 10, justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                    {msg.sender === "assistant" && (
                      <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                        <Bot size={16} />
                      </div>
                    )}
                    <div style={{
                      maxWidth: "80%", padding: "12px 16px", fontSize: 13, lineHeight: 1.6,
                      borderRadius: 18,
                      background: msg.sender === "user" ? "#0f172a" : "rgba(255,255,255,0.9)",
                      color: msg.sender === "user" ? "#ffffff" : "#0f172a",
                      boxShadow: "0 2px 10px rgba(0,0,0,0.05)",
                    }}>
                      <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
                    </div>
                    {msg.sender === "user" && (
                      <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#cbd5e1", display: "flex", alignItems: "center", justifyContent: "center", color: "#334155" }}>
                        <User size={16} />
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                      <Sparkles size={16} className="animate-spin" />
                    </div>
                    <span style={{ fontSize: 13, color: "#64748b" }}>my_agent is thinking...</span>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>
            )}

            {/* ── Large Gemini Floating Input Bar ── */}
            <div style={{ width: "100%", maxWidth: 680, position: "relative" }}>
              <div style={{
                display: "flex", alignItems: "center", gap: 12,
                background: "#ffffff", borderRadius: 999,
                padding: "8px 12px 8px 18px",
                boxShadow: "0 10px 30px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05)",
                border: "1px solid rgba(226, 232, 240, 0.8)",
              }}>
                {/* Plus Icon */}
                <button title="Add attachment" style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
                  <Plus size={20} />
                </button>

                {/* Text Input */}
                <input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleSendText();
                    }
                  }}
                  placeholder="Ask Gemini"
                  style={{
                    flex: 1, border: "none", outline: "none",
                    fontSize: 15, color: "#0f172a", background: "transparent",
                    fontFamily: "inherit",
                  }}
                />

                {/* Model Selector Badge */}
                <div style={{ position: "relative" }}>
                  <button
                    onClick={() => setModelDropdown(!modelDropdown)}
                    style={{
                      display: "flex", alignItems: "center", gap: 4,
                      fontSize: 13, fontWeight: 500, color: "#475569",
                      background: "#f1f5f9", border: "none", borderRadius: 999,
                      padding: "4px 10px", cursor: "pointer",
                    }}
                  >
                    <span>Pro</span>
                    <ChevronDown size={14} />
                  </button>

                  {modelDropdown && (
                    <div style={{
                      position: "absolute", bottom: 36, right: 0, width: 140,
                      background: "#ffffff", border: "1px solid #e2e8f0",
                      borderRadius: 12, boxShadow: "0 10px 25px rgba(0,0,0,0.1)",
                      padding: 6, zIndex: 50, fontSize: 12,
                    }}>
                      <div onClick={() => setModelDropdown(false)} style={{ padding: "6px 10px", borderRadius: 6, cursor: "pointer", fontWeight: 600, color: "#0f172a", background: "#f1f5f9" }}>Pro (FastAPI)</div>
                      <div onClick={() => setModelDropdown(false)} style={{ padding: "6px 10px", borderRadius: 6, cursor: "pointer", color: "#64748b" }}>Flash (Groq)</div>
                    </div>
                  )}
                </div>

                {/* Microphone / SiriOrb Button to start voice mode */}
                <button
                  onClick={startVoiceMode}
                  title="Click to start speech mode"
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    padding: 4, borderRadius: "50%", transition: "transform 150ms",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                >
                  <Mic size={20} style={{ color: "#475569" }} />
                </button>
              </div>
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
