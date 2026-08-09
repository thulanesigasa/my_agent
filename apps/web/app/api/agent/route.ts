import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const backendUrl = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
  try {
    const body = await req.json();
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { status: "error", message: "Failed to connect to Python Agent backend." },
      { status: 500 }
    );
  }
}
