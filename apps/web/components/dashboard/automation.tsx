"use client";

import { useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Config = { version: number; paused: boolean; location: string; country: string; region: string; target_month: string; time_zone: string; industry: string; research_enabled: boolean; research_results: number; research_requests: number; daily_draft_limit: number; local_time: string; weekdays_only: boolean; weekly_report_email: boolean; qualification_enabled: boolean };
type Run = { id: string; status: string; created_at: string; results: { stage: string; status: string; reason?: string; approval_id?: string; job_id?: string }[]; lead_exceptions: { lead_id: string; name: string; reason: string }[] };
type State = { config: Config; targets: Config[]; target_label: string; budget: { used: number; limit: number; remaining: number }; worker_enabled: boolean; warning: string; runtime: { last_started_at: string; next_tick_at: string } | null; runs: Run[] };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";
const field = "mt-1 block w-full rounded-lg border border-slate-300 p-2";
const time = (s: string) => new Date(s).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" });

export function AutomationPanel({ compact = false }: { compact?: boolean }) {
  const [data, setData] = useState<State | null>(null);
  const [form, setForm] = useState<Config | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const { setTab } = useContext(TabContext);
  async function load(reset = false) {
    const result: State = await apiRequest("/api/automation");
    setData(result);
    if (reset) {
      const c = result.config;
      setForm({ version: c.version, paused: c.paused, location: c.location, country: c.country, region: c.region, target_month: c.target_month, time_zone: c.time_zone, industry: c.industry, research_enabled: c.research_enabled, research_results: c.research_results, research_requests: c.research_requests, daily_draft_limit: c.daily_draft_limit, local_time: c.local_time, weekdays_only: c.weekdays_only, weekly_report_email: c.weekly_report_email, qualification_enabled: c.qualification_enabled });
    }
  }
  useEffect(() => { void load(true).catch((e) => setError(e instanceof Error ? e.message : "Automation status unavailable")); }, []);
  useEffect(() => {
    const timer = setInterval(() => { if (!busy && document.visibilityState === "visible") void load().catch(() => {}); }, 15000);
    return () => clearInterval(timer);
  }, [busy]);
  async function save(value: Config) {
    setBusy(true); setError(""); setNotice("");
    try {
      await apiRequest("/api/automation", { method: "PATCH", body: JSON.stringify(value) });
      await load(true);
      setNotice(value.paused ? "Automation mode paused. Saved approvals and separately activated schedules remain available." : "Automation mode enabled. The backend will check for work within 30 seconds; outgoing emails wait in Approvals.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save automation"); }
    finally { setBusy(false); }
  }
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Automation mode · approve emails before sending</h2>{data && <strong className={`text-sm ${data.config.paused ? "text-amber-800" : "text-emerald-800"}`}>{data.config.paused ? "Paused" : "Enabled"}</strong>}</div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}{notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    <p className="text-sm text-slate-600">One-time setup, then automatic Gmail polling, optional daily research, reply suggestions and supported response drafts, eligible outreach/follow-up drafts and weekly reports. Review exact outgoing messages in Approvals. Keep the backend running.</p>
    {data && <p className="text-xs text-slate-500">Worker configuration: {data.worker_enabled ? "enabled" : "disabled"} · {data.budget.used}/{data.budget.limit} automatic business draft attempts today (SAST) · Last tick started: {data.runtime ? time(data.runtime.last_started_at) + " SAST" : "not recorded"}. Mode polls Gmail at most once every two minutes.</p>}
    {data && <p className="text-sm font-medium">Selected target: {data.target_label || "not set"}{data.config.target_month ? ` · ${data.config.target_month}` : " · legacy schedule"}</p>}
    {compact ? <div className="flex flex-wrap gap-4 text-sm text-indigo-700 underline"><button onClick={() => setTab("settings")}>Configure automation</button><button onClick={() => setTab("approvals")}>Open Approvals</button></div> : data && form && <>
      <div className="grid gap-4 text-sm sm:grid-cols-2">
        <label>Saved monthly target<select className={field} value="" onChange={(e) => { const t = data.targets.find((v) => v.target_month === e.target.value); if (t) setForm({ ...form, location: t.location, country: t.country, region: t.region, target_month: t.target_month, time_zone: t.time_zone, industry: t.industry }); }}><option value="">Choose a saved month…</option>{data.targets.map((t) => <option key={t.target_month} value={t.target_month}>{t.target_month} · {t.location}, {t.country}</option>)}</select></label>
        <label>Target month<input type="month" className={field} value={form.target_month} onChange={(e) => setForm({ ...form, target_month: e.target.value })} /></label>
        <label>Country<input className={field} value={form.country} maxLength={80} placeholder="For example: South Africa or United Kingdom" onChange={(e) => setForm({ ...form, country: e.target.value })} /></label>
        <label>Province / region<input className={field} value={form.region} maxLength={80} onChange={(e) => setForm({ ...form, region: e.target.value })} /></label>
        <label>Town time zone<input className={field} value={form.time_zone} maxLength={80} placeholder="Europe/London" onChange={(e) => setForm({ ...form, time_zone: e.target.value })} /></label>
        <label>Target town<input className={field} value={form.location} maxLength={200} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Your target town" /></label>
        <label>Business type<input className={field} value={form.industry} maxLength={200} onChange={(e) => setForm({ ...form, industry: e.target.value })} placeholder="For example: plumbers" /></label>
        <label>New outreach/research after (town time zone)<input type="time" className={field} value={form.local_time} onChange={(e) => setForm({ ...form, local_time: e.target.value })} /></label>
        <label>Daily business draft attempts<select className={field} value={form.daily_draft_limit} onChange={(e) => setForm({ ...form, daily_draft_limit: Number(e.target.value) })}>{Array.from({ length: 10 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label>
      </div>
      <p className="text-sm text-slate-600">Saved research target: {data.target_label || "not set"}. Search results remain candidates; the town label is a query constraint, not proof of location.</p>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={form.weekdays_only} onChange={(e) => setForm({ ...form, weekdays_only: e.target.checked })} />Prepare initial outreach, research and follow-ups on weekdays only. Sync and supported reply drafts continue every day.</label>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={form.research_enabled} onChange={(e) => setForm({ ...form, research_enabled: e.target.checked })} />Enable one bounded Tavily research job per day. Requires your existing key and research opt-in; shared daily/monthly limits still apply. Research may consume provider credits.</label>
      {form.research_enabled && <div className="flex flex-wrap gap-4 text-sm"><label>Results per job<select className={field} value={form.research_results} onChange={(e) => setForm({ ...form, research_results: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></label><label>Maximum requests per job<select className={field} value={form.research_requests} onChange={(e) => setForm({ ...form, research_requests: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select></label></div>}
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={form.qualification_enabled} onChange={(e) => setForm({ ...form, qualification_enabled: e.target.checked })} />Automatically qualify supported research sources using corroborating branch/contact details, explicit recent activity and a website search. Uses up to two extra research requests per candidate within the saved job budget. Start with one result and at least four total requests. Contact permission remains separate.</label>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={form.weekly_report_email} onChange={(e) => setForm({ ...form, weekly_report_email: e.target.checked })} />Prepare a weekly report email to my connected mailbox for approval, with an Excel attachment. The latest completed week's snapshot is saved either way.</label>
      <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">The saved town, region and country form one exact target label. Monthly research and initial outreach stop outside the selected month; no worldwide sweep runs. Reply processing for existing conversations continues. Enabling includes eligible saved leads matching the target labels and tracked business conversations in this mailbox's workflow. Legacy settings without a monthly target keep their existing label behavior. Choose a month, country and town to constrain new research. Town matching is exact; business type matches the saved industry text. Automatic qualification supports explicit structured listing fields on supported directory domains; general prose, bare dates and missing map tags are insufficient. Passed decisions include source evidence with proposals. Uncertain/unpermitted candidates are skipped; permission is never inferred.</p>
      <div className="flex flex-wrap gap-3"><button className={button} disabled={busy || !form.local_time} onClick={() => void save({ ...form, paused: false })}>Save and enable automation</button><button className={button} disabled={busy} onClick={() => void save({ ...form, paused: true })}>Save paused</button><button className={button} disabled={busy} onClick={() => void load(true).catch((e) => setError(String(e)))}>Refresh saved settings</button><button className="text-sm text-indigo-700 underline" onClick={() => setTab("approvals")}>Open Approvals</button></div>
      <p className="text-xs text-slate-500">{data.warning} The mode's draft cap is shared by its initial/reply/follow-up attempts. Independently activated campaign/follow-up schedules have their own caps; leave those paused when using this mode. Weekly report drafts do not consume business draft slots.</p>
      <details><summary className="cursor-pointer text-sm font-medium">Recent work and skipped candidates</summary><div className="mt-3 space-y-3">{data.runs.length === 0 && <p className="text-sm text-slate-500">No recorded automation runs yet.</p>}{data.runs.map((run) => <article key={run.id} className="space-y-2 rounded-lg border p-3 text-xs"><p className="font-medium">{time(run.created_at)} SAST · {run.status}</p>{run.results.map((r, i) => <p key={i} className="break-all">{r.stage}: {r.status}{r.reason ? ` · ${r.reason}` : ""}{r.approval_id ? ` · approval ${r.approval_id}` : ""}{r.job_id ? ` · research ${r.job_id}` : ""}</p>)}{!!run.lead_exceptions.length && <details><summary className="cursor-pointer">Skipped lead exceptions (up to 20 shown)</summary>{run.lead_exceptions.map((e) => <p key={e.lead_id} className="mt-2">{e.name}: {e.reason}</p>)}</details>}{["failed", "interrupted"].includes(run.status) && <p className="text-amber-800">Interrupted bookkeeping recovers automatically using existing approval keys and attempt reservations. Three consecutive unexpected failures pause this mode; review saved progress before re-enabling.</p>}</article>)}</div></details>
    </>}
  </section>;
}
