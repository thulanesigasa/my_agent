"use client";

import React, { useState, useEffect } from "react";
import { apiRequest, getPendingApprovals } from "@/lib/api";
import { ShieldAlert, CheckCircle2, XCircle, Edit3, Mail, RefreshCw } from "lucide-react";

export interface PendingAction {
  thread_id: string;
  recipient_email: string;
  subject: string;
  report_id?: string;
  followup_of?: string;
  reply_snapshot?: { assessment: { category: string }; edited_before_queue: boolean };
  proposal_snapshot?: { portfolio_url: string; projects: { id: string; name: string; url: string; reason: string }[]; edited_before_queue: boolean };
  intent: string;
  email_input?: {
    sender?: string;
    subject?: string;
    body?: string;
  };
  draft_response: string;
  status: string;
  error?: string;
}

export const ApprovalQueueDashboard: React.FC = () => {
  const [queue, setQueue] = useState<PendingAction[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    try {
      setError("");
      setQueue(await getPendingApprovals());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval queue unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleAction = async (threadId: string, action: "approve" | "edit" | "reject") => {
    setBusy(threadId);
    setError("");
    try {
      await apiRequest(`/api/approvals/${encodeURIComponent(threadId)}/action`, {
        method: "POST", body: JSON.stringify({ action, new_content: action === "edit" ? editText : undefined }),
      });
      setEditingId(null);
      await fetchApprovals();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      // Keep the draft visible after failure. Refresh exposes any held delivery state.
      try { setQueue(await getPendingApprovals()); } catch { /* Keep the existing view. */ }
    } finally { setBusy(null); }
  };

  async function reconcile(threadId: string) {
    setBusy(threadId); setError(""); setNotice("");
    try {
      const result = await apiRequest(`/api/gmail/approvals/${encodeURIComponent(threadId)}/reconcile`, { method: "POST" });
      await fetchApprovals();
      setNotice(result.message || "Gmail confirmed the original submission. No new email was sent.");
    } catch (e) { setError(e instanceof Error ? e.message : "Reconciliation failed"); }
    finally { setBusy(null); }
  }

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

      {notice && <p role="status" className="text-sm text-emerald-700 mb-4">{notice}</p>}
      {error && <p role="alert" className="text-sm text-red-700 mb-4">{error}</p>}
      {loading ? <p>Loading approval queue…</p> : !error && queue.length === 0 ? (
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

              <p className="text-sm break-all"><strong>To:</strong> {item.recipient_email}<br /><strong>Subject:</strong> {item.subject}</p>
              {item.followup_of && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Single follow-up to earlier outreach. Sync Gmail before approving: any recorded reply, bounce or outcome blocks sending. The saved message below is the content that will be sent.</p>}
              {item.reply_snapshot && <p className="rounded-lg bg-slate-50 p-3 text-sm">Local response template · suggested {item.reply_snapshot.assessment.category}. {item.reply_snapshot.edited_before_queue ? "Edited before queueing." : "Template text was used when queueing."} Check the message answers the actual reply. A newer human response blocks sending this draft.</p>}
              {item.proposal_snapshot && <div className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium">Portfolio used for initial proposal</p><a className="text-indigo-700 underline" href={item.proposal_snapshot.portfolio_url} target="_blank" rel="noreferrer">Agency portfolio</a>{item.proposal_snapshot.projects.map((p) => <p key={p.id}><a className="text-indigo-700 underline" href={p.url} target="_blank" rel="noreferrer">{p.name}</a> · {p.reason}</p>)}<p className="mt-2 text-xs text-slate-500">Saved source snapshot; later portfolio changes do not rewrite this message. {item.proposal_snapshot.edited_before_queue ? "The generated text was edited before queueing." : "Generated text was used when queueing."} Review the current message below before sending.</p></div>}
              {item.report_id && <p className="text-sm text-slate-600">Attachment: saved Excel report. Download the snapshot from Reports to review its figures.</p>}
              {/* Proposed Response Draft */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700">
                  Proposed Draft:
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

              <p className="text-xs text-slate-600">Status: {item.status} {item.error}</p>
              {["sending", "delivery_unknown"].includes(item.status) && <button disabled={busy === item.thread_id} onClick={() => reconcile(item.thread_id)} className="rounded border border-slate-300 p-2 text-sm">Reconcile with Gmail Sent</button>}
              {/* Interactive Controls */}
              <fieldset disabled={busy === item.thread_id || ["sending", "delivery_unknown"].includes(item.status)} className="flex items-center justify-end gap-2 pt-2 disabled:opacity-50">
                {editingId === item.thread_id ? (
                  <>
                    <button
                      onClick={() => handleAction(item.thread_id, "edit")}
                      className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow"
                    >
                      Save Draft
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
              </fieldset>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
