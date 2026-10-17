"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Project = { id: string; name: string; url: string; description: string; tags: string[]; active: boolean };
type Portfolio = { version: number; agency_name: string; portfolio_url: string; projects: Project[] };
export type ProposalPreview = { id: string; subject: string; body: string; projects: (Project & { reason: string })[] };
const input = "mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm";

export function PortfolioEditor() {
  const [catalog, setCatalog] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function load() {
    setBusy(true); setError(""); setNotice("");
    try { setCatalog(await apiRequest("/api/portfolio")); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load portfolio"); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, []);
  function update(index: number, changes: Partial<Project>) {
    if (catalog) setCatalog({ ...catalog, projects: catalog.projects.map((p, i) => i === index ? { ...p, ...changes } : p) });
  }
  async function save(e: FormEvent) {
    e.preventDefault(); if (!catalog) return;
    setBusy(true); setError(""); setNotice("");
    try {
      setCatalog(await apiRequest("/api/portfolio", { method: "PUT", body: JSON.stringify({ ...catalog, projects: catalog.projects.map((p) => ({ ...p, tags: p.tags.map((tag) => tag.trim()).filter(Boolean) })) }) }));
      setNotice("Portfolio saved. Generate a new proposal to use these changes; existing approvals keep their saved content.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save portfolio"); }
    finally { setBusy(false); }
  }
  return <details className="rounded-xl border border-slate-200 bg-white p-5">
    <summary className="cursor-pointer font-semibold">Portfolio &amp; proposals · TS Industries</summary>
    <p className="mt-3 text-sm text-slate-500">Your supplied project links are ready to use. Add only descriptions you can substantiate. Industry tags select relevant examples; with no match, proposals use up to two general examples. Generation uses no research or model credits.</p>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="mt-3 text-sm text-emerald-800">{notice}</p>}
    <button type="button" disabled={busy} className="mt-3 text-sm text-indigo-700 underline disabled:opacity-50" onClick={() => void load()}>Reload saved portfolio</button>
    {catalog && <form className="mt-4 space-y-4" onSubmit={save}>
      <label className="block text-sm">Agency name<input className={input} required maxLength={100} value={catalog.agency_name} onChange={(e) => setCatalog({ ...catalog, agency_name: e.target.value })} /></label>
      <label className="block text-sm">Portfolio URL<input className={input} required type="url" maxLength={2000} value={catalog.portfolio_url} onChange={(e) => setCatalog({ ...catalog, portfolio_url: e.target.value })} /></label>
      <div className="grid gap-4 md:grid-cols-2">{catalog.projects.map((project, index) => <fieldset key={project.id} className="min-w-0 space-y-3 rounded-lg border border-slate-200 p-4">
        <legend className="px-1 text-sm font-medium">Project {index + 1}</legend>
        <label className="block text-sm">Project name<input className={input} required maxLength={100} value={project.name} onChange={(e) => update(index, { name: e.target.value })} /></label>
        <label className="block text-sm">Project URL<input className={input} required type="url" maxLength={2000} value={project.url} onChange={(e) => update(index, { url: e.target.value })} /></label>
        <label className="block text-sm">Description (optional)<input className={input} maxLength={500} placeholder="Confirmed features or work you delivered" value={project.description} onChange={(e) => update(index, { description: e.target.value })} /></label>
        <label className="block text-sm">Industry tags (comma-separated)<input className={input} maxLength={1200} placeholder="Only industries relevant to this project" value={project.tags.join(",")} onChange={(e) => update(index, { tags: e.target.value.split(",") })} /></label>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={project.active} onChange={(e) => update(index, { active: e.target.checked })} />Include in proposal matching</label>
        <button type="button" className="text-sm text-red-700 underline" onClick={() => setCatalog({ ...catalog, projects: catalog.projects.filter((_, i) => i !== index) })}>Remove project</button>
      </fieldset>)}</div>
      <div className="flex flex-wrap gap-4"><button type="button" disabled={busy || catalog.projects.length >= 12} className="text-sm text-indigo-700 underline disabled:opacity-50" onClick={() => setCatalog({ ...catalog, projects: [...catalog.projects, { id: `project-${crypto.randomUUID()}`, name: "", url: "", description: "", tags: [], active: true }] })}>Add project</button><button disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50">Save portfolio</button></div>
      <p className="text-xs text-slate-500">Proposal signature: pharezsigasa@gmail.com · +447544357979. Links and descriptions are supplied by you; the app has not checked the sites. No pricing or results are inferred.</p>
    </form>}
  </details>;
}
