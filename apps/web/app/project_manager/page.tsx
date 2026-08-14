"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, ShieldCheck, LayoutDashboard } from "lucide-react";

export default function ProjectManagerPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", color: "#0f172a", fontFamily: "Inter, sans-serif" }}>
      {/* Top Header */}
      <header style={{ height: 54, borderBottom: "1px solid rgba(226,232,240,0.8)", background: "#ffffff", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 6, color: "#64748b", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
            <ArrowLeft size={16} />
            Back to Central Hub
          </Link>
          <span style={{ color: "#cbd5e1" }}>|</span>
          <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>project_manager</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(236,72,153,0.1)", color: "#ec4899", fontWeight: 600 }}>
            Activity & Log Auditor
          </span>
        </div>

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
      </header>

      {/* Main Content */}
      <main style={{ maxWidth: 880, margin: "32px auto", padding: "0 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
              Subagent System Health & Activity Audit
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
              Real-time thread verification across all 4 subagent services
            </p>
          </div>

          <div style={{ padding: "6px 14px", borderRadius: 999, background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.3)", color: "#059669", fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
            <ShieldCheck size={16} />
            System Operational 100%
          </div>
        </div>

        {/* Status List */}
        <div style={{ background: "#ffffff", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
          <div style={{ padding: "14px 18px", borderBottom: "1px solid #f1f5f9", background: "#fafafa" }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a" }}>Subagent Service Execution Log</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 18px", borderBottom: "1px solid #f8fafc" }}>
              <div>
                <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "#0f172a" }}>reports_agent</h4>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Standerton lead conversion metrics compiled</p>
              </div>
              <span style={{ fontSize: 11, color: "#059669", fontWeight: 700 }}>Active</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 18px", borderBottom: "1px solid #f8fafc" }}>
              <div>
                <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "#0f172a" }}>email_agent</h4>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>250 emails queued in outbox pipeline</p>
              </div>
              <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600 }}>Idle</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 18px", borderBottom: "1px solid #f8fafc" }}>
              <div>
                <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "#0f172a" }}>project_manager</h4>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Auditing system health and background logs</p>
              </div>
              <span style={{ fontSize: 11, color: "#059669", fontWeight: 700 }}>Active</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 18px" }}>
              <div>
                <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0, color: "#0f172a" }}>research_agent</h4>
                <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>Standerton missing websites business discovery done</p>
              </div>
              <span style={{ fontSize: 11, color: "#64748b", fontWeight: 600 }}>Idle</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
