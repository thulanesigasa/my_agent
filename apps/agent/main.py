"""
FastAPI Backend Entrypoint featuring real-time WebSocket audio endpoints, HTTP API handlers,
Twilio WhatsApp webhooks, OpenTelemetry observability, SlowAPI rate limiting, and Human-in-the-Loop approvals.
"""
import logging
import json
from typing import Dict, Any, Optional

# Initialize Telemetry Tracing first before framework startup
import core.telemetry

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from core.state import AgentState
from core.graph import agent_workflow
from core.memory import memory_manager
from core.security import limiter, verify_api_key, verify_websocket_api_key
from services.audio_service import audio_service
from services.whatsapp_service import whatsapp_service
from services.sandbox_service import sandbox_service
from services.voice_biometrics import voice_biometrics_service
from tools.procedural_tools import list_available_skills
from agents.human_approval import get_pending_approvals, approve_draft, reject_or_edit_draft
from routers import health, webhooks
from scheduler import agent_scheduler

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent.main")

app = FastAPI(
    title="Autonomous AI Agent Platform Backend",
    description="Python FastAPI backend powered by LangGraph, Supabase pgvector, Groq, Gemini 1.5 Pro, and Edge-TTS.",
    version="1.0.0"
)

# Mount Health check and Webhooks routers
app.include_router(health.router)
app.include_router(webhooks.router)


