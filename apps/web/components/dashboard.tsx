"use client";

import React, { useState, useEffect } from "react";
import {
  Mail, Reply, TrendingUp, Users, CheckCircle2, Eye, Clock,
  AlertCircle, ChevronDown, ChevronRight, ArrowUpRight, Sparkles,
  ShieldAlert, RefreshCw, XCircle, Edit3, Database, Trash2, Search
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────
interface EmailLog {
  id: string; recipient: string; company: string; subject: string;
  dateSent: string; status: "Sent" | "Opened" | "Responded" | "Bounced";
  thread?: string; reply?: string;
}

interface OutreachMetrics {
  totalEmailsSent: number; totalResponsesReceived: number;
  responseRatePercent: number; activeLeadsInPipeline: number;
}

interface MemoryRecord {
  id: string; namespace: string; key: string;
  value: { content?: string }; created_at?: string;
}

interface PendingAction {
  thread_id: string; intent: string;
  email_input?: { sender?: string; subject?: string; body?: string };
  draft_response: string; status: string;
}

// ─── Mock Data ────────────────────────────────────────────────────
const METRICS: OutreachMetrics = {
  totalEmailsSent: 284, totalResponsesReceived: 91,
  responseRatePercent: 32.0, activeLeadsInPipeline: 47
};

const LOGS: EmailLog[] = [
  { id: "1", recipient: "cto@techcorp.io", company: "TechCorp", subject: "Enterprise License Proposal", dateSent: "2026-08-08", status: "Responded", thread: "We are interested in the 50-seat enterprise license.", reply: "Would love to schedule a call Friday 10am EST?" },
  { id: "2", recipient: "founder@startupco.com", company: "StartupCo", subject: "AI Agent Pilot Invitation", dateSent: "2026-08-07", status: "Opened", thread: "Inviting 10 startups to our 14-day AI pilot program." },
  { id: "3", recipient: "ops@retailgiant.com", company: "RetailGiant", subject: "Customer Support Automation", dateSent: "2026-08-06", status: "Responded", thread: "Our agent handles tier-1 support with full escalation controls.", reply: "Can you send a case study or demo video first?" },
  { id: "4", recipient: "partnerships@financeplus.co", company: "FinancePlus", subject: "Compliance Automation Partnership", dateSent: "2026-08-05", status: "Sent", thread: "Exploring a compliance automation partnership." },
  { id: "5", recipient: "ceo@healthsystem.org", company: "HealthSystem", subject: "Document Processing Agent", dateSent: "2026-08-04", status: "Bounced", thread: "Our agent automates medical document intake." },
  { id: "6", recipient: "tech@mediahouse.tv", company: "MediaHouse", subject: "Real-time Transcription Agent", dateSent: "2026-08-03", status: "Responded", thread: "AI transcription & summary in near real-time.", reply: "Exactly what we need for our production pipeline. Let's talk." },
];

const MEMORIES: MemoryRecord[] = [
  { id: "m1", namespace: "users:cto@enterprise-client.com", key: "pref_seats", value: { content: "Client requested 50 seat enterprise license pricing." }, created_at: "2 hours ago" },
  { id: "m2", namespace: "users:support@tier1.io", key: "pref_lang", value: { content: "Preferred communication language: English (Formal)." }, created_at: "1 day ago" },
  { id: "m3", namespace: "users:ops@retailgiant.com", key: "channel_pref", value: { content: "Prefers email over phone. Business hours: 9-5 EST." }, created_at: "3 days ago" },
];

const APPROVALS: PendingAction[] = [
  { thread_id: "outreach_mikes_auto_repair", intent: "sales", email_input: { sender: "mike@mikesauto.com", subject: "Web Presence Proposal", body: "Your business was found without a website." }, draft_response: "Hi Mike's Auto Repair team,\n\nWe help local businesses get a professional website quickly. Would love to offer you a free 30-minute strategy call.\n\nBest,\nWeb Dev Team", status: "pending" },
  { thread_id: "outreach_sunrise_bakery", intent: "sales", email_input: { sender: "hello@sunrisebakery.biz", subject: "Grow Your Bakery Online", body: "Sunrise Bakery & Café is missing an online presence." }, draft_response: "Hi Sunrise Bakery & Café,\n\nAn attractive website could bring dozens of new customers each week. Let's build yours.\n\nBest,\nWeb Dev Team", status: "pending" },
];

// ─── Status Config ────────────────────────────────────────────────
const STATUS_CFG = {
  Responded: { icon: CheckCircle2, cls: "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" },
  Opened: { icon: Eye, cls: "text-blue-400 bg-blue-400/10 border-blue-400/20" },
  Sent: { icon: Clock, cls: "text-white/40 bg-white/[0.04] border-white/[0.08]" },
  Bounced: { icon: AlertCircle, cls: "text-rose-400 bg-rose-400/10 border-rose-400/20" },
};

// ─── Shared Primitives ────────────────────────────────────────────
const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = "" }) => (
  <div className={`rounded-2xl border border-white/[0.06] bg-[#1a1d27] p-5 ${className}`}>{children}</div>
);

