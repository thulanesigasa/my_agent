"use client";

import React, { useState } from "react";
import {
  Users, Puzzle, KeyRound, Settings, CreditCard,
  HelpCircle, BookOpen, LayoutDashboard, Mail,
  ShieldCheck, Database, PanelLeft, Bell, Send
} from "lucide-react";

export type NavTab = "overview" | "logs" | "approvals" | "memory" | "settings";

const WORKSPACE_NAV = [
  { id: "overview"  as NavTab, label: "Overview",      icon: LayoutDashboard },
  { id: "logs"      as NavTab, label: "Outreach Logs", icon: Mail            },
  { id: "approvals" as NavTab, label: "Approvals",     icon: ShieldCheck     },
];

const ADMIN_NAV = [
  { id: "memory"   as NavTab, label: "Memory Bank", icon: Database  },
  { id: "settings" as NavTab, label: "Settings",    icon: Settings  },
];

const ALL_NAV = [...WORKSPACE_NAV, ...ADMIN_NAV];

interface AppShellProps { children: React.ReactNode; }

export const TabContext = React.createContext<{
  tab: NavTab; setTab: (t: NavTab) => void;
}>({ tab: "overview", setTab: () => {} });

export function AppShell({ children }: AppShellProps) {
  const [tab, setTab] = useState<NavTab>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const urlTab = params.get("tab") as NavTab;
      if (urlTab && ["overview", "logs", "approvals", "memory", "settings"].includes(urlTab)) {
        setTab(urlTab);
      }
    }
  }, []);

  const activeNav = ALL_NAV.find(n => n.id === tab) || WORKSPACE_NAV[0];
  const ActiveIcon = activeNav.icon;

  const NavItem = ({ id, label, icon: Icon }: { id: NavTab; label: string; icon: React.ElementType }) => (
    <button
      onClick={() => setTab(id)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        width: "100%", padding: "6px 8px",
        background: tab === id ? "#f3f3f3" : "transparent",
        border: "none", borderRadius: 6, cursor: "pointer",
        fontSize: 13, color: tab === id ? "#111" : "#555",
        fontWeight: tab === id ? 600 : 400,
        textAlign: "left",
        whiteSpace: "nowrap",
      }}
    >
      <Icon size={15} strokeWidth={1.8} style={{ color: tab === id ? "#111" : "#888", flexShrink: 0 }} />
      {label}
    </button>
  );

  return (
    <TabContext.Provider value={{ tab, setTab }}>
      <div style={{
        position: "fixed", inset: 0, display: "flex",
        background: "#f0f0f0",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        fontSize: 14,
      }}>
        {/* ── Outer shell with border & shadow ── */}
        <div style={{
          display: "flex", flex: 1, margin: 12,
          background: "#fff",
          border: "1px solid #e0e0e0",
          borderRadius: 10,
          boxShadow: "0 2px 16px rgba(0,0,0,0.07)",
          overflow: "hidden",
        }}>

          {/* ── Sidebar ── */}
          <aside style={{
            width: sidebarOpen ? 210 : 0,
            opacity: sidebarOpen ? 1 : 0,
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            borderRight: sidebarOpen ? "1px solid #e8e8e8" : "none",
            background: "#fff",
            overflow: "hidden",
            transition: "width 150ms cubic-bezier(.4,0,.2,1), opacity 150ms ease",
          }}>
            {/* Inner fixed-width wrapper to prevent text overflow during slide */}
            <div style={{ width: 210, display: "flex", flexDirection: "column", height: "100%" }}>
              {/* Brand Logo */}
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #e8e8e8" }}>
              <span style={{ fontWeight: 700, fontSize: 15, color: "#111" }}>Dashboard</span>
            </div>

              {/* Nav */}
              <div style={{ flex: 1, padding: "14px 10px", overflowY: "auto" }}>
                {/* Workspace */}
                <p style={{ fontSize: 11, fontWeight: 600, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6, paddingLeft: 8 }}>
                  Workspace
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 1, marginBottom: 18 }}>
                  {WORKSPACE_NAV.map(n => <NavItem key={n.id} {...n} />)}
                </div>

                {/* Administration */}
                <p style={{ fontSize: 11, fontWeight: 600, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6, paddingLeft: 8 }}>
                  Administration
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {ADMIN_NAV.map(n => <NavItem key={n.id} {...n} />)}
                </div>
              </div>

              {/* Changelog / bottom */}
              <div style={{ borderTop: "1px solid #e8e8e8", padding: "12px 16px" }}>
                <p style={{ fontSize: 10, fontWeight: 700, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>Changelog</p>
                <p style={{ fontSize: 12, fontWeight: 700, color: "#111", marginBottom: 2 }}>Agent v1.0 launch</p>
                <p style={{ fontSize: 11, color: "#888", marginBottom: 6, lineHeight: 1.5 }}>LangGraph + Groq pipeline live.</p>
                <a href="#" style={{ fontSize: 11, color: "#555", textDecoration: "none", fontWeight: 500 }}>Learn more</a>

                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 4 }}>
                  <button style={{ display: "flex", alignItems: "center", gap: 8, background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#666", padding: "3px 0", textAlign: "left" }}>
                    <HelpCircle size={13} strokeWidth={1.8} /> Help Center
                  </button>
                  <button style={{ display: "flex", alignItems: "center", gap: 8, background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#666", padding: "3px 0", textAlign: "left" }}>
                    <BookOpen size={13} strokeWidth={1.8} /> Documentation
                  </button>
                </div>

                <p style={{ fontSize: 10, color: "#ccc", marginTop: 14 }}>© 2026 my_agent LLC</p>
              </div>
            </div>
          </aside>

          {/* ── Main Area ── */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
            {/* Topbar */}
            <header style={{
              height: 48, display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "0 20px", borderBottom: "1px solid #e8e8e8", flexShrink: 0, background: "#fff",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <button
                  onClick={() => setSidebarOpen(open => !open)}
                  title={sidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
                  style={{
                    background: sidebarOpen ? "none" : "#f0f0f0",
                    border: "1px solid #e0e0e0",
                    padding: 5, borderRadius: 6,
                    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                    color: "#111",
                    transition: "all 150ms",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#e5e5e5")}
                  onMouseLeave={e => (e.currentTarget.style.background = sidebarOpen ? "none" : "#f0f0f0")}
                >
                  <PanelLeft size={16} strokeWidth={1.8} />
                </button>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <ActiveIcon size={14} strokeWidth={1.5} style={{ color: "#999" }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#333" }}>{activeNav.label}</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <Send size={15} strokeWidth={1.5} style={{ color: "#999", cursor: "pointer" }} />
                <Bell size={15} strokeWidth={1.5} style={{ color: "#999", cursor: "pointer" }} />
                <div style={{
                  width: 28, height: 28, borderRadius: "50%", background: "#111",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 12, fontWeight: 700, color: "#fff", cursor: "pointer",
                }}>A</div>
              </div>
            </header>

            {/* Content */}
            <main style={{ flex: 1, overflowY: "auto", background: "#fff" }}>
              {children}
            </main>
          </div>
        </div>
      </div>
    </TabContext.Provider>
  );
}
