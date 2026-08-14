"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Plus, Square, X, MicOff, LayoutDashboard,
  Download, CheckCircle, Edit3, XCircle, CheckCircle2,
  ShieldCheck, MapPin, Building2
} from "lucide-react";
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
  status: "pending" | "approved" | "rejected";
}

const INITIAL_APPROVALS: ApprovalItem[] = [
  {
    id: "a1",
    company: "Standerton Auto Repair & Panelbeating",
    to: "info@standertonauto.co.za",
    subject: "Web Presence & Local SEO Proposal",
    body: "Hi Standerton Auto Repair team,\n\nWe help local businesses in Standerton, Mpumalanga get online fast with professional websites and high-ranking local SEO.\n\nReply to this email to claim your free 30-minute strategy call or custom quotation.\n\nBest,\nAgent Team\npharezsigasa@gmail.com | +447544357979",
    status: "pending",
  },
  {
    id: "a2",
    company: "Lekwa Bakery & Supply Store",
    to: "orders@lekwabakery.co.za",
    subject: "Grow Your Bakery Online in Standerton",
    body: "Hi Lekwa Bakery team,\n\nA professional online ordering storefront could bring dozens of new local customers weekly.\n\nReply to claim your strategy session.\n\nBest,\nAgent Team\npharezsigasa@gmail.com | +447544357979",
    status: "pending",
  },
];