const SectionTitle: React.FC<{ icon: React.ElementType; title: string; sub: string; accent?: string }> = ({ icon: Icon, title, sub, accent = "text-indigo-400 bg-indigo-400/10 border-indigo-400/20" }) => (
  <div className="flex items-center gap-3">
    <div className={`rounded-xl border p-2 ${accent}`}><Icon className="h-4 w-4" /></div>
    <div><p className="text-sm font-semibold text-white/90">{title}</p><p className="text-[11px] text-white/30">{sub}</p></div>
  </div>
);

// ─── Overview Metrics ──────────────────────────────────────────────
const MetricCards: React.FC = () => {
  const cards = [
    { label: "Total Emails Sent", val: METRICS.totalEmailsSent.toLocaleString(), delta: "+14.2%", icon: Mail, color: "from-blue-500/20 to-blue-600/5 border-blue-500/20", dot: "bg-blue-400" },
    { label: "Responses Received", val: METRICS.totalResponsesReceived.toLocaleString(), delta: "+8.5%", icon: Reply, color: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20", dot: "bg-emerald-400" },
    { label: "Response Rate", val: `${METRICS.responseRatePercent}%`, delta: "vs 21% avg", icon: TrendingUp, color: "from-violet-500/20 to-violet-600/5 border-violet-500/20", dot: "bg-violet-400" },
    { label: "Active Leads", val: METRICS.activeLeadsInPipeline.toLocaleString(), delta: "In pipeline", icon: Users, color: "from-amber-500/20 to-amber-600/5 border-amber-500/20", dot: "bg-amber-400" },
  ];
  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div key={i} className={`rounded-2xl border bg-gradient-to-br p-5 ${c.color}`}>
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-white/40">{c.label}</p>
              <Icon className="h-4 w-4 text-white/20" />
            </div>
            <p className="mt-3 text-3xl font-bold tabular-nums text-white">{c.val}</p>
            <p className={`mt-2 flex items-center gap-1.5 text-[11px] font-medium`}>
              <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} /><span className="text-white/40">{c.delta}</span>
            </p>
          </div>
        );
      })}
    </div>
  );
};

