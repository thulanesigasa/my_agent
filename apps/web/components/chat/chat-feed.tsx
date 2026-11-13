"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Volume2, Sparkles, AlertTriangle, ShieldCheck } from "lucide-react";
import { playBase64Audio } from "@/lib/audio";

export interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text: string;
  timestamp: string;
  intent?: string;
  audioPayload?: string;
  requiresApproval?: boolean;
  approvalStatus?: string;
  memories?: any[];
}

interface ChatFeedProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
  onApproveAction?: (messageId: string, approved: boolean) => void;
  isProcessing?: boolean;
}

export const ChatFeed: React.FC<ChatFeedProps> = ({
  messages,
  onSendMessage,
  onApproveAction,
  isProcessing = false,
}) => {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-[580px] glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
      {/* Feed Header */}
      <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between bg-black/30">
        <div className="flex items-center gap-2.5">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-ping" />
          <h3 className="text-sm font-semibold text-gray-200 tracking-wide">
            Autonomous Conversation Feed
          </h3>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full glass-pill text-indigo-300 font-mono">
          LangGraph Active
        </span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-5 overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-400">
            <Sparkles className="w-10 h-10 text-indigo-400/60 mb-3 animate-bounce" />
            <p className="text-sm font-medium text-gray-300">
              Start talking to your continuous learning AI agent.
            </p>
            <p className="text-xs text-gray-500 max-w-sm mt-1">
              Voice commands, emails, WhatsApp messages, and vector memory recall are active.
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex gap-3 ${
                  msg.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.sender === "agent" && (
                  <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-indigo-300" />
                  </div>
                )}

                <div
                  className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed shadow-lg ${
                    msg.sender === "user"
                      ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-br-none"
                      : "glass-card text-gray-200 border border-white/10 rounded-bl-none"
                  }`}
                >
                  {/* Intent & Memory badges */}
                  {msg.sender === "agent" && msg.intent && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono">
                        intent: {msg.intent}
                      </span>
                      {msg.audioPayload && (
                        <button
                          onClick={() => playBase64Audio(msg.audioPayload!)}
                          className="flex items-center gap-1 text-[10px] text-pink-300 hover:text-pink-200 glass-pill px-2 py-0.5 rounded-full"
                        >
                          <Volume2 className="w-3 h-3" /> Play Voice
                        </button>
                      )}
                    </div>
                  )}

                  <p className="whitespace-pre-wrap">{msg.text}</p>

                  {/* Human-in-the-loop Approval Card */}
                  {msg.requiresApproval && msg.approvalStatus === "pending" && (
                    <div className="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30">
                      <div className="flex items-center gap-2 text-amber-400 font-medium text-xs mb-2">
                        <AlertTriangle className="w-4 h-4" />
                        Human Approval Required for High-Risk Task
                      </div>
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => onApproveAction?.(msg.id, true)}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1 shadow"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" /> Approve & Execute
                        </button>
                        <button
                          onClick={() => onApproveAction?.(msg.id, false)}
                          className="px-3 py-1.5 bg-red-600/80 hover:bg-red-500 text-white text-xs font-semibold rounded-lg"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  )}

                  <span className="block text-[10px] opacity-40 text-right mt-1">
                    {msg.timestamp}
                  </span>
                </div>

                {msg.sender === "user" && (
                  <div className="w-8 h-8 rounded-full bg-cyan-600/30 border border-cyan-500/40 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-cyan-300" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-white/10 bg-black/40 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask agent, search memories, draft email..."
          disabled={isProcessing}
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500 transition-colors placeholder:text-gray-500"
        />
        <button
          type="submit"
          disabled={isProcessing || !input.trim()}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl font-medium transition-all shadow-lg flex items-center gap-1.5"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
