"use client";

import React, { useContext, useState } from "react";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import * as Avatar from "@radix-ui/react-avatar";
import * as Separator from "@radix-ui/react-separator";
import {
  Mail, Reply, TrendingUp, Users, CheckCircle2, Eye,
  Clock, AlertCircle, ChevronDown, ChevronRight,
  ShieldAlert, XCircle, Edit3, Database, Trash2,
  Search, Sparkles, Settings, ArrowUpRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TabContext } from "@/components/app-shell";

// ─── Types ────────────────────────────────────────────────────────
type Status = "Sent" | "Opened" | "Responded" | "Bounced";
type NavTab = "overview" | "logs" | "approvals" | "memory" | "settings";

interface EmailLog {
  id: string; recipient: string; company: string;
  subject: string; dateSent: string; status: Status;
  thread?: string; reply?: string;
}

// ─── Mock Data ────────────────────────────────────────────────────
const METRICS = [
  { label: "Emails Sent",    value: "284", delta: "+14.2%", positive: true,  icon: Mail,        color: "text-blue-400",   bg: "bg-blue-400/10"    },
  { label: "Responses",      value: "91",  delta: "+8.5%",  positive: true,  icon: Reply,       color: "text-emerald-400",bg: "bg-emerald-400/10" },
  { label: "Response Rate",  value: "32%", delta: "vs 21%", positive: true,  icon: TrendingUp,  color: "text-violet-400", bg: "bg-violet-400/10"  },
  { label: "Active Leads",   value: "47",  delta: "pipeline",positive: null, icon: Users,       color: "text-amber-400",  bg: "bg-amber-400/10"   },
];

const AREA_DATA = [
  { day: "Mon", sent: 30, replied: 8  },
  { day: "Tue", sent: 42, replied: 14 },
  { day: "Wed", sent: 38, replied: 11 },
  { day: "Thu", sent: 55, replied: 18 },
  { day: "Fri", sent: 48, replied: 16 },
  { day: "Sat", sent: 62, replied: 20 },
  { day: "Sun", sent: 71, replied: 24 },
];

const BAR_DATA = [
  { status: "Responded", count: 91,  fill: "#10b981" },
  { status: "Opened",    count: 76,  fill: "#6366f1" },
  { status: "Sent",      count: 104, fill: "#475569" },
  { status: "Bounced",   count: 13,  fill: "#f43f5e" },
];

const LOGS: EmailLog[] = [
  { id:"1", recipient:"cto@techcorp.io",        company:"TechCorp",    subject:"Enterprise License Proposal",      dateSent:"2026-08-08", status:"Responded", thread:"Interested in the 50-seat license.",   reply:"Let's connect Friday 10am EST?" },
  { id:"2", recipient:"founder@startupco.com",  company:"StartupCo",   subject:"AI Agent Pilot Invitation",        dateSent:"2026-08-07", status:"Opened",    thread:"14-day AI pilot program invitation."                                    },
  { id:"3", recipient:"ops@retailgiant.com",    company:"RetailGiant", subject:"Customer Support Automation",      dateSent:"2026-08-06", status:"Responded", thread:"Tier-1 support with full escalation.", reply:"Send a case study first?" },
  { id:"4", recipient:"partnerships@finplus.co",company:"FinancePlus", subject:"Compliance Automation Partnership",dateSent:"2026-08-05", status:"Sent",      thread:"Exploring compliance automation."                                       },
  { id:"5", recipient:"ceo@healthsys.org",      company:"HealthSystem",subject:"Document Processing Agent",       dateSent:"2026-08-04", status:"Bounced",   thread:"Automates medical document intake."                                     },
  { id:"6", recipient:"tech@mediahouse.tv",     company:"MediaHouse",  subject:"Real-time Transcription Agent",   dateSent:"2026-08-03", status:"Responded", thread:"Near real-time AI transcription.",     reply:"Exactly what we need!" },
];

const STATUS_CFG: Record<Status, { label: string; icon: React.ElementType; cls: string }> = {
  Responded: { label:"Responded", icon:CheckCircle2, cls:"text-emerald-400 bg-emerald-400/10 border-emerald-400/25" },
  Opened:    { label:"Opened",    icon:Eye,          cls:"text-blue-400 bg-blue-400/10 border-blue-400/25"          },
  Sent:      { label:"Sent",      icon:Clock,        cls:"text-slate-400 bg-slate-400/10 border-slate-400/20"       },
  Bounced:   { label:"Bounced",   icon:AlertCircle,  cls:"text-rose-400 bg-rose-400/10 border-rose-400/25"         },
};

