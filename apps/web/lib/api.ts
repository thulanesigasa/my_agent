/** API errors stay visible; no demonstration values are returned on failure. */
const API_BASE_URL = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
const AGENT_API_KEY = process.env.NEXT_PUBLIC_AGENT_API_KEY || "";

export class ApiError extends Error {
  constructor(message: string, public retryAfterSeconds = 0) { super(message); this.name = "ApiError"; }
}

export async function apiResponse(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (AGENT_API_KEY) headers.set("X-API-Key", AGENT_API_KEY);
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    const detail = error.detail;
    throw new ApiError(typeof detail === "string" ? detail : typeof detail?.message === "string" ? detail.message : `Request failed (${res.status})`,
      typeof detail?.retry_after_seconds === "number" ? detail.retry_after_seconds : 0);
  }
  return res;
}

export async function apiRequest(path: string, init: RequestInit = {}) {
  return (await apiResponse(path, init)).json();
}

export interface SystemHealth {
  status: "UP" | "DEGRADED" | "DOWN" | "healthy";
  environment?: string;
  services?: Record<string, { status: string; latency_ms: number; details?: string }>;
}
export interface EmailLog {
  id: string; recipient: string; company: string; subject: string; dateSent: string;
  status: "Sent" | "Opened" | "Responded" | "Bounced";
  thread?: string; reply?: string;
}
export interface OutreachMetrics {
  totalEmailsSent: number; totalResponsesReceived: number | null;
  responseRatePercent: number | null; activeLeadsInPipeline: number;
  replyTrackingAvailable?: boolean;
}
export interface MemoryRecord {
  id: string; namespace: string; key: string;
  value: { content: string; [key: string]: any }; created_at?: string;
}
export async function getSystemHealth(): Promise<SystemHealth> {
  try { return await apiRequest("/health/detailed"); }
  catch { return { status: "DOWN" }; }
}
export async function getOutreachMetrics(): Promise<OutreachMetrics> {
  return (await apiRequest("/api/outreach/metrics")).metrics;
}
export async function getEmailLogs(filter = "all"): Promise<EmailLog[]> {
  return (await apiRequest(`/api/outreach/logs?filter=${encodeURIComponent(filter)}`)).logs;
}
export async function getPendingApprovals(): Promise<any[]> {
  return (await apiRequest("/api/approvals")).approvals;
}
export async function queryAgentMemory(query: string): Promise<MemoryRecord[]> {
  return (await apiRequest(`/api/memory/search?query=${encodeURIComponent(query)}`)).memories;
}
export async function deleteMemory(id: string): Promise<boolean> {
  await apiRequest(`/api/memory/${encodeURIComponent(id)}`, { method: "DELETE" });
  return true;
}