// ─── Status Breakdown ─────────────────────────────────────────────
const StatusBreakdown: React.FC = () => {
  const rows = [
    { label: "Responded", n: 91, pct: 32, color: "bg-emerald-500" },
    { label: "Opened", n: 76, pct: 27, color: "bg-blue-500" },
    { label: "Sent (No Open)", n: 104, pct: 37, color: "bg-white/20" },
    { label: "Bounced", n: 13, pct: 4, color: "bg-rose-500" },
  ];
  return (
    <Card>
      <SectionTitle icon={Sparkles} title="Status Breakdown" sub="Email engagement distribution" accent="text-violet-400 bg-violet-400/10 border-violet-400/20" />
      <div className="mt-5 space-y-3.5">
        {rows.map((r) => (
          <div key={r.label}>
            <div className="flex justify-between text-[11px] mb-1.5">
              <span className="font-medium text-white/60">{r.label}</span>
              <span className="tabular-nums text-white/30">{r.n}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
              <div className={`h-full rounded-full ${r.color} transition-all duration-700`} style={{ width: `${r.pct}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};

// ─── Weekly Bar Chart ─────────────────────────────────────────────
const WeeklyChart: React.FC = () => {
  const data = [30, 42, 38, 55, 48, 62, 71];
  const max = Math.max(...data);
  return (
    <Card>
      <SectionTitle icon={TrendingUp} title="Weekly Send Volume" sub="Emails dispatched per day" accent="text-emerald-400 bg-emerald-400/10 border-emerald-400/20" />
      <div className="mt-5 flex items-end gap-2 h-24">
        {data.map((v, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
            <div className="w-full rounded-t-md bg-indigo-500/30 hover:bg-indigo-400/50 transition-colors" style={{ height: `${(v / max) * 88}px` }} />
            <span className="text-[9px] text-white/20">{["M","T","W","T","F","S","S"][i]}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};

// ─── Email Logs Table ────────────────────────────────────────────
const EmailLogsPanel: React.FC<{ filter?: string }> = ({ filter = "all" }) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [activeFilter, setFilter] = useState(filter);
  const filters = ["all", "responded", "opened", "sent"];
  const filtered = LOGS.filter(l => activeFilter === "all" || l.status.toLowerCase() === activeFilter);

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#1a1d27] overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <SectionTitle icon={Mail} title="Outreach Logs" sub={`${filtered.length} records · click to expand thread`} />
        <div className="flex gap-1 rounded-xl bg-white/[0.04] p-1">
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold capitalize transition-all ${activeFilter === f ? "bg-indigo-500/20 text-indigo-300 shadow" : "text-white/30 hover:text-white/50"}`}>{f}</button>
          ))}
        </div>
      </div>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-white/[0.04] bg-white/[0.02]">
            <th className="w-8" />
            {["Recipient","Company","Subject","Date","Status"].map(h => (
              <th key={h} className="px-3 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-white/20">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map(log => {
            const open = expanded === log.id;
            const { icon: StatusIcon, cls } = STATUS_CFG[log.status];
            return (
              <React.Fragment key={log.id}>
                <tr onClick={() => setExpanded(open ? null : log.id)} className={`border-b border-white/[0.03] cursor-pointer transition-colors ${open ? "bg-indigo-500/5" : "hover:bg-white/[0.02]"}`}>
                  <td className="pl-4">{open ? <ChevronDown className="h-3.5 w-3.5 text-indigo-400" /> : <ChevronRight className="h-3.5 w-3.5 text-white/20" />}</td>
                  <td className="px-3 py-3.5 font-medium text-white/80">{log.recipient}</td>
                  <td className="px-3 py-3.5 font-semibold text-white/60">{log.company}</td>
                  <td className="px-3 py-3.5 max-w-[240px] truncate text-white/40">{log.subject}</td>
                  <td className="px-3 py-3.5 tabular-nums text-white/30">{log.dateSent}</td>
                  <td className="px-3 py-3.5">
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${cls}`}>
                      <StatusIcon className="h-3 w-3" />{log.status}
                    </span>
                  </td>
                </tr>
                {open && (
                  <tr className="border-b border-indigo-500/10 bg-indigo-500/[0.03]">
                    <td colSpan={6} className="px-8 py-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-white/20 mb-2">Thread Sent</p>
                          <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] p-3.5 text-[12px] text-white/60 leading-relaxed">{log.thread || "—"}</div>
                        </div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-white/20 mb-2">Client Reply</p>
                          {log.reply
                            ? <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.06] p-3.5 text-[12px] text-emerald-300/80 leading-relaxed">{log.reply}</div>
                            : <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 text-[12px] text-white/20 italic">No reply received yet.</div>}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

// ─── Approval Queue ───────────────────────────────────────────────
const ApprovalPanel: React.FC = () => {
  const [queue, setQueue] = useState(APPROVALS);
  const [editing, setEditing] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const dismiss = (tid: string) => setQueue(q => q.filter(a => a.thread_id !== tid));

  return (
    <div className="space-y-4">
      <SectionTitle icon={ShieldAlert} title="Human Approval Queue" sub="Review agent-drafted emails before they are dispatched" accent="text-amber-400 bg-amber-400/10 border-amber-400/20" />
      {queue.length === 0 ? (
        <Card className="py-10 text-center">
          <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400/40 mb-2" />
          <p className="text-sm font-semibold text-white/40">Queue is clear</p>
          <p className="text-[11px] text-white/20 mt-1">All agent actions have been reviewed.</p>
        </Card>
      ) : queue.map(item => (
        <Card key={item.thread_id} className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400/70 flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5" /> {item.intent}
            </span>
            <span className="font-mono text-[10px] text-white/20">{item.thread_id}</span>
          </div>
          {item.email_input && (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3 text-[12px] space-y-1">
              <p className="font-semibold text-white/60">To: {item.email_input.sender}</p>
              <p className="text-white/40">Subject: {item.email_input.subject}</p>
            </div>
          )}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-white/20 font-bold mb-2">Draft Response</p>
            {editing === item.thread_id
              ? <textarea value={editText} onChange={e => setEditText(e.target.value)} rows={5} className="w-full rounded-xl border border-indigo-500/30 bg-indigo-500/[0.06] p-3 text-[12px] text-white/80 outline-none resize-none" />
              : <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 text-[12px] text-white/60 leading-relaxed whitespace-pre-wrap">{item.draft_response}</div>}
          </div>
          <div className="flex justify-end gap-2 pt-1">
            {editing === item.thread_id ? (
              <>
                <button onClick={() => dismiss(item.thread_id)} className="rounded-xl bg-indigo-500 hover:bg-indigo-600 px-4 py-2 text-[12px] font-bold text-white transition-colors shadow">Save & Send</button>
                <button onClick={() => setEditing(null)} className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2 text-[12px] font-medium text-white/40 hover:text-white/60 transition-colors">Cancel</button>
              </>
            ) : (
              <>
                <button onClick={() => dismiss(item.thread_id)} className="flex items-center gap-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 px-4 py-2 text-[12px] font-bold text-emerald-300 transition-colors">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approve & Send
                </button>
                <button onClick={() => { setEditing(item.thread_id); setEditText(item.draft_response); }} className="flex items-center gap-1.5 rounded-xl border border-indigo-500/20 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-2 text-[12px] font-bold text-indigo-300 transition-colors">
                  <Edit3 className="h-3.5 w-3.5" /> Edit
                </button>
                <button onClick={() => dismiss(item.thread_id)} className="flex items-center gap-1.5 rounded-xl border border-rose-500/20 bg-rose-500/[0.06] hover:bg-rose-500/10 px-3 py-2 text-[12px] font-bold text-rose-400 transition-colors">
                  <XCircle className="h-3.5 w-3.5" /> Reject
                </button>
              </>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
};

// ─── Memory Viewer ────────────────────────────────────────────────
const MemoryPanel: React.FC = () => {
  const [memories, setMemories] = useState(MEMORIES);
  const [query, setQuery] = useState("");
  return (
    <div className="space-y-4">
      <SectionTitle icon={Database} title="Vector Memory Bank" sub="Inspect facts stored in Supabase pgvector" accent="text-purple-400 bg-purple-400/10 border-purple-400/20" />
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 h-3.5 w-3.5 text-white/20" />
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Semantic search memory..." className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] pl-9 pr-4 py-2.5 text-[12px] text-white/70 placeholder:text-white/20 outline-none focus:border-purple-500/40 transition-colors" />
        </div>
        <button className="flex items-center gap-1.5 rounded-xl border border-purple-500/20 bg-purple-500/10 px-4 py-2.5 text-[12px] font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors">
          <Sparkles className="h-3.5 w-3.5" /> Query
        </button>
      </div>
      <div className="space-y-2">
        {memories.map(m => (
          <div key={m.id} className="flex items-start justify-between gap-4 rounded-xl border border-white/[0.04] bg-white/[0.02] px-4 py-3.5 hover:border-purple-500/20 transition-colors">
            <div className="space-y-1 min-w-0">
              <p className="font-mono text-[10px] font-semibold text-purple-400/70">{m.namespace} · {m.key}</p>
              <p className="text-[12px] text-white/70 font-medium">{m.value.content}</p>
              <p className="text-[10px] text-white/20">{m.created_at}</p>
            </div>
            <button onClick={() => setMemories(ms => ms.filter(x => x.id !== m.id))} className="shrink-0 rounded-lg p-1.5 text-white/20 hover:text-rose-400 hover:bg-rose-400/10 transition-colors">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Settings Stub ────────────────────────────────────────────────
const SettingsPanel: React.FC = () => (
  <div className="space-y-4">
    <SectionTitle icon={Sparkles} title="Platform Settings" sub="Configure agent behaviour and API credentials" accent="text-white/40 bg-white/[0.04] border-white/[0.08]" />
    {[
      { label: "GROQ_API_KEY", placeholder: "gsk_••••••••" },
      { label: "GEMINI_API_KEY", placeholder: "AIza••••••••" },
      { label: "TAVILY_API_KEY", placeholder: "tvly-••••••••" },
      { label: "AGENT_API_KEY", placeholder: "agent-secret-key" },
    ].map(f => (
      <Card key={f.label}>
        <label className="block text-[11px] font-semibold uppercase tracking-wider text-white/30 mb-2">{f.label}</label>
        <input type="password" placeholder={f.placeholder} className="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-2.5 text-[12px] text-white/60 font-mono outline-none focus:border-indigo-500/40 transition-colors" />
      </Card>
    ))}
    <button className="rounded-xl bg-indigo-500 hover:bg-indigo-600 px-5 py-2.5 text-[12px] font-bold text-white transition-colors shadow">Save Settings</button>
  </div>
);

// ─── Main Dashboard ───────────────────────────────────────────────
type NavTab = "overview" | "logs" | "approvals" | "memory" | "settings";

export const Dashboard: React.FC<{ activeTab: NavTab }> = ({ activeTab }) => {
  const heading: Record<NavTab, { title: string; sub: string }> = {
    overview: { title: "Email Outreach Command Centre", sub: "Real-time monitoring of agent-drafted campaigns, responses, and pipeline conversion" },
    logs: { title: "Outreach Logs", sub: "Full email log with recipient details, thread content, and client replies" },
    approvals: { title: "Approval Queue", sub: "Review and approve outgoing drafts before they are dispatched" },
    memory: { title: "Memory Bank", sub: "Inspect, search, and manage continuous facts stored in Supabase pgvector" },
    settings: { title: "Settings", sub: "Configure agent behaviour, credentials, and pipeline preferences" },
  };
  const h = heading[activeTab];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-lg font-bold text-white/90">{h.title}</h1>
        <p className="mt-0.5 text-[12px] text-white/30">{h.sub}</p>
      </div>

      {activeTab === "overview" && (
        <>
          <MetricCards />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <StatusBreakdown />
            <WeeklyChart />
          </div>
          <EmailLogsPanel />
        </>
      )}
      {activeTab === "logs" && <EmailLogsPanel />}
      {activeTab === "approvals" && <ApprovalPanel />}
      {activeTab === "memory" && <MemoryPanel />}
      {activeTab === "settings" && <SettingsPanel />}
    </div>
  );
};
