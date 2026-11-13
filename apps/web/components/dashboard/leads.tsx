"use client";

import { FormEvent, useContext, useEffect, useState } from "react";
import { apiRequest, ApiError } from "@/lib/api";
import { ResearchJobs, ResearchJob } from "@/components/dashboard/research-jobs";
import { Campaigns } from "@/components/dashboard/campaigns";
import { PortfolioEditor, ProposalPreview } from "@/components/dashboard/portfolio";
import { TabContext } from "@/components/app-shell";

type Review = {
  revision: number; confirmed_name: string; identity_verified: boolean; identity_source: string; identity_note: string;
  business_status: string; activity_method: string; activity_date: string; website_status: string; website_url: string; website_source: string; website_note: string;
  contact_verified: boolean; email: string; contact_source: string; contact_note: string; decision: string; decision_note: string;
};
type Observation = { name?: string; email?: string; website?: string; source_url?: string; observed_at?: string; source_updated_at?: string; source_check_date?: string; source_kind?: string; source_note?: string };
type WebResearch = { enabled: boolean; configured: boolean; daily_limit: number; monthly_limit: number; daily_used: number; monthly_used: number; retry_after_seconds: number };
type Finding = { value: string; evidence: string };
type Inspection = { source_url: string; checked_at: string; stale: boolean; warning: string; findings: { emails: Finding[]; phones: Finding[]; links: Finding[]; external_links: Finding[]; dates: Finding[]; closure_mentions: Finding[]; location_text_seen: boolean } };
type Lead = { id: string; name: string; location: string; address?: string; phone?: string; industry?: string; source_url: string; source: string; revision?: number; status?: string; review?: Review & { reviewed_at?: string }; observation?: Observation; observations?: Observation[]; review_invalidated?: boolean; ready_to_draft: boolean; dispatch_blocker: string; consent: string; possible_duplicates: string[]; source_inspection?: Inspection | null; source_freshness?: { status: string; age_days: number | null } };
const input = "mt-1 block w-full min-w-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
const button = "rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const panel = "rounded-xl border border-slate-200 bg-white p-5 space-y-4";
const empty = { name: "", location: "", address: "", phone: "", email: "", website: "", industry: "", source_url: "", source_kind: "", source_note: "" };
const sourceKinds: Record<string, string> = { business_owned_page: "Business-owned page", public_business_social: "Public business social profile", owner_provided: "Details supplied by the business", local_observation: "Personal observation / visit", other: "Other independent source" };
function freshReview(lead: Lead): Review {
  const saved = lead.review;
  return { revision: lead.revision || 0, confirmed_name: saved?.confirmed_name || "", identity_verified: saved?.identity_verified || false,
    identity_source: saved?.identity_source || lead.source_url || "", identity_note: saved?.identity_note || "",
    business_status: saved?.business_status || "unknown", activity_method: saved?.activity_method || "", activity_date: saved?.activity_date || "", website_status: saved?.website_status || "not_checked",
    website_url: saved?.website_url || "", website_source: saved?.website_source || "", website_note: saved?.website_note || "",
    contact_verified: saved?.contact_verified || false, email: saved?.email || lead.observation?.email || "",
    contact_source: saved?.contact_source || lead.source_url || "", contact_note: saved?.contact_note || "",
    decision: saved?.decision || "needs_review", decision_note: saved?.decision_note || "" };
}
function Field({ title, children }: { title: string; children: React.ReactNode }) { return <label className="block text-sm font-medium text-slate-700">{title}{children}</label>; }

