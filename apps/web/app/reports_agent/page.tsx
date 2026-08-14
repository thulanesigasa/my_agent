"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Download, FileText, TrendingUp, Users } from "lucide-react";

export default function ReportsAgentPage() {
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
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "#ec4899", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <BarChart3 size={18} />
            </div>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>reports_agent Dashboard</h1>
              <span style={{ fontSize: 11, color: "#64748b" }}>Analytics & Lead Conversion Reports</span>
            </div>
          </div>
        </div>

        <button style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "8px 16px", borderRadius: 10, background: "#0f172a", color: "#fff",
          fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer",
        }}>
          <Download size={14} />
          Export Report PDF
        </button>
      </div>

      {/* Metrics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16, marginBottom: 24 }}>
        <div style={{ background: "#ffffff", padding: "16px", borderRadius: 14, border: "1px solid rgba(226,232,240,0.8)", boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
          <span style={{ fontSize: 12, color: "#64748b" }}>Standerton Leads Discovered</span>
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: "6px 0 0", color: "#0f172a" }}>8 Businesses</h2>
        </div>
        <div style={{ background: "#ffffff", padding: "16px", borderRadius: 14, border: "1px solid rgba(226,232,240,0.8)", boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
          <span style={{ fontSize: 12, color: "#64748b" }}>Emails Dispatched</span>
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: "6px 0 0", color: "#ec4899" }}>250 Emails</h2>
        </div>
        <div style={{ background: "#ffffff", padding: "16px", borderRadius: 14, border: "1px solid rgba(226,232,240,0.8)", boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
          <span style={{ fontSize: 12, color: "#64748b" }}>Engagement Response Rate</span>
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: "6px 0 0", color: "#10b981" }}>32.0%</h2>
        </div>
        <div style={{ background: "#ffffff", padding: "16px", borderRadius: 14, border: "1px solid rgba(226,232,240,0.8)", boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
          <span style={{ fontSize: 12, color: "#64748b" }}>Active Leads Pipeline</span>
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: "6px 0 0", color: "#0f172a" }}>47 Prospects</h2>
        </div>
      </div>

      {/* Summary Stream */}
      <div style={{ background: "#ffffff", borderRadius: 16, border: "1px solid rgba(226,232,240,0.8)", padding: "20px" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 12px" }}>Standerton Lead Performance Report</h3>
        <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.6 }}>
          The <strong>reports_agent</strong> compiled recent lead discovery metrics for Standerton, Mpumalanga. 8 active local service businesses without websites were identified and enriched with contact information. Outreach campaigns achieved a 32% response rate.
        </p>
      </div>
    </div>
  );
}
