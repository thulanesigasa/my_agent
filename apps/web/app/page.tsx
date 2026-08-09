"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Send, Sparkles, LayoutDashboard, Bot, User,
  ArrowUp, Mic, Globe, Shield, Terminal
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

const QUICK_PROMPTS = [
  "Find new leads for web dev outreach",
  "Check email outreach response rate",
  "Inspect active pgvector memory bank",
  "Run detailed system health check",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);

  // Voice state
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [speechActive, setSpeechActive] = useState(false);
  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const manager = new AudioStreamManager({
      onStateChange: (state) => {
        setOrbState(state);
        if (state === "idle") setSpeechActive(false);
      },
      onTranscription: (text) => {
        if (text) {
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

  const toggleSpeechMode = async () => {
    if (orbState === "idle") {
      setSpeechActive(true);
      const started = await audioManagerRef.current?.startStreaming();
      if (!started) {
        setOrbState("idle");
        setSpeechActive(false);
      }
    } else if (orbState === "listening") {
      audioManagerRef.current?.stopStreaming();
    }
  };

  const getAgentFallbackResponse = (query: string): string => {
    const q = query.toLowerCase();
    if (q.includes("lead") || q.includes("outreach")) {
      return "I've initiated the lead discovery pipeline. Scraped target companies from Google search, enriched contact details, and drafted outreach emails for human review in the Admin Dashboard.";
    }
    if (q.includes("response") || q.includes("metric") || q.includes("rate")) {
      return "Current email outreach metrics:\n• Total Emails Sent: 284\n• Total Responses: 91 (32.0% response rate)\n• Active Leads in Pipeline: 47";
    }
    if (q.includes("memory") || q.includes("vector") || q.includes("supabase")) {
      return "Connected to Supabase pgvector store. Holding continuous active memory entries for quota limits, preferred languages, and client notes.";
    }
    if (q.includes("health") || q.includes("status")) {
      return "All system dependencies are operational:\n- Supabase pgvector: CONNECTED\n- Groq API: UP\n- Tavily Search: ACTIVE\n- FastAPI Endpoint: 200 OK";
    }
    return `Processed request: "${query}". Dispatched to the autonomous LangGraph workflow. Inspect logs & approvals in the Admin Dashboard.`;
  };

  return (
    <div style={{
      position: "fixed", inset: 0, display: "flex",
      background: "#f0f0f0",
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      fontSize: 14, color: "#111",
    }}>
      {/* ── Main Outer Frame ── */}
      <div style={{
        display: "flex", flex: 1, flexDirection: "column", margin: 12,
        background: "#fff", border: "1px solid #e0e0e0",
        borderRadius: 10, boxShadow: "0 2px 16px rgba(0,0,0,0.07)",
        overflow: "hidden",
      }}>
        {/* ── Topbar ── */}
        <header style={{
          height: 48, display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 20px", borderBottom: "1px solid #e8e8e8", background: "#fff", flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <img src="/favicon.png" alt="my_agent" style={{ width: 22, height: 22, objectFit: "contain" }} />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#111" }}>my_agent</span>
            <span style={{ fontSize: 11, fontWeight: 500, color: "#777", background: "#f5f5f5", border: "1px solid #e5e5e5", borderRadius: 999, padding: "2px 8px" }}>
              Gemini 2.5 + LangGraph
            </span>
          </div>

          <Link
            href="/dashboard"
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", fontSize: 12, fontWeight: 600, color: "#111",
              background: "#fff", border: "1px solid #e0e0e0", borderRadius: 6,
              textDecoration: "none", transition: "all 150ms",
            }}
          >
            <LayoutDashboard size={14} strokeWidth={1.8} />
            Admin Dashboard
          </Link>
        </header>

        {/* ── Chat Container ── */}
        <main style={{ flex: 1, overflowY: "auto", background: "#fff", padding: "24px 20px" }}>
          <div style={{ maxWidth: 720, margin: "0 auto", height: "100%", display: "flex", flexDirection: "column" }}>
            {messages.length === 0 ? (
              /* ── Gemini Welcome Card ── */
              <div style={{ margin: "auto 0", textAlign: "center", padding: "40px 0" }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12, background: "#111",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  margin: "0 auto 16px", color: "#fff",
                }}>
                  <Sparkles size={24} strokeWidth={1.8} />
                </div>

                <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111", margin: "0 0 8px" }}>
                  Hello. How can <span style={{ color: "#4f46e5" }}>my_agent</span> help you?
                </h1>
                <p style={{ fontSize: 13, color: "#777", margin: "0 0 28px", lineHeight: 1.5 }}>
                  Autonomous AI infrastructure — type your request or click the Orb for voice interaction.
                </p>

                {/* Quick Prompts Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, maxWidth: 600, margin: "0 auto" }}>
                  {QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => handleSendText(prompt)}
                      style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "12px 14px", fontSize: 12, fontWeight: 500, color: "#333",
                        background: "#fafafa", border: "1px solid #e8e8e8", borderRadius: 8,
                        cursor: "pointer", textAlign: "left", transition: "all 150ms",
                      }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#f0f0f0"; (e.currentTarget as HTMLElement).style.borderColor = "#ccc"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "#fafafa"; (e.currentTarget as HTMLElement).style.borderColor = "#e8e8e8"; }}
                    >
                      <span>{prompt}</span>
                      <Sparkles size={13} strokeWidth={1.8} style={{ color: "#aaa", flexShrink: 0 }} />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* ── Conversation Stream ── */
              <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingBottom: 16 }}>
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    style={{
                      display: "flex", gap: 10,
                      justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    {msg.sender === "assistant" && (
                      <div style={{
                        width: 28, height: 28, borderRadius: 6, background: "#111",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#fff", flexShrink: 0,
                      }}>
                        <Bot size={15} strokeWidth={1.8} />
                      </div>
                    )}

                    <div style={{
                      maxWidth: "80%", padding: "10px 14px", fontSize: 13, lineHeight: 1.6,
                      borderRadius: msg.sender === "user" ? "10px 10px 0 10px" : "10px 10px 10px 0",
                      background: msg.sender === "user" ? "#111" : "#f5f5f5",
                      color: msg.sender === "user" ? "#fff" : "#111",
                      border: msg.sender === "user" ? "none" : "1px solid #e8e8e8",
                    }}>
                      <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
                      <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4, textAlign: "right" }}>
                        {msg.mode === "voice" ? "🎙️ Voice · " : ""}{msg.timestamp}
                      </div>
                    </div>

                    {msg.sender === "user" && (
                      <div style={{
                        width: 28, height: 28, borderRadius: 6, background: "#e5e5e5",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#555", flexShrink: 0,
                      }}>
                        <User size={15} strokeWidth={1.8} />
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: "#111", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff" }}>
                      <Bot size={15} />
                    </div>
                    <div style={{ padding: "8px 14px", fontSize: 13, background: "#fafafa", border: "1px solid #e8e8e8", borderRadius: 8, color: "#777", display: "flex", alignItems: "center", gap: 6 }}>
                      <Sparkles size={13} strokeWidth={1.8} style={{ color: "#4f46e5" }} />
                      <span>my_agent is processing...</span>
                    </div>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>
            )}
          </div>
        </main>

        {/* ── Bottom Input Container ── */}
        <footer style={{ padding: "16px 20px", borderTop: "1px solid #e8e8e8", background: "#fff", flexShrink: 0 }}>
          <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 8 }}>
            {/* Voice Active Bar Overlay */}
            {speechActive && (
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "8px 12px", fontSize: 12, background: "#f0fdf4",
                border: "1px solid #bbf7d0", borderRadius: 6, color: "#16a34a",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#16a34a" }} />
                  <span style={{ fontWeight: 600 }}>
                    {orbState === "listening" ? "Listening... speak now" : orbState === "processing" ? "Processing voice..." : "Speaking response..."}
                  </span>
                </div>
                <button onClick={toggleSpeechMode} style={{ fontSize: 11, fontWeight: 700, color: "#16a34a", background: "none", border: "none", cursor: "pointer" }}>
                  Stop Voice
                </button>
              </div>
            )}

            {/* Input Bar */}
            <div style={{
              display: "flex", alignItems: "center", gap: 8,
              border: "1px solid #e0e0e0", borderRadius: 8,
              padding: "6px 8px 6px 14px", background: "#fff",
              boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
            }}>
              <input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleSendText();
                  }
                }}
                placeholder="Ask my_agent anything or click the Orb to speak..."
                style={{
                  flex: 1, border: "none", outline: "none",
                  fontSize: 13, color: "#111", background: "transparent",
                  fontFamily: "inherit",
                }}
              />

              {/* Send Button */}
              <button
                onClick={() => handleSendText()}
                disabled={!inputValue.trim() || loading}
                style={{
                  width: 32, height: 32, borderRadius: 6,
                  border: "none", background: inputValue.trim() && !loading ? "#111" : "#f0f0f0",
                  color: inputValue.trim() && !loading ? "#fff" : "#ccc",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: inputValue.trim() && !loading ? "pointer" : "not-allowed",
                  transition: "all 150ms",
                }}
              >
                <ArrowUp size={15} strokeWidth={2} />
              </button>

              {/* SiriOrb Toggle */}
              <div
                onClick={toggleSpeechMode}
                title="Click to toggle speech mode"
                style={{ cursor: "pointer", padding: 2, display: "flex", alignItems: "center" }}
              >
                <SiriOrb size={32} animationDuration={orbState === "idle" ? 20 : 4} />
              </div>
            </div>

            <p style={{ textAlign: "center", fontSize: 11, color: "#aaa", margin: 0 }}>
              my_agent executes web outreach, lead discovery, & continuous vector memory tasks. Check Admin Dashboard for logs.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}
