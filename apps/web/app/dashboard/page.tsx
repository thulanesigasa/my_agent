"use client";

import React, { useState, useEffect } from "react";
import { LayoutDashboard, ShieldCheck, Database, BarChart3, Activity, Cpu } from "lucide-react";
import { getSystemHealth, SystemHealth } from "@/lib/api";
import { ApprovalQueueDashboard } from "@/components/dashboard/approval_queue";
import { MemoryViewer } from "@/components/dashboard/memory-viewer";
import { AnalyticsDashboard } from "@/components/dashboard/analytics";

type TabType = "overview" | "approvals" | "memory";

export default function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [health, setHealth] = useState<SystemHealth>({ status: "healthy" });

  useEffect(() => {
    getSystemHealth().then((h) => setHealth(h));
  }, []);

  return (
    <div className="min-h-screen w-screen bg-slate-50 flex text-slate-800 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-200 bg-white p-6 flex flex-col justify-between select-none">
        <div className="space-y-6">
          <div className="flex items-center gap-3 px-2">
            <div className="p-2 rounded-xl bg-indigo-600 text-white shadow">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 leading-none">
                Autonomous Agent
              </h1>
              <span className="text-[10px] text-slate-400 font-mono">v1.0.0 Enterprise</span>
            </div>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab("overview")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "overview"
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" /> System Overview
            </button>

            <button
              onClick={() => setActiveTab("approvals")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "approvals"
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <ShieldCheck className="w-4 h-4" /> Approval Queue
            </button>

            <button
              onClick={() => setActiveTab("memory")}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                activeTab === "memory"
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <Database className="w-4 h-4" /> Memory Bank (pgvector)
            </button>
          </nav>
        </div>

        {/* System Health Badge */}
        <div className="p-3.5 rounded-xl bg-slate-100/80 border border-slate-200 space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-600 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-500" /> Backend Status
            </span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                health.status === "UP" || health.status === "healthy"
                  ? "bg-emerald-100 text-emerald-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {health.status}
            </span>
          </div>
          <p className="text-[10px] text-slate-400">
            LangGraph engine running on 0.0.0.0:8000
          </p>
        </div>
      </aside>

      {/* Main Content Viewport */}
      <main className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-5xl mx-auto space-y-8">
          {activeTab === "overview" && (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Admin Control Center</h2>
                  <p className="text-xs text-slate-500">
                    Real-time monitoring for LangGraph state graph and multi-agent execution
                  </p>
                </div>
              </div>
              <AnalyticsDashboard />
              <ApprovalQueueDashboard />
            </>
          )}

          {activeTab === "approvals" && <ApprovalQueueDashboard />}
          {activeTab === "memory" && <MemoryViewer />}
        </div>
      </main>
    </div>
  );
}
