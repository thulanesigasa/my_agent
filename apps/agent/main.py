"""
FastAPI Backend Entrypoint featuring real-time WebSocket audio endpoints and HTTP API handlers.
"""
import logging
import json
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


@app.websocket("/ws/audio")
async def websocket_audio_endpoint(websocket: WebSocket):
    """
    Real-time Bidirectional Audio Streaming WebSocket Endpoint:
    Receives incoming WebM audio chunks, runs Groq Whisper STT -> LangGraph Workflow -> Edge-TTS synthesis,
    and returns speech audio bytes directly over the socket connection.
    """
    await websocket.accept()
    logger.info("Real-time Audio WebSocket connected at /ws/audio.")

    try:
        while True:
            # Receive raw binary audio bytes or JSON frame from client
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                
                # 1. State change: Listening -> Processing
                await websocket.send_json({"type": "state_change", "state": "processing"})
                
                # 2. Transcribe audio via Whisper STT
                transcription = await audio_service.transcribe_audio_bytes(audio_bytes)
                if transcription:
                    await websocket.send_json({"type": "transcription", "text": transcription})
                    
                    # 3. Execute LangGraph agent workflow
                    config = {"configurable": {"thread_id": "ws_audio_thread"}}
                    state: AgentState = {
                        "messages": [{"role": "user", "content": transcription}],
                        "approval_status": "none"
                    }
                    
                    final_state = await agent_workflow.ainvoke(state, config=config)
                    output_text = final_state.get("final_output") or final_state.get("draft_response") or "Audio request complete."
                    
                    # 4. State change: Processing -> Speaking
                    await websocket.send_json({"type": "state_change", "state": "speaking"})
                    await websocket.send_json({
                        "type": "text_response",
                        "text": output_text,
                        "intent": final_state.get("intent")
                    })
                    
                    # 5. Synthesize speech bytes and stream back over socket
                    speech_bytes = await audio_service.synthesize_speech_bytes(str(output_text))
                    if speech_bytes:
                        await websocket.send_bytes(speech_bytes)

                # 6. Revert state to Idle
                await websocket.send_json({"type": "state_change", "state": "idle"})
                
            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Audio WebSocket client disconnected from /ws/audio.")
    except Exception as e:
        logger.error(f"Error in Audio WebSocket stream: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    Control & JSON WebSocket Endpoint for SiriOrb state visualizer & chat events.
    """
    await websocket.accept()
    logger.info("Agent Control WebSocket connected at /ws/agent.")

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)

            user_text = data.get("text", "")
            if not user_text:
                continue

            await websocket.send_json({"type": "state_change", "state": "processing"})
            config = {"configurable": {"thread_id": "ws_agent_thread"}}
            state: AgentState = {
                "messages": [{"role": "user", "content": user_text}],
                "approval_status": "none"
            }

            final_state = await agent_workflow.ainvoke(state, config=config)
            output_text = final_state.get("final_output") or final_state.get("draft_response") or "Complete."

            await websocket.send_json({"type": "state_change", "state": "speaking"})
            await websocket.send_json({
                "type": "agent_response",
                "text": output_text,
                "intent": final_state.get("intent"),
                "needs_human_approval": final_state.get("needs_human_approval", False)
            })
            await websocket.send_json({"type": "state_change", "state": "idle"})

    except WebSocketDisconnect:
        logger.info("Agent Control WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"Agent WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