@app.get("/", response_class=HTMLResponse)
async def root_status_page():
    """Root endpoint: Displays backend status dashboard with quick navigation links."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>my_agent - Backend API</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
            html, body { width: 100%; height: 100%; overflow-x: hidden; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                color: #0f172a;
                display: flex;
                flex-direction: column;
                min-height: 100vh;
            }
            header {
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 32px;
                background: rgba(255, 255, 255, 0.85);
                backdrop-filter: blur(12px);
                border-bottom: 1px solid rgba(226, 232, 240, 0.8);
            }
            .logo { font-weight: 700; font-size: 16px; color: #0f172a; letter-spacing: -0.01em; }
            .status-badge {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(16, 185, 129, 0.08);
                color: #059669;
                border: 1px solid rgba(16, 185, 129, 0.25);
                padding: 6px 16px;
                border-radius: 9999px;
                font-size: 13px;
                font-weight: 600;
            }
            .dot {
                width: 8px; height: 8px;
                background: #10b981;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.4; }
            }
            main {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 60px 24px;
                text-align: center;
                max-width: 800px;
                margin: 0 auto;
                width: 100%;
            }
            .pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: #ffffff;
                border: 1px solid rgba(226, 232, 240, 0.9);
                padding: 6px 16px;
                border-radius: 9999px;
                font-size: 12px;
                font-weight: 600;
                color: #059669;
                margin-bottom: 24px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.03);
            }
            h1 {
                font-size: 38px;
                font-weight: 600;
                letter-spacing: -0.02em;
                margin: 0 0 16px;
                color: #0f172a;
            }
            .subtitle {
                font-size: 15px;
                color: #64748b;
                line-height: 1.6;
                margin-bottom: 40px;
                max-width: 580px;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 14px;
                width: 100%;
                max-width: 680px;
            }
            .btn {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 14px 20px;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.15s ease;
                border: 1px solid rgba(226, 232, 240, 0.9);
                color: #334155;
                background: #ffffff;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
            }
            .btn:hover {
                border-color: #ec4899;
                color: #ec4899;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(236, 72, 153, 0.12);
            }
            .btn-primary {
                grid-column: 1 / -1;
                background: #0f172a;
                color: #ffffff;
                border-color: #0f172a;
                font-weight: 600;
                padding: 16px 24px;
            }
            .btn-primary:hover {
                background: #1e293b;
                border-color: #1e293b;
                color: #ffffff;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2);
            }
            footer {
                padding: 24px;
                text-align: center;
                font-size: 12px;
                color: #94a3b8;
                border-top: 1px solid rgba(226, 232, 240, 0.8);
                background: rgba(255, 255, 255, 0.5);
            }
        </style>
    </head>
    <body>
        <header>
            <span class="logo">my_agent</span>
            <div class="status-badge"><span class="dot"></span>Backend Online &mdash; port 8000</div>
        </header>

        <main>
            <div class="pill"><span class="dot"></span>FastAPI Engine Running</div>
            <h1>T.s Industries Agent</h1>
            <p class="subtitle">
                LangGraph multi-agent orchestrator. Groq Whisper STT, ElevenLabs TTS, Supabase pgvector memory and Human-in-the-Loop engine.
            </p>
            <div class="grid">
                <a href="http://localhost:3000/dashboard" class="btn btn-primary">Launch Admin Dashboard</a>
                <a href="http://localhost:3000/" class="btn">Voice Hub</a>
                <a href="/docs" class="btn">Swagger API Docs</a>
                <a href="/health" class="btn">Health Check</a>
                <a href="/api/skills" class="btn">Active Skills</a>
            </div>
        </main>

        <footer>
            LangGraph &middot; Groq &middot; ElevenLabs &middot; Supabase pgvector &middot; T.s Industries
        </footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)




@app.on_event("startup")
async def on_startup():
    """
    Startup lifecycle: Starts APScheduler background worker for 2-min polling & weekly Excel report cron.
    """
    logger.info("Initializing application startup services...")
    try:
        agent_scheduler.start()
    except Exception as e:
        logger.warning(f"Failed to start background scheduler: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    """
    Shutdown lifecycle: Gracefully stops background scheduler worker.
    """
    logger.info("Shutting down background services...")
    try:
        agent_scheduler.shutdown()
    except Exception as e:
        logger.warning(f"Error shutting down scheduler: {e}")

# Attach SlowAPI limiter state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for Next.js web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware injecting standard security headers into all responses.
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Request Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    thread_id: Optional[str] = "session_001"
    email_input: Optional[Dict[str, Any]] = None

class VoiceRequest(BaseModel):
    audio_base64: str
    user_id: Optional[str] = "default_user"

class ActionDecisionRequest(BaseModel):
    action: str  # 'approve', 'edit', 'reject'
    new_content: Optional[str] = None

class SandboxRequest(BaseModel):
    code: str
    max_retries: Optional[int] = 3


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker & frontend monitoring."""
    return {
        "status": "healthy",
        "service": "agent_backend",
        "environment": settings.ENV,
        "supabase_connected": memory_manager.client is not None,
        "providers": {
            "groq": bool(settings.GROQ_API_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "openrouter": bool(settings.OPENROUTER_API_KEY)
        }
    }


@app.post("/api/chat")
@limiter.limit("60/minute")
async def chat_endpoint(request: Request, payload: ChatRequest, token: str = Depends(verify_api_key)):
    """
    Process incoming chat messages through the LangGraph state machine workflow.
    """
    thread_id = payload.thread_id or "session_001"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "messages": [{"role": "user", "content": payload.message}],
        "email_input": payload.email_input,
        "approval_status": "none",
        "needs_human_approval": False
    }

    try:
        final_state = await agent_workflow.ainvoke(initial_state, config=config)
        output_text = final_state.get("final_output") or final_state.get("draft_response") or "Request processed."
        audio_b64 = await audio_service.synthesize_speech_bytes(str(output_text)[:250])

        return {
            "status": "success",
            "sender": final_state.get("sender"),
            "intent": final_state.get("intent"),
            "response": output_text,
            "needs_human_approval": final_state.get("needs_human_approval", False),
            "approval_status": final_state.get("approval_status"),
            "retrieved_context": final_state.get("retrieved_context", []),
            "extracted_learnings": final_state.get("extracted_learnings", [])
        }
    except Exception as e:
        logger.error(f"Error invoking agent workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/whatsapp")
@limiter.limit("30/minute")
async def whatsapp_webhook(request: Request):
    """
    Twilio WhatsApp Webhook Endpoint: Receives incoming WhatsApp messages and triggers LangGraph agent.
    """
    form_data = await request.form()
    payload_dict = dict(form_data)
    parsed = whatsapp_service.parse_webhook_payload(payload_dict)

    sender = parsed["sender"]
    body = parsed["body"]
    logger.info(f"Incoming WhatsApp webhook from {sender}: '{body}'")

    thread_id = f"wa_{sender}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "messages": [{"role": "user", "content": body}],
        "email_input": {"sender": sender, "body": body, "thread_id": thread_id},
        "approval_status": "none"
    }

    final_state = await agent_workflow.ainvoke(initial_state, config=config)
    output_text = final_state.get("final_output") or final_state.get("draft_response") or "Processed."

    if not final_state.get("needs_human_approval"):
        await whatsapp_service.send_whatsapp_message(to_number=sender, message_body=str(output_text))

    return {"status": "received", "sender": sender, "intent": final_state.get("intent")}


