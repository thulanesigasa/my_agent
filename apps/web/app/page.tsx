"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Plus, Square, X, MicOff, LayoutDashboard, Download, CheckCircle, Edit3, XCircle, Building2, MapPin, ShieldCheck } from "lucide-react";
import SiriOrb from "@/components/ui/siri-orb";
import { AudioStreamManager, SiriOrbState } from "@/lib/audio";
import CalendarWidget from "@/components/CalendarWidget";
import EmployeeStack, { AGENT_EMPLOYEES } from "@/components/EmployeeStack";
import AgentTodoList from "@/components/AgentTodoList";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

interface ApprovalItem {
  id: string;
  company: string;
  to: string;
  subject: string;
  body: string;
}

const STANDERTON_LEADS = [
  { name: "Standerton Auto Repair & Panelbeating", address: "42 Main Street, Standerton, Mpumalanga", phone: "+27177121101", email: "info@standertonauto.co.za" },
  { name: "Lekwa Bakery & Supply Store", address: "15 Kerk Street, Standerton, Mpumalanga", phone: "+27177121920", email: "orders@lekwabakery.co.za" },
  { name: "Standerton Plumbing & Hardware", address: "88 Burger Street, Standerton, Mpumalanga", phone: "+27177122220", email: "contact@standertonplumbing.co.za" },
  { name: "Highveld Agricultural Equipment & Spares", address: "5 Vaal River Road, Standerton, Mpumalanga", phone: "+27177123450", email: "sales@highveldagri.co.za" },
  { name: "Standerton Tyre & Fitment Center", address: "201 Meyerville Drive, Standerton, Mpumalanga", phone: "+27177124560", email: "fitment@standertontyres.co.za" },
  { name: "Lekwa Electrical & Solar Services", address: "74 Calie Street, Standerton, Mpumalanga", phone: "+27177125120", email: "service@lekwaelectrical.co.za" },
  { name: "Standerton Laundry & Dry Cleaners", address: "33 Charl Cilliers Street, Standerton, Mpumalanga", phone: "+27177126770", email: "clean@standertonlaundry.co.za" },
  { name: "Vaal River Landscaping & Fencing", address: "66 Industrial Road, Standerton, Mpumalanga", phone: "+27177127880", email: "projects@vaallandscaping.co.za" },
];

const INITIAL_QUEUE: ApprovalItem[] = [
  {
    id: "a1",
    company: "Standerton Auto Repair & Panelbeating",
    to: "info@standertonauto.co.za",
    subject: "Web Presence & Local SEO Proposal",
    body: "Hi Standerton Auto Repair team,\n\nWe help local businesses in Standerton, Mpumalanga get online fast with professional websites and high-ranking local SEO.\n\nReply to this email to claim your free 30-minute strategy call or custom quotation.\n\nBest,\nAgent Team\npharezsigasa@gmail.com | +447544357979",
  },
  {
    id: "a2",
    company: "Lekwa Bakery & Supply Store",
    to: "orders@lekwabakery.co.za",
    subject: "Grow Your Bakery Online in Standerton",
    body: "Hi Lekwa Bakery team,\n\nA professional online ordering storefront could bring dozens of new local customers weekly.\n\nReply to claim your strategy session.\n\nBest,\nAgent Team\npharezsigasa@gmail.com | +447544357979",
  },
];

