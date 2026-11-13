"use client";

import { useContext, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Evidence = { generated_at: string; mailbox: string; warning: string; checks: { name: string; status: string; detail: string }[]; research: { configured: boolean; enabled: boolean; daily_used: number; daily_limit: number; monthly_used: number; monthly_limit: number } };

export function PilotReadiness() {
  const [data, setData] = useState<Evidence | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { setTab } = useContext(TabContext);
  async function refresh() {
    setBusy(true); setError("");
    try { setData(await apiRequest("/api/pilot/readiness")); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not read pilot evidence"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void refresh(); }, []);
  return <section className="max-w-5xl space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Pilot readiness · local evidence</h2><button className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50" disabled={busy} onClick={() => void refresh()}>Refresh local evidence</button></div>
    <p className="text-sm text-slate-600">Review the recorded test cycle, current lead eligibility, budgets and held submissions before a small live pilot. This check makes no Gmail, research or model request and changes no records.</p>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {data && <><p className="text-xs text-slate-500">Mailbox: {data.mailbox || "Not configured"} · Checked {new Date(data.generated_at).toLocaleString("en-ZA", { timeZone: "Africa/Johannesburg" })} SAST</p>
      <div className="grid gap-3 md:grid-cols-2">{data.checks.map((check) => <article key={check.name} className={`rounded-lg border p-3 ${check.status === "action" ? "border-amber-200 bg-amber-50" : "border-slate-200"}`}><h3 className="text-sm font-medium">{check.name} · {check.status === "pass" ? "Evidence available" : check.status === "action" ? "Review / action needed" : "Information"}</h3><p className="mt-1 text-xs text-slate-600">{check.detail}</p></article>)}</div>
      <p className="text-xs text-slate-500">Optional research: {data.research.configured && data.research.enabled ? "enabled/configured locally" : "not enabled/configured"} · {data.research.daily_used}/{data.research.daily_limit} attempts today · {data.research.monthly_used}/{data.research.monthly_limit} this month. Campaign drafts do not use this allowance. These are local counters, not provider billing verification.</p>
      <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{data.warning}</p>
    </>}
    <div className="flex flex-wrap gap-4 text-sm text-indigo-700 underline"><button onClick={() => document.getElementById("gmail-connection")?.scrollIntoView({ behavior: "smooth" })}>Verify or sync Gmail below</button><button onClick={() => setTab("leads")}>Open Leads and campaign previews</button><button onClick={() => setTab("approvals")}>Review Approvals</button></div>
  </section>;
}
