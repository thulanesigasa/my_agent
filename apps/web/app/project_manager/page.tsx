"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, FolderKanban, ShieldCheck, Zap, Activity } from "lucide-react";

export default function ProjectManagerPage() {
  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(to bottom, rgba(255,255,255,0.9), rgba(248,250,252,0.95)), url('/gemini-bg.png')",
      backgroundSize: "cover",
      color: "#0f172a",
      fontFamily: "'Inter', sans-serif",
      padding: "24px",
    }}>
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, color: "#64748b", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            <ArrowLeft size={16} />
            Back to Hub
          </Link>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "#0f172a", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <FolderKanban size={18} />
            </div>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>project_manager Dashboard</h1>
              <span style={{ fontSize: 11, color: "#64748b" }}>Agent Activity Auditor & Log Monitor</span>
            </div>
          </div>
        </div>

        <div style={{ padding: "6px 12px", borderRadius: 999, background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)", color: "#059669", fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
          <ShieldCheck size={16} />
          System Operational 100%
        </div>
      </div>

      {/* Agent Activity Cards */}
      <div style={{ background: "#ffffff", borderRadius: 16, border: "1px solid rgba(226,232,240,0.8)", padding: "20px" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 16px" }}>Subagent System Health & Activity Audit</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>reports_agent</span>
            <span style={{ fontSize: 12, color: "#059669", fontWeight: 600 }}>🟢 Active — Standerton report compiled</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>email_agent</span>
            <span style={{ fontSize: 12, color: "#64748b" }}>💤 Asleep — 250 emails queued</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>project_manager</span>
            <span style={{ fontSize: 12, color: "#059669", fontWeight: 600 }}>🟢 Active — Auditing log health</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>research_agent</span>
            <span style={{ fontSize: 12, color: "#64748b" }}>💤 Asleep — Standerton business discovery done</span>
          </div>
        </div>
      </div>
    </div>
  );
}