// Suggestion chips per agent
const AGENT_SUGGESTIONS: Record<string, string[]> = {
  research_agent: [
    "Show all discovered leads",
    "Scrape new businesses in Standerton",
    "Find companies missing websites",
    "Export contact directory",
  ],
  email_agent: [
    "Review pending email pitches",
    "Generate proposal for Auto Repair",
    "Dispatch approved emails now",
    "Check outbox queue status",
  ],
  reports_agent: [
    "Show this week's analytics",
    "Export PDF report",
    "Summarise lead conversion rates",
    "Compare week-on-week performance",
  ],
  project_manager: [
    "Check subagent system status",
    "Audit all running agent threads",
    "Restart idle agents",
    "Show error logs from last 24h",
  ],
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);

  // Inline workspace panel visibility
  const [workspaceOpen, setWorkspaceOpen] = useState(false);

  // Email agent queue state
  const [queue, setQueue] = useState<ApprovalItem[]>(INITIAL_QUEUE);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  // Voice / Full-screen White Orb Live mode state
  const [voiceActive, setVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [liveResponse, setLiveResponse] = useState("");

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const activeAgent = AGENT_EMPLOYEES.find((a) => a.id === activeAgentId);

  // When agent is selected — open workspace and clear messages
  const handleSelectAgent = (id: string) => {
    if (id === activeAgentId && workspaceOpen) {
      // Clicking same agent again collapses workspace
      setWorkspaceOpen(false);
      return;
    }
    setActiveAgentId(id);
    setWorkspaceOpen(true);
    setMessages([]);
  };

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startVoiceMode = async () => {
    setVoiceActive(true);
    setOrbState("listening");

    const manager = new AudioStreamManager({
      onStateChange: (s) => setOrbState(s),
      onTranscription: (t) => setTranscription(t),
      onResponseText: (r) => setLiveResponse(r),
      onError: () => setVoiceActive(false),
    });
    audioManagerRef.current = manager;
    manager.connect();
    const ok = await manager.startStreaming();
    if (!ok) setVoiceActive(false);
  };

  const stopVoiceMode = () => {
    audioManagerRef.current?.disconnect();
    audioManagerRef.current = null;
    setVoiceActive(false);
    setOrbState("idle");
    setTranscription("");
    setLiveResponse("");
  };

  const handleSend = (text?: string) => {
    const userText = (text || inputValue).trim();
    if (!userText || loading) return;
    setInputValue("");
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), sender: "user", text: userText, timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) },
    ]);
    setLoading(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: `[${activeAgent?.name ?? "agent"}] Processing: "${userText}"`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setLoading(false);
    }, 900);
  };

  // ── INLINE WORKSPACE PANELS ───────────────────────────────────────
  const renderWorkspace = () => {
    if (!workspaceOpen || !activeAgentId) return null;

    return (
      <div style={{ width: "100%", maxWidth: 640, marginTop: 28, display: "flex", flexDirection: "column", gap: 0 }}>
        {/* Panel header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>{activeAgent?.name}</span>
          <button
            onClick={() => setWorkspaceOpen(false)}
            style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 12, fontWeight: 600, padding: "2px 8px", borderRadius: 6 }}
          >
            Close
          </button>
        </div>

        {activeAgentId === "research_agent" && (
          <div style={{ background: "rgba(255,255,255,0.6)", backdropFilter: "blur(12px)", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Active Companies Missing Official Websites</h3>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Scraped business directory leads in Standerton, Mpumalanga</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, background: "#f8fafc", padding: "4px 10px", borderRadius: 999, border: "1px solid #e2e8f0" }}>
                <MapPin size={11} color="#ec4899" />
                <span style={{ fontSize: 11, fontWeight: 600, color: "#0f172a" }}>Standerton</span>
              </div>
            </div>
            <div style={{ maxHeight: 260, overflowY: "auto" }}>
              {STANDERTON_LEADS.map((lead, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "11px 16px", borderBottom: idx < STANDERTON_LEADS.length - 1 ? "1px solid #f8fafc" : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#f1f5f9", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Building2 size={14} color="#64748b" />
                    </div>
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 600, margin: 0, color: "#0f172a" }}>{lead.name}</p>
                      <p style={{ fontSize: 10, color: "#64748b", margin: "1px 0 0" }}>{lead.address}</p>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <p style={{ fontSize: 10, color: "#ec4899", fontWeight: 600, margin: 0 }}>{lead.email}</p>
                    <span style={{ fontSize: 9, padding: "2px 7px", borderRadius: 999, background: "rgba(239,68,68,0.1)", color: "#dc2626", fontWeight: 700 }}>No Website</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeAgentId === "email_agent" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Human Approval Queue</h3>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Review agent-drafted emails before dispatch</p>
              </div>
            </div>
            {queue.length === 0 ? (
              <div style={{ padding: "28px", textAlign: "center", background: "rgba(255,255,255,0.6)", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)" }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "#10b981", margin: 0 }}>Queue is clear — all emails dispatched.</p>
              </div>
            ) : (
              queue.map((item) => (
                <div key={item.id} style={{ background: "rgba(255,255,255,0.6)", backdropFilter: "blur(12px)", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: "1px solid #f1f5f9", background: "rgba(250,250,250,0.5)" }}>
                    <div>
                      <h4 style={{ fontSize: 12, fontWeight: 700, margin: 0, color: "#111" }}>{item.company}</h4>
                      <p style={{ fontSize: 10, color: "#64748b", margin: "1px 0 0" }}>To: {item.to} · {item.subject}</p>
                    </div>
                    <span style={{ fontSize: 9, fontWeight: 700, color: "#888", border: "1px solid #e0e0e0", borderRadius: 4, padding: "2px 6px" }}>PENDING</span>
                  </div>
                  <div style={{ padding: "10px 14px", fontSize: 11, color: "#334155", whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                    {editingId === item.id ? (
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={5}
                        style={{ width: "100%", border: "1px solid #e0e0e0", borderRadius: 8, padding: "8px", fontSize: 11, color: "#0f172a", outline: "none", resize: "vertical", fontFamily: "inherit", background: "rgba(255,255,255,0.8)" }}
                      />
                    ) : (
                      item.body
                    )}
                  </div>
                  <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, padding: "8px 14px", borderTop: "1px solid #f1f5f9" }}>
                    {editingId === item.id ? (
                      <>
                        <button onClick={() => { setQueue((p) => p.map((x) => x.id === item.id ? { ...x, body: editText } : x)); setEditingId(null); }} style={{ padding: "5px 12px", fontSize: 11, fontWeight: 600, background: "#0f172a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>Save & Send</button>
                        <button onClick={() => setEditingId(null)} style={{ padding: "5px 10px", fontSize: 11, background: "transparent", color: "#64748b", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setQueue((p) => p.filter((x) => x.id !== item.id))} style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 12px", fontSize: 11, fontWeight: 600, background: "#0f172a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
                          <CheckCircle size={12} /> Approve & Send
                        </button>
                        <button onClick={() => { setEditingId(item.id); setEditText(item.body); }} style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", fontSize: 11, background: "transparent", color: "#475569", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>
                          <Edit3 size={12} /> Edit
                        </button>
                        <button onClick={() => setQueue((p) => p.filter((x) => x.id !== item.id))} style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", fontSize: 11, background: "transparent", color: "#dc2626", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>
                          <XCircle size={12} /> Reject
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeAgentId === "reports_agent" && (
          <div style={{ background: "rgba(255,255,255,0.6)", backdropFilter: "blur(12px)", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Standerton Lead Conversion & Analytics Report</h3>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Weekly discovery metrics compiled for Standerton, Mpumalanga</p>
              </div>
              <button style={{ display: "flex", alignItems: "center", gap: 5, padding: "6px 12px", fontSize: 11, fontWeight: 600, background: "#ec4899", color: "#fff", border: "none", borderRadius: 999, cursor: "pointer" }}>
                <Download size={11} /> Export PDF
              </button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: "#f1f5f9" }}>
              {[
                { label: "Standerton Discovered Leads", value: "8 Businesses", color: "#0f172a" },
                { label: "Emails Dispatched", value: "250 Emails", color: "#ec4899" },
                { label: "Engagement Response Rate", value: "32.0%", color: "#10b981" },
                { label: "Active Leads Pipeline", value: "47 Prospects", color: "#0f172a" },
              ].map((m, i) => (
                <div key={i} style={{ padding: "14px 16px", background: "rgba(255,255,255,0.7)" }}>
                  <span style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: 4 }}>{m.label}</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: m.color }}>{m.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeAgentId === "project_manager" && (
          <div style={{ background: "rgba(255,255,255,0.6)", backdropFilter: "blur(12px)", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden" }}>
            <div style={{ padding: "12px 16px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Subagent System Health & Activity Audit</h3>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Real-time log verification across all active subagent tasks</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 5, background: "rgba(16,185,129,0.1)", padding: "4px 10px", borderRadius: 999, border: "1px solid rgba(16,185,129,0.3)" }}>
                <ShieldCheck size={11} color="#059669" />
                <span style={{ fontSize: 11, fontWeight: 700, color: "#059669" }}>System Operational 100%</span>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {[
                { name: "reports_agent", status: "Active", note: "Standerton report compiled", active: true },
                { name: "email_agent", status: "Idle", note: "250 emails queued", active: false },
                { name: "project_manager", status: "Active", note: "Auditing log health", active: true },
                { name: "research_agent", status: "Idle", note: "Standerton business discovery done", active: false },
              ].map((agent, idx, arr) => (
                <div key={agent.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: idx < arr.length - 1 ? "1px solid #f8fafc" : "none" }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#0f172a" }}>{agent.name}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: agent.active ? "#10b981" : "#cbd5e1", display: "inline-block" }} />
                    <span style={{ fontSize: 11, color: agent.active ? "#059669" : "#94a3b8", fontWeight: 600 }}>
                      {agent.status} — {agent.note}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "hidden" }}>
      {voiceActive ? (
        <div style={{ position: "fixed", inset: 0, zIndex: 1000, background: "#ffffff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-between", padding: "40px 24px", color: "#0f172a" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", maxWidth: 800 }}>
            <span style={{ fontWeight: 700, fontSize: 18, color: "#0f172a" }}>my_agent · Live Voice</span>
            <button onClick={stopVoiceMode} style={{ background: "rgba(0,0,0,0.05)", border: "none", borderRadius: "50%", width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#64748b" }}><X size={18} /></button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, margin: "auto" }}>
            <SiriOrb size={220} animationDuration={12} />
            <div style={{ textAlign: "center", maxWidth: 500 }}>
              <p style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#ec4899", fontWeight: 700, margin: "0 0 6px" }}>
                {orbState === "listening" ? "Listening to your voice..." : orbState === "speaking" ? "Agent is speaking..." : "Processing..."}
              </p>
              {transcription && <p style={{ fontSize: 16, color: "#0f172a", fontWeight: 500, margin: "6px 0" }}>"{transcription}"</p>}
              {liveResponse && <p style={{ fontSize: 14, color: "#64748b", fontStyle: "italic", margin: "6px 0" }}>{liveResponse}</p>}
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button onClick={() => setIsMuted(!isMuted)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 999, background: isMuted ? "#fee2e2" : "#f1f5f9", color: isMuted ? "#dc2626" : "#334155", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
              <MicOff size={16} /><span>{isMuted ? "Unmute Mic" : "Mute Mic"}</span>
            </button>
            <button onClick={stopVoiceMode} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 24px", borderRadius: 999, background: "#ec4899", color: "#ffffff", border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600, boxShadow: "0 4px 14px rgba(236,72,153,0.4)" }}>
              <Square size={14} fill="#ffffff" /><span>Click to Interrupt</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="dashboard-container" style={{ backgroundImage: "linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url('/gemini-bg.png')", backgroundSize: "cover", backgroundPosition: "center", color: "#1e293b" }}>
          {/* Header */}
          <header style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px" }}>
            <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>my_agent</span>
            <Link href="/dashboard" style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a", background: "#ffffff", border: "1px solid rgba(0,0,0,0.1)", borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
              <LayoutDashboard size={14} />Admin Dashboard
            </Link>
          </header>

          <main className="dashboard-main-grid">
            {/* LEFT: Calendar + Employee Roster */}
            <div style={{ display: "flex", flexDirection: "column", gap: "clamp(6px, 1.2vh, 14px)", overflow: "hidden", height: "100%" }}>
              <CalendarWidget />
              <EmployeeStack activeAgentId={activeAgentId ?? ""} onSelectAgent={handleSelectAgent} />
            </div>

            {/* CENTER: Hero + Prompt Capsule + Suggestions + Workspace Panel */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: messages.length === 0 ? "center" : "flex-start", position: "relative", height: "100%", overflowY: "auto", paddingRight: 4, paddingTop: messages.length > 0 ? 20 : 0 }}>

              {messages.length === 0 ? (
                <div style={{ textAlign: "center", marginBottom: 28, maxWidth: 600 }}>
                  <h1 style={{ fontSize: 38, fontWeight: 400, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 8px" }}>
                    What's next, sir?
                  </h1>
                  <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                    {activeAgent
                      ? <>Interacting with <strong style={{ color: "#ec4899" }}>{activeAgent.name}</strong>. Ask a question or click the Orb for speech mode.</>
                      : "Select an agent from AI Employees to get started."}
                  </p>
                </div>
              ) : (
                <div style={{ width: "100%", maxWidth: 640, flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 16, paddingBottom: 20 }}>
                  {messages.map((msg) => (
                    <div key={msg.id} style={{ display: "flex", justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                      <div style={{ maxWidth: "80%", padding: "12px 16px", fontSize: 13, lineHeight: 1.6, borderRadius: 18, background: msg.sender === "user" ? "#0f172a" : "#ffffff", color: msg.sender === "user" ? "#ffffff" : "#0f172a", border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 2px 10px rgba(0,0,0,0.04)" }}>
                        <div style={{ whiteSpace: "pre-wrap" }}>{msg.text}</div>
                      </div>
                    </div>
                  ))}
                  {loading && <div style={{ fontSize: 13, color: "#64748b" }}>{activeAgent?.name} is thinking...</div>}
                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* Prompt Capsule */}
              <div style={{ width: "100%", maxWidth: 600, position: "relative" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#ffffff", borderRadius: 999, padding: "8px 12px 8px 18px", boxShadow: "0 10px 30px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.05)", border: "1px solid rgba(226,232,240,0.9)" }}>
                  <button style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
                    <Plus size={20} />
                  </button>
                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSend(); } }}
                    placeholder={activeAgent ? `Ask ${activeAgent.name}...` : "Select an agent to begin..."}
                    style={{ flex: 1, border: "none", outline: "none", fontSize: 14, color: "#0f172a", background: "transparent", fontFamily: "inherit" }}
                  />
                  <button onClick={startVoiceMode} title="Speech mode" style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: 2, borderRadius: "50%", transition: "transform 150ms" }} onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")} onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}>
                    <SiriOrb size={24} animationDuration={20} />
                  </button>
                </div>
              </div>

              {/* SUGGESTION CHIPS — only visible when no messages yet and agent selected */}
              {messages.length === 0 && activeAgentId && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 600, marginTop: 18 }}>
                  {(AGENT_SUGGESTIONS[activeAgentId] ?? []).map((chip) => (
                    <button
                      key={chip}
                      onClick={() => handleSend(chip)}
                      style={{
                        padding: "6px 14px", fontSize: 12, fontWeight: 500,
                        background: "rgba(255,255,255,0.6)", backdropFilter: "blur(8px)",
                        border: "1px solid rgba(226,232,240,0.9)",
                        borderRadius: 999, cursor: "pointer", color: "#334155",
                        transition: "all 150ms ease",
                      }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#ec4899"; (e.currentTarget as HTMLButtonElement).style.color = "#ec4899"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(226,232,240,0.9)"; (e.currentTarget as HTMLButtonElement).style.color = "#334155"; }}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}

              {/* INLINE AGENT WORKSPACE PANEL */}
              {renderWorkspace()}
            </div>

            {/* RIGHT: Daily To-Do List */}
            <div style={{ height: "100%", overflow: "hidden" }}>
              <AgentTodoList activeAgentId={activeAgentId ?? ""} activeAgentName={activeAgent?.name ?? ""} />
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
