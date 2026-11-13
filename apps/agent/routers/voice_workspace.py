"""Private voice configuration, generated speech and operator conversation history."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from config import settings
from core.security import verify_api_key
from services.audio_service import audio_service
from services.conversations import history
from services import spend

router = APIRouter(prefix="/api/voice", dependencies=[Depends(verify_api_key)])


class SpeechInput(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


@router.get("")
def status():
    return {
        "provider": settings.VOICE_PROVIDER,
        "stt_provider": settings.STT_PROVIDER,
        "elevenlabs_ready": bool(
            settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID
        ),
        "llm_provider": settings.LLM_PROVIDER,
        "openai_ready": bool(settings.OPENAI_API_KEY),
        "budget": spend.status(),
    }


@router.post("/speech")
async def speech(payload: SpeechInput):
    if settings.VOICE_PROVIDER != "elevenlabs":
        raise HTTPException(
            409, "Select ElevenLabs voice in the local backend configuration"
        )
    try:
        audio = await audio_service.synthesize_speech_bytes(payload.text)
        return Response(
            audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"}
        )
    except Exception as exc:
        raise HTTPException(
            503,
            "Speech unavailable. Check provider configuration or monthly allowance; text is still available.",
        ) from exc


@router.get("/history/{thread_id}")
def conversation(thread_id: str):
    try:
        return history(thread_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
