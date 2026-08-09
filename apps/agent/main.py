import logging
import json
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from core.state import AgentState
from core.graph import agent_workflow
from core.memory import memory_store
from services.audio_service import audio_service

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent.main")

app = FastAPI(
    title="Autonomous AI Agent Platform Backend",
    description="Python FastAPI backend powered by LangGraph, Supabase pgvector, Groq, Gemini 1.5 Pro, and Edge-TTS.",
    version="1.0.0"
)

# Enable CORS for Next.js web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = "session_001"

class VoiceRequest(BaseModel):
    audio_base64: str
    user_id: Optional[str] = "default_user"

class ApprovalRequest(BaseModel):
    approved: bool
    session_id: Optional[str] = "session_001"
    proposed_action: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker & frontend monitoring."""
    return {
        "status": "healthy",
        "service": "agent_backend",
        "environment": settings.ENV,
        "supabase_connected": memory_store.client is not None,
        "providers": {
            "groq": bool(settings.GROQ_API_KEY),
            "gemini": bool(settings.GEMINI_API_KEY),
            "openrouter": bool(settings.OPENROUTER_API_KEY)
        }
    }


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """
    Process incoming chat messages through the LangGraph state machine.
    """
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": payload.message}],
        "approval_status": "none",
        "requires_human_approval": False
    }

    try:
        final_state = await agent_workflow.ainvoke(initial_state)
        return {
            "status": "success",
            "intent": final_state.get("intent"),
            "response": final_state.get("draft_response"),
            "audio_payload": final_state.get("audio_payload"),
            "requires_human_approval": final_state.get("requires_human_approval"),
            "approval_status": final_state.get("approval_status"),
            "retrieved_memories": final_state.get("retrieved_memory", []),
            "extracted_learnings": final_state.get("extracted_learnings", [])
        }
    except Exception as e:
        logger.error(f"Error invoking agent workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice")
async def voice_endpoint(payload: VoiceRequest):
    """
    Process voice audio input: Groq Whisper STT -> LangGraph agent -> Edge-TTS voice synthesis.
    """
    # 1. Transcribe audio
    transcription = await audio_service.transcribe_audio_base64(payload.audio_base64)
    if not transcription:
        raise HTTPException(status_code=400, detail="Failed to transcribe audio.")

    # 2. Invoke workflow
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": transcription}],
        "approval_status": "none"
    }

    final_state = await agent_workflow.ainvoke(initial_state)

    return {
        "status": "success",
        "transcription": transcription,
        "response": final_state.get("draft_response"),
        "audio_payload": final_state.get("audio_payload"),
        "intent": final_state.get("intent")
    }


@app.get("/api/memory")
async def get_memories(query: Optional[str] = None):
    """
    Query long-term memories stored in Supabase pgvector.
    """
    q = query or "user preferences project status"
    memories = await memory_store.recall_memories(q, limit=10)
    return {"status": "success", "query": q, "memories": memories}


@app.post("/api/approve")
async def approve_action(payload: ApprovalRequest):
    """
    Human-in-the-Loop Endpoint: Grant or reject pending agent tool actions.
    """
    approval_status = "approved" if payload.approved else "rejected"
    
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": "Execute approved action."}],
        "intent": "email_dispatch",
        "approval_status": approval_status,
        "requires_human_approval": False,
        "proposed_action": payload.proposed_action or {"recipient": "lead@company.com", "subject": "Approved Action"}
    }

    final_state = await agent_workflow.ainvoke(initial_state)

    return {
        "status": "success",
        "approval_status": approval_status,
        "response": final_state.get("draft_response")
    }


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    Real-time WebSocket endpoint: Handles continuous audio streaming, live agent state visualizer events, and TTS payloads.
    """
    await websocket.accept()
    logger.info("WebSocket connection established with client.")

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            msg_type = data.get("type", "message")
            
            # State Update Event: Notify UI that Agent is Listening
            await websocket.send_json({"type": "state_change", "state": "listening"})

            user_text = ""
            if msg_type == "audio_stream":
                # Audio input stream -> Whisper STT
                audio_b64 = data.get("payload", "")
                user_text = await audio_service.transcribe_audio_base64(audio_b64)
                await websocket.send_json({"type": "transcription", "text": user_text})
            else:
                user_text = data.get("text", "")

            if not user_text:
                continue

            # State Update Event: Processing
            await websocket.send_json({"type": "state_change", "state": "processing"})

            # Invoke Agent Workflow
            state: AgentState = {
                "messages": [{"role": "user", "content": user_text}],
                "approval_status": "none"
            }
            
            # Send step-by-step progress events for SiriOrb visualizer
            await websocket.send_json({"type": "node_execution", "node": "triage_node"})
            final_state = await agent_workflow.ainvoke(state)
            
            await websocket.send_json({"type": "node_execution", "node": "output_dispatcher_node"})
            
            # Send Speaking state change
            await websocket.send_json({"type": "state_change", "state": "speaking"})

            response_payload = {
                "type": "agent_response",
                "text": final_state.get("draft_response"),
                "audio_payload": final_state.get("audio_payload"),
                "intent": final_state.get("intent"),
                "requires_human_approval": final_state.get("requires_human_approval"),
                "memories": final_state.get("retrieved_memory", [])
            }
            await websocket.send_json(response_payload)

            # Revert to Idle
            await websocket.send_json({"type": "state_change", "state": "idle"})

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