function LeadReview({ lead, busy, onReview, onDraft, onInspect, inspectionAvailable, inspectionWait }: { lead: Lead; busy: boolean; onInspect: () => void; inspectionAvailable: boolean; inspectionWait: number; onReview: (payload: Review) => void; onDraft: (subject: string, body: string, previewId?: string) => void }) {
  const [review, setReview] = useState<Review>(freshReview(lead));
  const [subject, setSubject] = useState(`Website enquiry for ${lead.name}`);
  const [body, setBody] = useState("");
  const [preview, setPreview] = useState<ProposalPreview | null>(null);
  const [generating, setGenerating] = useState(false);
  const [proposalError, setProposalError] = useState("");
  async function generate() {
    setGenerating(true); setProposalError("");
    try { const result: ProposalPreview = await apiRequest(`/api/leads/${lead.id}/proposal`, { method: "POST" }); setPreview(result); setSubject(result.subject); setBody(result.body); }
    catch (e) { setProposalError(e instanceof Error ? e.message : "Could not generate proposal"); }
    finally { setGenerating(false); }
  }
  const { setTab } = useContext(TabContext);
  useEffect(() => { setReview(freshReview(lead)); }, [lead.id, lead.revision]);
  useEffect(() => { setSubject(`Website enquiry for ${lead.name}`); setBody(""); setPreview(null); setProposalError(""); }, [lead.id]);
  function text(key: keyof Review, title: string, type = "text") {
    return <Field title={title}><input type={type} className={input} value={String(review[key])} maxLength={2000} onChange={(e) => setReview({ ...review, [key]: e.target.value })} /></Field>;
  }
  function note(key: keyof Review, title: string) {
    return <Field title={title}><textarea className={input} rows={3} value={String(review[key])} maxLength={2000} onChange={(e) => setReview({ ...review, [key]: e.target.value })} /></Field>;
  }
  const inspection = lead.source_inspection;
  return <div className="space-y-5">
    <div className={panel}><div><h3 className="text-lg font-semibold">{lead.name}</h3><p className="text-sm text-slate-500">{lead.location} · {lead.industry || "Category not recorded"}</p></div>
      <p className="text-sm">{lead.address || "Address not recorded"}<br />{lead.phone || "Phone not recorded"}</p>
      {/^https?:\/\//i.test(lead.source_url || "") && <a className="block break-all text-sm text-indigo-700 underline" href={lead.source_url} target="_blank" rel="noreferrer">Open discovery source</a>}
      <div className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium">Unverified source observations</p><p className="mt-1 break-all">Email: {lead.observation?.email || "Not listed"}<br />Website: {lead.observation?.website || "Not listed"}</p><p className="mt-2 text-xs text-slate-500">A missing listing is not proof that no website exists. A listed email is not verified permission to contact.</p></div>
      {lead.source === "tavily" && <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900"><p className="font-medium">Unverified web search source</p><p className="mt-1 break-words">Search title: {lead.observation?.name}</p><p className="mt-2 text-xs">This title may describe a directory, multiple businesses or an unrelated page. Confirm the exact business name and branch in the review. No email, activity or website finding was inferred.</p></div>}
      {lead.source === "manual" && <div className="rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium">Source: {sourceKinds[lead.observation?.source_kind || ""] || "Manual entry · source type not recorded"}</p><p className="mt-1 whitespace-pre-wrap break-words">{lead.observation?.source_note || "No provenance note recorded. Check the original source before qualification."}</p><p className="mt-2 text-xs text-slate-500">Source information is entered by the researcher; saving it does not verify activity, website absence or permission.</p></div>}
      {lead.source === "openstreetmap" && <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900"><p className="font-medium">Map listing · current activity unverified</p>{lead.source_freshness?.status === "old" && <p className="mt-1 font-medium">This map entry has not been edited for over a year.</p>}<p className="mt-1 break-all">Last map edit: {lead.observation?.source_updated_at || "Unknown (older results may lack metadata)"}<br />Mapper check/survey date: {lead.observation?.source_check_date || "Not recorded"}<br />Retrieved by this app: {lead.observation?.observed_at || "Unknown"}</p><p className="mt-2 text-xs">A recent retrieval or map edit does not confirm this business is open. Listings can remain after closure. Verify recent business activity separately; use manual entry or CSV for businesses missing from the map.</p></div>}
      {lead.review_invalidated && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Source details changed. Review the current evidence before qualifying this lead again.</p>}
      {lead.possible_duplicates.length > 0 && <p className="text-sm text-amber-800">{lead.possible_duplicates.length} other entries share this name and location. Check the branch/address; reject duplicate entries rather than contacting twice.</p>}
      <details><summary className="cursor-pointer text-sm font-medium">Source history</summary><ul className="mt-3 space-y-3 text-xs text-slate-600">{lead.observations?.slice().reverse().map((o, i) => <li key={i} className="break-all">Retrieved: {o.observed_at} · {o.source_url}<br />Map edit: {o.source_updated_at || "Unknown"}<br />Source: {sourceKinds[o.source_kind || ""] || "Not classified"} · {o.source_note || "No provenance note"}<br />Email: {o.email || "Not listed"} · Website: {o.website || "Not listed"}</li>)}</ul></details>
    </div>
    {lead.source !== "openstreetmap" && <div className={panel}><h3 className="font-semibold">Inspect source evidence</h3><p className="text-sm text-slate-500">Read this saved page through Tavily and suggest literal emails, South African phone numbers and links. This uses one shared research attempt unless cached. Other pages are not followed.</p><button type="button" className={button} disabled={busy || !inspectionAvailable || inspectionWait > 0} onClick={onInspect}>{inspectionWait > 0 ? `Inspection available in ${Math.floor(inspectionWait / 60)}:${String(inspectionWait % 60).padStart(2, "0")}` : "Inspect this source"}</button>{!inspectionAvailable && <p className="text-xs text-amber-800">Enable Tavily research with a local key to inspect sources.</p>}
      {inspection && <div className="space-y-4"><p className="text-xs text-slate-500">Inspected: {inspection.checked_at}<br />Source: <a className="break-all text-indigo-700 underline" href={inspection.source_url} target="_blank" rel="noreferrer">{inspection.source_url}</a></p>{inspection.stale && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">These findings are over 24 hours old or describe an earlier source observation. Inspect the current source before using suggestions.</p>}<p className="text-xs text-amber-900">{inspection.warning}</p><button type="button" disabled={busy || inspection.stale} className="text-sm text-indigo-700 underline disabled:opacity-50" onClick={() => setReview({ ...review, website_status: "found", website_url: inspection.source_url, website_source: inspection.source_url, website_note: "Inspected source selected as the business website. Confirm this site belongs to the exact business and branch before saving." })}>Mark this inspected page as the business website after checking ownership</button><p className="text-xs text-slate-500">Recognized image and download assets are omitted. External references may be suppliers, articles or advertisers; they are not proposed as this business’s website.</p><p className="text-xs text-slate-500">Town name seen in extracted text: {inspection.findings.location_text_seen ? "Yes; this does not verify the branch" : "No; location remains unconfirmed"}</p>
      {(["emails", "phones", "links", "external_links", "dates", "closure_mentions"] as const).map((kind) => <div key={kind}><h4 className="text-sm font-medium">{{ emails: "Published email candidates", phones: "Phone candidates", links: "Same-site pages · business ownership unverified", external_links: "External references · not verified business websites", dates: "Dates seen · activity unverified", closure_mentions: "Closure phrases · read the context" }[kind]}</h4>{inspection.findings[kind].length === 0 ? <p className="mt-1 text-xs text-slate-500">Not found in extracted text. This does not prove absence.</p> : <ul className="mt-2 space-y-3">{inspection.findings[kind].map((item) => <li key={item.value} className="rounded-lg bg-slate-50 p-3 text-sm"><p className="break-all font-medium">{(kind === "links" || kind === "external_links") ? <a href={item.value} target="_blank" rel="noreferrer" className="text-indigo-700 underline">{item.value}</a> : item.value}</p><p className="mt-1 whitespace-pre-wrap break-words text-xs text-slate-600">{item.evidence}</p>{kind === "emails" && <button type="button" disabled={busy || inspection.stale} className="mt-2 text-xs text-indigo-700 underline disabled:opacity-50" onClick={() => setReview({ ...review, email: item.value, contact_source: inspection.source_url, contact_note: `Source inspection candidate: ${item.evidence}\nConfirm this exact email belongs to this branch.`, contact_verified: false })}>Use email in review · verification stays unchecked</button>}{kind === "links" && <button type="button" disabled={busy || inspection.stale} className="mt-2 block text-xs text-indigo-700 underline disabled:opacity-50" onClick={() => setReview({ ...review, website_status: "found", website_url: item.value, website_source: inspection.source_url, website_note: `Operator-selected website link; confirm business ownership: ${item.evidence}` })}>Record as website found after checking ownership</button>}</li>)}</ul>}</div>)}<p className="text-xs text-slate-500">Suggestion buttons only edit the unsaved review below. They do not verify a contact, grant permission or send email. Save your review after checking the original source and exact business. A fresh inspection requires a new review before an already qualified lead can send outreach.</p></div>}
    </div>}
    <form onSubmit={(e) => { e.preventDefault(); onReview(review); }} className={panel}>
      <h3 className="font-semibold">Review the business</h3>
      <p className="text-sm text-slate-500">Use public sources and your own verification. The app stores your evidence; it does not infer that a business is active or lacks a website.</p>
      <fieldset className="space-y-3 border-t border-slate-100 pt-4"><legend className="text-sm font-semibold">1. Business identity and activity</legend>
        {lead.source === "tavily" && text("confirmed_name", "Confirmed business and branch name (required to qualify)")}
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
    <form onSubmit={(e) => { e.preventDefault(); onDraft(subject, body, preview?.id); }} className={panel}>
      <h3 className="font-semibold">Prepare outreach for approval</h3>
      <p className="text-sm">Review: <strong>{lead.status || "needs_review"}</strong> · Permission: <strong>{lead.consent}</strong></p>
      {!lead.ready_to_draft && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{lead.dispatch_blocker}</p>}
      <button type="button" className="text-sm text-indigo-700 underline" onClick={() => setTab("settings")}>Open Settings to record actual contact permission</button>
      <button type="button" disabled={busy || generating || !lead.ready_to_draft} className={button} onClick={() => void generate()}>{generating ? "Generating…" : "Generate portfolio proposal"}</button>
      {proposalError && <p role="alert" className="text-sm text-red-700">{proposalError}</p>}
      {preview && <div className="space-y-2 rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium">Selected portfolio examples</p>{preview.projects.map((p) => <p key={p.id}><a href={p.url} target="_blank" rel="noreferrer" className="text-indigo-700 underline">{p.name}</a><br /><span className="text-xs text-slate-500">{p.reason}</span></p>)}{!preview.projects.length && <p>No active project examples; agency portfolio link only.</p>}<p className="text-xs text-slate-500">Edit the subject and message below before saving. Regenerate after changing the lead review or portfolio.</p></div>}
      <Field title="Subject"><input className={input} required maxLength={300} value={subject} onChange={(e) => setSubject(e.target.value)} /></Field>
      <Field title="Message"><textarea className={input} required rows={7} maxLength={20000} value={body} onChange={(e) => setBody(e.target.value)} /></Field>
      <p className="text-xs text-slate-500">Describe your service accurately. Use “I couldn’t find your website” when that is your evidence, rather than claiming the business has none. Generated text uses your saved portfolio and reviewed business details.</p>
      <button disabled={busy || generating || !lead.ready_to_draft} className={button}>Save for approval</button>
      <p className="text-xs text-slate-500">Creates one initial outreach draft per connected mailbox/contact. Review it in Approvals to send. Repeating this action does not resend or replace an existing draft.</p>
    </form>
  </div>;
}

export function LeadsDashboard() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [workerEnabled, setWorkerEnabled] = useState(false);
  const [selected, setSelected] = useState("");
  const [filter, setFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [research, setResearch] = useState({ town: "Standerton, Mpumalanga", trade: "", name: "" });
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [webStatus, setWebStatus] = useState<WebResearch | null>(null);
  const [webCooldownUntil, setWebCooldownUntil] = useState(0);
  const [webLimit, setWebLimit] = useState("5");
  const [dailyLimit, setDailyLimit] = useState(20);
  const [providerName, setProviderName] = useState("Private.coffee");
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const webRemaining = Math.max(0, Math.ceil((webCooldownUntil - clock) / 1000));
  const remaining = Math.max(0, Math.ceil((cooldownUntil - clock) / 1000));
  useEffect(() => { const timer = setInterval(() => setClock(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const [manual, setManual] = useState(empty);
  const [csv, setCsv] = useState("name,location,source_url,address,phone,email,website,industry,source_kind,source_note\n");
  const [area, setArea] = useState({ location: "Standerton, Mpumalanga", latitude: "", longitude: "", radius_km: "1", category: "all", limit: "25" });
  async function refresh() { const result = await apiRequest("/api/leads"); setLeads(result.leads); setJobs(result.research_jobs || []); setWorkerEnabled(Boolean(result.research_worker_enabled)); setWebStatus(result.web_research); setWebCooldownUntil(Date.now() + (result.web_research?.retry_after_seconds || 0) * 1000); setDailyLimit(result.daily_limit); setProviderName(result.provider?.name || "OpenStreetMap provider"); setCooldownUntil(Date.now() + (result.retry_after_seconds || 0) * 1000); setClock(Date.now()); }
  async function act(call: () => Promise<void>, provider: "osm" | "tavily" = "osm") {
    setBusy(true); setError(""); setNotice("");
    try { await call(); } catch (e) { setError(e instanceof Error ? e.message : "Lead operation failed"); if (e instanceof ApiError && e.retryAfterSeconds > 0) { if (provider === "tavily") setWebCooldownUntil(Date.now() + e.retryAfterSeconds * 1000); else setCooldownUntil(Date.now() + e.retryAfterSeconds * 1000); setClock(Date.now()); } }
    finally { setBusy(false); }
  }
  useEffect(() => { void act(refresh); }, []);
  const activeJob = jobs.some((job) => ["queued", "running", "waiting"].includes(job.status));
  useEffect(() => {
    if (!activeJob) return;
    let pending = false;
    const timer = setInterval(async () => { if (pending) return; pending = true; try { await refresh(); } catch (e) { setError(e instanceof Error ? e.message : "Could not refresh job progress"); } finally { pending = false; } }, 5000);
    return () => clearInterval(timer);
  }, [activeJob]);
  async function discover(e: FormEvent) {
    e.preventDefault();
    await act(async () => { const result = await apiRequest("/api/leads/discover", { method: "POST", body: JSON.stringify({ ...area, latitude: Number(area.latitude), longitude: Number(area.longitude), radius_km: Number(area.radius_km), limit: Number(area.limit) }) }); await refresh(); setSourceFilter("all"); setFilter("all"); setSearch(""); if (result.leads[0]) setSelected(result.leads[0].id); setNotice(`${result.leads.length} unverified candidates loaded${result.cached ? " from the 24-hour cache" : " from OpenStreetMap"}.${result.truncated ? " Results were capped; narrow the radius." : ""} No email was sent.`); });
  }
  async function inspectCandidate(leadId: string) {
    await act(async () => { try {
      const result = await apiRequest(`/api/leads/${leadId}/inspect`, { method: "POST" });
      await refresh(); setNotice(`Source inspected${result.cached ? " from cache (no new request)" : " through Tavily"}. Findings remain unverified. Review the evidence before saving; no email was sent.`);
    } catch (e) { await refresh(); throw e; } }, "tavily");
  }
  async function webSearch(e: FormEvent) {
    e.preventDefault();
    await act(async () => { try {
      const result = await apiRequest("/api/leads/research", { method: "POST", body: JSON.stringify({ location: research.town, industry: research.trade, limit: Number(webLimit) }) });
      await refresh(); setSourceFilter("tavily"); setFilter("all"); setSearch(""); if (result.leads[0]) setSelected(result.leads[0].id);
      setNotice(`${result.leads.length} unverified source candidates loaded${result.cached ? " from cache (no new request)" : " from Tavily"}. ${result.skipped_results || 0} unusable results skipped. ${result.warning} No email was sent.`);
    } catch (e) { await refresh(); throw e; } }, "tavily");
  }
  async function add(e: FormEvent) {
    e.preventDefault(); await act(async () => { const lead = await apiRequest("/api/leads", { method: "POST", body: JSON.stringify(manual) }); await refresh(); setSourceFilter("manual"); setFilter("all"); setSearch(""); setSelected(lead.id); setManual(empty); setNotice("Candidate saved for evidence review. No email was sent."); });
  }
  async function importCSV(e: FormEvent) {
    e.preventDefault(); await act(async () => { const result = await apiRequest("/api/leads/import", { method: "POST", body: JSON.stringify({ csv_text: csv }) }); await refresh(); setSourceFilter("manual"); setFilter("all"); setSearch(""); if (result.lead_ids[0]) setSelected(result.lead_ids[0]); setNotice(`${result.rows} CSV rows processed; ${result.unique_leads} unique candidates. No permission was granted and no email was sent.`); });
  }
  const active = leads.find((l) => l.id === selected);
  const visible = leads.filter((l) => (sourceFilter === "all" || l.source === sourceFilter) && (filter === "all" || (l.status || "needs_review") === filter) && `${l.name} ${l.location} ${l.industry || ""}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="space-y-6">
    <div><h2 className="text-xl font-semibold">Business research</h2><p className="mt-1 text-sm text-slate-500">Find candidates, review evidence, and prepare eligible outreach. Discovery never sends emails.</p></div>
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
    <Campaigns leads={leads} />
    <PortfolioEditor />
    <ResearchJobs jobs={jobs} available={Boolean(webStatus?.enabled && webStatus?.configured)} workerEnabled={workerEnabled} busy={busy} clock={clock} onStart={(payload) => void act(async () => { await apiRequest("/api/leads/jobs", { method: "POST", body: JSON.stringify(payload) }); await refresh(); setNotice("Research job started. Progress is saved; cooldown waits are automatic. No email will be drafted or sent."); }, "tavily")} onControl={(id, action, budget) => void act(async () => { await apiRequest(`/api/leads/jobs/${id}`, { method: "PATCH", body: JSON.stringify({ action, ...(budget === undefined ? {} : { max_requests: budget }) }) }); await refresh(); }, "tavily")} onSelect={(id) => { setSelected(id); setFilter("all"); setSourceFilter("all"); setSearch(""); document.getElementById("lead-candidates")?.scrollIntoView({ behavior: "smooth" }); }} />
    <div className="grid items-start gap-5 xl:grid-cols-2">
      <div className="space-y-5"><details open className={panel}><summary className="cursor-pointer font-semibold">Add an independently sourced business</summary><form onSubmit={add} className="mt-4 space-y-3">{Object.entries({ name: "Business name", location: "Town / area", source_url: "Original business / independent source URL", address: "Address / branch", phone: "Phone", email: "Listed email (unverified)", website: "Listed website URL (if any)", industry: "Industry" }).map(([key, title]) => <Field key={key} title={title}><input className={input} type={key === "source_url" || key === "website" ? "url" : key === "email" ? "email" : "text"} required={["name", "location", "source_url"].includes(key)} maxLength={key.endsWith("url") || key === "website" ? 2000 : key === "address" ? 500 : 200} value={manual[key as keyof typeof manual]} onChange={(e) => setManual({ ...manual, [key]: e.target.value })} /></Field>)}<Field title="Where did these details come from?"><select className={input} required value={manual.source_kind} onChange={(e) => setManual({ ...manual, source_kind: e.target.value })}><option value="">Choose a source type</option>{Object.entries(sourceKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field><Field title="Source note"><textarea className={input} required rows={3} maxLength={2000} placeholder="Describe the page, owner confirmation or visit supporting these details. Record when it happened." value={manual.source_note} onChange={(e) => setManual({ ...manual, source_note: e.target.value })} /></Field><p className="text-xs text-slate-500">Save facts from the original business source or your own observations. Do not copy Google Maps listings into this ledger. Qualification and contact permission are reviewed separately.</p><button disabled={busy} className={button}>Save candidate</button></form></details>
        <details className={panel}><summary className="cursor-pointer font-semibold">Import CSV</summary><form onSubmit={importCSV} className="mt-4 space-y-3"><p className="text-sm text-slate-500">Up to 100 rows, 200 KB. Required headers: name, location, source_url. Optional source_kind and source_note columns preserve provenance. Source kinds: business_owned_page, public_business_social, owner_provided, local_observation, other. A selected kind requires a note. Older CSV files still work. Imports create candidates and cannot grant consent.</p><Field title="Choose a CSV file"><input className={input} type="file" accept=".csv,text/csv" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; if (file.size > 200000) { setError("CSV exceeds 200 KB"); return; } setCsv(await file.text()); }} /></Field><Field title="CSV content"><textarea className={`${input} font-mono`} rows={6} required maxLength={200000} value={csv} onChange={(e) => setCsv(e.target.value)} /></Field><button disabled={busy} className={button}>Import candidates</button></form></details>
      </div>
      <div className="space-y-5"><form onSubmit={webSearch} className={panel}><h3 className="font-semibold">Automatic web discovery · Tavily</h3><p className="text-sm text-slate-500">Search public web sources by town and business type. Results are source candidates requiring review, not confirmed businesses without websites.</p><p className="text-sm">{webStatus ? `Today: ${webStatus.daily_used} / ${webStatus.daily_limit} research attempts · This month: ${webStatus.monthly_used} / ${webStatus.monthly_limit}` : "Loading search configuration…"}</p>{webStatus && (!webStatus.enabled || !webStatus.configured) && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{!webStatus.configured ? "Tavily API key is not configured on the backend." : "Tavily research is disabled."} Configure the local backend, then restart it. Your key is never entered in this page.</p>}<Field title="Discovery town / area"><input className={input} required maxLength={200} value={research.town} onChange={(e) => setResearch({ ...research, town: e.target.value })} /></Field><Field title="Discovery business type"><input className={input} required maxLength={200} placeholder="e.g. plumbers" value={research.trade} onChange={(e) => setResearch({ ...research, trade: e.target.value })} /></Field><Field title="Source result limit"><input className={input} type="number" min={1} max={10} required value={webLimit} onChange={(e) => setWebLimit(e.target.value)} /></Field><button className={button} disabled={busy || !webStatus?.enabled || !webStatus?.configured || webRemaining > 0}>{webRemaining > 0 ? `Try again in ${Math.floor(webRemaining / 60)}:${String(webRemaining % 60).padStart(2, "0")}` : "Discover web candidates"}</button><p className="text-xs text-slate-500">Search and source inspection share these limits: 2-minute cooldown and 24-hour cache. Each new search or inspection reserves one attempt. Failed attempts count toward local limits. Counters cover this installation, not other uses of your account. Check the provider dashboard for remaining credits and keep paid usage off. No retries, crawling, LLM calls or automatic emails.</p></form><details className={panel}><summary className="cursor-pointer font-semibold">Manual research searches</summary><p className="text-sm text-slate-500">Start with public business-owned pages, public business social profiles, direct confirmation or your own visits. Record the original evidence in the form alongside. This is a manual research workflow.</p>
        <Field title="Research town / area"><input className={input} maxLength={200} value={research.town} onChange={(e) => setResearch({ ...research, town: e.target.value })} /></Field>
        <Field title="Business type"><input className={input} maxLength={200} placeholder="e.g. salon, plumber, bakery" value={research.trade} onChange={(e) => setResearch({ ...research, trade: e.target.value })} /></Field>
        <Field title="Business name (optional)"><input className={input} maxLength={200} value={research.name} onChange={(e) => setResearch({ ...research, name: e.target.value })} /></Field>
        {research.town.trim() && (research.trade.trim() || research.name.trim()) ? <div className="flex flex-col gap-3 text-sm text-indigo-700 underline">{[["Search business pages", ""], ["Search public Facebook business pages", "site:facebook.com"], ["Search public Instagram business profiles", "site:instagram.com"]].map(([label, scope]) => <a key={label} href={`https://www.google.com/search?q=${encodeURIComponent([research.name, research.trade, research.town, scope].filter(Boolean).join(" "))}`} target="_blank" rel="noreferrer">{label}</a>)}</div> : <p className="text-xs text-slate-500">Enter a town and a business type or name to open research searches.</p>}
        <p className="text-xs text-slate-500">Links open ordinary web searches. The app does not fetch results, scrape profiles or automatically import listings. Follow the original business page and confirm the branch. A recent post can support activity; a profile alone does not establish that the business is open or lacks a website.</p>
      </details>
      <details className={panel}><summary className="cursor-pointer font-semibold">Optional OpenStreetMap discovery</summary><form onSubmit={discover} className="mt-4 space-y-4"><p className="text-sm text-slate-500">Enter the centre coordinates of your target area. Searches use OpenStreetMap, not Google Maps or a paid API. Coordinates and radius are sent to {providerName}, the selected public Overpass provider.</p>
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Map coverage may be incomplete or years out of date. Results are research candidates, not a list of currently operating businesses. Changing Overpass providers does not change the underlying map source.</p>
        <a href="https://www.openstreetmap.org" target="_blank" rel="noreferrer" className="block text-sm text-indigo-700 underline">Find your area on OpenStreetMap (map URL contains latitude/longitude)</a>
        <Field title="Location label"><input className={input} required maxLength={200} value={area.location} onChange={(e) => setArea({ ...area, location: e.target.value })} /></Field>
        <div className="grid gap-3 sm:grid-cols-2"><Field title="Latitude"><input className={input} type="number" step="any" min={-85} max={85} required placeholder="Latitude" value={area.latitude} onChange={(e) => setArea({ ...area, latitude: e.target.value })} /></Field><Field title="Longitude"><input className={input} type="number" step="any" min={-180} max={180} required placeholder="Longitude" value={area.longitude} onChange={(e) => setArea({ ...area, longitude: e.target.value })} /></Field></div>
        <div className="grid gap-3 sm:grid-cols-3"><Field title="Radius (km)"><input className={input} type="number" min={0.1} max={5} step={0.1} required value={area.radius_km} onChange={(e) => setArea({ ...area, radius_km: e.target.value })} /></Field><Field title="Category"><select className={input} value={area.category} onChange={(e) => setArea({ ...area, category: e.target.value })}><option value="all">All supported</option><option value="shops">Shops</option><option value="food">Food</option><option value="services">Trades / offices</option></select></Field><Field title="Result limit"><input className={input} type="number" min={1} max={50} required value={area.limit} onChange={(e) => setArea({ ...area, limit: e.target.value })} /></Field></div>
        <button className={button} disabled={busy || remaining > 0}>{busy ? "Working…" : remaining > 0 ? `Try again in ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}` : "Discover candidates"}</button>
        {remaining > 0 && <p role="status" className="text-sm text-amber-800">The search cooldown is active. The button will become available automatically; this will not send another request.</p>}
        <p className="text-xs text-slate-500">Up to {dailyLimit} new queries per SAST day; 2-minute cooldown; identical results cached for 24 hours. Public coverage can be sparse. No automatic retries or paid fallback.</p>
        <a className="inline-block text-xs text-slate-500 underline" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors · ODbL</a>
      </form></details>
      </div>
    </div>
    <div id="lead-candidates" className="grid items-start gap-5 lg:grid-cols-3">
      <div className={panel}><div className="flex items-center justify-between gap-2"><h3 className="font-semibold">Candidates ({visible.length} / {leads.length})</h3><button className="text-sm text-indigo-700 underline disabled:opacity-50" disabled={busy} onClick={() => act(refresh)}>Refresh</button></div><Field title="Search candidates"><input className={input} value={search} onChange={(e) => setSearch(e.target.value)} /></Field><Field title="Candidate source"><select className={input} value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}><option value="all">All sources</option><option value="manual">Manual / CSV research</option><option value="openstreetmap">OpenStreetMap</option><option value="tavily">Tavily (optional)</option></select></Field><Field title="Review status"><select className={input} value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option><option value="needs_review">Needs review</option><option value="qualified">Qualified</option><option value="rejected">Rejected</option></select></Field>
        <div className="max-h-[36rem] space-y-2 overflow-auto">{visible.map((lead) => <button key={lead.id} className={`w-full rounded-lg border p-3 text-left text-sm ${selected === lead.id ? "border-indigo-300 bg-indigo-50" : "border-slate-200 hover:bg-slate-50"}`} onClick={() => setSelected(lead.id)}><strong className="block">{lead.name}</strong><span className="block text-xs text-slate-500">{lead.location} · {lead.status || "needs_review"}</span><span className="block text-xs text-slate-500">{lead.source === "manual" ? sourceKinds[lead.observation?.source_kind || ""] || "Manual / CSV" : lead.source === "openstreetmap" ? "OpenStreetMap" : lead.source}</span><span className="block text-xs text-slate-500">{lead.observation?.website ? "Website listed · verify" : "No website listed · unverified"}</span><span className="block text-xs text-slate-500">{lead.ready_to_draft ? "Ready to draft" : "Review or permission required"}</span></button>)}{visible.length === 0 && <p className="text-sm text-slate-500">No matching candidates. Run a small search or add/import sourced businesses.</p>}</div>
      </div>
      <div className="min-w-0 lg:col-span-2">{active ? <LeadReview key={active.id} lead={active} busy={busy} onInspect={() => void inspectCandidate(active.id)} inspectionAvailable={Boolean(webStatus?.enabled && webStatus?.configured)} inspectionWait={webRemaining} onReview={(payload) => act(async () => { await apiRequest(`/api/leads/${active.id}/review`, { method: "PUT", body: JSON.stringify(payload) }); await refresh(); setNotice("Review saved. Contact permission and suppression were preserved."); })} onDraft={(subject, body, previewId) => act(async () => { const result = await apiRequest(`/api/leads/${active.id}/draft`, { method: "POST", body: JSON.stringify({ subject, body, proposal_preview_id: previewId }) }); setNotice(`Initial outreach draft status: ${result.status}. Open Approvals to review it. No email was sent by this action.`); })} /> : <div className={`${panel} text-sm text-slate-500`}>Select a candidate to review its business identity, website research and contact evidence.</div>}</div>
    </div>
  </section>;
}
