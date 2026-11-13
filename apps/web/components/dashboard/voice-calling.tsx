"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";
type Budget = { limit_pence: number; fixed_pence: number; reserved_pence: number; remaining_pence: number; warning: string };
type Call = { id: string; name: string; number: string; status: string; opening: string; permission_evidence: string; max_seconds: number; conversation_id?: string; summary?: string; transcript?: { role: string; text: string }[] };
type State = { setup: { enabled: boolean; blockers: string[]; warning: string }; calls: Call[]; leads: { id: string; name: string; location: string; phone: string }[]; budget: Budget };
const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";
const field = "mt-1 block w-full rounded-lg border border-slate-300 p-2";
const money = (p: number) => `£${(p / 100).toFixed(2)}`;
export function VoiceCallingPanel() {
  const [data, setData] = useState<State | null>(null);
  const [voice, setVoice] = useState<{ provider: string; stt_provider: string; llm_provider: string; elevenlabs_ready: boolean; openai_ready: boolean } | null>(null);
  const [lead, setLead] = useState(""); const [evidence, setEvidence] = useState("");
  const [number, setNumber] = useState(""); const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  async function load() { const [calls, v] = await Promise.all([apiRequest("/api/calls"), apiRequest("/api/voice")]); setData(calls); setVoice(v); }
  useEffect(() => { void load().catch((e) => setError(String(e))); }, []);
  async function act(path: string, body?: object) {
    setBusy(true); setError(""); setNotice("");
    try { await apiRequest(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }); await load(); setNotice("Saved. Check the recorded status below."); }
    catch (e) { setError(e instanceof Error ? e.message : "Call action unavailable"); await load().catch(() => {}); }
    finally { setBusy(false); }
  }
  return <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
    <h2 className="font-semibold">Voice and phone calls · ElevenLabs + OpenAI</h2>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}{notice && <p role="status" className="text-sm text-emerald-800">{notice}</p>}
    {voice && <p className="text-sm text-slate-600">Voice output: {voice.provider} · Server recognition: {voice.stt_provider} · Agent model provider: {voice.llm_provider}. ElevenLabs key/voice: {voice.elevenlabs_ready ? "configured" : "missing"}; OpenAI key: {voice.openai_ready ? "configured" : "missing"}. <Link href="/" className="underline">Open voice chat</Link>.</p>}
    <p className="text-sm text-slate-600">Set provider keys in your local backend .env, then restart. Keys are never entered here. Clicking the blob on the chat screen starts voice; it does not place a phone call. Configure the ElevenLabs agent's Custom LLM endpoint and SIP service before enabling calls. See ELEVENLABS_SETUP.md in the repository.</p>
    {data && <>
      <p className="rounded-lg bg-slate-50 p-3 text-sm">Local monthly allowance: {money(data.budget.limit_pence)} · Fixed-cost reserve: {money(data.budget.fixed_pence)} · Request reservations: {money(data.budget.reserved_pence)} · Available: {money(data.budget.remaining_pence)}.</p>
      <p className="text-xs text-amber-900">{data.budget.warning}</p>
      <div className="text-sm"><strong>{data.setup.enabled ? "Phone integration configured · live verification still required" : "Phone calls blocked"}</strong>{data.setup.blockers.map((b) => <p key={b}>{b}</p>)}<p className="mt-2 text-slate-600">{data.setup.warning}</p></div>
      <div className="grid gap-3 text-sm sm:grid-cols-2"><label>Business in selected town<select className={field} value={lead} onChange={(e) => setLead(e.target.value)}><option value="">Select a saved business…</option>{data.leads.map((l) => <option key={l.id} value={l.id}>{l.name} · {l.location} · {l.phone}</option>)}</select></label><label>Evidence of permission for an AI phone call<textarea className={field} maxLength={2000} value={evidence} onChange={(e) => setEvidence(e.target.value)} placeholder="Who agreed, when, and where that permission is recorded. A public phone number or email permission alone is insufficient." /></label></div>
      <button className={button} disabled={busy || !lead || evidence.trim().length < 10} onClick={() => void act("/api/calls", { lead_id: lead, permission_evidence: evidence })}>Prepare call for review</button>
      <p className="text-xs text-slate-500">One call proposal per business/number/month. Dispatch rechecks reviewed evidence, the selected town/month, phone suppression, weekday calling hours and local allowance. No automatic dialing or redial. Incoming caller speech cannot approve emails or run owner commands.</p>
      {data.calls.map((c) => <article key={c.id} className="space-y-2 rounded-lg border p-3 text-sm"><p className="font-medium">{c.name} · {c.number} · {c.status}</p><p>Opening: {c.opening}</p><p>Recorded permission: {c.permission_evidence}</p><p>Maximum duration: {c.max_seconds} seconds</p><div className="flex flex-wrap gap-2">{c.status === "awaiting_approval" && <><button className={button} disabled={busy || !data.setup.enabled} onClick={() => void act(`/api/calls/${c.id}/approve-and-call`)}>Approve and call this number</button><button className={button} disabled={busy} onClick={() => void act(`/api/calls/${c.id}/reject`)}>Reject</button></>}{c.conversation_id && <button className={button} disabled={busy} onClick={() => void act(`/api/calls/${c.id}/sync`)}>Sync call result</button>}</div>{["sending", "delivery_unknown"].includes(c.status) && <p className="text-amber-900">Submission may have reached the provider. Inspect the ElevenLabs call log; this app will not redial.</p>}{c.summary && <p>Provider summary (unverified): {c.summary}</p>}{!!c.transcript?.length && <details><summary>Recorded conversation</summary>{c.transcript.map((t, i) => <p key={i}>{t.role}: {t.text}</p>)}</details>}</article>)}
      <details><summary className="cursor-pointer text-sm">Add a number to do-not-call</summary><div className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><label>International phone number<input className={field} value={number} maxLength={30} onChange={(e) => setNumber(e.target.value)} placeholder="+27…" /></label><label>Reason<input className={field} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} /></label></div><button className={button} disabled={busy || !number || !reason.trim()} onClick={() => void act("/api/calls/suppress", { number, reason })}>Block future calls</button></details>
    </>}
  </section>;
}
