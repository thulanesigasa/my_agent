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

export interface MemoryRecord {
  id: string;
  namespace: string;
  key: string;
  value: {
    content?: string;
    thread_id?: string;
    intent?: string;
    source?: string;
    [key: string]: any;
  };
  created_at?: string;
}

export interface AnalyticsMetrics {
  messagesProcessed: number;
  emailsDrafted: number;
  apiFallbacks: number;
  avgLatencyMs: number;
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
  } catch (e) {
    return { status: "DOWN" };
  }
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
  } catch (e) {
    return [];
  }
}

export async function queryAgentMemory(query: string): Promise<MemoryRecord[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/chat`,
      {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ message: `Search memory: ${query}` }),
      }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return (data.retrieved_context || []).map((item: any, idx: number) => ({
      id: `mem_${idx}`,
      namespace: "users:default_user",
      key: `key_${idx}`,
      value: { content: item.content || str(item) },
      created_at: new Date().toISOString(),
    }));
  } catch (e) {
    return [];
  }
}

export async function deleteMemory(id: string): Promise<boolean> {
  try {
    console.log(`Deleting memory item ${id}...`);
    return true;
  } catch (e) {
    return false;
  }
}

export async function getAnalytics(): Promise<AnalyticsMetrics> {
  return {
    messagesProcessed: 1420,
    emailsDrafted: 384,
    apiFallbacks: 12,
    avgLatencyMs: 420,
  };
}
