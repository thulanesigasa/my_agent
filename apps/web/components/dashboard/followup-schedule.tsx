"use client";

import { useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Config = { version: number; paused: boolean; local_time: string; weekdays_only: boolean; batch_size: number; next_run_at: string | null };
type Run = { id: string; status: string; created_at: string; results: { outbound_id: string; decision: string; approval_id?: string; reason?: string }[] };
type State = { config: Config; runs: Run[]; eligible_count: number; next_candidates: { id: string; recipient: string; subject: string }[]; fresh_sync: boolean; worker_enabled: boolean };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";

export function FollowupSchedule() {
  const [data, setData] = useState<State | null>(null);
  const [form, setForm] = useState<Config | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const { setTab } = useContext(TabContext);
  async function load() {
    const result: State = await apiRequest("/api/followups/schedule");
    setData(result); setForm(result.config);
  }
  async function act(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); } catch (e) { setError(e instanceof Error ? e.message : "Follow-up schedule failed"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(load); }, []);
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Scheduled follow-up drafts</h2><button className={button} disabled={busy} onClick={() => void act(load)}>Refresh schedule and history</button></div>
    <p className="text-sm text-slate-600">Opt in to one daily batch of up to three eligible no-response follow-ups. The schedule starts paused. Enabling it includes all current and future eligible conversations for this mailbox. Drafts go to Approvals; they are never sent by this schedule. No model or research credits are used.</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    {data && form && <>
      <p className="text-sm">Saved schedule: <strong>{data.config.paused ? "Paused" : "Enabled"}</strong> · Worker configuration: {data.worker_enabled ? "enabled" : "disabled"} · Next due: {data.config.next_run_at ? new Date(data.config.next_run_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" }) + " SAST" : "not scheduled"}</p>
      <div className="flex flex-wrap items-end gap-4 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={!form.paused} onChange={(e) => setForm({ ...form, paused: !e.target.checked })} />Enable daily draft preparation</label>
        <label>Time (SAST)<input type="time" className="mt-1 block rounded border p-2" value={form.local_time} onChange={(e) => setForm({ ...form, local_time: e.target.value })} /></label>
        <label>Batch size<select className="mt-1 block rounded border p-2" value={form.batch_size} onChange={(e) => setForm({ ...form, batch_size: Number(e.target.value) })}>{[1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={form.weekdays_only} onChange={(e) => setForm({ ...form, weekdays_only: e.target.checked })} />Weekdays only</label>
        <button className={button} disabled={busy || !form.local_time} onClick={() => void act(async () => { await apiRequest("/api/followups/schedule", { method: "PATCH", body: JSON.stringify({ version: form.version, paused: form.paused, local_time: form.local_time, weekdays_only: form.weekdays_only, batch_size: form.batch_size }) }); await load(); setNotice("Schedule saved. Review refreshed history for any batch already in progress."); })}>Save schedule</button>
      </div>
      <p className={`text-sm ${data.fresh_sync ? "text-slate-600" : "text-amber-800"}`}>{data.fresh_sync ? "A sync within 15 minutes is recorded." : "Waiting for a fresh Gmail sync (within 15 minutes)."} Each conversation must also be included in that sync and pass all current evidence, permission and no-response checks. This worker does not sync Gmail.</p>
      <p className="text-sm text-slate-600">{data.eligible_count} currently eligible conversation(s). Next candidates, oldest first:</p>
      {data.next_candidates.length ? <ul className="space-y-1 text-sm">{data.next_candidates.map((c) => <li key={c.id} className="break-all">{c.recipient} · {c.subject}</li>)}</ul> : <p className="text-sm text-slate-500">No eligible follow-ups now. Connection tests are excluded.</p>}
      <p className="text-xs text-slate-500">Keep the backend running. Missed days are not replayed. Manual preparation ignores the scheduled time and weekday, but still requires an enabled schedule, fresh sync and an unused daily batch. The scheduled cap is separate from campaign drafting and business sending limits. Existing individual follow-up controls remain available.</p>
      <div className="flex flex-wrap gap-3"><button className={button} disabled={busy || data.config.paused || !data.fresh_sync || !data.eligible_count} onClick={() => void act(async () => { const result = await apiRequest("/api/followups/schedule/run", { method: "POST" }); await load(); setNotice(result ? `Batch ${result.status}. Review its results and Approvals. No email was sent.` : "No eligible batch was prepared. Refresh eligibility after syncing."); })}>Prepare today’s batch now</button><button className="text-sm text-indigo-700 underline" onClick={() => setTab("settings")}>Sync Gmail in Settings</button><button className="text-sm text-indigo-700 underline" onClick={() => setTab("approvals")}>Review Approvals</button></div>
      <details><summary className="cursor-pointer text-sm font-medium">Recent batch history ({data.runs.length})</summary><div className="mt-3 space-y-3">{data.runs.map((run) => <article key={run.id} className="rounded-lg border p-3 text-xs"><p>{new Date(run.created_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" })} SAST · {run.status}</p>{run.results.map((row) => <p key={row.outbound_id} className="mt-1 break-all">{row.decision} · {row.approval_id || row.outbound_id}{row.reason ? ` · ${row.reason}` : ""}</p>)}{["interrupted", "stopped", "failed"].includes(run.status) && <p className="mt-2 text-amber-800">Some members may be unfinished. Review existing Approvals before resuming. A partial batch is not replayed today.</p>}</article>)}</div></details>
    </>}
  </section>;
}
