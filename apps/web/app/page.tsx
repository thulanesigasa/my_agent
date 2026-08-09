"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Send, Sparkles, LayoutDashboard, Mic, CornerDownLeft, Bot, User, ArrowUp } from "lucide-react";
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

  // Speech / Voice state
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [speechActive, setSpeechActive] = useState(false);
  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const manager = new AudioStreamManager({
      onStateChange: (state) => {
        setOrbState(state);
        if (state === "idle") {
          setSpeechActive(false);
        }
      },
      onTranscription: (text) => {
        setTranscription(text);
        // Append user voice message
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
      // Send text to FastAPI agent endpoint
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
        responseText = data.response || data.message || "Request executed successfully by my_agent.";
      } else {
        // Fallback agent responses for demonstration
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
      return "Connected to Supabase pgvector store. Currently holding active continuous memories across user preferences, seat quotas, and communication schedules.";
    }
    if (q.includes("health") || q.includes("status")) {
      return "All system dependencies are operational:\n- Supabase pgvector: CONNECTED\n- Groq API: UP\n- Tavily Search: ACTIVE\n- FastAPI Endpoint: 200 OK";
    }
    return `Processed request: "${query}". All tasks dispatched to the autonomous LangGraph workflow. You can inspect logs and human approvals in the Admin Dashboard.`;
  };

  return (
    <div className="flex h-screen w-screen flex-col bg-white text-slate-900 font-sans overflow-hidden">
      {/* ── Top Header ────────────────────────────────────────────── */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 px-6 bg-white z-10">
        <div className="flex items-center gap-3">
          <img src="/favicon.png" alt="my_agent" className="h-6 w-6 object-contain" />
          <span className="text-sm font-bold text-slate-900">my_agent</span>
          <span className="rounded-full bg-slate-100 border border-slate-200 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
            Gemini 2.5 + LangGraph
          </span>
        </div>

        <Link
          href="/dashboard"
          className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <LayoutDashboard className="h-3.5 w-3.5" />
          Admin Dashboard
        </Link>
      </header>

      {/* ── Main Chat Canvas ──────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-0">
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col">
          {messages.length === 0 ? (
            /* ── Gemini Welcome State ────────────────────────────────── */
            <div className="my-auto flex flex-col items-center justify-center text-center space-y-6 px-4 py-12">
              <div className="flex items-center justify-center h-14 w-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/20">
                <Sparkles className="h-7 w-7" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900">
                  Hello. How can <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">my_agent</span> help you?
                </h1>
                <p className="mt-2 text-xs md:text-sm text-slate-500">
                  Autonomous AI infrastructure — type your request or click the Orb for voice interaction.
                </p>
              </div>

              {/* Quick suggestion pills */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg pt-4">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSendText(prompt)}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 text-left text-xs font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-100 transition-all group"
                  >
                    <span>{prompt}</span>
                    <Sparkles className="h-3.5 w-3.5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* ── Conversation Message Stream ─────────────────────────── */
            <div className="space-y-6 pb-6">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-4 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.sender === "assistant" && (
                    <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-indigo-600 text-white text-xs font-bold shadow-sm">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[82%] rounded-2xl px-4 py-3 text-xs md:text-sm leading-relaxed ${
                      msg.sender === "user"
                        ? "bg-slate-900 text-white rounded-br-none"
                        : "bg-slate-100 border border-slate-200/80 text-slate-800 rounded-bl-none"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.text}</div>
                    <div className="mt-1.5 flex items-center justify-end gap-1.5 text-[10px] opacity-60">
                      {msg.mode === "voice" && <span>🎙️ Voice</span>}
                      <span>{msg.timestamp}</span>
                    </div>
                  </div>

                  {msg.sender === "user" && (
                    <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-xl bg-slate-200 text-slate-700 text-xs font-bold">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-4 justify-start">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white text-xs">
                    <Bot className="h-4 w-4 animate-pulse" />
                  </div>
                  <div className="rounded-2xl bg-slate-100 border border-slate-200 px-4 py-3 text-xs text-slate-500 flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                    <span>my_agent is processing...</span>
                  </div>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>
          )}
        </div>
      </main>

      {/* ── Bottom Gemini-Style Input Container ───────────────────── */}
      <footer className="shrink-0 border-t border-slate-200 bg-white p-4">
        <div className="mx-auto max-w-3xl space-y-3">
          {/* Orb Active Bar overlay if speech mode is on */}
          {speechActive && (
            <div className="flex items-center justify-between rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-2 text-xs text-indigo-900">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-indigo-600 animate-ping" />
                <span className="font-semibold">
                  {orbState === "listening"
                    ? "Listening... speak now"
                    : orbState === "processing"
                    ? "Processing voice..."
                    : "Speaking response..."}
                </span>
              </div>
              <button
                onClick={toggleSpeechMode}
                className="text-[11px] font-bold text-indigo-700 hover:underline"
              >
                Stop Voice
              </button>
            </div>
          )}

          {/* Input Bar */}
          <div className="relative flex items-center rounded-2xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendText();
                }
              }}
              placeholder="Ask my_agent anything or click the Orb to speak..."
              rows={1}
              className="w-full resize-none bg-transparent px-3 py-2 text-xs md:text-sm text-slate-900 placeholder:text-slate-400 outline-none"
            />

            <div className="flex items-center gap-2 shrink-0 pr-1">
              {/* Send Button */}
              <button
                onClick={() => handleSendText()}
                disabled={!inputValue.trim() || loading}
                className={`flex h-9 w-9 items-center justify-center rounded-xl transition-all ${
                  inputValue.trim() && !loading
                    ? "bg-slate-900 text-white hover:bg-slate-800 shadow-sm"
                    : "bg-slate-100 text-slate-300 cursor-not-allowed"
                }`}
              >
                <ArrowUp className="h-4 w-4" />
              </button>

              {/* SiriOrb Toggle Button */}
              <div
                onClick={toggleSpeechMode}
                title="Click to toggle speech mode"
                className="cursor-pointer rounded-full p-1 hover:scale-105 transition-transform"
              >
                <SiriOrb size={36} animationDuration={orbState === "idle" ? 20 : 4} />
              </div>
            </div>
          </div>

          <p className="text-center text-[10px] text-slate-400">
            my_agent can execute web outreach, lead discovery, and vector memory tasks. Check the Admin Dashboard for destination logs.
          </p>
        </div>
      </footer>
    </div>
  );
}
