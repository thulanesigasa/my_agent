"use client";

import React from "react";
import { Mail, MessageSquare, Database, Zap, Cpu, Volume2, ShieldCheck } from "lucide-react";

export const ToolIntegrations: React.FC = () => {
  const tools = [
    {
      name: "Groq (Llama 3.3 70B & Whisper)",
      type: "Fast Triage & STT",
      status: "Active",
      icon: <Zap className="w-4 h-4 text-cyan-400" />,
      color: "border-cyan-500/30 bg-cyan-500/5",
    },
    {
      name: "Google AI Studio (Gemini 1.5 Pro)",
      type: "Long-Context Drafting",
      status: "Active",
      icon: <Cpu className="w-4 h-4 text-purple-400" />,
      color: "border-purple-500/30 bg-purple-500/5",
    },
    {
      name: "Supabase (PostgreSQL pgvector)",
      type: "Vector Memory Store",
      status: "Active",
      icon: <Database className="w-4 h-4 text-emerald-400" />,
      color: "border-emerald-500/30 bg-emerald-500/5",
    },
    {
      name: "Edge-TTS & Web Audio",
      type: "Neural Voice Output",
      status: "Active",
      icon: <Volume2 className="w-4 h-4 text-pink-400" />,
      color: "border-pink-500/30 bg-pink-500/5",
    },
    {
      name: "Gmail API Adapter",
      type: "Email Automation",
      status: "Approval Required",
      icon: <Mail className="w-4 h-4 text-amber-400" />,
      color: "border-amber-500/30 bg-amber-500/5",
    },
    {
      name: "WhatsApp / Twilio Adapter",
      type: "Messaging Dispatch",
      status: "Approval Required",
      icon: <MessageSquare className="w-4 h-4 text-indigo-400" />,
      color: "border-indigo-500/30 bg-indigo-500/5",
    },
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 shadow-2xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-gray-100">
            Multi-Model & Integration Services
          </h3>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full glass-pill text-indigo-300 font-mono">
          6 Connected Services
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {tools.map((t, idx) => (
          <div
            key={idx}
            className={`p-3.5 rounded-xl border ${t.color} flex items-center justify-between transition-transform hover:scale-[1.02]`}
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-black/40 border border-white/10">
                {t.icon}
              </div>
              <div>
                <h4 className="text-xs font-semibold text-gray-200">
                  {t.name}
                </h4>
                <p className="text-[10px] text-gray-400">{t.type}</p>
              </div>
            </div>
            <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-gray-300 font-mono">
              {t.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
