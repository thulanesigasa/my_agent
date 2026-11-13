import { NextRequest, NextResponse } from "next/server";
export const maxDuration = 60;
async function proxy(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const suffix = path.join("/");
  if (!(suffix === "status" || suffix === "speech" || /^history\/[A-Za-z0-9_-]{1,100}$/.test(suffix))) return new NextResponse(null, { status: 404 });
  if ((req.method === "POST") !== (suffix === "speech")) return new NextResponse(null, { status: 405 });
  const target = suffix === "status" ? "" : `/${suffix}`;
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (process.env.AGENT_API_KEY) headers["X-API-Key"] = process.env.AGENT_API_KEY;
    const body = req.method === "POST" ? await req.text() : undefined;
    if (body && body.length > 20000) return new NextResponse(null, { status: 413 });
    const response = await fetch(`${process.env.AGENT_API_URL || process.env.NEXT_PUBLIC_AGENT_API_URL || "http://127.0.0.1:8000"}/api/voice${target}`, {
      method: req.method, headers, body, cache: "no-store", signal: AbortSignal.timeout(45000),
    });
    return new NextResponse(await response.arrayBuffer(), { status: response.status, headers: { "Content-Type": response.headers.get("content-type") || "application/json", "Cache-Control": "no-store" } });
  } catch { return NextResponse.json({ detail: "Voice backend unavailable" }, { status: 502 }); }
}
export const GET = proxy;
export const POST = proxy;
