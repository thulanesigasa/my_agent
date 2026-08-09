"use client";

import React, { useState, useEffect, useRef } from "react";
import { SiriOrb, SiriOrbState } from "@/components/ui/siri-orb";
import { ChatFeed, ChatMessage } from "@/components/chat/chat-feed";
import { MemoryViewer, MemoryItem } from "@/components/chat/memory-viewer";
import { AgentMonitor } from "@/components/dashboard/agent-monitor";
import { ToolIntegrations } from "@/components/dashboard/tool-integrations";
import { AudioRecorderManager, playBase64Audio } from "@/lib/audio";
import { MessageSquare, Brain, Cpu, ShieldCheck, Sparkles, Activity, Layers } from "lucide-react";

export default function Home() {
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [audioLevel, setAudioLevel] = useState(0.2);
  const [activeTab, setActiveTab] = useState<"chat" | "memory" | "monitor" | "tools">("chat");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [activeNode, setActiveNode] = useState("triage_node");
  const [currentIntent, setCurrentIntent] = useState("general_qa");
  const [isProcessing, setIsProcessing] = useState(false);

  const recorderRef = useRef<AudioRecorderManager | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // Initialize WebSocket connection to Python FastAPI agent backend
  useEffect(() => {
    recorderRef.current = new AudioRecorderManager();
    const wsUrl = process.env.NEXT_PUBLIC_AGENT_WS_URL || "ws://localhost:8000/ws/agent";

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("WebSocket connected to Agent Backend");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "state_change") {
            setOrbState(data.state as SiriOrbState);
          } else if (data.type === "node_execution") {
            setActiveNode(data.node);
          } else if (data.type === "agent_response") {
            const agentMsg: ChatMessage = {
              id: Date.now().toString(),
              sender: "agent",
              text: data.text || "Task complete.",
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              intent: data.intent,
              audioPayload: data.audio_payload,
              requiresApproval: data.requires_human_approval,
              approvalStatus: data.requires_human_approval ? "pending" : "approved",
              memories: data.memories || []
            };

            setMessages((prev) => [...prev, agentMsg]);
            if (data.intent) setCurrentIntent(data.intent);

            if (data.memories && data.memories.length > 0) {
              setMemories((prev) => [...data.memories, ...prev]);
            }

            if (data.audio_payload) {
              playBase64Audio(data.audio_payload);
            }
            setIsProcessing(false);
          }
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      socketRef.current = ws;
    } catch (e) {
      console.warn("WebSocket connection error:", e);
    }

    // Initial memory fetch
    fetchMemories();

    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, []);

  const fetchMemories = async (query: string = "") => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/memory?query=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (data.memories) setMemories(data.memories);
    } catch (e) {
      console.warn("Error fetching memories:", e);
    }
  };

  // Toggle voice recording when clicking SiriOrb
  const handleOrbClick = async () => {
    if (orbState === "idle") {
      setOrbState("listening");
      const success = await recorderRef.current?.startRecording((lvl) => setAudioLevel(lvl));
      if (!success) setOrbState("idle");
    } else if (orbState === "listening") {
      setOrbState("processing");
      const base64Audio = await recorderRef.current?.stopRecording();
      if (base64Audio && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        setIsProcessing(true);
        socketRef.current.send(
          JSON.stringify({ type: "audio_stream", payload: base64Audio })
        );
      } else {
        setOrbState("idle");
      }
    }
  };

  // Send text message
  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setOrbState("processing");
    setIsProcessing(true);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "text_message", text }));
    } else {
      // Fallback HTTP POST
      try {
        const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        const data = await res.json();

        const agentMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          sender: "agent",
          text: data.response || "Request processed.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          intent: data.intent,
          audioPayload: data.audio_payload,
          requiresApproval: data.requires_human_approval,
          approvalStatus: data.requires_human_approval ? "pending" : "approved"
        };
        setMessages((prev) => [...prev, agentMsg]);
        if (data.audio_payload) playBase64Audio(data.audio_payload);
      } catch (e) {
        console.error("HTTP chat error:", e);
      } finally {
        setOrbState("idle");
        setIsProcessing(false);
      }
    }
  };

  // Human-in-the-loop action approval
  const handleApproveAction = async (messageId: string, approved: boolean) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, approvalStatus: approved ? "approved" : "rejected" } : m
      )
    );

    try {
      const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
    } catch (e) {
      console.error("Error submitting approval:", e);
    }
  };

  return (
    <main className="min-h-screen bg-[#08090d] text-gray-100 p-4 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Header Banner */}
      <header className="flex flex-col md:flex-row items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 p-0.5 shadow-lg glow-purple">
            <div className="w-full h-full bg-[#08090d] rounded-[14px] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-gray-100 via-indigo-200 to-gray-400">
              Autonomous AI Agent Platform
            </h1>
            <p className="text-xs text-gray-400">
              LangGraph Multi-Agent • Supabase pgvector • Groq & Gemini 1.5 Pro
            </p>
          </div>
        </div>

        {/* Live System Pills */}
        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1.5 rounded-full glass-pill border border-emerald-500/30 text-emerald-300 font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            FastAPI Live
          </span>
          <span className="text-xs px-3 py-1.5 rounded-full glass-pill border border-indigo-500/30 text-indigo-300 font-mono">
            WebSocket Connected
          </span>
        </div>
      </header>

      {/* Hero SiriOrb Voice Interface */}
      <section className="flex flex-col items-center justify-center py-6 glass-panel rounded-3xl border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />
        <SiriOrb
          state={orbState}
          audioLevel={audioLevel}
          onClick={handleOrbClick}
          size={210}
        />
      </section>

      {/* Navigation Tabs */}
      <nav className="flex items-center justify-center gap-2 border-b border-white/10 pb-4">
        <button
          onClick={() => setActiveTab("chat")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
            activeTab === "chat"
              ? "bg-indigo-600 text-white shadow-lg glow-purple"
              : "glass-pill text-gray-400 hover:text-gray-200"
          }`}
        >
          <MessageSquare className="w-4 h-4" /> Voice & Chat Feed
        </button>
        <button
          onClick={() => setActiveTab("memory")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
            activeTab === "memory"
              ? "bg-cyan-600 text-white shadow-lg glow-cyan"
              : "glass-pill text-gray-400 hover:text-gray-200"
          }`}
        >
          <Brain className="w-4 h-4" /> Memory Vault (pgvector)
        </button>
        <button
          onClick={() => setActiveTab("monitor")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
            activeTab === "monitor"
              ? "bg-purple-600 text-white shadow-lg glow-purple"
              : "glass-pill text-gray-400 hover:text-gray-200"
          }`}
        >
          <Cpu className="w-4 h-4" /> LangGraph Monitor
        </button>
        <button
          onClick={() => setActiveTab("tools")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
            activeTab === "tools"
              ? "bg-pink-600 text-white shadow-lg glow-pink"
              : "glass-pill text-gray-400 hover:text-gray-200"
          }`}
        >
          <ShieldCheck className="w-4 h-4" /> Tool Approvals
        </button>
      </nav>

      {/* Tab Panels */}
      <section>
        {activeTab === "chat" && (
          <ChatFeed
            messages={messages}
            onSendMessage={handleSendMessage}
            onApproveAction={handleApproveAction}
            isProcessing={isProcessing}
          />
        )}

        {activeTab === "memory" && (
          <MemoryViewer
            memories={memories}
            onSearchQuery={(q) => fetchMemories(q)}
          />
        )}

        {activeTab === "monitor" && (
          <div className="space-y-6">
            <AgentMonitor
              activeNode={activeNode}
              intent={currentIntent}
            />
            <ToolIntegrations />
          </div>
        )}

        {activeTab === "tools" && <ToolIntegrations />}
      </section>
    </main>
  );
}
