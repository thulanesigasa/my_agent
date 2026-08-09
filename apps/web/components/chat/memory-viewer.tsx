"use client";

import React, { useState } from "react";
import { Database, Search, Brain, Sparkles, Clock, Tag } from "lucide-react";

export interface MemoryItem {
  id?: string;
  content: string;
  metadata?: any;
  created_at?: string;
}

interface MemoryViewerProps {
  memories: MemoryItem[];
  onSearchQuery?: (query: string) => void;
}

export const MemoryViewer: React.FC<MemoryViewerProps> = ({
  memories,
  onSearchQuery,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchQuery?.(searchTerm);
  };

  return (
    <div className="flex flex-col h-[580px] glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between bg-black/30">
        <div className="flex items-center gap-2.5">
          <Brain className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-gray-200 tracking-wide">
            Supabase pgvector Memory Vault
          </h3>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-full glass-pill text-cyan-300 font-mono">
          {memories.length} Vector Index Items
        </span>
      </div>

      {/* Search Input */}
      <div className="p-4 border-b border-white/10 bg-black/20">
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search semantic memory index..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-xs text-gray-200 focus:outline-none focus:border-cyan-500 transition-colors"
          />
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
        </form>
      </div>

      {/* Memory Cards Grid */}
      <div className="flex-1 p-5 overflow-y-auto space-y-3">
        {memories.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-400">
            <Database className="w-10 h-10 text-cyan-400/50 mb-3 animate-pulse" />
            <p className="text-sm font-medium text-gray-300">
              No vector memories indexed yet.
            </p>
            <p className="text-xs text-gray-500 max-w-xs mt-1">
              As you interact with the agent, the LearnerNode automatically extracts key facts into Supabase pgvector.
            </p>
          </div>
        ) : (
          memories.map((item, idx) => (
            <div
              key={item.id || idx}
              className="p-4 rounded-xl glass-card border border-white/5 hover:border-cyan-500/30 transition-all duration-300"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 font-mono flex items-center gap-1">
                  <Tag className="w-3 h-3" />
                  {item.metadata?.source || "continuous_learning"}
                </span>
                <span className="text-[10px] text-gray-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Just now"}
                </span>
              </div>
              <p className="text-xs text-gray-200 leading-relaxed font-sans">
                {item.content}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
