"use client";

import React, { useContext, useState } from "react";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import {
  ChevronRight, ChevronDown, CheckCircle2, Eye,
  Clock, AlertCircle, CheckCircle, XCircle, Edit3,
  Trash2, Search, Sparkles, Settings, ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { TabContext } from "@/components/app-shell";
import type { NavTab } from "@/components/app-shell";

// ─── Types ────────────────────────────────────────────────────────
type Status = "Sent" | "Opened" | "Responded" | "Bounced";

interface EmailLog {
  id: string; recipient: string; company: string;
  subject: string; dateSent: string; status: Status;
  thread?: string; reply?: string;
}

// ─── Data ─────────────────────────────────────────────────────────
const METRICS = [
  { label: "Emails Sent",   value: "284", delta: "+14.2% vs last week", up: true  },
  { label: "Responses",     value: "91",  delta: "+8.5% vs last week",  up: true  },
  { label: "Response Rate", value: "32%", delta: "−0.4% vs last week",  up: false },
  { label: "Active Leads",  value: "47",  delta: "+8.7% vs last week",  up: true  },
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

const STEP_DATA = [
  { day: "Mon", direct: 15, outreach: 8  },
  { day: "Tue", direct: 35, outreach: 18 },
  { day: "Wed", direct: 32, outreach: 25 },
  { day: "Thu", direct: 48, outreach: 30 },
  { day: "Fri", direct: 45, outreach: 40 },
  { day: "Sat", direct: 58, outreach: 44 },
  { day: "Sun", direct: 62, outreach: 52 },
];

const BAR_DATA = [
  { status: "Responded", count: 91  },
  { status: "Opened",    count: 76  },
  { status: "Sent",      count: 104 },
  { status: "Bounced",   count: 13  },
];

const LOGS: EmailLog[] = [
  { id:"1", recipient:"cto@techcorp.io",         company:"TechCorp",    subject:"Enterprise License Proposal",       dateSent:"2026-08-08", status:"Responded", thread:"Interested in the 50-seat license.",    reply:"Let's connect Friday 10am EST?" },
  { id:"2", recipient:"founder@startupco.com",   company:"StartupCo",   subject:"AI Agent Pilot Invitation",         dateSent:"2026-08-07", status:"Opened",    thread:"14-day AI pilot program invitation."                                     },
  { id:"3", recipient:"ops@retailgiant.com",     company:"RetailGiant", subject:"Customer Support Automation",       dateSent:"2026-08-06", status:"Responded", thread:"Tier-1 support with full escalation.",  reply:"Send a case study first?"      },
  { id:"4", recipient:"partnerships@finplus.co", company:"FinancePlus", subject:"Compliance Automation Partnership", dateSent:"2026-08-05", status:"Sent",      thread:"Exploring compliance automation."                                         },
  { id:"5", recipient:"ceo@healthsys.org",       company:"HealthSystem",subject:"Document Processing Agent",        dateSent:"2026-08-04", status:"Bounced",   thread:"Automates medical document intake."                                       },
  { id:"6", recipient:"tech@mediahouse.tv",      company:"MediaHouse",  subject:"Real-time Transcription Agent",    dateSent:"2026-08-03", status:"Responded", thread:"Near real-time AI transcription.",      reply:"Exactly what we need!"         },
];

const APPROVALS = [
  { id:"a1", company:"Mike's Auto Repair",  to:"mike@mikesauto.com",     subject:"Web Presence Proposal",   body:"Hi Mike's Auto Repair,\n\nWe help local businesses get online fast. Claim your free 30-min strategy call.\n\nBest,\nAgent Team" },
  { id:"a2", company:"Sunrise Bakery",      to:"hello@sunrisebakery.biz",subject:"Grow Your Bakery Online", body:"Hi Sunrise Bakery,\n\nA professional website could bring dozens of new customers weekly.\n\nBest,\nAgent Team" },
];

const MEMORIES = [
  { id:"m1", ns:"users:cto@enterprise.com",  key:"pref_seats",   value:"Client requested 50-seat enterprise pricing.", age:"2 hours ago" },
  { id:"m2", ns:"users:support@tier1.io",    key:"pref_lang",    value:"Preferred language: English (Formal).",         age:"1 day ago"   },
  { id:"m3", ns:"users:ops@retailgiant.com", key:"channel_pref", value:"Prefers email. Business hours: 9–5 EST.",       age:"3 days ago"  },
];

const STATUS_CFG: Record<Status, { label: string; dot: string }> = {
  Responded: { label: "Responded", dot: "#16a34a" },
  Opened:    { label: "Opened",    dot: "#2563eb" },
  Sent:      { label: "Sent",      dot: "#9ca3af" },
  Bounced:   { label: "Bounced",   dot: "#dc2626" },
};

// ─── Shared Styles ────────────────────────────────────────────────
const S = {
  sectionBorder: { borderBottom: "1px solid #e8e8e8" } as React.CSSProperties,
  colDivider:    { borderRight: "1px solid #e8e8e8"  } as React.CSSProperties,
  label:   { fontSize: 12, color: "#888", marginBottom: 6 } as React.CSSProperties,
  bigNum:  { fontSize: 26, fontWeight: 700, color: "#111", lineHeight: 1, margin: "6px 0" } as React.CSSProperties,
  sectionTitle: { fontSize: 14, fontWeight: 700, color: "#111" } as React.CSSProperties,
  sectionSub:   { fontSize: 12, color: "#888", marginTop: 2 } as React.CSSProperties,
};

// ─── Custom Tooltip ───────────────────────────────────────────────
function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:"#fff", border:"1px solid #e0e0e0", borderRadius:6, padding:"8px 12px", fontSize:12 }}>
      <p style={{ fontWeight:600, marginBottom:4, color:"#111" }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color:"#555" }}>{p.dataKey}: <strong>{p.value}</strong></p>
      ))}
    </div>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────
