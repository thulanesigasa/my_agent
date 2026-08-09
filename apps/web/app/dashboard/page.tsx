"use client";

import React, { useState, useEffect } from "react";
import {
  LayoutDashboard, Mail, ShieldCheck, Activity, Cpu, Circle
} from "lucide-react";
import { getSystemHealth, SystemHealth } from "@/lib/api";
import { AnalyticsDashboard } from "@/components/dashboard/analytics";
import { EmailLogsTable } from "@/components/dashboard/email-logs";
import { ApprovalQueueDashboard } from "@/components/dashboard/approval_queue";

type TabType = "overview" | "logs" | "approvals";

export default function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [health, setHealth] = useState<SystemHealth>({ status: "healthy" });

  useEffect(() => {
    getSystemHealth().then(setHealth);
  }, []);

  const isUp =
    health.status === "UP" || health.status === "healthy";

  const navItems: { id: TabType; label: string; icon: React.ElementType }[] = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "logs", label: "Outreach Logs", icon: Mail },
    { id: "approvals", label: "Approval Queue", icon: ShieldCheck },
  ];

  return (
    <div className="min-h-screen w-screen bg-slate-50 flex select-none font-sans overflow-hidden">
      {/* ── Sidebar ────────────────────────────────────── */}
      <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col justify-between px-5 py-7">
        <div className="space-y-7">
          {/* Logo */}
          <div className="flex items-center gap-3 px-1">
            <div className="p-2 rounded-xl bg-indigo-600 text-white shadow">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 leading-none">Agent Platform</h1>
              <span className="text-[10px] text-slate-400 font-mono">v1.0 Enterprise</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-1">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all text-left ${
                  activeTab === id
                    ? "bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* Health Badge */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-600 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" /> Backend Status
            </span>
            <span
              className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                isUp
                  ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                  : "text-amber-700 bg-amber-50 border-amber-200"
              }`}
            >
              <Circle className={`w-1.5 h-1.5 fill-current ${isUp ? "text-emerald-500" : "text-amber-500"}`} />
              {isUp ? "ONLINE" : health.status.toUpperCase()}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            LangGraph engine · Groq Whisper · Edge-TTS · Supabase pgvector
          </p>
        </div>
      </aside>

      {/* ── Main Content ───────────────────────────────── */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto space-y-8">
          {activeTab === "overview" && (
            <>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Email Outreach Command Center</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Real-time monitoring of agent-drafted email campaigns, responses, and pipeline conversion
                </p>
              </div>
              <AnalyticsDashboard />
              <EmailLogsTable />
            </>
          )}

          {activeTab === "logs" && (
            <>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Outreach Logs</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Full email log with recipient details, thread content, and client replies
                </p>
              </div>
              <EmailLogsTable />
            </>
          )}

          {activeTab === "approvals" && (
            <>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Human-in-the-Loop Approval Queue</h2>
                <p className="text-xs text-slate-400 mt-1">
                  Review and approve outgoing email drafts before they are dispatched
                </p>
              </div>
              <ApprovalQueueDashboard />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
