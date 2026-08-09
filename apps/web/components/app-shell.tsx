"use client";

import React, { useState } from "react";
import {
  LayoutDashboard, Mail, ShieldCheck, Database,
  Settings, Cpu, Bell, Search, ChevronLeft, ChevronRight,
  ChevronsUpDown, Check, Circle
} from "lucide-react";

type NavTab = "overview" | "logs" | "approvals" | "memory" | "settings";

const NAV: { id: NavTab; label: string; icon: React.ElementType; badge?: number }[] = [
  { id: "overview",  label: "Overview",       icon: LayoutDashboard },
  { id: "logs",      label: "Outreach Logs",  icon: Mail,           badge: 6  },
  { id: "approvals", label: "Approvals",      icon: ShieldCheck,    badge: 3  },
  { id: "memory",    label: "Memory Bank",    icon: Database               },
  { id: "settings",  label: "Settings",       icon: Settings               },
];

interface AppShellProps {
  children: React.ReactNode;
}

// ── Context so Dashboard can read the active tab ────────────────────
export const TabContext = React.createContext<{
  tab: NavTab;
  setTab: (t: NavTab) => void;
}>({ tab: "overview", setTab: () => {} });

export function AppShell({ children }: AppShellProps) {
  const [tab, setTab]           = useState<NavTab>("overview");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <TabContext.Provider value={{ tab, setTab }}>
      {/* Root — fixed full-screen dark canvas */}
      <div
        style={{
          position: "fixed", inset: 0,
          display: "flex", overflow: "hidden",
          background: "hsl(224 71% 4%)",   /* --background */
          color: "hsl(213 31% 91%)",        /* --foreground */
          fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        }}
      >
        {/* ── Sidebar ── */}
        <aside
          style={{
            width: collapsed ? 64 : 220,
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            transition: "width 280ms cubic-bezier(.4,0,.2,1)",
            background: "hsl(222.2 84% 4.9%)",
            borderRight: "1px solid hsl(217.2 32.6% 17.5%)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          {/* Logo */}
          <div style={{ padding: "18px 16px 14px", display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 32, height: 32, flexShrink: 0,
              borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
              background: "linear-gradient(135deg, hsl(239 84% 67%), hsl(262 83% 58%))",
              boxShadow: "0 4px 14px rgba(99,102,241,.45)",
            }}>
              <Cpu size={15} color="#fff" />
            </div>
            {!collapsed && (
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 13, fontWeight: 700, color: "hsl(210 40% 98%)", lineHeight: 1.2, whiteSpace: "nowrap" }}>
                  Agent Platform
                </p>
                <p style={{ fontSize: 10, color: "hsl(215 20.2% 35%)", fontFamily: "monospace", marginTop: 2 }}>
                  v1.0 Enterprise
                </p>
              </div>
            )}
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: "hsl(217.2 32.6% 17.5%)", margin: "0 12px" }} />

          {/* Nav items */}
          <nav style={{ flex: 1, padding: "12px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
            {NAV.map(({ id, label, icon: Icon, badge }) => {
              const active = tab === id;
              return (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  title={collapsed ? label : undefined}
                  style={{
                    width: "100%", display: "flex", alignItems: "center",
                    gap: 10, padding: collapsed ? "10px 0" : "9px 12px",
                    justifyContent: collapsed ? "center" : "flex-start",
                    borderRadius: 10, border: "none", cursor: "pointer",
                    fontSize: 13, fontWeight: 500, textAlign: "left",
                    position: "relative", transition: "all 150ms",
                    background: active ? "hsl(239 84% 67% / .12)" : "transparent",
                    color: active ? "hsl(239 100% 80%)" : "hsl(215 20.2% 55%)",
                  }}
                  onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "hsl(215 27.9% 16.9%)"; }}
                  onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                >
                  {/* Active accent bar */}
                  {active && (
                    <span style={{
                      position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)",
                      width: 3, height: 20, borderRadius: "0 3px 3px 0",
                      background: "hsl(239 84% 67%)",
                    }} />
                  )}
                  <Icon size={16} style={{ flexShrink: 0, color: active ? "hsl(239 84% 72%)" : "hsl(215 20.2% 45%)" }} />
                  {!collapsed && <span style={{ flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{label}</span>}
                  {!collapsed && badge && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 999,
                      background: "hsl(239 84% 67% / .15)", color: "hsl(239 100% 77%)",
                    }}>{badge}</span>
                  )}
                  {collapsed && badge && (
                    <span style={{
                      position: "absolute", top: 6, right: 8,
                      width: 6, height: 6, borderRadius: "50%", background: "hsl(239 84% 67%)",
                    }} />
                  )}
                </button>
              );
            })}
          </nav>

          {/* Backend status */}
          {!collapsed && (
            <div style={{
              margin: "0 10px 14px",
              borderRadius: 12,
              border: "1px solid hsl(217.2 32.6% 17.5%)",
              background: "hsl(215 27.9% 16.9% / .4)",
              padding: "10px 12px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: "hsl(215 20.2% 45%)" }}>Backend</span>
                <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10, fontWeight: 700, color: "hsl(142.1 70.6% 45.3%)" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "hsl(142.1 70.6% 45.3%)", display: "inline-block" }} />
                  ONLINE
                </span>
              </div>
              <p style={{ fontSize: 10, color: "hsl(215 20.2% 35%)", marginTop: 5, lineHeight: 1.6 }}>
                LangGraph · Groq · Supabase pgvector
              </p>
            </div>
          )}

          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed(c => !c)}
            style={{
              position: "absolute", right: -12, top: 72,
              width: 24, height: 24, borderRadius: "50%",
              border: "1px solid hsl(217.2 32.6% 17.5%)",
              background: "hsl(222.2 84% 4.9%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              cursor: "pointer", color: "hsl(215 20.2% 45%)",
              boxShadow: "0 2px 8px rgba(0,0,0,.4)",
              zIndex: 10,
            }}
          >
            {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
          </button>
        </aside>

        {/* ── Main area ── */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Top bar */}
          <header style={{
            height: 56, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "0 24px",
            background: "hsl(222.2 84% 4.9% / .85)",
            borderBottom: "1px solid hsl(217.2 32.6% 17.5%)",
            backdropFilter: "blur(8px)",
          }}>
            {/* Breadcrumb */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, color: "hsl(215 20.2% 45%)" }}>Agent Platform</span>
              <span style={{ fontSize: 12, color: "hsl(215 20.2% 35%)" }}>/</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: "hsl(210 40% 88%)" }}>
                {NAV.find(n => n.id === tab)?.label}
              </span>
            </div>

            {/* Right controls */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {/* Search */}
              <div style={{
                display: "flex", alignItems: "center", gap: 8,
                border: "1px solid hsl(217.2 32.6% 17.5%)",
                borderRadius: 10, padding: "6px 12px",
                background: "hsl(215 27.9% 16.9% / .5)",
              }}>
                <Search size={13} style={{ color: "hsl(215 20.2% 40%)" }} />
                <input
                  placeholder="Search..."
                  style={{
                    width: 160, background: "transparent", border: "none", outline: "none",
                    fontSize: 12, color: "hsl(210 40% 80%)",
                  }}
                />
              </div>

              {/* Bell */}
              <button style={{
                position: "relative", width: 36, height: 36, borderRadius: 10,
                border: "1px solid hsl(217.2 32.6% 17.5%)",
                background: "transparent", cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "hsl(215 20.2% 45%)",
              }}>
                <Bell size={15} />
                <span style={{
                  position: "absolute", top: 7, right: 7,
                  width: 6, height: 6, borderRadius: "50%", background: "hsl(239 84% 67%)",
                }} />
              </button>

              {/* Divider */}
              <div style={{ width: 1, height: 24, background: "hsl(217.2 32.6% 17.5%)" }} />

              {/* Avatar */}
              <div style={{
                width: 30, height: 30, borderRadius: "50%",
                background: "linear-gradient(135deg, hsl(239 84% 67%), hsl(262 83% 58%))",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 700, color: "#fff", cursor: "pointer",
              }}>A</div>
            </div>
          </header>

          {/* Page content */}
          <main style={{ flex: 1, overflowY: "auto", padding: 24 }}>
            {children}
          </main>
        </div>
      </div>
    </TabContext.Provider>
  );
}
