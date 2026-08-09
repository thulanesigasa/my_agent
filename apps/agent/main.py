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
from agents.human_approval import get_pending_approvals, approve_draft, reject_or_edit_draft

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent.main")

app = FastAPI(
    title="Autonomous AI Agent Platform Backend",
    description="Python FastAPI backend powered by LangGraph, Supabase pgvector, Groq, Gemini 1.5 Pro, and Edge-TTS.",
    version="1.0.0"
)

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


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """
    Real-time Bidirectional Audio Streaming WebSocket Endpoint with strict token & rate limits.
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
