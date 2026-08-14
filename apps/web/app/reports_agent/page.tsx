"use client";

import React from "react";
import Link from "next/link";
import { ArrowLeft, Download, LayoutDashboard } from "lucide-react";

export default function ReportsAgentPage() {
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
          <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>reports_agent</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(236,72,153,0.1)", color: "#ec4899", fontWeight: 600 }}>
            Lead Analytics & Reports
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

      {/* Main Content Area */}
      <main style={{ maxWidth: 1000, margin: "32px auto", padding: "0 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
              Standerton Lead Conversion & Analytics Report
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
              Weekly discovery & campaign performance compiled for Standerton, Mpumalanga
            </p>
          </div>

          <button style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "8px 16px", borderRadius: 999, background: "#ec4899", color: "#ffffff",
            fontSize: 12, fontWeight: 600, border: "none", cursor: "pointer",
            boxShadow: "0 4px 12px rgba(236, 72, 153, 0.3)",
          }}>
            <Download size={14} />
            Export PDF Report
          </button>
        </div>

        {/* Metric Cards Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
          <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>Discovered Leads</span>
            <h3 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: "#0f172a" }}>8 Businesses</h3>
            <span style={{ fontSize: 11, color: "#16a34a", fontWeight: 600, marginTop: 4, display: "block" }}>+100% vs last week</span>
          </div>

          <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>Emails Dispatched</span>
            <h3 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: "#ec4899" }}>250 Emails</h3>
            <span style={{ fontSize: 11, color: "#16a34a", fontWeight: 600, marginTop: 4, display: "block" }}>+14.2% delivery speed</span>
          </div>

          <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>Response Rate</span>
            <h3 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: "#10b981" }}>32.0%</h3>
            <span style={{ fontSize: 11, color: "#10b981", fontWeight: 600, marginTop: 4, display: "block" }}>Above average</span>
          </div>

          <div style={{ background: "#ffffff", padding: "18px 20px", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)", boxShadow: "0 2px 8px rgba(0,0,0,0.02)" }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>Active Pipeline</span>
            <h3 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: "#0f172a" }}>47 Prospects</h3>
            <span style={{ fontSize: 11, color: "#16a34a", fontWeight: 600, marginTop: 4, display: "block" }}>Qualified leads</span>
          </div>
        </div>

        {/* Detailed Summary Box */}
        <div style={{ background: "#ffffff", padding: "24px", borderRadius: 12, border: "1px solid rgba(226,232,240,0.9)" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 10px", color: "#0f172a" }}>Executive Summary & Lead Breakdown</h3>
          <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.6, margin: 0 }}>
            Research agent scanned local business registries across Standerton, Mpumalanga and identified 8 high-intent commercial entities operating without an official website. Email outreach agent launched initial digital strategy proposals yielding 32% direct client response.
          </p>
        </div>
      </main>
    </div>
  );
}