function StatusBadge({ status }: { status: Status }) {
  const { label, dot } = STATUS_CFG[status];
  return (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, fontSize:12 }}>
      <span style={{ width:7, height:7, borderRadius:"50%", background:dot, flexShrink:0, display:"inline-block" }} />
      <span style={{ color:"#333" }}>{label}</span>
    </span>
  );
}

// ─── Overview Panel ───────────────────────────────────────────────
function OverviewPanel() {
  return (
    <div>
      {/* KPI Row */}
      <div style={{ display:"flex", borderBottom:"1px solid #e8e8e8" }}>
        {METRICS.map((m, i) => (
          <div key={m.label} style={{
            flex: 1, padding: "20px 24px",
            borderRight: i < METRICS.length - 1 ? "1px solid #e8e8e8" : "none",
          }}>
            <p style={S.label}>{m.label}</p>
            <p style={S.bigNum}>{m.value}</p>
            <p style={{ display:"flex", alignItems:"center", gap:4, fontSize:12, color: m.up ? "#16a34a" : "#dc2626", margin:0 }}>
              {m.up
                ? <ArrowUpRight size={13} strokeWidth={2} />
                : <ArrowDownRight size={13} strokeWidth={2} />}
              {m.delta}
            </p>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div style={{ display:"flex", borderBottom:"1px solid #e8e8e8" }}>
        {/* Area chart */}
        <div style={{ flex:3, padding:"20px 24px", borderRight:"1px solid #e8e8e8" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:4 }}>
            <p style={S.sectionTitle}>Email Volume</p>
            <span style={{ fontSize:11, fontWeight:700, color:"#16a34a", background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:999, padding:"1px 8px" }}>↑ 36.9%</span>
          </div>
          <p style={S.sectionSub}>Daily sent vs replies, last 7 days.</p>
          <div style={{ marginTop:16 }}>
            <ResponsiveContainer width="100%" height={170}>
              <AreaChart data={AREA_DATA} margin={{ top:4, right:4, bottom:0, left:-24 }}>
                <defs>
                  <linearGradient id="sentG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#555" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#555" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="repG" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#aaa" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#aaa" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize:10, fill:"#bbb" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize:10, fill:"#bbb" }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTip />} />
                <Area type="monotone" dataKey="sent"    stroke="#444" fill="url(#sentG)" strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="replied" stroke="#999" fill="url(#repG)"  strokeWidth={1.5} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar chart */}
        <div style={{ flex:2, padding:"20px 24px" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:4 }}>
            <p style={S.sectionTitle}>Channel Sales</p>
            <span style={{ fontSize:11, fontWeight:700, color:"#16a34a", background:"#f0fdf4", border:"1px solid #bbf7d0", borderRadius:999, padding:"1px 8px" }}>↑ 58.3%</span>
          </div>
          <p style={S.sectionSub}>Responses by status, last 7 days.</p>
          <div style={{ marginTop:16 }}>
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={BAR_DATA} margin={{ top:4, right:4, bottom:0, left:-28 }} barSize={28}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis dataKey="status" tick={{ fontSize:9, fill:"#bbb" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize:10, fill:"#bbb" }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTip />} />
                <Bar dataKey="count" fill="#ccc" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Logs Table inline */}
      <LogsTable />
    </div>
  );
}

// ─── Logs Table ───────────────────────────────────────────────────
function LogsTable() {
  type FilterType = "all" | Status;
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter]     = useState<FilterType>("all");
  const filters: FilterType[]   = ["all", "Responded", "Opened", "Sent", "Bounced"];
  const rows = filter === "all" ? LOGS : LOGS.filter(l => l.status === filter);

  return (
    <div>
      {/* Table header bar */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"12px 24px", borderBottom:"1px solid #e8e8e8" }}>
        <p style={{ fontSize:13, fontWeight:700, color:"#111" }}>Recent Outreach</p>
        {/* Filter pills */}
        <div style={{ display:"flex", gap:4 }}>
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding:"3px 10px", fontSize:11, fontWeight:500,
              borderRadius:4, cursor:"pointer",
              border: filter === f ? "1px solid #999" : "1px solid #e0e0e0",
              background: filter === f ? "#f5f5f5" : "#fff",
              color: filter === f ? "#111" : "#888",
            }}>{f}</button>
          ))}
        </div>
      </div>

      {/* Table */}
      <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
        <thead>
          <tr style={{ borderBottom:"1px solid #e8e8e8", background:"#fafafa" }}>
            <th style={{ width:32 }} />
            {["Recipient","Company","Subject","Date","Status"].map(h => (
              <th key={h} style={{ padding:"10px 16px", textAlign:"left", fontSize:11, fontWeight:600, color:"#555", letterSpacing:"0.04em", textTransform:"uppercase" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(log => {
            const open = expanded === log.id;
            return (
              <React.Fragment key={log.id}>
                <tr
                  onClick={() => setExpanded(open ? null : log.id)}
                  style={{ borderBottom:"1px solid #e8e8e8", cursor:"pointer", background: open ? "#fafafa" : "#fff" }}
                  onMouseEnter={e => { if (!open) (e.currentTarget as HTMLElement).style.background = "#fafafa"; }}
                  onMouseLeave={e => { if (!open) (e.currentTarget as HTMLElement).style.background = "#fff"; }}
                >
                  <td style={{ paddingLeft:16, width:32 }}>
                    {open
                      ? <ChevronDown size={13} strokeWidth={2} style={{ color:"#999" }} />
                      : <ChevronRight size={13} strokeWidth={2} style={{ color:"#ccc" }} />}
                  </td>
                  <td style={{ padding:"11px 16px", color:"#111", fontWeight:500 }}>{log.recipient}</td>
                  <td style={{ padding:"11px 16px", color:"#555" }}>{log.company}</td>
                  <td style={{ padding:"11px 16px", color:"#555", maxWidth:260, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{log.subject}</td>
                  <td style={{ padding:"11px 16px", color:"#999", fontVariantNumeric:"tabular-nums" }}>{log.dateSent}</td>
                  <td style={{ padding:"11px 16px" }}><StatusBadge status={log.status} /></td>
                </tr>
                {open && (
                  <tr style={{ borderBottom:"1px solid #e8e8e8", background:"#fafafa" }}>
                    <td colSpan={6} style={{ padding:"16px 24px 16px 48px" }}>
                      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
                        <div>
                          <p style={{ fontSize:10, fontWeight:700, color:"#aaa", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:8 }}>Thread Sent</p>
                          <div style={{ border:"1px solid #e8e8e8", borderRadius:6, padding:"10px 14px", fontSize:12, color:"#555", lineHeight:1.6, background:"#fff" }}>{log.thread || "—"}</div>
                        </div>
                        <div>
                          <p style={{ fontSize:10, fontWeight:700, color:"#aaa", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:8 }}>Client Reply</p>
                          {log.reply
                            ? <div style={{ border:"1px solid #e8e8e8", borderRadius:6, padding:"10px 14px", fontSize:12, color:"#333", lineHeight:1.6, background:"#fff" }}>{log.reply}</div>
                            : <div style={{ border:"1px solid #e8e8e8", borderRadius:6, padding:"10px 14px", fontSize:12, color:"#bbb", lineHeight:1.6, fontStyle:"italic", background:"#fff" }}>No reply yet.</div>}
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

      {/* View All */}
      <div style={{ padding:"12px 24px", borderTop:"1px solid #e8e8e8" }}>
        <button style={{ fontSize:12, color:"#555", background:"none", border:"none", cursor:"pointer", fontWeight:500 }}>
          View All →
        </button>
      </div>
    </div>
  );
}

// ─── Approval Panel ───────────────────────────────────────────────
function ApprovalPanel() {
  const [queue, setQueue]  = useState(APPROVALS);
  const [editing, setEdit] = useState<string | null>(null);
  const [text, setText]    = useState("");
  const dismiss = (id: string) => setQueue(q => q.filter(a => a.id !== id));

  return (
    <div style={{ padding:"24px" }}>
      <p style={{ ...S.sectionTitle, marginBottom:4 }}>Human Approval Queue</p>
      <p style={{ ...S.sectionSub, marginBottom:20 }}>Review agent-drafted emails before dispatch</p>

      {queue.length === 0 ? (
        <div style={{ border:"1px solid #e8e8e8", borderRadius:8, padding:"40px 24px", textAlign:"center" }}>
          <CheckCircle2 size={32} strokeWidth={1.5} style={{ color:"#ccc", marginBottom:8 }} />
          <p style={{ fontSize:13, fontWeight:600, color:"#888" }}>Queue is clear</p>
          <p style={{ fontSize:12, color:"#bbb", marginTop:4 }}>All actions reviewed.</p>
        </div>
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {queue.map(item => (
            <div key={item.id} style={{ border:"1px solid #e8e8e8", borderRadius:8, overflow:"hidden" }}>
              {/* Header */}
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"12px 16px", borderBottom:"1px solid #e8e8e8", background:"#fafafa" }}>
                <div>
                  <p style={{ fontSize:13, fontWeight:700, color:"#111" }}>{item.company}</p>
                  <p style={{ fontSize:11, color:"#888", marginTop:2 }}>To: {item.to} · Subject: {item.subject}</p>
                </div>
                <span style={{ fontSize:10, fontWeight:700, color:"#888", border:"1px solid #e0e0e0", borderRadius:4, padding:"2px 8px", background:"#fff" }}>PENDING</span>
              </div>

              {/* Body */}
              <div style={{ padding:"12px 16px", borderBottom:"1px solid #e8e8e8" }}>
                <p style={{ fontSize:10, fontWeight:700, color:"#aaa", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:8 }}>Draft Response</p>
                {editing === item.id
                  ? <textarea value={text} onChange={e => setText(e.target.value)} rows={5}
                      style={{ width:"100%", border:"1px solid #e0e0e0", borderRadius:6, padding:"10px 12px", fontSize:12, color:"#333", outline:"none", resize:"vertical", fontFamily:"inherit" }} />
                  : <div style={{ border:"1px solid #e8e8e8", borderRadius:6, padding:"10px 12px", fontSize:12, color:"#555", lineHeight:1.7, whiteSpace:"pre-wrap", background:"#fafafa" }}>{item.body}</div>}
              </div>

              {/* Actions */}
              <div style={{ display:"flex", justifyContent:"flex-end", gap:8, padding:"10px 16px" }}>
                {editing === item.id ? (
                  <>
                    <button onClick={() => dismiss(item.id)} style={{ padding:"6px 14px", fontSize:12, fontWeight:600, background:"#111", color:"#fff", border:"none", borderRadius:6, cursor:"pointer" }}>Save & Send</button>
                    <button onClick={() => setEdit(null)} style={{ padding:"6px 14px", fontSize:12, fontWeight:500, background:"#fff", color:"#555", border:"1px solid #e0e0e0", borderRadius:6, cursor:"pointer" }}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => dismiss(item.id)} style={{ display:"flex", alignItems:"center", gap:5, padding:"6px 14px", fontSize:12, fontWeight:600, background:"#111", color:"#fff", border:"none", borderRadius:6, cursor:"pointer" }}>
                      <CheckCircle size={13} strokeWidth={2} /> Approve & Send
                    </button>
                    <button onClick={() => { setEdit(item.id); setText(item.body); }} style={{ display:"flex", alignItems:"center", gap:5, padding:"6px 12px", fontSize:12, fontWeight:500, background:"#fff", color:"#555", border:"1px solid #e0e0e0", borderRadius:6, cursor:"pointer" }}>
                      <Edit3 size={13} strokeWidth={2} /> Edit
                    </button>
                    <button onClick={() => dismiss(item.id)} style={{ display:"flex", alignItems:"center", gap:5, padding:"6px 12px", fontSize:12, fontWeight:500, background:"#fff", color:"#999", border:"1px solid #e0e0e0", borderRadius:6, cursor:"pointer" }}>
                      <XCircle size={13} strokeWidth={2} /> Reject
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Memory Panel ─────────────────────────────────────────────────
function MemoryPanel() {
  const [memories, setMem] = useState(MEMORIES);
  const [query, setQuery]  = useState("");
  return (
    <div style={{ padding:"24px" }}>
      <p style={{ ...S.sectionTitle, marginBottom:4 }}>Vector Memory Bank</p>
      <p style={{ ...S.sectionSub, marginBottom:16 }}>Facts stored in Supabase pgvector</p>

      <div style={{ display:"flex", gap:8, marginBottom:20 }}>
        <div style={{ position:"relative", flex:1 }}>
          <Search size={13} strokeWidth={1.8} style={{ position:"absolute", left:10, top:"50%", transform:"translateY(-50%)", color:"#bbb" }} />
          <input value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Semantic search memory..."
            style={{ width:"100%", padding:"8px 12px 8px 32px", fontSize:12, border:"1px solid #e0e0e0", borderRadius:6, outline:"none", color:"#333", fontFamily:"inherit" }} />
        </div>
        <button style={{ display:"flex", alignItems:"center", gap:5, padding:"8px 14px", fontSize:12, fontWeight:500, border:"1px solid #e0e0e0", borderRadius:6, background:"#fff", color:"#555", cursor:"pointer" }}>
          <Sparkles size={13} strokeWidth={1.8} /> Query
        </button>
      </div>

      <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
        <thead>
          <tr style={{ borderBottom:"1px solid #e8e8e8" }}>
            {["Namespace · Key","Value","Age",""].map(h => (
              <th key={h} style={{ padding:"8px 12px", textAlign:"left", fontSize:11, fontWeight:600, color:"#999", textTransform:"uppercase", letterSpacing:"0.04em" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {memories.map(m => (
            <tr key={m.id} style={{ borderBottom:"1px solid #e8e8e8" }}
              onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "#fafafa"}
              onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "#fff"}>
              <td style={{ padding:"11px 12px", fontFamily:"monospace", fontSize:11, color:"#888" }}>{m.ns} · {m.key}</td>
              <td style={{ padding:"11px 12px", color:"#333" }}>{m.value}</td>
              <td style={{ padding:"11px 12px", color:"#bbb", whiteSpace:"nowrap" }}>{m.age}</td>
              <td style={{ padding:"11px 12px", textAlign:"right" }}>
                <button onClick={() => setMem(ms => ms.filter(x => x.id !== m.id))}
                  style={{ padding:"3px 8px", fontSize:11, color:"#bbb", border:"1px solid #e8e8e8", borderRadius:4, background:"#fff", cursor:"pointer" }}>
                  <Trash2 size={12} strokeWidth={1.8} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Settings Panel ───────────────────────────────────────────────
function SettingsPanel() {
  const FIELDS = [
    { label:"GROQ_API_KEY",   ph:"gsk_••••••••"         },
    { label:"GEMINI_API_KEY", ph:"AIza••••••••"          },
    { label:"TAVILY_API_KEY", ph:"tvly-••••••••"         },
    { label:"AGENT_API_KEY",  ph:"agent-secret-key"      },
    { label:"SUPABASE_URL",   ph:"https://xxxx.supabase.co" },
  ];
  return (
    <div style={{ padding:"24px" }}>
      <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:20 }}>
        <Settings size={16} strokeWidth={1.8} style={{ color:"#888" }} />
        <div>
          <p style={S.sectionTitle}>Platform Settings</p>
          <p style={{ ...S.sectionSub }}>Configure API credentials and agent behaviour</p>
        </div>
      </div>

      <table style={{ width:"100%", borderCollapse:"collapse", fontSize:12 }}>
        <tbody>
          {FIELDS.map((f, i) => (
            <tr key={f.label} style={{ borderBottom: i < FIELDS.length - 1 ? "1px solid #e8e8e8" : "none" }}>
              <td style={{ padding:"14px 0", width:180 }}>
                <label style={{ fontSize:11, fontWeight:600, color:"#555", textTransform:"uppercase", letterSpacing:"0.06em", fontFamily:"monospace" }}>{f.label}</label>
              </td>
              <td style={{ padding:"14px 0" }}>
                <input type="password" placeholder={f.ph}
                  style={{ width:"100%", maxWidth:400, padding:"7px 12px", fontSize:12, border:"1px solid #e0e0e0", borderRadius:6, outline:"none", fontFamily:"monospace", color:"#333" }} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop:20 }}>
        <button style={{ padding:"8px 20px", fontSize:12, fontWeight:600, background:"#111", color:"#fff", border:"none", borderRadius:6, cursor:"pointer" }}>
          Save Settings
        </button>
      </div>
    </div>
  );
}

// ─── Page headings ────────────────────────────────────────────────
const HEADINGS: Record<NavTab, { title: string; sub: string }> = {
  overview:  { title:"Email Outreach Command Centre", sub:"Real-time monitoring of agent-drafted campaigns, responses, and pipeline conversion" },
  logs:      { title:"Outreach Logs",                 sub:"Full email log with recipient details, threads, and client replies"                  },
  approvals: { title:"Approval Queue",                sub:"Review and approve outgoing drafts before they are dispatched"                       },
  memory:    { title:"Memory Bank",                   sub:"Inspect, search, and manage facts stored in Supabase pgvector"                       },
  settings:  { title:"Settings",                      sub:"Configure agent behaviour, credentials, and pipeline preferences"                    },
};

// ─── Root Dashboard ───────────────────────────────────────────────
export function Dashboard() {
  const { tab } = useContext(TabContext);
  const h = HEADINGS[tab];

  return (
    <div>
      {/* Page title */}
      <div style={{ padding:"20px 24px 16px", borderBottom:"1px solid #e8e8e8" }}>
        <h1 style={{ fontSize:16, fontWeight:700, color:"#111", margin:0 }}>{h.title}</h1>
        <p style={{ fontSize:12, color:"#888", marginTop:4 }}>{h.sub}</p>
      </div>

      {tab === "overview"  && <OverviewPanel />}
      {tab === "logs"      && <div style={{ padding:"0" }}><LogsTable /></div>}
      {tab === "approvals" && <ApprovalPanel />}
      {tab === "memory"    && <MemoryPanel />}
      {tab === "settings"  && <SettingsPanel />}
    </div>
  );
}
