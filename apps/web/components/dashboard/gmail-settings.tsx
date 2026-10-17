"use client";
import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { ReplyReview, Incoming, ReplyPreview } from "@/components/dashboard/reply-review";

type Contact = { email: string; name?: string; consent: string; verified: boolean; test_recipient: boolean };
type GmailStatus = { configured: boolean; connection?: { status: string; email?: string }; reply_drafting_enabled: boolean };

export function GmailSettings() {
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [inbox, setInbox] = useState<Incoming[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [evidence, setEvidence] = useState("");
  const [consent, setConsent] = useState("unknown");
  const [verified, setVerified] = useState(false);
  const [owned, setOwned] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [subject, setSubject] = useState("Gmail connection test");
  const [body, setBody] = useState("This is a connection test from my_agent. Please reply so I can verify that replies are matched to this conversation.");
  const [purpose, setPurpose] = useState("test");
  const [incomingId, setIncomingId] = useState<string | null>(null);
  const [replyPreviewId, setReplyPreviewId] = useState<string | null>(null);
  function selectReply(mail: Incoming, preview?: ReplyPreview) {
    setPurpose("reply"); setIncomingId(mail.id); setReplyPreviewId(preview?.id || null); setRecipient(mail.sender);
    setSubject(preview?.subject || (mail.subject.toLowerCase().startsWith("re:") ? mail.subject : `Re: ${mail.subject}`));
    setBody(preview?.body || "");
    document.getElementById("gmail-reply-draft")?.scrollIntoView({ behavior: "smooth" });
  }

  async function refresh() {
    const [state, people, messages] = await Promise.all([
      apiRequest("/api/gmail/status"), apiRequest("/api/gmail/contacts"), apiRequest("/api/gmail/inbox"),
    ]);
    setStatus(state); setContacts(people.contacts); setInbox(messages.messages.slice().reverse());
  }
  useEffect(() => { refresh().catch((e) => setError(e.message)); }, []);
  async function action(call: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setNotice("");
    try { await call(); await refresh(); setNotice(success); }
    catch (e) { setError(e instanceof Error ? e.message : "Operation failed"); }
    finally { setBusy(false); }
  }
  function saveContact(e: FormEvent) {
    e.preventDefault();
    void action(() => apiRequest(`/api/gmail/contacts/${encodeURIComponent(email)}`, {
      method: "PUT", body: JSON.stringify({ verified, consent, evidence, test_recipient: owned }),
    }), "Contact eligibility saved. This did not send an email.");
  }
  function draft(e: FormEvent) {
    e.preventDefault();
    void action(() => apiRequest("/api/gmail/drafts", { method: "POST", body: JSON.stringify({
      recipient, subject, body, purpose, incoming_id: purpose === "reply" ? incomingId : undefined, reply_preview_id: purpose === "reply" ? replyPreviewId : undefined,
    }) }), "Draft saved. Open Approval Queue to review it and explicitly send.");
  }
  const input = "mt-2 block w-full min-w-0 rounded-lg border border-slate-300 px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500";
  const button = "rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
  return <section className="space-y-6 max-w-5xl">
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {notice && <p role="status" className="text-sm text-emerald-700">{notice}</p>}
    <div className="rounded-xl border border-slate-200 p-5 space-y-3">
      <h2 className="font-semibold">Gmail connection</h2>
      <p className="text-sm">{status ? `${status.configured ? "Credentials loaded" : "Not configured"} · ${status.connection?.status || "Not verified yet"} ${status.connection?.email || ""}` : "Loading connection status…"}</p>
      <p className="text-sm text-slate-600">Uses the Gmail credentials configured on your computer. If you need to reconnect, follow <code>GMAIL_SETUP.md</code>.</p>
      <div className="flex flex-wrap gap-2">
        <button disabled={busy} className={button} onClick={() => action(() => apiRequest("/api/gmail/verify", { method: "POST" }), "Mailbox verified. No email was sent.")}>Verify connection</button>
        <button disabled={busy} className={button} onClick={() => action(() => apiRequest("/api/gmail/sync", { method: "POST" }), "Sync finished. Recorded conversations refreshed.")}>Sync replies</button>
      </div>
      <p className="text-xs text-slate-500">Sync reads recorded conversations, including read and archived replies. Local response-template drafting is {status?.reply_drafting_enabled ? "enabled" : "off"}. Testing-mode Google authorisation can expire after seven days.</p>
    </div>
    <div className="grid gap-6 xl:grid-cols-2 items-start">
    <form onSubmit={saveContact} className="rounded-xl border border-slate-200 p-5 space-y-3">
      <h2 className="font-semibold">Contact eligibility</h2>
      <label className="block text-sm">Email<input type="email" required className={input} value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label className="block text-sm">Evidence of address ownership, verification or permission<textarea className={input} required rows={3} value={evidence} onChange={(e) => setEvidence(e.target.value)} /></label>
      <label className="flex items-start gap-3 text-sm leading-relaxed"><input type="checkbox" className="mt-1 h-4 w-4 shrink-0" checked={owned} onChange={(e) => setOwned(e.target.checked)} />I control this address and will use it for connection tests.</label>
      <label className="flex items-start gap-3 text-sm leading-relaxed"><input type="checkbox" className="mt-1 h-4 w-4 shrink-0" checked={verified} onChange={(e) => setVerified(e.target.checked)} />I have verified this contact address against the evidence recorded above.</label>
      <label className="block text-sm">Marketing permission<select className={input} value={consent} onChange={(e) => setConsent(e.target.value)}>
        <option value="unknown">Not recorded</option><option value="granted">Granted, with evidence above</option><option value="declined">Declined</option><option value="unsubscribed">Do not contact</option>
      </select></label>
      <button disabled={busy} className={button}>Save contact</button>
      <ul className="space-y-1 text-xs text-slate-600">{contacts.map((c) => <li key={c.email}>{c.email} · {c.consent} · {c.test_recipient ? "owned test address" : c.verified ? "verified address" : "unverified"}</li>)}</ul>
    </form>
    <form id="gmail-reply-draft" onSubmit={draft} className="rounded-xl border border-slate-200 p-5 space-y-3">
      <h2 className="font-semibold">Create a draft</h2>
      <p className="text-sm text-slate-500">For new business outreach, review a candidate in Leads and prepare its draft there.</p>
      <label className="block text-sm">Purpose<select className={input} value={purpose} onChange={(e) => { setPurpose(e.target.value); setIncomingId(null); setReplyPreviewId(null); }}>
        <option value="test">Connection test to an address I control</option><option value="reply">Reply to the message selected below</option>
      </select></label>
      {purpose === "reply" && <p className="text-xs">{incomingId ? "Reply selected. Recipient and thread will be taken from the saved incoming message." : "Select Reply on an incoming message below."}</p>}
      <label className="block text-sm">Recipient<input className={input} type="email" required readOnly={purpose === "reply"} value={recipient} onChange={(e) => setRecipient(e.target.value)} /></label>
      <label className="block text-sm">Subject<input className={input} required readOnly={purpose === "reply"} value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
      {replyPreviewId && <p className="text-xs text-slate-500">Response template selected. Edit it to answer the actual question before saving for approval. Regenerate if the incoming reply or portfolio changes.</p>}
      <label className="block text-sm">Message<textarea className={input} required rows={5} value={body} onChange={(e) => setBody(e.target.value)} /></label>
      <button disabled={busy || (purpose === "reply" && !incomingId)} className={button}>Save for approval</button>
    </form>
    </div>
    <div className="rounded-xl border border-slate-200 p-5 space-y-4">
      <h2 className="font-semibold">Replies in recorded conversations</h2>
      {inbox.length === 0 && <p className="text-sm text-slate-500">No incoming messages recorded yet. Send your test draft, reply from the other inbox, then sync.</p>}
      <p className="text-sm text-slate-500">Reply suggestions and response templates run locally without model or research credits. Sync never sends them; approval is always required.</p>
      {inbox.map((mail) => <ReplyReview key={mail.id} mail={mail} busy={busy}
        onManual={() => { selectReply(mail); setNotice("Reply selected. Write the response in Create a draft above."); }}
        onTemplate={() => void action(async () => { const preview: ReplyPreview = await apiRequest(`/api/gmail/inbox/${encodeURIComponent(mail.id)}/reply-preview`, { method: "POST" }); selectReply(mail, preview); }, "Response template prepared. Edit it in Create a draft, then save for approval.")}
        onConfirm={(outcome, note) => void action(() => apiRequest(`/api/gmail/inbox/${encodeURIComponent(mail.id)}/outcome`, { method: "PUT", body: JSON.stringify({ fingerprint: mail.reply_assessment.fingerprint, outcome, note }) }), "Conversation outcome confirmed. Refresh Reports to include it; saved report snapshots keep their original values.")}
        onRetry={() => void action(() => apiRequest(`/api/gmail/inbox/${encodeURIComponent(mail.id)}/retry`, { method: "POST" }), "Incoming message processing retried.")}
      />)}
    </div>
  </section>;
}
