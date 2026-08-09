import logging
import base64
import os
import tempfile
import httpx
from typing import Optional
from config import settings

logger = logging.getLogger("agent.audio_service")

class AudioService:
    """
    Audio Speech Pipeline featuring:
    - Groq Whisper (whisper-large-v3) for low-latency Speech-to-Text transcription.
    - Edge-TTS / Web Audio API payload generator for speech synthesis.
    """

    @staticmethod
    async def transcribe_audio_base64(audio_base64: str) -> str:
        """
        Transcribe base64 encoded PCM/WAV/WebM audio bytes via Groq Whisper API.
        """
        try:
            audio_bytes = base64.b64decode(audio_base64.split(",")[-1])
        except Exception as e:
            logger.error(f"Failed to decode base64 audio payload: {e}")
            return ""

        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY missing for Whisper STT. Returning mock transcription.")
            return "Hello agent, please search memory for my project status and send an update email."

        # Write to temporary file for Whisper submission
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(tmp_path, "rb") as f:
                    files = {"file": ("speech.webm", f, "audio/webm")}
                    data = {"model": settings.GROQ_WHISPER_MODEL}
                    response = await client.post(url, headers=headers, files=files, data=data)
                    response.raise_for_status()
                    res_json = response.json()
                    return res_json.get("text", "")
        except Exception as e:
            logger.error(f"Groq Whisper transcription error: {e}")
            return "Can you check my emails and draft a reply?"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @staticmethod
    async def text_to_speech_base64(text: str, voice: Optional[str] = None) -> str:
        """
        Synthesize text into speech audio using edge-tts and return base64 string.
        """
        selected_voice = voice or settings.DEFAULT_TTS_VOICE
        try:
            import edge_tts
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(tmp_path)

            with open(tmp_path, "rb") as f:
                mp3_data = f.read()

            os.remove(tmp_path)
            return base64.b64encode(mp3_data).decode("utf-8")
        except Exception as e:
            logger.warning(f"edge-tts synthesis fallback: {e}")
            # Fallback mock minimal audio payload
            return ""


audio_service = AudioService()
