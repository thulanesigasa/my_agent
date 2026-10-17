"use client";

import { FormEvent, useContext, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import { TabContext } from "@/components/app-shell";

type Review = {
  revision: number; identity_verified: boolean; identity_source: string; identity_note: string;
  business_status: string; activity_method: string; activity_date: string; website_status: string; website_url: string; website_source: string; website_note: string;
  contact_verified: boolean; email: string; contact_source: string; contact_note: string; decision: string; decision_note: string;
};
type Observation = { name?: string; email?: string; website?: string; source_url?: string; observed_at?: string; source_updated_at?: string; source_check_date?: string };
type Lead = { id: string; name: string; location: string; address?: string; phone?: string; industry?: string; source_url: string; source: string; revision?: number; status?: string; review?: Review & { reviewed_at?: string }; observation?: Observation; observations?: Observation[]; review_invalidated?: boolean; ready_to_draft: boolean; dispatch_blocker: string; consent: string; possible_duplicates: string[]; source_freshness?: { status: string; age_days: number | null } };
const input = "mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
const button = "rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const panel = "rounded-xl border border-slate-200 bg-white p-5 space-y-4";
const empty = { name: "", location: "", address: "", phone: "", email: "", website: "", industry: "", source_url: "" };
function freshReview(lead: Lead): Review {
  const saved = lead.review;
  return { revision: lead.revision || 0, identity_verified: saved?.identity_verified || false,
    identity_source: saved?.identity_source || lead.source_url || "", identity_note: saved?.identity_note || "",
    business_status: saved?.business_status || "unknown", activity_method: saved?.activity_method || "", activity_date: saved?.activity_date || "", website_status: saved?.website_status || "not_checked",
    website_url: saved?.website_url || "", website_source: saved?.website_source || "", website_note: saved?.website_note || "",
    contact_verified: saved?.contact_verified || false, email: saved?.email || lead.observation?.email || "",
    contact_source: saved?.contact_source || lead.source_url || "", contact_note: saved?.contact_note || "",
    decision: saved?.decision || "needs_review", decision_note: saved?.decision_note || "" };
}
function Field({ title, children }: { title: string; children: React.ReactNode }) { return <label className="block text-sm font-medium text-slate-700">{title}{children}</label>; }

function LeadReview({ lead, busy, onReview, onDraft }: { lead: Lead; busy: boolean; onReview: (payload: Review) => void; onDraft: (subject: string, body: string) => void }) {
  const [review, setReview] = useState<Review>(freshReview(lead));
  const [subject, setSubject] = useState(`Website enquiry for ${lead.name}`);
  const [body, setBody] = useState("");
  const { setTab } = useContext(TabContext);
  useEffect(() => { setReview(freshReview(lead)); }, [lead.id, lead.revision]);
  useEffect(() => { setSubject(`Website enquiry for ${lead.name}`); setBody(""); }, [lead.id]);
  function text(key: keyof Review, title: string, type = "text") {
    return <Field title={title}><input type={type} className={input} value={String(review[key])} maxLength={2000} onChange={(e) => setReview({ ...review, [key]: e.target.value })} /></Field>;
  }
  function note(key: keyof Review, title: string) {
    return <Field title={title}><textarea className={input} rows={3} value={String(review[key])} maxLength={2000} onChange={(e) => setReview({ ...review, [key]: e.target.value })} /></Field>;
  }
  return <div className="space-y-5">
    <div className={panel}><div><h3 className="text-lg font-semibold">{lead.name}</h3><p className="text-sm text-slate-500">{lead.location} · {lead.industry || "Category not recorded"}</p></div>
      <p className="text-sm">{lead.address || "Address not recorded"}<br />{lead.phone || "Phone not recorded"}</p>
      {/^https?:\/\//i.test(lead.source_url || "") && <a className="block break-all text-sm text-indigo-700 underline" href={lead.source_url} target="_blank" rel="noreferrer">Open discovery source</a>}
      <div className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium">Unverified source observations</p><p className="mt-1 break-all">Email: {lead.observation?.email || "Not listed"}<br />Website: {lead.observation?.website || "Not listed"}</p><p className="mt-2 text-xs text-slate-500">A missing listing is not proof that no website exists. A listed email is not verified permission to contact.</p></div>
      {lead.source === "openstreetmap" && <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900"><p className="font-medium">Map listing · current activity unverified</p>{lead.source_freshness?.status === "old" && <p className="mt-1 font-medium">This map entry has not been edited for over a year.</p>}<p className="mt-1 break-all">Last map edit: {lead.observation?.source_updated_at || "Unknown (older results may lack metadata)"}<br />Mapper check/survey date: {lead.observation?.source_check_date || "Not recorded"}<br />Retrieved by this app: {lead.observation?.observed_at || "Unknown"}</p><p className="mt-2 text-xs">A recent retrieval or map edit does not confirm this business is open. Listings can remain after closure. Verify recent business activity separately; use manual entry or CSV for businesses missing from the map.</p></div>}
      {lead.review_invalidated && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Source details changed. Review the current evidence before qualifying this lead again.</p>}
      {lead.possible_duplicates.length > 0 && <p className="text-sm text-amber-800">{lead.possible_duplicates.length} other entries share this name and location. Check the branch/address; reject duplicate entries rather than contacting twice.</p>}
      <details><summary className="cursor-pointer text-sm font-medium">Source history</summary><ul className="mt-3 space-y-3 text-xs text-slate-600">{lead.observations?.slice().reverse().map((o, i) => <li key={i} className="break-all">Retrieved: {o.observed_at} · {o.source_url}<br />Map edit: {o.source_updated_at || "Unknown"}<br />Email: {o.email || "Not listed"} · Website: {o.website || "Not listed"}</li>)}</ul></details>
    </div>
    <form onSubmit={(e) => { e.preventDefault(); onReview(review); }} className={panel}>
      <h3 className="font-semibold">Review the business</h3>
      <p className="text-sm text-slate-500">Use public sources and your own verification. The app stores your evidence; it does not infer that a business is active or lacks a website.</p>
      <fieldset className="space-y-3 border-t border-slate-100 pt-4"><legend className="text-sm font-semibold">1. Business identity and activity</legend>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={review.identity_verified} onChange={(e) => setReview({ ...review, identity_verified: e.target.checked })} />I verified this business and branch against the sources.</label>
        {text("identity_source", "Identity/activity source URL", "url")}{note("identity_note", "How the identity and current activity were confirmed")}
        <Field title="Business status"><select className={input} value={review.business_status} onChange={(e) => setReview({ ...review, business_status: e.target.value })}><option value="unknown">Unknown</option><option value="active">Active, supported by evidence above</option><option value="inactive">Inactive / closed</option></select></Field>
        <Field title="How current activity was verified"><select className={input} value={review.activity_method} onChange={(e) => setReview({ ...review, activity_method: e.target.value })}><option value="">Not verified</option><option value="recent_public_activity">Dated public business activity</option><option value="direct_confirmation">Direct confirmation from the business</option><option value="local_observation">Personally observed this branch operating</option></select></Field>
        {text("activity_date", "Activity evidence date (SAST)", "date")}
        <p className="text-xs text-slate-500">Qualification requires activity evidence from the last 30 days. Use the date of the business activity, confirmation or visit, rather than today’s lookup date. For public evidence, link the dated post/update above; an OpenStreetMap listing alone is insufficient. For direct/local checks, describe who confirmed or what you observed in the note above.</p>
        <a href={`https://www.google.com/search?q=${encodeURIComponent(`${lead.name} ${lead.location} open closed recent activity`)}`} target="_blank" rel="noreferrer" className="inline-block text-sm text-indigo-700 underline">Open a manual activity search</a>
        <p className="text-xs text-slate-500">Know this branch has closed? Choose Inactive / closed, select Rejected below, and record your reason. No email or website research is needed to reject it.</p>
      </fieldset>
      <fieldset className="space-y-3 border-t border-slate-100 pt-4"><legend className="text-sm font-semibold">2. Website research</legend>
        <p className="text-xs text-slate-500">Search the exact business name with its town/address, inspect the business listing and public social profiles, and note what you checked. Do not label a timed-out site as absent.</p>
        <a href={`https://www.google.com/search?q=${encodeURIComponent(`${lead.name} ${lead.location} official website`)}`} target="_blank" rel="noreferrer" className="inline-block text-sm text-indigo-700 underline">Open a manual website search</a>
        <Field title="Website finding"><select className={input} value={review.website_status} onChange={(e) => setReview({ ...review, website_status: e.target.value })}>
          <option value="not_checked">Not checked</option><option value="found">Independent website found</option><option value="not_found_after_review">No independent website found after review</option><option value="owner_confirmed_none">Owner confirmed no website</option><option value="social_only">Only social profiles found after review</option><option value="uncertain">Uncertain / conflicting evidence</option>
        </select></Field>
        {text("website_url", "Independent website URL, if found", "url")}{text("website_source", "Website research source URL", "url")}{note("website_note", "Searches/sources checked, findings, and any conflicting evidence")}
      </fieldset>
      <fieldset className="space-y-3 border-t border-slate-100 pt-4"><legend className="text-sm font-semibold">3. Contact evidence</legend>
        {text("email", "One public business email", "email")}{text("contact_source", "Page where this exact email was published", "url")}{note("contact_note", "How this email was matched to this business")}
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1" checked={review.contact_verified} onChange={(e) => setReview({ ...review, contact_verified: e.target.checked })} />I verified this exact email against the source.</label>
        <p className="text-xs text-slate-500">This saves contact verification and preserves existing consent/suppression. It does not grant marketing permission.</p>
      </fieldset>
      <Field title="Review decision"><select className={input} value={review.decision} onChange={(e) => setReview({ ...review, decision: e.target.value })}><option value="needs_review">Needs more review</option><option value="qualified">Qualified as a potential website client</option><option value="rejected">Rejected / duplicate / unsuitable</option></select></Field>
      {note("decision_note", "Decision note (required for rejection)")}
      <button className={button} disabled={busy}>Save review</button>
      <p className="text-xs text-slate-500">Review validity: 30 days. Unknown identity/activity, uncertain website status or missing contact evidence blocks qualification.</p>
    </form>
    <form onSubmit={(e) => { e.preventDefault(); onDraft(subject, body); }} className={panel}>
      <h3 className="font-semibold">Prepare outreach for approval</h3>
      <p className="text-sm">Review: <strong>{lead.status || "needs_review"}</strong> · Permission: <strong>{lead.consent}</strong></p>
      {!lead.ready_to_draft && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{lead.dispatch_blocker}</p>}
      <button type="button" className="text-sm text-indigo-700 underline" onClick={() => setTab("settings")}>Open Settings to record actual contact permission</button>
      <Field title="Subject"><input className={input} required maxLength={300} value={subject} onChange={(e) => setSubject(e.target.value)} /></Field>
      <Field title="Message"><textarea className={input} required rows={7} maxLength={20000} value={body} onChange={(e) => setBody(e.target.value)} /></Field>
      <p className="text-xs text-slate-500">Describe your service accurately. Use “I couldn’t find your website” when that is your evidence, rather than claiming the business has none. Portfolio matching/templates come in Phase 5.</p>
      <button disabled={busy || !lead.ready_to_draft} className={button}>Save for approval</button>
      <p className="text-xs text-slate-500">Creates one initial outreach draft per connected mailbox/contact. Review it in Approvals to send. Repeating this action does not resend or replace an existing draft.</p>
    </form>
  </div>;
}

export function LeadsDashboard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState("");
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dailyLimit, setDailyLimit] = useState(20);
  const [providerName, setProviderName] = useState("Private.coffee");
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const remaining = Math.max(0, Math.ceil((cooldownUntil - clock) / 1000));
  useEffect(() => { const timer = setInterval(() => setClock(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const [manual, setManual] = useState(empty);
  const [csv, setCsv] = useState("name,location,source_url,address,phone,email,website,industry\n");
  const [area, setArea] = useState({ location: "Standerton, Mpumalanga", latitude: "", longitude: "", radius_km: "1", category: "all", limit: "25" });
  async function refresh() { const result = await apiRequest("/api/leads"); setLeads(result.leads); setDailyLimit(result.daily_limit); setProviderName(result.provider?.name || "OpenStreetMap provider"); setCooldownUntil(Date.now() + (result.retry_after_seconds || 0) * 1000); setClock(Date.now()); }
  async function act(call: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); } catch (e) { setError(e instanceof Error ? e.message : "Lead operation failed"); if (e instanceof ApiError && e.retryAfterSeconds > 0) { setCooldownUntil(Date.now() + e.retryAfterSeconds * 1000); setClock(Date.now()); } }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(refresh); }, []);
  async function discover(e: FormEvent) {
    e.preventDefault();
    await act(async () => { const result = await apiRequest("/api/leads/discover", { method: "POST", body: JSON.stringify({ ...area, latitude: Number(area.latitude), longitude: Number(area.longitude), radius_km: Number(area.radius_km), limit: Number(area.limit) }) }); await refresh(); if (result.leads[0]) setSelected(result.leads[0].id); setNotice(`${result.leads.length} unverified candidates loaded${result.cached ? " from the 24-hour cache" : " from OpenStreetMap"}.${result.truncated ? " Results were capped; narrow the radius." : ""} No email was sent.`); });
  }
  async function add(e: FormEvent) {
    e.preventDefault(); await act(async () => { const lead = await apiRequest("/api/leads", { method: "POST", body: JSON.stringify(manual) }); await refresh(); setSelected(lead.id); setManual(empty); setNotice("Candidate saved for evidence review. No email was sent."); });
  }
  async function importCSV(e: FormEvent) {
    e.preventDefault(); await act(async () => { const result = await apiRequest("/api/leads/import", { method: "POST", body: JSON.stringify({ csv_text: csv }) }); await refresh(); if (result.lead_ids[0]) setSelected(result.lead_ids[0]); setNotice(`${result.rows} CSV rows processed; ${result.unique_leads} unique candidates. No permission was granted and no email was sent.`); });
  }
  const active = leads.find((l) => l.id === selected);
  const visible = leads.filter((l) => (filter === "all" || (l.status || "needs_review") === filter) && `${l.name} ${l.location} ${l.industry || ""}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="space-y-6">
    <div><h2 className="text-xl font-semibold">Business research</h2><p className="mt-1 text-sm text-slate-500">Find candidates, review evidence, and prepare eligible outreach. Discovery never sends emails.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    <div className="grid items-start gap-5 xl:grid-cols-2">
      <form onSubmit={discover} className={panel}><h3 className="font-semibold">Free nearby discovery</h3><p className="text-sm text-slate-500">Enter the centre coordinates of your target area. Searches use OpenStreetMap, not Google Maps or a paid API. Coordinates and radius are sent to {providerName}, the selected public Overpass provider.</p>
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Map coverage may be incomplete or years out of date. Results are research candidates, not a list of currently operating businesses. Changing Overpass providers does not change the underlying map source.</p>
        <a href="https://www.openstreetmap.org" target="_blank" rel="noreferrer" className="block text-sm text-indigo-700 underline">Find your area on OpenStreetMap (map URL contains latitude/longitude)</a>
        <Field title="Location label"><input className={input} required maxLength={200} value={area.location} onChange={(e) => setArea({ ...area, location: e.target.value })} /></Field>
        <div className="grid gap-3 sm:grid-cols-2"><Field title="Latitude"><input className={input} type="number" step="any" min={-85} max={85} required placeholder="Latitude" value={area.latitude} onChange={(e) => setArea({ ...area, latitude: e.target.value })} /></Field><Field title="Longitude"><input className={input} type="number" step="any" min={-180} max={180} required placeholder="Longitude" value={area.longitude} onChange={(e) => setArea({ ...area, longitude: e.target.value })} /></Field></div>
        <div className="grid gap-3 sm:grid-cols-3"><Field title="Radius (km)"><input className={input} type="number" min={0.1} max={5} step={0.1} required value={area.radius_km} onChange={(e) => setArea({ ...area, radius_km: e.target.value })} /></Field><Field title="Category"><select className={input} value={area.category} onChange={(e) => setArea({ ...area, category: e.target.value })}><option value="all">All supported</option><option value="shops">Shops</option><option value="food">Food</option><option value="services">Trades / offices</option></select></Field><Field title="Result limit"><input className={input} type="number" min={1} max={50} required value={area.limit} onChange={(e) => setArea({ ...area, limit: e.target.value })} /></Field></div>
        <button className={button} disabled={busy || remaining > 0}>{busy ? "Working…" : remaining > 0 ? `Try again in ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}` : "Discover candidates"}</button>
        {remaining > 0 && <p role="status" className="text-sm text-amber-800">The search cooldown is active. The button will become available automatically; this will not send another request.</p>}
        <p className="text-xs text-slate-500">Up to {dailyLimit} new queries per SAST day; 2-minute cooldown; identical results cached for 24 hours. Public coverage can be sparse. No automatic retries or paid fallback.</p>
        <a className="inline-block text-xs text-slate-500 underline" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a>
      </form>
      <div className="space-y-5"><details className={panel}><summary className="cursor-pointer font-semibold">Add a business manually</summary><form onSubmit={add} className="mt-4 space-y-3">{Object.entries({ name: "Business name", location: "Town / area", source_url: "Public business source URL", address: "Address / branch", phone: "Phone", email: "Listed email (unverified)", website: "Listed website URL (if any)", industry: "Industry" }).map(([key, title]) => <Field key={key} title={title}><input className={input} type={key === "source_url" || key === "website" ? "url" : key === "email" ? "email" : "text"} required={["name", "location", "source_url"].includes(key)} maxLength={key.endsWith("url") || key === "website" ? 2000 : key === "address" ? 500 : 200} value={manual[key as keyof typeof manual]} onChange={(e) => setManual({ ...manual, [key]: e.target.value })} /></Field>)}<button disabled={busy} className={button}>Save candidate</button></form></details>
        <details className={panel}><summary className="cursor-pointer font-semibold">Import CSV</summary><form onSubmit={importCSV} className="mt-4 space-y-3"><p className="text-sm text-slate-500">Up to 100 rows, 200 KB. Required headers: name, location, source_url. Imports create candidates and cannot grant consent.</p><Field title="Choose a CSV file"><input className={input} type="file" accept=".csv,text/csv" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; if (file.size > 200000) { setError("CSV exceeds 200 KB"); return; } setCsv(await file.text()); }} /></Field><Field title="CSV content"><textarea className={`${input} font-mono`} rows={6} required maxLength={200000} value={csv} onChange={(e) => setCsv(e.target.value)} /></Field><button disabled={busy} className={button}>Import candidates</button></form></details>
      </div>
    </div>
    <div className="grid items-start gap-5 lg:grid-cols-3">
      <div className={panel}><div className="flex items-center justify-between gap-2"><h3 className="font-semibold">Candidates ({leads.length})</h3><button className="text-sm text-indigo-700 underline disabled:opacity-50" disabled={busy} onClick={() => act(refresh)}>Refresh</button></div><Field title="Search candidates"><input className={input} value={search} onChange={(e) => setSearch(e.target.value)} /></Field><Field title="Review status"><select className={input} value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option><option value="needs_review">Needs review</option><option value="qualified">Qualified</option><option value="rejected">Rejected</option></select></Field>
        <div className="max-h-[36rem] space-y-2 overflow-auto">{visible.map((lead) => <button key={lead.id} className={`w-full rounded-lg border p-3 text-left text-sm ${selected === lead.id ? "border-indigo-300 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"}`} onClick={() => setSelected(lead.id)}><strong className="block">{lead.name}</strong><span className="block text-xs text-slate-500">{lead.location} · {lead.status || "needs_review"}</span><span className="block text-xs text-slate-500">{lead.observation?.website ? "Website listed · verify" : "No website listed · unverified"}</span><span className="block text-xs text-slate-500">{lead.ready_to_draft ? "Ready to draft" : "Review or permission required"}</span></button>)}{visible.length === 0 && <p className="text-sm text-slate-500">No matching candidates. Run a small search or add/import sourced businesses.</p>}</div>
      </div>
      <div className="min-w-0 lg:col-span-2">{active ? <LeadReview key={active.id} lead={active} busy={busy} onReview={(payload) => act(async () => { await apiRequest(`/api/leads/${active.id}/review`, { method: "PUT", body: JSON.stringify(payload) }); await refresh(); setNotice("Review saved. Contact permission and suppression were preserved."); })} onDraft={(subject, body) => act(async () => { const result = await apiRequest(`/api/leads/${active.id}/draft`, { method: "POST", body: JSON.stringify({ subject, body }) }); setNotice(`Initial outreach draft status: ${result.status}. Open Approvals to review it. No email was sent by this action.`); })} /> : <div className={`${panel} text-sm text-slate-500`}>Select a candidate to review its business identity, website research and contact evidence.</div>}</div>
    </div>
  </section>;
}