@app.get("/api/approvals")
@limiter.limit("60/minute")
async def get_approvals(request: Request, token: str = Depends(verify_api_key)):
    """
    Returns the queue of pending actions requiring human review.
    """
    pending = get_pending_approvals()
    return {"status": "success", "count": len(pending), "approvals": pending}


@app.post("/api/approvals/{thread_id}/action")
@limiter.limit("30/minute")
async def process_approval_action(request: Request, thread_id: str, payload: ActionDecisionRequest, token: str = Depends(verify_api_key)):
    """
    Process human decision (approve, edit, or reject) and resume LangGraph workflow execution.
    """
    action = payload.action.lower()
    logger.info(f"Processing human approval decision '{action}' for thread '{thread_id}'")

    if action == "approve":
        res = await approve_draft(thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        state: AgentState = {
            "messages": [{"role": "user", "content": "Execute approved action."}],
            "approval_status": "approved",
            "needs_human_approval": False
        }
        final_state = await agent_workflow.ainvoke(state, config=config)
        return {"status": "success", "action": "approved", "result": final_state.get("final_output")}

    elif action == "edit":
        res = await reject_or_edit_draft(thread_id, new_content=payload.new_content)
        config = {"configurable": {"thread_id": thread_id}}
        state: AgentState = {
            "messages": [{"role": "user", "content": "Execute edited action."}],
            "draft_response": payload.new_content,
            "approval_status": "approved",
            "needs_human_approval": False
        }
        final_state = await agent_workflow.ainvoke(state, config=config)
        return {"status": "success", "action": "edited", "result": final_state.get("final_output")}

    elif action == "reject":
        res = await reject_or_edit_draft(thread_id, new_content=None)
        return {"status": "success", "action": "rejected"}

    raise HTTPException(status_code=400, detail="Invalid action type. Expected 'approve', 'edit', or 'reject'.")


@app.post("/api/sandbox/run")
@limiter.limit("20/minute")
async def run_sandbox_code(request: Request, payload: SandboxRequest, token: str = Depends(verify_api_key)):
    """
    Executes Python script inside an isolated self-healing sandbox.
    """
    retries = payload.max_retries or 3
    result = await sandbox_service.execute_with_self_healing(code=payload.code, max_retries=retries)
    return {"status": "success" if result["success"] else "error", "result": result}


@app.get("/api/skills")
@limiter.limit("60/minute")
async def get_active_skills(request: Request, token: str = Depends(verify_api_key)):
    """
    Returns a list of all active learned Standard Operating Procedures (SOP skills).
    """
    skills = list_available_skills()
    return {"status": "success", "count": len(skills), "skills": skills}


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """
    Real-time Bidirectional Audio Streaming WebSocket Endpoint.
    """
    is_authed = await verify_websocket_api_key(websocket)
    if not is_authed:
        return

    await websocket.accept()
    logger.info("Real-time Audio WebSocket connected at /ws/audio.")

    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                await websocket.send_json({"type": "state_change", "state": "processing"})
                
                transcription = await audio_service.transcribe_audio_bytes(audio_bytes)
                if transcription:
                    await websocket.send_json({"type": "transcription", "text": transcription})
                    config = {"configurable": {"thread_id": "ws_audio_thread"}}
                    state: AgentState = {
                        "messages": [{"role": "user", "content": transcription}],
                        "approval_status": "none"
                    }
                    
                    final_state = await agent_workflow.ainvoke(state, config=config)
                    output_text = final_state.get("final_output") or final_state.get("draft_response") or "Audio request complete."
                    
                    await websocket.send_json({"type": "state_change", "state": "speaking"})
                    await websocket.send_json({
                        "type": "text_response",
                        "text": output_text,
                        "intent": final_state.get("intent")
                    })
                    
                    speech_bytes = await audio_service.synthesize_speech_bytes(str(output_text))
                    if speech_bytes:
                        await websocket.send_bytes(speech_bytes)

                await websocket.send_json({"type": "state_change", "state": "idle"})
                
            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Audio WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"Error in Audio WebSocket stream: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
