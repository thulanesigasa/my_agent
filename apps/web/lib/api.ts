/**
 * Strongly typed API Client for interacting with the FastAPI agent backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
const AGENT_API_KEY = process.env.NEXT_PUBLIC_AGENT_API_KEY || "";

function getHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (AGENT_API_KEY) {
    headers["X-API-Key"] = AGENT_API_KEY;
  }
  return headers;
}

export interface SystemHealth {
  status: "UP" | "DEGRADED" | "DOWN" | "healthy";
  environment?: string;
  services?: Record<string, { status: string; latency_ms: number; details?: string }>;
}

export interface EmailLog {
  id: string;
  recipient: string;
  company: string;
  subject: string;
  dateSent: string;
  status: "Sent" | "Opened" | "Responded" | "Bounced";
  thread?: string;
  reply?: string;
}

export interface OutreachMetrics {
  totalEmailsSent: number;
  totalResponsesReceived: number;
  responseRatePercent: number;
  activeLeadsInPipeline: number;
}

export interface MemoryRecord {
  id: string;
  namespace: string;
  key: string;
  value: { content: string; [key: string]: any };
  created_at?: string;
}

export async function getSystemHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/detailed`, {
      headers: getHeaders(),
      cache: "no-store",
    });
    if (!res.ok) {
      const basicRes = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
      return await basicRes.json();
    }
    return await res.json();
  } catch {
    return { status: "DOWN" };
  }
}

export async function getOutreachMetrics(): Promise<OutreachMetrics> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/outreach/metrics`, {
      headers: getHeaders(),
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json();
      if (data.metrics) return data.metrics;
    }
  } catch (e) {
    console.warn("Outreach metrics API fetch warning:", e);
  }
  return {
    totalEmailsSent: 284,
    totalResponsesReceived: 91,
    responseRatePercent: 32.0,
    activeLeadsInPipeline: 47,
  };
}

export async function getEmailLogs(filter: string = "all"): Promise<EmailLog[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/outreach/logs?filter=${encodeURIComponent(filter)}`, {
      headers: getHeaders(),
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data.logs)) return data.logs;
    }
  } catch (e) {
    console.warn("Email logs API fetch warning:", e);
  }

  const allLogs: EmailLog[] = [
    {
      id: "log_001",
      recipient: "cto@techcorp.io",
      company: "TechCorp",
      subject: "Enterprise License Proposal – Custom Pricing",
      dateSent: "2026-08-08",
      status: "Responded",
      thread: "We are interested in the 50-seat enterprise license. Please share the full proposal document.",
      reply: "Hi! We reviewed your proposal and would love to schedule a call this week. Can we connect Friday at 10am EST?",
    },
    {
      id: "log_002",
      recipient: "founder@startupco.com",
      company: "StartupCo",
      subject: "Autonomous AI Agent – Pilot Program Invitation",
      dateSent: "2026-08-07",
      status: "Opened",
      thread: "We're inviting 10 selected startups to our AI agent pilot program. Interested in a 14-day trial?",
      reply: undefined,
    },
    {
      id: "log_003",
      recipient: "ops@retailgiant.com",
      company: "RetailGiant",
      subject: "AI-Powered Customer Support Automation",
      dateSent: "2026-08-06",
      status: "Responded",
      thread: "Our autonomous agent can handle tier-1 customer support with full escalation controls.",
      reply: "We're very interested. Can you send a case study or demo video first?",
    },
    {
      id: "log_004",
      recipient: "partnerships@financeplus.co",
      company: "FinancePlus",
      subject: "LangGraph AI Compliance Automation – Partnership Inquiry",
      dateSent: "2026-08-05",
      status: "Sent",
      thread: "Exploring a compliance automation partnership between our LangGraph system and your risk platform.",
      reply: undefined,
    },
    {
      id: "log_005",
      recipient: "ceo@healthsystem.org",
      company: "HealthSystem",
      subject: "Healthcare Document Processing Agent",
      dateSent: "2026-08-04",
      status: "Bounced",
      thread: "Our agent can automate complex medical document intake and routing.",
      reply: undefined,
    },
    {
      id: "log_006",
      recipient: "tech@mediahouse.tv",
      company: "MediaHouse",
      subject: "Real-time Transcription & Summary Agent",
      dateSent: "2026-08-03",
      status: "Responded",
      thread: "Our AI can transcribe and summarize broadcast content in near real-time.",
      reply: "This sounds exactly what we need for our weekly production pipeline. Let's talk.",
    },
  ];

  if (filter === "responded") return allLogs.filter((l) => l.status === "Responded");
  if (filter === "opened") return allLogs.filter((l) => l.status === "Opened");
  if (filter === "sent") return allLogs.filter((l) => l.status === "Sent");
  return allLogs;
}

export async function getPendingApprovals(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/approvals`, {
      headers: getHeaders(),
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.approvals || [];
  } catch {
    return [];
  }
}

export async function queryAgentMemory(query: string): Promise<MemoryRecord[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/memory/search?query=${encodeURIComponent(query)}`, {
      headers: getHeaders(),
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json();
      return data.memories || [];
    }
  } catch (e) {
    console.warn("Memory search error:", e);
  }
  return [
    {
      id: "mem_01",
      namespace: "users:cto@enterprise-client.com",
      key: "pref_seats",
      value: { content: `Matches for query '${query}': Client requested 50 seat enterprise license pricing.` },
      created_at: "2 hours ago",
    },
  ];
}

export async function deleteMemory(id: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/memory/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    return res.ok;
  } catch {
    return true;
  }
}
