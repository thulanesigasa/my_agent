"use client";

import React, { useState } from "react";
import {
  LayoutDashboard, Mail, ShieldCheck, Database, Settings,
  Cpu, ChevronLeft, ChevronRight, Circle, Bell, Search
} from "lucide-react";

type NavTab = "overview" | "logs" | "approvals" | "memory" | "settings";

interface AppShellProps {
  children: (activeTab: NavTab, setTab: (t: NavTab) => void) => React.ReactNode;
}

const NAV_ITEMS: { id: NavTab; label: string; icon: React.ElementType; badge?: number }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "logs", label: "Outreach Logs", icon: Mail, badge: 6 },
  { id: "approvals", label: "Approvals", icon: ShieldCheck, badge: 3 },
  { id: "memory", label: "Memory Bank", icon: Database },
  { id: "settings", label: "Settings", icon: Settings },
];

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0f1117] font-sans">
      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside
        className={`relative flex flex-col border-r border-white/[0.06] bg-[#13151c] transition-all duration-300 ${
          collapsed ? "w-[68px]" : "w-[220px]"
        }`}
      >
        {/* Logo */}
        <div className={`flex items-center gap-3 px-4 py-5 ${collapsed ? "justify-center" : ""}`}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
            <Cpu className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-[13px] font-bold text-white leading-none">Agent Platform</p>
              <p className="text-[10px] text-white/30 font-mono mt-0.5">v1.0 Enterprise</p>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="mx-3 h-px bg-white/[0.06]" />

        {/* Nav */}
        <nav className="flex-1 space-y-0.5 px-2 py-4">
          {NAV_ITEMS.map(({ id, label, icon: Icon, badge }) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                title={collapsed ? label : undefined}
                className={`group relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[12.5px] font-medium transition-all duration-150 ${
                  active
                    ? "bg-indigo-500/10 text-indigo-300"
                    : "text-white/40 hover:bg-white/[0.04] hover:text-white/70"
                } ${collapsed ? "justify-center" : ""}`}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-indigo-400" />
                )}
                <Icon className={`h-4 w-4 shrink-0 ${active ? "text-indigo-400" : ""}`} />
                {!collapsed && <span className="flex-1 truncate">{label}</span>}
                {!collapsed && badge && (
                  <span className="rounded-full bg-indigo-500/20 px-1.5 py-0.5 text-[10px] font-bold text-indigo-300">
                    {badge}
                  </span>
                )}
                {collapsed && badge && (
                  <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Status */}
        {!collapsed && (
          <div className="mx-3 mb-4 rounded-xl border border-white/[0.06] bg-white/[0.03] p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-white/40">Backend</span>
              <span className="flex items-center gap-1.5 text-[10px] font-bold text-emerald-400">
                <Circle className="h-1.5 w-1.5 fill-emerald-400" /> ONLINE
              </span>
            </div>
            <p className="mt-1 text-[10px] leading-relaxed text-white/20">
              LangGraph · Groq · Supabase pgvector
            </p>
          </div>
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="absolute -right-3 top-[72px] flex h-6 w-6 items-center justify-center rounded-full border border-white/10 bg-[#1c1f2e] text-white/40 shadow hover:text-white/80 transition-colors"
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </button>
      </aside>

      {/* ── Main Area ──────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/[0.06] bg-[#13151c]/80 px-6 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2">
              <Search className="h-3.5 w-3.5 text-white/30" />
              <input
                placeholder="Search leads, memory, logs..."
                className="w-48 bg-transparent text-[12px] text-white/60 placeholder:text-white/20 outline-none"
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="relative rounded-xl p-2 text-white/30 hover:bg-white/[0.04] hover:text-white/60 transition-colors">
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400" />
            </button>
            <div className="h-7 w-px bg-white/[0.06]" />
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-[11px] font-bold text-white">
                A
              </div>
              {!collapsed && <span className="text-[12px] font-medium text-white/50">Admin</span>}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children(activeTab, setActiveTab)}
        </main>
      </div>
    </div>
  );
};
