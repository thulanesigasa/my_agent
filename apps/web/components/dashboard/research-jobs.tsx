"use client";

import { useState } from "react";

export type ResearchResult = { lead_id: string; name: string; bucket: string; reason: string; flags: string[]; email_candidates: number; assessed_at: string; ready_to_draft: boolean };
export type ResearchJob = { id: string; location: string; industry: string; limit: number; max_requests: number; requests_used: number; status: string; stage: string; cursor: number; lead_ids: string[]; message: string; pause_requested: boolean; next_run_at: number; results: ResearchResult[] };
type Start = { location: string; industry: string; limit: number; max_requests: number };
const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";
const button = "rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50";
const labels: Record<string, string> = { excluded: "Excluded by operator evidence", website_found: "Website recorded", website_signal: "Possible existing website · review", potential_client: "Potential match · review", needs_review: "Uncertain · review" };

export function ResearchJobs({ jobs, available, workerEnabled, busy, clock, onStart, onControl, onSelect }: {
  jobs: ResearchJob[]; available: boolean; workerEnabled: boolean; busy: boolean; clock: number;
  onStart: (payload: Start) => void; onControl: (id: string, action: "pause" | "resume", budget?: number) => void; onSelect: (id: string) => void;
}) {
  const [form, setForm] = useState({ location: "Standerton, Mpumalanga", industry: "", limit: "2", max_requests: "3" });
  const [budgets, setBudgets] = useState<Record<string, string>>({});
  const active = jobs.some((job) => ["queued", "running", "waiting"].includes(job.status));
  return <div className="space-y-5 rounded-xl border border-indigo-200 bg-white p-5">
    <div><h3 className="text-lg font-semibold">Automatic research jobs</h3><p className="mt-1 text-sm text-slate-600">Start once: discover sources, inspect them within your budget, and group the findings for review. No email is drafted or sent by this job.</p></div>
    {!available && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Configure your local Tavily key and enable research before starting a job.</p>}
    {!workerEnabled && <p className="text-sm text-amber-900">The research worker is disabled. Set RESEARCH_JOBS_ENABLED=true and restart the backend.</p>}
    <form className="space-y-3" onSubmit={(event) => { event.preventDefault(); onStart({ location: form.location, industry: form.industry, limit: Number(form.limit), max_requests: Number(form.max_requests) }); }}>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm font-medium">Town / area<input className={field} required maxLength={200} value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} /></label>
        <label className="text-sm font-medium">Business type<input className={field} required maxLength={200} placeholder="e.g. plumbers" value={form.industry} onChange={(event) => setForm({ ...form, industry: event.target.value })} /></label>
        <label className="text-sm font-medium">Maximum source results<input className={field} type="number" min={1} max={10} required value={form.limit} onChange={(event) => setForm({ ...form, limit: event.target.value })} /></label>
        <label className="text-sm font-medium">Total job request budget<input className={field} type="number" min={1} max={10} required value={form.max_requests} onChange={(event) => setForm({ ...form, max_requests: event.target.value })} /></label>
      </div>
      <button className={button} disabled={busy || active || !available || !workerEnabled}>Start research</button>
      <p className="text-xs text-slate-500">New searches and inspections count toward this job budget and your shared daily/monthly limits. Cached steps are free. A budget of 3 normally allows one search and two inspections. Cooldowns are handled automatically; provider errors and exhausted budgets pause the job.</p>
      <p className="text-xs text-slate-500">Jobs continue with the backend running even if you close this dashboard. Keep the backend running; an interrupted in-flight request pauses for operator review on restart. Active progress refreshes every 5 seconds.</p>
    </form>
    <div className="space-y-3">
      {jobs.length === 0 && <p className="text-sm text-slate-500">No research jobs yet. Start a small pilot above.</p>}
      {jobs.map((job, index) => <details key={job.id} open={index === 0 || ["queued", "running", "waiting"].includes(job.status)} className="rounded-lg border border-slate-200 p-4">
        <summary className="cursor-pointer text-sm font-medium">{job.industry} · {job.location} · {job.pause_requested ? "pausing" : job.status} · {job.cursor}/{job.lead_ids.length} assessed · {job.requests_used}/{job.max_requests} requests</summary>
        <div className="mt-3 space-y-3">
          <p role="status" className="text-sm text-slate-700">{job.message}</p>
          {job.status === "waiting" && <p className="text-sm text-amber-800">Next step in {Math.max(0, Math.ceil((job.next_run_at * 1000 - clock) / 1000))} seconds. No click is needed.</p>}
          {["queued", "running", "waiting"].includes(job.status) && <button type="button" className={button} disabled={busy || job.pause_requested} onClick={() => onControl(job.id, "pause")}>Pause job</button>}
          {job.status === "paused" && <div className="flex flex-wrap items-end gap-3"><label className="text-sm font-medium">Total budget when resumed<input className={field} type="number" min={Math.max(1, job.requests_used)} max={10} value={budgets[job.id] ?? String(job.max_requests)} onChange={(event) => setBudgets({ ...budgets, [job.id]: event.target.value })} /></label><button type="button" className={button} disabled={busy || active || !available || !workerEnabled || !Number.isInteger(Number(budgets[job.id] ?? job.max_requests)) || Number(budgets[job.id] ?? job.max_requests) < Math.max(1, job.requests_used) || Number(budgets[job.id] ?? job.max_requests) > 10} onClick={() => onControl(job.id, "resume", Number(budgets[job.id] ?? job.max_requests))}>Resume saved job</button></div>}
          {job.results.length > 0 && <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="py-2 pr-3">Candidate</th><th className="py-2 pr-3">Assessment snapshot</th><th className="py-2">Evidence / exceptions</th></tr></thead><tbody>{[...job.results].sort((a, b) => (a.bucket === "potential_client" ? -1 : 0) - (b.bucket === "potential_client" ? -1 : 0)).map((result) => <tr key={result.lead_id} className="border-b align-top"><td className="py-3 pr-3"><button type="button" onClick={() => onSelect(result.lead_id)} className="text-indigo-700 underline">{result.name}</button></td><td className="py-3 pr-3"><strong className="font-medium">{labels[result.bucket] || result.bucket}</strong><p className="mt-1 text-xs text-slate-500">{result.reason}</p></td><td className="py-3"><p>{result.email_candidates} email candidates</p><ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">{result.flags.map((flag) => <li key={flag}>{flag}</li>)}</ul></td></tr>)}</tbody></table></div>}
          <p className="text-xs text-slate-500">Assessments summarize the saved research step and can become outdated. Open the candidate to review current evidence. Potential matches are unverified; no website found is not proof of absence. Contact permission and final email approval remain separate.</p>
        </div>
      </details>)}
    </div>
  </div>;
}
