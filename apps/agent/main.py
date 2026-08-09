import logging
import json
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from core.state import AgentState
from core.graph import agent_workflow
from core.memory import memory_manager
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
    thread_id: Optional[str] = "session_001"
    email_input: Optional[Dict[str, Any]] = None

class VoiceRequest(BaseModel):
    audio_base64: str
    user_id: Optional[str] = "default_user"

class ApprovalRequest(BaseModel):
    approved: bool
    thread_id: Optional[str] = "session_001"
    proposed_action: Optional[Dict[str, Any]] = None


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
async def chat_endpoint(payload: ChatRequest):
    """
    Process incoming chat messages through the LangGraph state machine workflow.
    """
    config = {"configurable": {"thread_id": payload.thread_id or "session_001"}}

    initial_state: AgentState = {
        "messages": [{"role": "user", "content": payload.message}],
        "email_input": payload.email_input,
        "approval_status": "none",
        "needs_human_approval": False
    }

    try:
        final_state = await agent_workflow.ainvoke(initial_state, config=config)
        output_text = final_state.get("final_output") or final_state.get("draft_response") or "Request processed."
        audio_b64 = await audio_service.text_to_speech_base64(str(output_text)[:250])

        return {
            "status": "success",
            "sender": final_state.get("sender"),
            "intent": final_state.get("intent"),
            "response": output_text,
            "audio_payload": audio_b64,
            "needs_human_approval": final_state.get("needs_human_approval", False),
            "approval_status": final_state.get("approval_status"),
            "retrieved_context": final_state.get("retrieved_context", []),
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
    transcription = await audio_service.transcribe_audio_base64(payload.audio_base64)
    if not transcription:
        raise HTTPException(status_code=400, detail="Failed to transcribe audio.")

    config = {"configurable": {"thread_id": "voice_thread"}}
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": transcription}],
        "approval_status": "none"
    }

    final_state = await agent_workflow.ainvoke(initial_state, config=config)
    output_text = final_state.get("final_output") or final_state.get("draft_response") or "Voice request processed."
    audio_b64 = await audio_service.text_to_speech_base64(str(output_text)[:250])

    return {
        "status": "success",
        "transcription": transcription,
        "response": output_text,
        "audio_payload": audio_b64,
        "intent": final_state.get("intent")
    }


@app.get("/api/memory")
async def get_memories(query: Optional[str] = None):
    """
    Query long-term memories stored in Supabase pgvector.
    """
    q = query or "user preferences project status"
    memories = await memory_manager.search_memory(q, limit=10)
    return {"status": "success", "query": q, "memories": memories}


@app.post("/api/approve")
async def approve_action(payload: ApprovalRequest):
    """
    Human-in-the-Loop Endpoint: Grant or reject pending agent tool actions.
    """
    config = {"configurable": {"thread_id": payload.thread_id or "session_001"}}
    approval_status = "approved" if payload.approved else "rejected"
    
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": "Execute approved action."}],
        "intent": "client_inquiry",
        "approval_status": approval_status,
        "needs_human_approval": False
    }

    final_state = await agent_workflow.ainvoke(initial_state, config=config)

    return {
        "status": "success",
        "approval_status": approval_status,
        "response": final_state.get("final_output") or final_state.get("draft_response")
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
            await websocket.send_json({"type": "state_change", "state": "listening"})

            user_text = ""
            if msg_type == "audio_stream":
                audio_b64 = data.get("payload", "")
                user_text = await audio_service.transcribe_audio_base64(audio_b64)
                await websocket.send_json({"type": "transcription", "text": user_text})
            else:
                user_text = data.get("text", "")

            if not user_text:
                continue

            await websocket.send_json({"type": "state_change", "state": "processing"})

            config = {"configurable": {"thread_id": "ws_session"}}
            state: AgentState = {
                "messages": [{"role": "user", "content": user_text}],
                "approval_status": "none"
            }
            
            await websocket.send_json({"type": "node_execution", "node": "triage"})
            final_state = await agent_workflow.ainvoke(state, config=config)
            
            await websocket.send_json({"type": "node_execution", "node": "drafter"})
            await websocket.send_json({"type": "state_change", "state": "speaking"})

            output_text = final_state.get("final_output") or final_state.get("draft_response") or "Processing complete."
            audio_b64 = await audio_service.text_to_speech_base64(str(output_text)[:250])

            response_payload = {
                "type": "agent_response",
                "text": output_text,
                "audio_payload": audio_b64,
                "intent": final_state.get("intent"),
                "needs_human_approval": final_state.get("needs_human_approval", False),
                "memories": final_state.get("retrieved_context", [])
            }
            await websocket.send_json(response_payload)
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
