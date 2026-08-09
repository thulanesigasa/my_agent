"use client";

import React, { useState } from "react";
import { Search, Trash2, Database, Sparkles, RefreshCw } from "lucide-react";
import { queryAgentMemory, deleteMemory, MemoryRecord } from "@/lib/api";

export const MemoryViewer: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [memories, setMemories] = useState<MemoryRecord[]>([
    {
      id: "mem_01",
      namespace: "users:cto@enterprise-client.com",
      key: "pref_seats",
      value: { content: "Client requested 50 seat enterprise license pricing." },
      created_at: "2 hours ago",
    },
    {
      id: "mem_02",
      namespace: "users:support@tier1.io",
      key: "pref_lang",
      value: { content: "Preferred communication language: English (Formal)." },
      created_at: "1 day ago",
    },
  ]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    const results = await queryAgentMemory(searchQuery);
    if (results.length > 0) {
      setMemories(results);
    }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    const success = await deleteMemory(id);
    if (success) {
      setMemories((prev) => prev.filter((m) => m.id !== id));
    }
  };

  return (
    <div className="w-full bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-50 text-purple-600 border border-purple-200">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-800">
              Vector Memory Store Inspector
            </h3>
            <p className="text-xs text-slate-500">
              Inspect, search, and manage continuous facts stored in Supabase pgvector
            </p>
          </div>
        </div>
      </div>

      {/* Semantic Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search past facts by semantic query (e.g. 'enterprise pricing', 'preferred language')..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-purple-400 text-slate-800"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-colors shadow"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Query Memory
        </button>
      </form>

      {/* Memory List */}
      <div className="space-y-3">
        {memories.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No memories match your semantic search query.
          </div>
        ) : (
          memories.map((mem) => (
            <div
              key={mem.id}
              className="p-4 rounded-xl border border-slate-100 bg-slate-50/60 flex items-start justify-between gap-4 hover:border-purple-200 transition-colors"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-[10px] font-mono text-purple-600 font-semibold">
                  <span>{mem.namespace}</span>
                  <span className="text-slate-300">•</span>
                  <span className="text-slate-400">{mem.key}</span>
                </div>
                <p className="text-xs text-slate-800 font-medium">
                  {mem.value.content || JSON.stringify(mem.value)}
                </p>
                <span className="text-[10px] text-slate-400 block pt-1">
                  Recorded: {mem.created_at || "Recently"}
                </span>
              </div>

              <button
                onClick={() => handleDelete(mem.id)}
                className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                title="Delete Memory Record"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
