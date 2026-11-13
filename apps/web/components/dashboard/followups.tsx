"use client";

import { useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Candidate = { id: string; recipient: string; subject: string; due_at: string | null; eligible: boolean; blocker: string };
type Policy = { wait_days: number; max_followups: number; sync_minutes: number; candidates: Candidate[] };
type Preview = { id: string; subject: string; body: string };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";

export function FollowupsDashboard() {
  const [data, setData] = useState<Policy | null>(null);
  const [selected, setSelected] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const { setTab } = useContext(TabContext);
  async function load() { setData(await apiRequest("/api/followups")); }
  async function act(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); }
    catch (e) { setError(e instanceof Error ? e.message : "Follow-up operation failed"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(load); }, []);
  const active = data?.candidates.find((candidate) => candidate.id === selected);
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Follow-ups awaiting review</h2><button className={button} disabled={busy} onClick={() => void act(load)}>Refresh eligibility</button></div>
    <p className="text-sm text-slate-600">One follow-up per outreach conversation, after {data?.wait_days ?? 7} days with no recorded reply. Sync Gmail within {data?.sync_minutes ?? 15} minutes before preparing or sending. Current lead qualification and contact permission remain required. Drafts use no model or research credits.</p>
    <button className="text-sm text-indigo-700 underline" onClick={() => setTab("settings")}>Open Gmail Settings to sync replies</button>
    <p className="text-xs text-slate-500">Connection tests are excluded. Any recorded reply, automated notice, bounce, explicit outcome or uncertain submission blocks this workflow. Opening this page never sends or queues an email.</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    {data?.candidates.length === 0 && <p className="text-sm text-slate-500">No confirmed business outreach conversations yet. Your connection-test emails will not appear here.</p>}
    <div className="grid gap-4 lg:grid-cols-2"><div className="max-h-80 space-y-2 overflow-auto">{data?.candidates.map((candidate) => <button key={candidate.id} onClick={() => { setSelected(candidate.id); setPreview(null); setBody(""); setNotice(""); }} className={`w-full space-y-1 rounded-lg border p-3 text-left text-sm ${candidate.id === selected ? "border-indigo-300 bg-indigo-50" : "border-slate-200"}`}>
      <strong className="block break-all">{candidate.recipient}</strong><span className="block">{candidate.subject}</span>
      {candidate.due_at && <span className="block text-xs text-slate-500">Available after: {new Date(candidate.due_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" })} SAST</span>}
      <span className={`block text-xs ${candidate.eligible ? "text-emerald-700" : "text-amber-800"}`}>{candidate.eligible ? "Eligible to prepare for approval" : candidate.blocker}</span>
    </button>)}</div>
    {active && <div className="space-y-3"><p className="break-all text-sm font-medium">Follow up with {active.recipient}</p>
      {!active.eligible && <p className="text-sm text-amber-800">{active.blocker}</p>}
      <button className={button} disabled={busy || !active.eligible} onClick={() => void act(async () => { const result: Preview = await apiRequest(`/api/followups/${encodeURIComponent(active.id)}/preview`, { method: "POST" }); setPreview(result); setBody(result.body); })}>Prepare follow-up draft</button>
      {preview && <><p className="text-sm">Subject: {preview.subject}</p><label className="block text-sm">Message<textarea className="mt-1 block w-full rounded-lg border border-slate-300 p-3 text-sm" rows={9} maxLength={20000} value={body} onChange={(e) => setBody(e.target.value)} /></label><button className={button} disabled={busy || !active.eligible || !body.trim()} onClick={() => void act(async () => { await apiRequest(`/api/followups/${encodeURIComponent(active.id)}/draft`, { method: "POST", body: JSON.stringify({ preview_id: preview.id, body }) }); await load(); setNotice("Follow-up saved in Approvals. No email was sent."); })}>Save for approval</button><button className="ml-3 text-sm text-indigo-700 underline" onClick={() => setTab("approvals")}>Open Approvals</button></>}
    </div>}
    </div>
  </section>;
}