const APPROVALS = [
  { id:"a1", company:"Mike's Auto Repair",  to:"mike@mikesauto.com",    subject:"Web Presence Proposal",  body:"Hi Mike's Auto Repair,\n\nWe help local businesses get online fast. Claim your free 30-min strategy call.\n\nBest,\nWeb Dev Team" },
  { id:"a2", company:"Sunrise Bakery",      to:"hello@sunrisebakery.biz",subject:"Grow Your Bakery Online",body:"Hi Sunrise Bakery,\n\nA professional website could bring dozens of new customers weekly. Let's build yours.\n\nBest,\nWeb Dev Team" },
];

const MEMORIES = [
  { id:"m1", ns:"users:cto@enterprise.com",  key:"pref_seats",    value:"Client requested 50-seat enterprise pricing.",  age:"2 hours ago" },
  { id:"m2", ns:"users:support@tier1.io",    key:"pref_lang",     value:"Preferred language: English (Formal).",          age:"1 day ago"   },
  { id:"m3", ns:"users:ops@retailgiant.com", key:"channel_pref",  value:"Prefers email. Business hours: 9–5 EST.",        age:"3 days ago"  },
];

// ─── Shared UI Primitives ─────────────────────────────────────────
function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-xl border border-border bg-card p-5 shadow-sm", className)}>
      {children}
    </div>
  );
}

function Badge({ status }: { status: Status }) {
  const { icon: Icon, label, cls } = STATUS_CFG[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold", cls)}>
      <Icon className="h-3 w-3" />{label}
    </span>
  );
}

// ─── Custom Tooltip ───────────────────────────────────────────────
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold text-foreground">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.stroke || p.fill }} className="capitalize">
          {p.dataKey}: <span className="font-bold">{p.value}</span>
        </p>
      ))}
    </div>
  );
}