const STANDERTON_LEADS = [
  { name: "Standerton Auto Repair & Panelbeating", address: "42 Main Street, Standerton, Mpumalanga", email: "info@standertonauto.co.za" },
  { name: "Lekwa Bakery & Supply Store", address: "15 Kerk Street, Standerton, Mpumalanga", email: "orders@lekwabakery.co.za" },
  { name: "Standerton Plumbing & Hardware", address: "88 Burger Street, Standerton, Mpumalanga", email: "contact@standertonplumbing.co.za" },
  { name: "Highveld Agricultural Equipment & Spares", address: "5 Vaal River Road, Standerton, Mpumalanga", email: "sales@highveldagri.co.za" },
  { name: "Standerton Tyre & Fitment Center", address: "201 Meyerville Drive, Standerton, Mpumalanga", email: "fitment@standertontyres.co.za" },
  { name: "Lekwa Electrical & Solar Services", address: "74 Calie Street, Standerton, Mpumalanga", email: "service@lekwaelectrical.co.za" },
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState<string>("reports_agent");

  // Approval queue state
  const [queue, setQueue] = useState<ApprovalItem[]>(INITIAL_APPROVALS);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  // Voice / Full-screen White Orb Live mode state
  const [voiceActive, setVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [liveResponse, setLiveResponse] = useState("");
  const [micError, setMicError] = useState<string | null>(null);

  const audioManagerRef = useRef<AudioStreamManager | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const activeAgent = AGENT_EMPLOYEES.find((a) => a.id === activeAgentId) || AGENT_EMPLOYEES[0];

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startVoiceMode = async () => {
    setMicError(null);
    setVoiceActive(true);
    setOrbState("listening");

    const manager = new AudioStreamManager({
      onStateChange: (newState) => setOrbState(newState),
      onTranscription: (userText) => setTranscription(userText),
      onResponseText: (agentText) => setLiveResponse(agentText),
      onError: (err) => {
        setMicError(err);
        setVoiceActive(false);
      },
    });

    audioManagerRef.current = manager;
    manager.connect();
    const ok = await manager.startStreaming();
    if (!ok) {
      setVoiceActive(false);
    }
  };

  const stopVoiceMode = () => {
    if (audioManagerRef.current) {
      audioManagerRef.current.disconnect();
      audioManagerRef.current = null;
    }
    setVoiceActive(false);
    setOrbState("idle");
    setTranscription("");
    setLiveResponse("");
  };

  const handleSendText = () => {
    if (!inputValue.trim() || loading) return;
    const userText = inputValue.trim();
    setInputValue("");
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        sender: "user",
        text: userText,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
    setLoading(true);

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: `[${activeAgent.name}] Received: "${userText}". Standerton lead pipeline updated.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setLoading(false);
    }, 1000);
  };

  // Render workspace info directly below prompt capsule
  const renderActiveAgentWorkspace = () => {
    switch (activeAgentId) {
      case "email_agent":
        return (
          <div style={{ width: "100%", textAlign: "left" }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "#111", margin: "0 0 2px" }}>
              Human Approval Queue
            </p>
            <p style={{ fontSize: 11, color: "#888", margin: "0 0 12px" }}>
              Review agent-drafted emails before dispatch
            </p>

            {queue.length === 0 ? (
              <div style={{ border: "1px solid #e8e8e8", borderRadius: 8, padding: "20px 16px", textAlign: "center", background: "#fff" }}>
                <CheckCircle2 size={24} strokeWidth={1.5} style={{ color: "#ccc", marginBottom: 4 }} />
                <p style={{ fontSize: 12, fontWeight: 600, color: "#888", margin: 0 }}>Queue is clear</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {queue.map((item) => (
                  <div key={item.id} style={{ border: "1px solid #e8e8e8", borderRadius: 8, overflow: "hidden", background: "#fff" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderBottom: "1px solid #e8e8e8", background: "#fafafa" }}>
                      <div>
                        <p style={{ fontSize: 12, fontWeight: 700, color: "#111", margin: 0 }}>{item.company}</p>
                        <p style={{ fontSize: 10, color: "#888", margin: "1px 0 0" }}>To: {item.to} · Subject: {item.subject}</p>
                      </div>
                      <span style={{ fontSize: 9, fontWeight: 700, color: "#888", border: "1px solid #e0e0e0", borderRadius: 4, padding: "2px 6px", background: "#fff" }}>
                        PENDING
                      </span>
                    </div>

                    <div style={{ padding: "10px 14px", borderBottom: "1px solid #e8e8e8" }}>
                      <p style={{ fontSize: 9, fontWeight: 700, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 6px" }}>
                        DRAFT RESPONSE
                      </p>
                      {editingId === item.id ? (
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={4}
                          style={{ width: "100%", border: "1px solid #e0e0e0", borderRadius: 6, padding: "8px 10px", fontSize: 11, color: "#333", outline: "none", fontFamily: "inherit" }}
                        />
                      ) : (
                        <div style={{ border: "1px solid #e8e8e8", borderRadius: 6, padding: "8px 12px", fontSize: 11, color: "#555", lineHeight: 1.6, whiteSpace: "pre-wrap", background: "#fafafa" }}>
                          {item.body}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, padding: "8px 14px", background: "#fff" }}>
                      {editingId === item.id ? (
                        <>
                          <button onClick={() => setEditingId(null)} style={{ padding: "5px 12px", fontSize: 11, fontWeight: 600, background: "#111", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>Save & Send</button>
                          <button onClick={() => setEditingId(null)} style={{ padding: "5px 12px", fontSize: 11, fontWeight: 500, background: "#fff", color: "#555", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => setQueue((prev) => prev.filter((x) => x.id !== item.id))} style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 12px", fontSize: 11, fontWeight: 600, background: "#111", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
                            <CheckCircle size={12} strokeWidth={2} /> Approve & Send
                          </button>
                          <button onClick={() => { setEditingId(item.id); setEditText(item.body); }} style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 10px", fontSize: 11, fontWeight: 500, background: "#fff", color: "#555", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>
                            <Edit3 size={12} strokeWidth={2} /> Edit
                          </button>
                          <button onClick={() => setQueue((prev) => prev.filter((x) => x.id !== item.id))} style={{ display: "flex", alignItems: "center", gap: 4, padding: "5px 10px", fontSize: 11, fontWeight: 500, background: "#fff", color: "#999", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}>
                            <XCircle size={12} strokeWidth={2} /> Reject
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "project_manager":
        return (
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Subagent System Health & Activity Audit</h3>
                <span style={{ fontSize: 11, color: "#64748b" }}>Real-time log verification across all active subagent tasks</span>
              </div>
              <div style={{ padding: "3px 8px", borderRadius: 999, background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)", color: "#059669", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                <ShieldCheck size={13} /> System Operational 100%
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#ffffff", borderRadius: 8, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, fontWeight: 600 }}>reports_agent</span>
                <span style={{ fontSize: 10, color: "#059669", fontWeight: 600 }}>🟢 Active — Standerton report compiled</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#ffffff", borderRadius: 8, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, fontWeight: 600 }}>email_agent</span>
                <span style={{ fontSize: 10, color: "#64748b" }}>💤 Asleep — 250 emails queued</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#ffffff", borderRadius: 8, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, fontWeight: 600 }}>project_manager</span>
                <span style={{ fontSize: 10, color: "#059669", fontWeight: 600 }}>🟢 Active — Auditing log health</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#ffffff", borderRadius: 8, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, fontWeight: 600 }}>research_agent</span>
                <span style={{ fontSize: 10, color: "#64748b" }}>💤 Asleep — Standerton business discovery done</span>
              </div>
            </div>
          </div>
        );

      case "research_agent":
        return (
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Active Companies Missing Websites in Standerton</h3>
                <span style={{ fontSize: 11, color: "#64748b" }}>Scraped business directory leads in Standerton, Mpumalanga</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, background: "#ffffff", padding: "3px 8px", borderRadius: 999, border: "1px solid rgba(226,232,240,0.9)" }}>
                <MapPin size={12} color="#ec4899" />
                <span style={{ fontSize: 10, fontWeight: 600, color: "#0f172a" }}>Standerton</span>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 220, overflowY: "auto", paddingRight: 2 }}>
              {STANDERTON_LEADS.map((lead, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "#ffffff", borderRadius: 8, border: "1px solid rgba(226,232,240,0.8)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Building2 size={14} color="#64748b" />
                    <div>
                      <h4 style={{ fontSize: 11, fontWeight: 600, margin: 0 }}>{lead.name}</h4>
                      <span style={{ fontSize: 9, color: "#64748b" }}>{lead.address}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 9, color: "#ec4899", fontWeight: 600 }}>{lead.email}</span>
                    <span style={{ fontSize: 8, padding: "2px 5px", borderRadius: 999, background: "rgba(239,68,68,0.1)", color: "#dc2626", fontWeight: 700 }}>No Website</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case "reports_agent":
      default:
        return (
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 700, margin: 0, color: "#0f172a" }}>Standerton Lead Conversion & Analytics Report</h3>
                <span style={{ fontSize: 11, color: "#64748b" }}>Weekly discovery metrics compiled for Standerton, Mpumalanga</span>
              </div>
              <button style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 999, background: "#ec4899", color: "#fff", fontSize: 11, fontWeight: 600, border: "none", cursor: "pointer" }}>
                <Download size={12} /> Export PDF Report
              </button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
              <div style={{ background: "#ffffff", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, color: "#64748b" }}>Standerton Discovered Leads</span>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "2px 0 0", color: "#0f172a" }}>8 Businesses</h3>
              </div>
              <div style={{ background: "#ffffff", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, color: "#64748b" }}>Emails Dispatched</span>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "2px 0 0", color: "#ec4899" }}>250 Emails</h3>
              </div>
              <div style={{ background: "#ffffff", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, color: "#64748b" }}>Engagement Response Rate</span>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "2px 0 0", color: "#10b981" }}>32.0%</h3>
              </div>
              <div style={{ background: "#ffffff", padding: "10px 12px", borderRadius: 10, border: "1px solid rgba(226,232,240,0.8)" }}>
                <span style={{ fontSize: 11, color: "#64748b" }}>Active Leads Pipeline</span>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: "2px 0 0", color: "#0f172a" }}>47 Prospects</h3>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <div style={{ width: "100vw", height: "100vh", overflow: "hidden" }}>
      {voiceActive ? (
        /* ── FULL-SCREEN WHITE ORB LIVE SPEECH MODE ── */
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "#ffffff",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-between",
          padding: "40px 24px", color: "#0f172a",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", maxWidth: 800 }}>
            <span style={{ fontWeight: 700, fontSize: 18, color: "#0f172a" }}>my_agent · Live Voice</span>
            <button
              onClick={stopVoiceMode}
              style={{
                background: "rgba(0,0,0,0.05)", border: "none", borderRadius: "50%",
                width: 36, height: 36, display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: "#64748b",
              }}
            >
              <X size={18} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 24, margin: "auto" }}>
            <SiriOrb size={220} animationDuration={12} />

            <div style={{ textAlign: "center", maxWidth: 500 }}>
              <p style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: "0.1em", color: "#ec4899", fontWeight: 700, margin: "0 0 6px" }}>
                {orbState === "listening" ? "Listening to your voice..." : orbState === "speaking" ? "Agent is speaking..." : "Processing..."}
              </p>

              {transcription && (
                <p style={{ fontSize: 16, color: "#0f172a", fontWeight: 500, margin: "6px 0" }}>
                  "{transcription}"
                </p>
              )}

              {liveResponse && (
                <p style={{ fontSize: 14, color: "#64748b", fontStyle: "italic", margin: "6px 0" }}>
                  {liveResponse}
                </p>
              )}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <button
              onClick={() => setIsMuted(!isMuted)}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 20px", borderRadius: 999,
                background: isMuted ? "#fee2e2" : "#f1f5f9",
                color: isMuted ? "#dc2626" : "#334155",
                border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
              }}
            >
              <MicOff size={16} />
              <span>{isMuted ? "Unmute Mic" : "Mute Mic"}</span>
            </button>

            <button
              onClick={stopVoiceMode}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "10px 24px", borderRadius: 999,
                background: "#ec4899", color: "#ffffff",
                border: "none", cursor: "pointer", fontSize: 13, fontWeight: 600,
                boxShadow: "0 4px 14px rgba(236, 72, 153, 0.4)",
              }}
            >
              <Square size={14} fill="#ffffff" />
              <span>Click to Interrupt</span>
            </button>
          </div>
        </div>
      ) : (
        /* ── CLIENT HOME UI ─────────────────── */
        <div className="dashboard-container" style={{
          backgroundImage: "linear-gradient(to bottom, rgba(255,255,255,0.85), rgba(255,255,255,0.95)), url('/gemini-bg.png')",
          backgroundSize: "cover", backgroundPosition: "center",
          color: "#1e293b",
        }}>
          {/* Top Bar Header */}
          <header style={{ height: 54, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>my_agent</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Link
                href="/dashboard"
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 14px", fontSize: 12, fontWeight: 600, color: "#0f172a",
                  background: "#ffffff", border: "1px solid rgba(0,0,0,0.1)",
                  borderRadius: 999, textDecoration: "none", boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                }}
              >
                <LayoutDashboard size={14} />
                Admin Dashboard
              </Link>
            </div>
          </header>

          {/* Main Responsive 3-Column Layout Container */}
          <main className="dashboard-main-grid">
            {/* ── LEFT COLUMN (Top: Calendar | Bottom: Employee Roster) ── */}
            <div style={{ display: "flex", flexDirection: "column", gap: "clamp(6px, 1.2vh, 14px)", overflow: "hidden", height: "100%" }}>
              <CalendarWidget />
              <EmployeeStack activeAgentId={activeAgentId} onSelectAgent={setActiveAgentId} />
            </div>

            {/* ── CENTER COLUMN (Main Hub Interaction View) ── */}
            <div style={{
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "flex-start",
              position: "relative", height: "100%", overflowY: "auto",
              paddingRight: 4, gap: 14,
            }}>
              {/* Centered Hero Title */}
              <div style={{ textAlign: "center", paddingTop: 10, maxWidth: 600 }}>
                <h1 style={{ fontSize: 32, fontWeight: 400, color: "#0f172a", letterSpacing: "-0.02em", margin: "0 0 4px" }}>
                  What's next, sir?
                </h1>
                <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                  Interacting with <strong style={{ color: "#ec4899" }}>{activeAgent.name}</strong>. Ask a question or click the Orb for speech mode.
                </p>
              </div>

              {/* Large Floating Input Bar with Glowing Pink Voice Orb */}
              <div style={{ width: "100%", maxWidth: 540, position: "relative" }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 10,
                  background: "#ffffff", borderRadius: 999,
                  padding: "6px 12px 6px 14px",
                  boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
                  border: "1px solid rgba(226, 232, 240, 0.9)",
                }}>
                  <button title="Add attachment" style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", display: "flex", alignItems: "center", padding: 2 }}>
                    <Plus size={16} />
                  </button>

                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleSendText();
                      }
                    }}
                    placeholder={`Ask ${activeAgent.name}...`}
                    style={{
                      flex: 1, border: "none", outline: "none",
                      fontSize: 12, color: "#0f172a", background: "transparent",
                      fontFamily: "inherit",
                    }}
                  />

                  <button
                    onClick={startVoiceMode}
                    title="Click to switch to speech mode"
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      padding: 2, borderRadius: "50%", transition: "transform 150ms",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.1)")}
                    onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
                  >
                    <SiriOrb size={22} animationDuration={20} />
                  </button>
                </div>
              </div>

              {/* Message Stream if user typed */}
              {messages.length > 0 && (
                <div style={{ width: "100%", maxWidth: 540, display: "flex", flexDirection: "column", gap: 8 }}>
                  {messages.map((msg) => (
                    <div key={msg.id} style={{ display: "flex", gap: 8, justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                      <div style={{
                        maxWidth: "85%", padding: "8px 12px", fontSize: 12, lineHeight: 1.5,
                        borderRadius: 12,
                        background: msg.sender === "user" ? "#0f172a" : "#ffffff",
                        color: msg.sender === "user" ? "#ffffff" : "#0f172a",
                        border: "1px solid rgba(0,0,0,0.06)",
                      }}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* Active Agent Workspace Information (Renders Directly Below Prompt Capsule) */}
              <div style={{ width: "100%", maxWidth: 600, paddingBottom: 16 }}>
                {renderActiveAgentWorkspace()}
              </div>
            </div>

            {/* ── RIGHT COLUMN (Right Box: Daily To-Do List) ── */}
            <div style={{ height: "100%", overflow: "hidden" }}>
              <AgentTodoList activeAgentId={activeAgentId} activeAgentName={activeAgent.name} />
            </div>
          </main>
        </div>
      )}
    </div>
  );
}
