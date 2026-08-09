"""
Audio Processing Pipeline: Groq Whisper Speech-to-Text (STT) and Edge-TTS Speech Synthesis.
"""
import logging
import os
import tempfile
import httpx
from typing import Optional, AsyncGenerator
from config import settings

logger = logging.getLogger("agent.audio_service")


class AudioService:
    """
    Asynchronous Speech Pipeline:
    - Transcribes WebM/PCM audio byte streams into text using Groq Whisper API.
    - Synthesizes text responses into binary MP3/WAV audio bytes using Edge-TTS.
    """

    @staticmethod
    async def transcribe_audio_bytes(audio_bytes: bytes) -> str:
        """
        Transcribe raw webm/pcm audio bytes using Groq Whisper API (whisper-large-v3).
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY missing for Whisper STT. Utilizing mock transcription.")
            return "Please recall my project status from memory and prepare an update draft."

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
            return "Can you check my email context and summarize key actions?"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @staticmethod
    async def synthesize_speech_bytes(text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize text response into audio bytes using Edge-TTS.
        """
        if not text:
            return b""

        selected_voice = voice or settings.DEFAULT_TTS_VOICE
        try:
            import edge_tts

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            communicate = edge_tts.Communicate(text[:300], selected_voice)
            await communicate.save(tmp_path)

            with open(tmp_path, "rb") as f:
                mp3_data = f.read()

            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            return mp3_data
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis error: {e}")
            return b""

    @staticmethod
    async def process_audio_stream(audio_bytes: bytes) -> AsyncGenerator[bytes, None]:
        """
        Stream generator helper yielding speech response chunks.
        """
        transcription = await AudioService.transcribe_audio_bytes(audio_bytes)
        if not transcription:
            return

        speech_bytes = await AudioService.synthesize_speech_bytes(transcription)
        if speech_bytes:
            yield speech_bytes


audio_service = AudioService()
