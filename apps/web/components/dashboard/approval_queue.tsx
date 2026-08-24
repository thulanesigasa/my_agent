"use client";

import React, { useState, useEffect } from "react";
import { ShieldAlert, CheckCircle2, XCircle, Edit3, Mail, RefreshCw } from "lucide-react";

export interface PendingAction {
  thread_id: string;
  intent: string;
  email_input?: {
    sender?: string;
    subject?: string;
    body?: string;
  };
  draft_response: string;
  status: string;
}

export const ApprovalQueueDashboard: React.FC = () => {
  const [queue, setQueue] = useState<PendingAction[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const fetchApprovals = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/approvals`);
      const data = await res.json();
      if (data.approvals) setQueue(data.approvals);
    } catch (e) {
      console.warn("Failed to fetch approvals:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleAction = async (threadId: string, action: "approve" | "edit" | "reject") => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/approvals/${threadId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          new_content: action === "edit" ? editText : undefined,
        }),
      });
      setEditingId(null);
      fetchApprovals();
    } catch (e) {
      console.error("Action submission error:", e);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-white rounded-2xl border border-slate-200 shadow-xl">
      <div className="flex items-center justify-between pb-4 mb-6 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-200">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-800">
              Human-in-the-Loop Approval Queue
            </h3>
            <p className="text-xs text-slate-500">
              Review and approve high-risk external dispatches and client inquiries
            </p>
          </div>
        </div>
        <button
          onClick={fetchApprovals}
          className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {queue.length === 0 ? (
        <div className="py-12 text-center text-slate-400">
          <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500/60" />
          <p className="text-sm font-medium text-slate-700">Approval Queue is Empty</p>
          <p className="text-xs text-slate-400">All agent actions are reviewed and clear.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {queue.map((item) => (
            <div
              key={item.thread_id}
              className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4 shadow-sm"
            >
              {/* Context Header */}
              <div className="flex items-center justify-between text-xs">
                <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 font-medium flex items-center gap-1">
                  <Mail className="w-3.5 h-3.5" /> Intent: {item.intent}
                </span>
                <span className="font-mono text-slate-400">Thread: {item.thread_id}</span>
              </div>

              {/* Incoming Context */}
              {item.email_input && (
                <div className="p-3 rounded-lg bg-white border border-slate-200 text-xs space-y-1">
                  <p className="font-semibold text-slate-700">From: {item.email_input.sender}</p>
                  <p className="text-slate-600">Subject: {item.email_input.subject}</p>
                  <p className="text-slate-500 italic">"{item.email_input.body}"</p>
                </div>
              )}

              {/* Proposed Response Draft */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700">
                  Proposed Draft (Gemini 1.5 Pro):
                </label>
                {editingId === item.thread_id ? (
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full p-3 text-xs bg-white border border-indigo-300 rounded-lg focus:outline-none text-slate-800"
                    rows={4}
                  />
                ) : (
                  <div className="p-3.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-800 leading-relaxed whitespace-pre-wrap">
                    {item.draft_response}
                  </div>
                )}
              </div>

              {/* Interactive Controls */}
              <div className="flex items-center justify-end gap-2 pt-2">
                {editingId === item.thread_id ? (
                  <>
                    <button
                      onClick={() => handleAction(item.thread_id, "edit")}
                      className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow"
                    >
                      Save & Approve
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-3 py-2 rounded-lg bg-slate-200 text-slate-700 text-xs"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleAction(item.thread_id, "approve")}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Approve & Send
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(item.thread_id);
                        setEditText(item.draft_response);
                      }}
                      className="px-3 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold flex items-center gap-1 border border-indigo-200"
                    >
                      <Edit3 className="w-3.5 h-3.5" /> Edit Draft
                    </button>
                    <button
                      onClick={() => handleAction(item.thread_id, "reject")}
                      className="px-3 py-2 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold flex items-center gap-1 border border-rose-200"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Reject
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
};
