"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest, apiResponse } from "@/lib/api";

type Conversation = { id: string; recipient: string; subject: string; state: string; reply_count: number; outcome: string; outcome_note: string; purpose: string };
type Summary = { emails_sent: number; conversations_sent: number; conversations_replied: number; awaiting_reply: number; bounced_conversations: number; reply_rate_percent: number | null; human_replies_received: number; automated_messages_received: number; outcomes: Record<string, number>; reply_suggestions?: Record<string, number> };
type Report = { id?: string; start: string; end: string; as_of: string; timezone: string; include_tests: boolean; last_sync_at: string | null; summary: Summary; conversations: Conversation[]; daily: { date: string; sent: number; human_replies: number }[]; definitions: Record<string, string> };
type Saved = Pick<Report, "id" | "start" | "end" | "as_of" | "include_tests">;
const field = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
const button = "rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const secondary = "rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50 disabled:opacity-50";
function dates(previous: boolean) {
  const today = new Date(Date.now() + 2 * 3600 * 1000);
  const monday = new Date(today);
  monday.setUTCDate(today.getUTCDate() - ((today.getUTCDay() + 6) % 7));
  const end = previous ? new Date(monday.getTime() - 86400000) : today;
  if (previous) monday.setUTCDate(monday.getUTCDate() - 7);
  return [monday.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}
const displayTime = (s: string) => new Date(s).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" });

function OutcomeEditor({ row, onSave, disabled }: { row: Conversation; onSave: (row: Conversation, outcome: string, note: string) => Promise<void>; disabled: boolean }) {
  const [outcome, setOutcome] = useState(row.outcome);
  const [note, setNote] = useState(row.outcome_note);
  useEffect(() => { setOutcome(row.outcome); setNote(row.outcome_note); }, [row]);
  return <form onSubmit={(e) => { e.preventDefault(); void onSave(row, outcome, note); }} className="space-y-2">
    <label className="block text-xs text-slate-600">Outcome for {row.recipient}<select aria-label={`Outcome for ${row.recipient}`} className={field} value={outcome} onChange={(e) => setOutcome(e.target.value)}>
      {Object.entries({ unclassified: "Unclassified", interested: "Interested", declined: "Declined", won: "Won", unsubscribed: "Unsubscribed" }).map(([v, label]) => <option value={v} key={v}>{label}</option>)}
    </select></label>
    <label className="block text-xs text-slate-600">Evidence or reason<input className={field} value={note} onChange={(e) => setNote(e.target.value)} required maxLength={2000} /></label>
    <button className={secondary} disabled={disabled || !note.trim()}>Save outcome</button>
  </form>;
}

export function ReportsDashboard() {
  const initial = dates(true);
  const [start, setStart] = useState(initial[0]);
  const [end, setEnd] = useState(initial[1]);
  const [tests, setTests] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function refresh(a = start, b = end, t = tests) {
    const [data, history] = await Promise.all([apiRequest(`/api/reports/summary?start=${a}&end=${b}&include_tests=${t}`), apiRequest("/api/reports/snapshots")]);
    setReport(data); setSaved(history.reports);
  }
  async function act(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); } catch (e) { setError(e instanceof Error ? e.message : "Report operation failed"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(() => refresh()); }, []);
  async function download(id: string) {
    const response = await apiResponse(`/api/reports/snapshots/${encodeURIComponent(id)}/export`);
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement("a"); a.href = url; a.download = `outreach-report-${id}.xlsx`; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function apply(e: FormEvent) { e.preventDefault(); void act(() => refresh()); }
  async function save(exportFile: boolean) {
    const data: Report = await apiRequest("/api/reports/snapshots", { method: "POST", body: JSON.stringify({ start, end, include_tests: tests }) });
    setReport(data); setSaved((await apiRequest("/api/reports/snapshots")).reports);
    if (exportFile) await download(data.id!);
    setNotice("Snapshot saved. Future replies will appear in a refreshed report; this saved copy stays unchanged.");
  }
  async function saveOutcome(row: Conversation, outcome: string, note: string) {
    await act(async () => {
      await apiRequest(`/api/reports/conversations/${encodeURIComponent(row.id)}/outcome`, { method: "PUT", body: JSON.stringify({ outcome, note }) });
      await refresh(report!.start, report!.end, report!.include_tests);
      setNotice("Outcome recorded. Saved report snapshots retain their original figures.");
    });
  }
  const s = report?.summary;
  return <section className="space-y-6">
    <div><h2 className="text-xl font-semibold">Outreach reports</h2><p className="mt-1 text-sm text-slate-500">Recorded activity in South African time. Connection tests are excluded by default.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    <form onSubmit={apply} className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-slate-50 p-5">
      <label className="text-sm font-medium">From<input className={field} type="date" value={start} onChange={(e) => setStart(e.target.value)} required /></label>
      <label className="text-sm font-medium">Through<input className={field} type="date" value={end} onChange={(e) => setEnd(e.target.value)} required /></label>
      <label className="flex items-center gap-2 py-2 text-sm"><input type="checkbox" checked={tests} onChange={(e) => setTests(e.target.checked)} />Include connection tests</label>
      <button className={button} disabled={busy}>Refresh report</button>
      <button type="button" className={secondary} disabled={busy} onClick={() => { const [a, b] = dates(false); setStart(a); setEnd(b); void act(() => refresh(a, b)); }}>This week</button>
      <button type="button" className={secondary} disabled={busy} onClick={() => { const [a, b] = dates(true); setStart(a); setEnd(b); void act(() => refresh(a, b)); }}>Previous week</button>
    </form>
    {busy && <p role="status" className="text-sm text-slate-500">Working…</p>}
    {report && s && <>
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm"><p>{report.start} – {report.end} · {report.include_tests ? "Includes tests" : "Outreach only"}<br /><span className="text-xs text-slate-500">As of {displayTime(report.as_of)} SAST · {report.id ? "Saved snapshot" : "Current ledger"}. Last sync: {report.last_sync_at ? `${displayTime(report.last_sync_at)} SAST` : "No successful sync recorded"}</span></p>
        <div className="flex flex-wrap gap-2"><button disabled={busy} className={secondary} onClick={() => act(() => save(false))}>Save selected dates</button><button disabled={busy} className={button} onClick={() => act(() => save(true))}>Export selected dates to Excel</button></div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
        ["Confirmed emails sent", s.emails_sent], ["Conversations replied", `${s.conversations_replied} / ${s.conversations_sent}`],
        ["Conversation reply rate", s.reply_rate_percent === null ? "—" : `${s.reply_rate_percent}%`], ["Awaiting reply", s.awaiting_reply],
      ].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}</div>
      <p className="text-sm text-slate-600">During these dates: {s.human_replies_received} human reply messages, {s.automated_messages_received} automated messages. {s.bounced_conversations} cohort conversations have a recorded bounce. Reply rate follows conversations first sent in this period, including later replies up to the snapshot time.</p>
      <div className="flex flex-wrap gap-3">{Object.entries(s.outcomes).map(([label, count]) => <span className="rounded-full bg-slate-100 px-3 py-2 text-sm capitalize" key={label}>{label}: <strong>{count}</strong></span>)}</div>
      {s.reply_suggestions && <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4"><h3 className="text-sm font-medium">Automatic reply suggestions · unconfirmed</h3><p className="mt-1 text-xs text-slate-600">Latest human reply per conversation, classified by local rules. These do not change confirmed outcomes or mark sales as won.</p><div className="mt-2 flex flex-wrap gap-3 text-sm">{Object.entries(s.reply_suggestions).map(([label, count]) => <span key={label}>{label.replaceAll("_", " ")}: <strong>{count}</strong></span>)}</div></div>}
      <details className="rounded-xl border border-slate-200 p-5"><summary className="cursor-pointer font-medium">Daily activity</summary><div className="mt-4 max-h-64 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Date (SAST)</th><th>Confirmed sends</th><th>Human reply messages</th></tr></thead><tbody>{report.daily.map((d) => <tr key={d.date} className="border-t border-slate-100"><td className="p-2">{d.date}</td><td>{d.sent}</td><td>{d.human_replies}</td></tr>)}</tbody></table></div></details>
      <div className="rounded-xl border border-slate-200 p-5"><h3 className="font-semibold">Conversation outcomes</h3><p className="mt-1 text-sm text-slate-500">Classify a synced human response and record why. Unsubscribing also blocks further contact.</p>
        {report.conversations.length === 0 && <p className="mt-4 text-sm text-slate-500">No confirmed conversations first sent in these dates. For your connection test, choose This week and include connection tests.</p>}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">{report.conversations.map((row) => <article key={row.id} className="space-y-3 rounded-lg border border-slate-200 p-4"><div><p className="break-all font-medium">{row.recipient}</p><p className="text-sm">{row.subject}</p><p className="mt-1 text-xs text-slate-500">{row.state.replaceAll("_", " ")} · {row.reply_count} human replies · {row.purpose}</p></div>{report.id ? <p className="text-sm capitalize">{row.outcome} · {row.outcome_note || "No outcome note"}</p> : <OutcomeEditor row={row} onSave={saveOutcome} disabled={busy} />}</article>)}</div>
      </div>
      <details className="rounded-xl border border-slate-200 p-5"><summary className="cursor-pointer font-medium">How these figures are counted</summary><dl className="mt-4 space-y-3 text-sm text-slate-600">{Object.entries(report.definitions).map(([key, text]) => <div key={key}><dt className="font-medium capitalize">{key.replaceAll("_", " ")}</dt><dd>{text}</dd></div>)}</dl></details>
    </>}
    <div className="rounded-xl border border-slate-200 p-5"><h3 className="font-semibold">Saved reports</h3><p className="mt-1 text-sm text-slate-500">Email drafts include an Excel attachment and are addressed to your connected Gmail account. Send them from Approvals.</p>
      {saved.length === 0 && <p className="mt-4 text-sm text-slate-500">No snapshots saved yet.</p>}
      <div className="mt-4 space-y-3">{saved.map((r) => <div key={r.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3"><p className="text-sm">{r.start} – {r.end} {r.include_tests ? "· includes tests" : ""}<br /><span className="text-xs text-slate-500">Saved {displayTime(r.as_of)} SAST</span></p><div className="flex flex-wrap gap-2"><button disabled={busy} className={secondary} onClick={() => act(async () => { setReport(await apiRequest(`/api/reports/snapshots/${r.id}`)); })}>View snapshot</button><button disabled={busy} className={secondary} onClick={() => act(() => download(r.id!))}>Download Excel</button><button disabled={busy} className={button} onClick={() => act(async () => { const draft = await apiRequest(`/api/reports/snapshots/${r.id}/draft`, { method: "POST" }); setNotice(`Report draft status: ${draft.status}. Review it in Approvals.`); })}>Create email draft</button></div></div>)}</div>
    </div>
  </section>;
}
