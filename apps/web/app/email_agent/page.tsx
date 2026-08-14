"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle, Edit3, XCircle, CheckCircle2, LayoutDashboard } from "lucide-react";

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

export default function EmailAgentPage() {
  const [queue, setQueue] = useState<ApprovalItem[]>(INITIAL_APPROVALS);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const handleApprove = (id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
  };

  const handleReject = (id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
  };

  const handleStartEdit = (item: ApprovalItem) => {
    setEditingId(item.id);
    setEditText(item.body);
  };

  const handleSaveEdit = (id: string) => {
    setQueue((prev) =>
      prev.map((item) => (item.id === id ? { ...item, body: editText } : item))
    );
    setEditingId(null);
  };

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
          <span style={{ fontWeight: 700, fontSize: 16, color: "#0f172a" }}>email_agent</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, background: "rgba(236,72,153,0.1)", color: "#ec4899", fontWeight: 600 }}>
            Cold Outreach & Email Dispatch
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
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 4px", color: "#0f172a" }}>
            Human Approval Queue
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            Review agent-drafted emails for Standerton prospects before dispatch
          </p>
        </div>

        {queue.length === 0 ? (
          <div style={{ border: "1px solid #e8e8e8", borderRadius: 12, padding: "48px 24px", textAlign: "center", background: "#ffffff" }}>
            <CheckCircle2 size={36} strokeWidth={1.5} style={{ color: "#10b981", marginBottom: 8 }} />
            <h3 style={{ fontSize: 15, fontWeight: 600, color: "#0f172a", margin: 0 }}>Queue is Clear</h3>
            <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>All agent-drafted emails have been reviewed and dispatched.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {queue.map((item) => (
              <div
                key={item.id}
                style={{
                  border: "1px solid #e8e8e8",
                  borderRadius: 12,
                  overflow: "hidden",
                  background: "#ffffff",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
                }}
              >
                {/* Header */}
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "14px 18px", borderBottom: "1px solid #e8e8e8", background: "#fafafa",
                }}>
                  <div>
                    <h4 style={{ fontSize: 14, fontWeight: 700, color: "#111", margin: 0 }}>{item.company}</h4>
                    <p style={{ fontSize: 12, color: "#64748b", margin: "2px 0 0" }}>To: {item.to} · Subject: {item.subject}</p>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 700, color: "#64748b", border: "1px solid #e0e0e0", borderRadius: 4, padding: "3px 8px", background: "#ffffff" }}>
                    PENDING
                  </span>
                </div>

                {/* Draft Response Area */}
                <div style={{ padding: "16px 18px", borderBottom: "1px solid #e8e8e8" }}>
                  <p style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em", margin: "0 0 8px" }}>
                    DRAFT RESPONSE
                  </p>
                  {editingId === item.id ? (
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={5}
                      style={{
                        width: "100%", border: "1px solid #e0e0e0", borderRadius: 8,
                        padding: "10px 14px", fontSize: 13, color: "#0f172a", outline: "none",
                        resize: "vertical", fontFamily: "inherit",
                      }}
                    />
                  ) : (
                    <div style={{
                      border: "1px solid #e8e8e8", borderRadius: 8,
                      padding: "12px 16px", fontSize: 13, color: "#334155",
                      lineHeight: 1.6, whiteSpace: "pre-wrap", background: "#fafafa",
                    }}>
                      {item.body}
                    </div>
                  )}
                </div>

                {/* Actions Bar */}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "12px 18px", background: "#ffffff" }}>
                  {editingId === item.id ? (
                    <>
                      <button
                        onClick={() => handleSaveEdit(item.id)}
                        style={{ padding: "8px 16px", fontSize: 12, fontWeight: 600, background: "#111", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
                      >
                        Save & Send
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        style={{ padding: "8px 16px", fontSize: 12, fontWeight: 500, background: "#fff", color: "#64748b", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleApprove(item.id)}
                        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", fontSize: 12, fontWeight: 600, background: "#0f172a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
                      >
                        <CheckCircle size={14} strokeWidth={2} /> Approve & Send
                      </button>
                      <button
                        onClick={() => handleStartEdit(item)}
                        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 12, fontWeight: 500, background: "#fff", color: "#475569", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}
                      >
                        <Edit3 size={14} strokeWidth={2} /> Edit
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 14px", fontSize: 12, fontWeight: 500, background: "#fff", color: "#dc2626", border: "1px solid #e0e0e0", borderRadius: 6, cursor: "pointer" }}
                      >
                        <XCircle size={14} strokeWidth={2} /> Reject
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
