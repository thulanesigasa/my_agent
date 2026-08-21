import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 60; // seconds — allow full multi-agent workflow to complete

export async function POST(req: NextRequest) {
  const backendUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
  try {
    const body = await req.json();
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      // Node.js fetch on the server side - no CORS issue
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    return NextResponse.json(
      { status: "error", message: `Backend unreachable: ${msg}` },
      { status: 502 }
    );
  }
}
