"""
Audio Processing Pipeline: Groq Whisper Speech-to-Text (STT) and ElevenLabs / Edge-TTS Speech Synthesis.
"""
import logging
import os
import tempfile
import httpx
from typing import Optional, AsyncGenerator
from config import settings

logger = logging.getLogger("agent.audio_service")

# ElevenLabs voice — Arnold (deep, powerful, commanding)
# Browse voices at https://elevenlabs.io/voice-library
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "VR6AewLTigWG4xSOukaG")  # Arnold
ELEVENLABS_MODEL    = "eleven_flash_v2_5"  # lowest latency model


import re

def clean_text_for_speech(raw_text: str) -> str:
    """Clean markdown tags, URLs, and emojis so speech synthesis reads clean, natural prose."""
    if not raw_text:
        return ""
    # Strip markdown links [label](url) -> label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw_text)
    # Strip markdown bold/italic asterisks **bold** -> bold
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    # Convert bullet points at line starts to smooth natural pauses
    text = re.sub(r'^\s*[-•]\s*', '. ', text, flags=re.MULTILINE)
    # Remove raw emojis so TTS engine doesn't stutter or read emoji codes
    text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27ff\u2300-\u23ff]', '', text)
    # Normalize extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class AudioService:
    """
    Asynchronous Speech Pipeline:
    - Transcribes WebM/PCM audio byte streams into text using Groq Whisper API.
    - Synthesizes text responses into MP3 audio bytes using ElevenLabs API.
      Falls back to Edge-TTS if ELEVENLABS_API_KEY is not set.
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
        Synthesize text response into MP3 audio bytes.
        Uses ElevenLabs API if ELEVENLABS_API_KEY is set, otherwise falls back to Edge-TTS.
        """
        if not text:
            return b""

        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return b""

        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")

        # ── ElevenLabs (primary) ──────────────────────────────────────────
        if elevenlabs_key:
            voice_id = voice or ELEVENLABS_VOICE_ID
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": elevenlabs_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            payload = {
                "text": clean_text[:3000],
                "model_id": ELEVENLABS_MODEL,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True,
                },
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    logger.info(f"ElevenLabs TTS: {len(response.content)} bytes")
                    return response.content
            except Exception as e:
                logger.warning(f"ElevenLabs TTS error, falling back to Edge-TTS: {e}")

        # ── Edge-TTS fallback ─────────────────────────────────────────────
        selected_voice = settings.DEFAULT_TTS_VOICE
        try:
            import edge_tts
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            communicate = edge_tts.Communicate(clean_text[:3000], selected_voice)
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                mp3_data = f.read()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return mp3_data
        except Exception as e:
            logger.warning(f"Edge-TTS fallback error: {e}")
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
