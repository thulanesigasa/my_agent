"use client";

import React from "react";
import { motion } from "framer-motion";
import { Cpu, ArrowRight, ShieldAlert, CheckCircle2, Zap, Brain } from "lucide-react";

interface AgentMonitorProps {
  activeNode?: string;
  intent?: string;
  approvalRequired?: boolean;
}

export const AgentMonitor: React.FC<AgentMonitorProps> = ({
  activeNode = "triage_node",
  intent = "general_qa",
  approvalRequired = false,
}) => {
  const nodes = [
    {
      id: "triage_node",
      name: "Triage Node",
      model: "Groq (Llama 3.3 70B)",
      color: "from-cyan-500 to-blue-600",
      description: "Fast intent routing & memory lookup",
    },
    {
      id: "human_approval_node",
      name: "Approval Gate",
      model: "Human-in-the-Loop",
      color: "from-amber-500 to-orange-600",
      description: "High-risk action check",
    },
    {
      id: "drafter_node",
      name: "Drafter Node",
      model: "Gemini 1.5 Pro",
      color: "from-purple-500 to-indigo-600",
      description: "Deep reasoning & drafting",
    },
    {
      id: "learner_node",
      name: "Learner Node",
      model: "Supabase pgvector",
      color: "from-emerald-500 to-teal-600",
      description: "Continuous memory indexer",
    },
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-500/20 border border-purple-500/30">
            <Cpu className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-100">
              LangGraph State Machine Visualizer
            </h3>
            <p className="text-xs text-gray-400">
              Real-time multi-agent execution pipeline & state routing
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 font-mono flex items-center gap-1.5 border border-indigo-500/30">
            <Zap className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
            Intent: {intent}
          </span>
        </div>
      </div>

      {/* State Graph Nodes Flow */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
        {nodes.map((node, index) => {
          const isActive = activeNode === node.id;
          return (
            <div key={node.id} className="relative">
              <motion.div
                animate={{
                  scale: isActive ? 1.03 : 1,
                  borderColor: isActive
                    ? "rgba(168, 85, 247, 0.6)"
                    : "rgba(255, 255, 255, 0.08)",
                }}
                className={`p-4 rounded-xl glass-card transition-all duration-300 relative overflow-hidden ${
                  isActive ? "border-2 shadow-xl shadow-purple-500/10" : ""
                }`}
              >
                {isActive && (
                  <div className="absolute top-0 right-0 w-16 h-16 bg-purple-500/10 rounded-full blur-xl animate-pulse" />
                )}

                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-200">
                    {node.name}
                  </span>
                  {isActive ? (
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-gray-600" />
                  )}
                </div>

                <div className="text-[10px] px-2 py-0.5 rounded glass-pill text-gray-400 w-fit mb-2 font-mono">
                  {node.model}
                </div>

                <p className="text-[11px] text-gray-400 leading-tight">
                  {node.description}
                </p>
              </motion.div>

              {index < nodes.length - 1 && (
                <div className="hidden md:block absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-gray-600">
                  <ArrowRight className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
