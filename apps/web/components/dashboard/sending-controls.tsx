"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Config = { version: number; paused: boolean; daily_limit: number };
type Status = { config: Config; mailbox: string; day: string; used: number; remaining: number; reserved_attempts: number; legacy_submissions: number; resets_at: string };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";

export function SendingControls() {
  const [data, setData] = useState<Status | null>(null);
  const [limit, setLimit] = useState("5");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  function display(result: Status) { setData(result); setLimit(String(result.config.daily_limit)); }
  async function action(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not update sending controls"); }
    finally { setBusy(false); }
  }
  async function refresh() { display(await apiRequest("/api/sending-controls")); }
  async function save(config: Config) {
    display(await apiRequest("/api/sending-controls", { method: "PUT", body: JSON.stringify(config) }));
    setNotice("Sending controls saved. Resuming or raising a limit does not send queued drafts; approve them explicitly.");
  }
  useEffect(() => { void action(refresh); }, []);
  return <section className="max-w-5xl space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Sending controls</h2><button className={button} disabled={busy} onClick={() => void action(refresh)}>Reload controls &amp; usage</button></div>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    {data && <>
      <p className={`rounded-lg p-3 text-sm font-medium ${data.config.paused ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-800"}`}>{data.config.paused ? "Business sending is paused" : "Business sending is enabled, subject to approval and eligibility"}</p>
      <button disabled={busy} className={`${button} ${data.config.paused ? "bg-white" : "border-red-300 text-red-700"}`} onClick={() => void action(() => save({ ...data.config, paused: !data.config.paused }))}>{data.config.paused ? "Resume business sending" : "Pause business sending"}</button>
      <p className="text-sm">Today ({data.day}, SAST): <strong>{data.used} / {data.config.daily_limit}</strong> business-send attempts used · <strong>{data.remaining}</strong> remaining<br /><span className="text-xs text-slate-500">Mailbox: {data.mailbox || "Connect Gmail to use business sending"}<br />Allowance resets: {new Date(data.resets_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" })} SAST</span></p>
      <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); void action(() => save({ ...data.config, daily_limit: Number(limit) })); }}>
        <label className="text-sm">Daily attempt limit (1–25)<input className="mt-1 block w-40 rounded-lg border border-slate-300 px-3 py-2 text-sm" required type="number" min={1} max={25} step={1} value={limit} onChange={(e) => setLimit(e.target.value)} /></label>
        <button disabled={busy} className={button}>Save daily limit</button>
      </form>
      <p className="text-xs text-slate-500">Outreach, business replies and follow-ups share this allowance for each mailbox. Attempts are reserved before submission; uncertain/failed attempts keep their slot. {data.legacy_submissions > 0 ? `${data.legacy_submissions} earlier confirmed or uncertain submissions are included.` : ""} This is your local pilot limit, not Gmail's sending quota.</p>
    </>}
    <p className="text-xs text-slate-500">Pause blocks new business submission reservations. An attempt already admitted may finish. Drafting, research, inbox sync, owned-address connection tests and reports remain available. These controls do not enable automatic sending or provider spending.</p>
  </section>;
}
