"use client";

import { useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Lead = { id: string; name: string; location: string; ready_to_draft: boolean };
type Campaign = { id: string; name: string; status: string; version: number; cursor: number; lead_ids: string[]; local_time: string; weekdays_only: boolean; batch_size: number; next_run_at: string | null };
type Run = { id: string; campaign_id: string; day: string; status: string; results: { lead_id: string; decision: string; approval_status?: string; reason?: string }[] };
type Data = { campaigns: Campaign[]; runs: Run[]; draft_budget: { day: string; used: number; limit: number }; worker_enabled: boolean };
const input = "mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";

export function Campaigns({ leads }: { leads: Lead[] }) {
  const [data, setData] = useState<Data | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [form, setForm] = useState({ name: "", local_time: "09:00", batch_size: "3", weekdays_only: true });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const { setTab } = useContext(TabContext);
  async function load() { setData(await apiRequest("/api/campaigns")); }
  async function act(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); await load(); }
    catch (e) { setError(e instanceof Error ? e.message : "Campaign operation failed"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(load); }, []);
  useEffect(() => { setSelected((prior) => prior.filter((id) => leads.some((lead) => lead.id === id && lead.ready_to_draft))); }, [leads]);
  const active = Boolean(data?.campaigns.some((c) => c.status === "active"));
  useEffect(() => {
    if (!active) return;
    let pending = false;
    const timer = setInterval(async () => { if (pending) return; pending = true; try { await load(); } catch (e) { setError(e instanceof Error ? e.message : "Could not refresh campaigns"); } finally { pending = false; } }, 15000);
    return () => clearInterval(timer);
  }, [active]);
  const eligible = leads.filter((lead) => lead.ready_to_draft);
  async function control(c: Campaign, action: string) {
    await apiRequest(`/api/campaigns/${c.id}`, { method: "PATCH", body: JSON.stringify({ action, version: c.version }) });
  }
  return <details className="space-y-4 rounded-xl border border-indigo-200 bg-white p-5">
    <summary className="cursor-pointer font-semibold">Campaign schedules · drafts for approval</summary>
    <p className="text-sm text-slate-600">Select up to 20 currently qualified leads with recorded permission. Each daily batch assesses 1–5 selected leads and prepares local portfolio proposals for Approvals. It never sends email or performs research. Campaigns start paused.</p>
    <p className="text-sm">Campaign drafting attempts today ({data?.draft_budget.day || "SAST"}): <strong>{data?.draft_budget.used ?? 0} / {data?.draft_budget.limit ?? 10}</strong> across this installation. This is separate from the business-send limit.</p>
    {data && !data.worker_enabled && <p className="text-sm text-amber-800">Scheduled campaign worker is disabled. Set CAMPAIGNS_ENABLED=true and restart the backend for scheduled runs. Manual batches remain available after activation.</p>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    <div className="flex flex-wrap gap-3"><button className={button} disabled={busy} onClick={() => void act(load)}>Refresh campaigns</button><button className={button} onClick={() => setTab("approvals")}>Open Approvals</button></div>
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); void act(async () => { await apiRequest("/api/campaigns", { method: "POST", body: JSON.stringify({ ...form, batch_size: Number(form.batch_size), lead_ids: selected }) }); setSelected([]); setForm({ ...form, name: "" }); setNotice("Campaign saved paused. Review its members and schedule, then activate when ready."); }); }}>
      <div className="grid gap-3 sm:grid-cols-3"><label className="text-sm">Campaign name<input className={input} required maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label className="text-sm">Daily run time · SAST<input className={input} type="time" required value={form.local_time} onChange={(e) => setForm({ ...form, local_time: e.target.value })} /></label><label className="text-sm">Leads assessed per batch<input className={input} type="number" required min={1} max={5} value={form.batch_size} onChange={(e) => setForm({ ...form, batch_size: e.target.value })} /></label></div>
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={form.weekdays_only} onChange={(e) => setForm({ ...form, weekdays_only: e.target.checked })} />Scheduled runs Monday–Friday only</label>
      <fieldset className="max-h-48 space-y-2 overflow-auto rounded-lg border border-slate-200 p-3"><legend className="text-sm">Selected leads ({selected.length}/20)</legend>{eligible.map((lead) => <label key={lead.id} className="flex gap-2 text-sm"><input type="checkbox" checked={selected.includes(lead.id)} disabled={!selected.includes(lead.id) && selected.length >= 20} onChange={(e) => setSelected(e.target.checked ? [...selected, lead.id] : selected.filter((id) => id !== lead.id))} />{lead.name} · {lead.location}</label>)}{eligible.length === 0 && <p className="text-sm text-slate-500">No eligible reviewed leads yet. Complete the evidence review and record actual contact permission before adding campaign members. Connection-test contacts are not campaign leads.</p>}</fieldset>
      <button className={button} disabled={busy || selected.length === 0}>Save paused campaign</button>
    </form>
    <p className="text-xs text-slate-500">At most one batch per campaign per SAST day, including manual runs. A manual batch can run before its scheduled time or on a weekend. Pausing stops subsequent leads; a draft already being prepared may finish. Keep the backend running for schedules. Interrupted batches pause for review; missed dates are not replayed as separate batches. Business-send pause does not pause campaign drafting.</p>
    <div className="space-y-3">{data?.campaigns.map((c) => {
      const runs = data.runs.filter((r) => r.campaign_id === c.id);
      const ranToday = runs.some((r) => r.day === data.draft_budget.day);
      const unfinished = ["active", "paused"].includes(c.status);
      return <article key={c.id} className="space-y-3 rounded-lg border border-slate-200 p-4"><div><h3 className="font-medium">{c.name}</h3><p className="text-sm capitalize">{c.status} · {c.cursor}/{c.lead_ids.length} assessed · {c.batch_size} per batch</p><p className="text-xs text-slate-500">{c.local_time} SAST · {c.weekdays_only ? "Monday–Friday" : "Daily"}{c.next_run_at ? ` · Next: ${new Date(c.next_run_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" })} SAST` : ""}</p></div>
        {unfinished && <div className="flex flex-wrap gap-2"><button className={button} disabled={busy} onClick={() => void act(() => control(c, c.status === "active" ? "pause" : "resume"))}>{c.status === "active" ? "Pause campaign" : "Activate schedule"}</button><button className={button} disabled={busy || c.status !== "active" || ranToday} onClick={() => void act(async () => { await apiRequest(`/api/campaigns/${c.id}/run`, { method: "POST" }); setNotice("Campaign batch finished. Review the saved run history and Approvals; no email was sent."); })}>{ranToday ? "Batch already attempted today" : "Prepare today's batch now"}</button><button className={button} disabled={busy} onClick={() => void act(() => control(c, "cancel"))}>Cancel remaining campaign</button></div>}
        <details><summary className="cursor-pointer text-sm">Selected members and recent run history</summary><ul className="mt-2 space-y-1 text-xs text-slate-600">{c.lead_ids.map((id) => <li key={id}>{leads.find((lead) => lead.id === id)?.name || id}</li>)}</ul>{runs.map((r) => <div key={r.id} className="mt-3 space-y-1 text-xs"><strong>{r.day} · {r.status.replaceAll("_", " ")}</strong>{r.results.map((result) => <p key={result.lead_id}>{leads.find((lead) => lead.id === result.lead_id)?.name || result.lead_id}: {result.decision.replaceAll("_", " ")}{result.approval_status ? ` (${result.approval_status})` : ""}{result.reason ? ` · ${result.reason}` : ""}</p>)}</div>)}</details>
      </article>;
    })}</div>
  </details>;
}
