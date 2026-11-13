import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60; // seconds — allow full multi-agent workflow to complete

export async function POST(req: NextRequest) {
  const backendUrl =
    process.env.AGENT_API_URL ||
    process.env.NEXT_PUBLIC_AGENT_API_URL ||
    "http://127.0.0.1:8000";

  let response: Response | undefined;
  try {
    const body = await req.json();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (process.env.AGENT_API_KEY) {
      headers["X-API-Key"] = process.env.AGENT_API_KEY;
    }

    response = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    // Read as text first so a non-JSON body never throws an opaque error
    const rawText = await response.text();

    let data: unknown;
    try {
      data = JSON.parse(rawText);
    } catch {
      // Backend returned non-JSON (e.g. plain-text 500 from uvicorn)
      return NextResponse.json(
        { status: "error", message: `Backend error (${response.status}): ${rawText.slice(0, 300)}` },
        { status: 502 }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { status: "error", message: `Could not reach agent backend: ${msg}` },
      { status: 502 }
    );
  }
}