// ─── Overview Panel ───────────────────────────────────────────────
function OverviewPanel() {
  return (
    <div className="space-y-5">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {METRICS.map((m) => {
          const Icon = m.icon;
          return (
            <Card key={m.label} className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{m.label}</p>
                <div className={cn("rounded-lg p-2", m.bg)}>
                  <Icon className={cn("h-4 w-4", m.color)} />
                </div>
              </div>
              <div>
                <p className="text-3xl font-bold tabular-nums text-foreground">{m.value}</p>
                <p className={cn("mt-1 flex items-center gap-1 text-xs font-medium",
                  m.positive === true ? "text-emerald-400" : m.positive === false ? "text-rose-400" : "text-muted-foreground"
                )}>
                  {m.positive === true && <ArrowUpRight className="h-3 w-3" />}
                  {m.delta}
                </p>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Area chart — spans 3 */}
        <Card className="lg:col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-foreground">Weekly Send Volume</p>
              <p className="text-xs text-muted-foreground">Emails sent vs replies received</p>
            </div>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={AREA_DATA} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0.03} />
                </linearGradient>
                <linearGradient id="replyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 32% 17%)" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "hsl(218 11% 55%)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(218 11% 55%)" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="sent"    stroke="#6366f1" fill="url(#sentGrad)"  strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="replied" stroke="#10b981" fill="url(#replyGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Bar chart — spans 2 */}
        <Card className="lg:col-span-2 space-y-3">
          <div>
            <p className="text-sm font-semibold text-foreground">Status Breakdown</p>
            <p className="text-xs text-muted-foreground">Email engagement by status</p>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={BAR_DATA} margin={{ top: 4, right: 4, bottom: 0, left: -28 }} barSize={20}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 32% 17%)" horizontal={false} />
              <XAxis dataKey="status" tick={{ fontSize: 9, fill: "hsl(218 11% 55%)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(218 11% 55%)" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}
                   fill="#6366f1"
                   /* per-bar colour via Cell equivalent handled by fill array */
              >
                {BAR_DATA.map((entry, i) => (
                  <rect key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Email Logs */}
      <LogsPanel />
    </div>
  );
}

// ─── Logs Panel ───────────────────────────────────────────────────
function LogsPanel() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter]     = useState<"all" | Status>("all");
  const filters: ("all" | Status)[] = ["all", "Responded", "Opened", "Sent", "Bounced"];
  const rows = filter === "all" ? LOGS : LOGS.filter(l => l.status === filter);

  return (
    <Card className="p-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2"><Mail className="h-4 w-4 text-primary" /></div>
          <div>
            <p className="text-sm font-semibold text-foreground">Outreach Logs</p>
            <p className="text-xs text-muted-foreground">{rows.length} records · click row to expand</p>
          </div>
        </div>
        {/* Filter pills */}
        <div className="flex gap-1 rounded-lg bg-secondary p-1">
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn("px-3 py-1 rounded-md text-[11px] font-semibold capitalize transition-all",
                filter === f ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="w-8" />
            {["Recipient","Company","Subject","Date","Status"].map(h => (
              <th key={h} className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(log => {
            const open = expanded === log.id;
            return (
              <React.Fragment key={log.id}>
                <tr onClick={() => setExpanded(open ? null : log.id)}
                  className={cn("border-b border-border cursor-pointer transition-colors",
                    open ? "bg-primary/5" : "hover:bg-muted/40"
                  )}>
                  <td className="pl-4 py-3">
                    {open ? <ChevronDown className="h-3.5 w-3.5 text-primary" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
                  </td>
                  <td className="px-4 py-3 font-medium text-foreground">{log.recipient}</td>
                  <td className="px-4 py-3 font-semibold text-muted-foreground">{log.company}</td>
                  <td className="px-4 py-3 max-w-[240px] truncate text-muted-foreground">{log.subject}</td>
                  <td className="px-4 py-3 tabular-nums text-muted-foreground">{log.dateSent}</td>
                  <td className="px-4 py-3"><Badge status={log.status} /></td>
                </tr>
                {open && (
                  <tr className="border-b border-primary/10 bg-primary/[0.03]">
                    <td colSpan={6} className="px-8 py-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Thread Sent</p>
                          <div className="rounded-lg border border-border bg-secondary/50 p-3.5 text-xs text-muted-foreground leading-relaxed">
                            {log.thread || "—"}
                          </div>
                        </div>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Client Reply</p>
                          {log.reply
                            ? <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/8 p-3.5 text-xs text-emerald-300 leading-relaxed">{log.reply}</div>
                            : <div className="rounded-lg border border-border bg-secondary/30 p-3.5 text-xs text-muted-foreground italic">No reply yet.</div>
                          }
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
    </Card>
  );
}

// ─── Approval Panel ───────────────────────────────────────────────
function ApprovalPanel() {
  const [queue, setQueue]   = useState(APPROVALS);
  const [editing, setEdit]  = useState<string | null>(null);
  const [text, setText]     = useState("");
  const dismiss = (id: string) => setQueue(q => q.filter(a => a.id !== id));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-amber-400/10 p-2"><ShieldAlert className="h-4 w-4 text-amber-400" /></div>
        <div>
          <p className="text-sm font-semibold text-foreground">Human Approval Queue</p>
          <p className="text-xs text-muted-foreground">Review agent-drafted emails before dispatch</p>
        </div>
      </div>

      {queue.length === 0 ? (
        <Card className="py-14 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400/30 mb-3" />
          <p className="text-sm font-semibold text-muted-foreground">Queue is clear</p>
          <p className="text-xs text-muted-foreground/60 mt-1">All actions reviewed.</p>
        </Card>
      ) : queue.map(item => (
        <Card key={item.id} className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Avatar.Root className="h-8 w-8">
                <Avatar.Fallback className="h-8 w-8 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                  {item.company[0]}
                </Avatar.Fallback>
              </Avatar.Root>
              <div>
                <p className="text-sm font-semibold text-foreground">{item.company}</p>
                <p className="text-xs text-muted-foreground">{item.to}</p>
              </div>
            </div>
            <span className="rounded-full border border-amber-400/25 bg-amber-400/10 px-2.5 py-1 text-[10px] font-bold text-amber-400">
              PENDING REVIEW
            </span>
          </div>

          <Separator.Root className="h-px bg-border" />

          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-muted-foreground mb-2">
              Subject: {item.subject}
            </p>
            {editing === item.id
              ? <textarea value={text} onChange={e => setText(e.target.value)} rows={5}
                  className="w-full rounded-lg border border-primary/30 bg-primary/5 p-3 text-xs text-foreground outline-none resize-none focus:border-primary/50 transition-colors" />
              : <div className="rounded-lg border border-border bg-secondary/40 p-3.5 text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">{item.body}</div>
            }
          </div>

          <div className="flex justify-end gap-2">
            {editing === item.id ? (
              <>
                <button onClick={() => dismiss(item.id)} className="rounded-lg bg-primary px-4 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-colors">Save & Send</button>
                <button onClick={() => setEdit(null)} className="rounded-lg border border-border bg-secondary px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">Cancel</button>
              </>
            ) : (
              <>
                <button onClick={() => dismiss(item.id)} className="flex items-center gap-1.5 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-4 py-2 text-xs font-bold text-emerald-400 hover:bg-emerald-500/20 transition-colors">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approve & Send
                </button>
                <button onClick={() => { setEdit(item.id); setText(item.body); }} className="flex items-center gap-1.5 rounded-lg border border-primary/25 bg-primary/10 px-3 py-2 text-xs font-bold text-primary hover:bg-primary/20 transition-colors">
                  <Edit3 className="h-3.5 w-3.5" /> Edit
                </button>
                <button onClick={() => dismiss(item.id)} className="flex items-center gap-1.5 rounded-lg border border-destructive/25 bg-destructive/10 px-3 py-2 text-xs font-bold text-rose-400 hover:bg-destructive/20 transition-colors">
                  <XCircle className="h-3.5 w-3.5" /> Reject
                </button>
              </>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}

// ─── Memory Panel ─────────────────────────────────────────────────
function MemoryPanel() {
  const [memories, setMem] = useState(MEMORIES);
  const [query, setQuery]  = useState("");
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-violet-400/10 p-2"><Database className="h-4 w-4 text-violet-400" /></div>
        <div>
          <p className="text-sm font-semibold text-foreground">Vector Memory Bank</p>
          <p className="text-xs text-muted-foreground">Facts stored in Supabase pgvector</p>
        </div>
      </div>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Semantic search memory..."
            className="w-full rounded-lg border border-border bg-secondary/50 pl-9 pr-4 py-2.5 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:border-primary/50 transition-colors" />
        </div>
        <button className="flex items-center gap-1.5 rounded-lg border border-violet-500/25 bg-violet-500/10 px-4 py-2.5 text-xs font-semibold text-violet-400 hover:bg-violet-500/20 transition-colors">
          <Sparkles className="h-3.5 w-3.5" /> Query
        </button>
      </div>
      <div className="space-y-2">
        {memories.map(m => (
          <Card key={m.id} className="flex items-start justify-between gap-4 p-4">
            <div className="space-y-1 min-w-0">
              <p className="font-mono text-[10px] font-semibold text-violet-400/70">{m.ns} · {m.key}</p>
              <p className="text-xs font-medium text-foreground">{m.value}</p>
              <p className="text-[10px] text-muted-foreground">{m.age}</p>
            </div>
            <button onClick={() => setMem(ms => ms.filter(x => x.id !== m.id))}
              className="shrink-0 rounded-lg p-1.5 text-muted-foreground hover:text-rose-400 hover:bg-rose-400/10 transition-colors">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Settings Panel ───────────────────────────────────────────────
function SettingsPanel() {
  const FIELDS = [
    { label: "GROQ_API_KEY",    placeholder: "gsk_••••••••" },
    { label: "GEMINI_API_KEY",  placeholder: "AIza••••••••" },
    { label: "TAVILY_API_KEY",  placeholder: "tvly-••••••••" },
    { label: "AGENT_API_KEY",   placeholder: "agent-secret-key" },
    { label: "SUPABASE_URL",    placeholder: "https://xxxx.supabase.co" },
  ];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-muted p-2"><Settings className="h-4 w-4 text-muted-foreground" /></div>
        <div>
          <p className="text-sm font-semibold text-foreground">Platform Settings</p>
          <p className="text-xs text-muted-foreground">Configure agent API credentials</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {FIELDS.map(f => (
          <Card key={f.label} className="space-y-2">
            <label className="block text-[11px] font-bold uppercase tracking-widest text-muted-foreground">{f.label}</label>
            <input type="password" placeholder={f.placeholder}
              className="w-full rounded-lg border border-border bg-secondary/50 px-3 py-2.5 text-xs text-foreground font-mono placeholder:text-muted-foreground/50 outline-none focus:border-primary/50 transition-colors" />
          </Card>
        ))}
      </div>
      <button className="rounded-lg bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm">
        Save Settings
      </button>
    </div>
  );
}

// ─── Root Dashboard ───────────────────────────────────────────────
const HEADINGS: Record<NavTab, { title: string; sub: string }> = {
  overview:  { title: "Email Outreach Command Centre", sub: "Real-time monitoring of agent-drafted campaigns, responses, and pipeline conversion" },
  logs:      { title: "Outreach Logs",                 sub: "Full email log with recipient details, threads, and client replies"                  },
  approvals: { title: "Approval Queue",                sub: "Review and approve outgoing drafts before they are dispatched"                       },
  memory:    { title: "Memory Bank",                   sub: "Inspect, search, and manage facts stored in Supabase pgvector"                       },
  settings:  { title: "Settings",                      sub: "Configure agent behaviour, credentials, and pipeline preferences"                    },
};

export function Dashboard() {
  const { tab } = useContext(TabContext);
  const h = HEADINGS[tab];
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-lg font-bold text-foreground">{h.title}</h1>
        <p className="mt-0.5 text-xs text-muted-foreground">{h.sub}</p>
      </div>
      {tab === "overview"  && <OverviewPanel />}
      {tab === "logs"      && <LogsPanel />}
      {tab === "approvals" && <ApprovalPanel />}
      {tab === "memory"    && <MemoryPanel />}
      {tab === "settings"  && <SettingsPanel />}
    </div>
  );
}
