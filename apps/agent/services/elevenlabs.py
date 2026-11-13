"""Bounded ElevenLabs API transport. Secrets never leave the server API host."""

import re
import httpx
from config import settings


class VoiceUnavailable(RuntimeError):
    pass


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value or ""):
        raise VoiceUnavailable("Configure a valid ElevenLabs resource ID locally")
    return value


async def request(method, path, *, json=None, files=None, data=None, maximum=8_000_000):
    if not settings.ELEVENLABS_API_KEY:
        raise VoiceUnavailable("ELEVENLABS_API_KEY is not configured")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            async with client.stream(
                method,
                "https://api.elevenlabs.io/v1/" + path,
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
                json=json,
                files=files,
                data=data,
            ) as response:
                response.raise_for_status()
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > maximum:
                        raise VoiceUnavailable(
                            "ElevenLabs response exceeded the local size limit"
                        )
                return bytes(chunks)
    except VoiceUnavailable:
        raise
    except Exception as exc:
        # Do not expose provider body, key-bearing request headers or contact data.
        raise VoiceUnavailable(
            "ElevenLabs request failed; check account configuration and allowance"
        ) from exc
