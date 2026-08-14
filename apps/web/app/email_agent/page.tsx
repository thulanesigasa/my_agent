"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Send, CheckCircle2, Clock } from "lucide-react";

export default function EmailAgentPage() {
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
              <Mail size={18} />
            </div>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: "#0f172a" }}>email_agent Dashboard</h1>
              <span style={{ fontSize: 11, color: "#64748b" }}>Outreach Email Dispatcher & Queue</span>
            </div>
          </div>
        </div>

        <button style={{
          display: "flex", alignItems: "center", gap: 6,
          padding: "8px 16px", borderRadius: 10, background: "#ec4899", color: "#fff",
          fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer",
        }}>
          <Send size={14} />
          Dispatch Email Batch
        </button>
      </div>

      {/* Email Queue Card */}
      <div style={{ background: "#ffffff", borderRadius: 16, border: "1px solid rgba(226,232,240,0.8)", padding: "20px" }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: "0 0 16px" }}>Standerton Outreach Queued Emails</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Standerton Auto Repair & Panelbeating</h4>
              <span style={{ fontSize: 11, color: "#64748b" }}>info@standertonauto.co.za</span>
            </div>
            <span style={{ fontSize: 11, color: "#10b981", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle2 size={13} /> Queued
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px", background: "#f8fafc", borderRadius: 10 }}>
            <div>
              <h4 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>Lekwa Bakery & Supply Store</h4>
              <span style={{ fontSize: 11, color: "#64748b" }}>orders@lekwabakery.co.za</span>
            </div>
            <span style={{ fontSize: 11, color: "#10b981", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle2 size={13} /> Queued
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
