"use client";

import { FormEvent, useEffect, useState } from "react";

export type ReplyAssessment = { category: string; reason: string; evidence: string[]; suggested_outcome: string | null; template_available: boolean; fingerprint: string };
export type Incoming = { id: string; sender: string; subject: string; body: string; status: string; error?: string; automated?: boolean; bounce?: boolean; unsubscribe?: boolean; reply_blocker?: string; draft_action?: string; reply_assessment: ReplyAssessment };
export type ReplyPreview = { id: string; subject: string; body: string };

export function ReplyReview({ mail, busy, onManual, onTemplate, onConfirm, onRetry }: { mail: Incoming; busy: boolean; onManual: () => void; onTemplate: () => void; onConfirm: (outcome: string, note: string) => void; onRetry: () => void }) {
  const assessment = mail.reply_assessment;
  const [outcome, setOutcome] = useState(assessment.suggested_outcome || "unclassified");
  const [note, setNote] = useState("");
  useEffect(() => { setOutcome(assessment.suggested_outcome || "unclassified"); setNote(""); }, [mail.id, assessment.fingerprint]);
  const button = "rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:opacity-50";
  function confirm(e: FormEvent) { e.preventDefault(); onConfirm(outcome, note); }
  return <article className="space-y-3 border-t border-slate-200 pt-4">
    <div><p className="text-sm font-medium">{mail.sender} · {mail.subject}</p><p className="text-xs text-slate-500">{mail.status} {mail.automated ? "· Automated message" : ""} {mail.unsubscribe && !mail.automated ? "· Contact suppressed" : ""} {mail.error}</p></div>
    <p className="max-h-48 overflow-auto whitespace-pre-wrap text-sm">{mail.body}</p>
    <div className="space-y-1 rounded-lg bg-slate-50 p-3 text-sm"><p className="font-medium capitalize">Suggested category: {assessment.category.replaceAll("_", " ")}</p><p>{assessment.reason}</p>{assessment.evidence.length > 0 && <p className="text-xs text-slate-600">Phrases seen: {assessment.evidence.join(" · ")}</p>}<p className="text-xs text-slate-500">Rule-based suggestion. Interested and declined counts change only after you confirm an outcome. Templates ask about scope; check that your response actually answers the message.</p>{mail.draft_action === "queued" && <p className="text-xs text-indigo-700">A response was queued for approval during sync.</p>}</div>
    {mail.reply_blocker && <p className="text-sm text-amber-800">{mail.reply_blocker}</p>}
    {!mail.automated && !mail.bounce && !mail.unsubscribe && <>
      <div className="flex flex-wrap gap-2"><button disabled={busy || Boolean(mail.reply_blocker)} className={button} onClick={onManual}>Write reply</button>{assessment.template_available && <button disabled={busy || Boolean(mail.reply_blocker)} className={button} onClick={onTemplate}>Prepare response template</button>}</div>
      <form onSubmit={confirm} className="space-y-2 rounded-lg border border-slate-200 p-3">
        <label className="block text-sm">Confirm conversation outcome<select className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm" value={outcome} onChange={(e) => setOutcome(e.target.value)}><option value="unclassified">Unclassified / needs review</option><option value="interested">Interested</option><option value="declined">Declined</option></select></label>
        <label className="block text-sm">Your evidence or reason<input className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-sm" required maxLength={1800} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <button disabled={busy || !note.trim()} className={button}>Confirm outcome for reports</button>
        <p className="text-xs text-slate-500">Read the full reply before confirming. This does not send a message or change contact permission. Mark won in Reports only after checking the result.</p>
      </form>
    </>}
    {mail.status === "failed" && <button disabled={busy} className={button} onClick={onRetry}>Retry processing</button>}
  </article>;
}
