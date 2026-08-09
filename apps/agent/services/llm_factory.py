import logging
import httpx
from typing import Optional, Dict, Any, List
from config import settings

logger = logging.getLogger("agent.llm_factory")

class LLMFactory:
    """
    Unified Multi-Model Gateway supporting:
    - Groq API (Llama 3.3 70B for fast triage & intent routing)
    - Google AI Studio (Gemini 1.5 Pro for deep reasoning & drafting)
    - OpenRouter API (Fallback gateway for Claude 3.5 / Llama 3)
    """

    @staticmethod
    async def call_groq(prompt: str, system_prompt: str = "", temperature: float = 0.2) -> str:
        """
        Call Groq API using Llama 3.3 70B for lightning-fast classification and triage.
        """
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY missing. Falling back to synthetic responder.")
            return LLMFactory._synthetic_triage_response(prompt)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Groq API call error: {e}. Trying OpenRouter fallback...")
                return await LLMFactory.call_openrouter(prompt, system_prompt, temperature)

    @staticmethod
    async def call_gemini(prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """
        Call Google AI Studio API (Gemini 1.5 Pro) for long-context drafting and reasoning.
        """
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY missing. Falling back to Groq / OpenRouter.")
            return await LLMFactory.call_groq(prompt, system_prompt, temperature)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        
        full_content = prompt
        if system_prompt:
            full_content = f"System Instructions: {system_prompt}\n\nUser Request: {prompt}"

        payload = {
            "contents": [{
                "parts": [{"text": full_content}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2048
            }
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Gemini API call error: {e}. Trying Groq fallback...")
                return await LLMFactory.call_groq(prompt, system_prompt, temperature)

    @staticmethod
    async def call_openrouter(prompt: str, system_prompt: str = "", temperature: float = 0.5) -> str:
        """
        Call OpenRouter API as high-reliability fallback gateway.
        """
        if not settings.OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY missing. Returning simulated agent response.")
            return f"Processed request: '{prompt}'. Autonomous agent operational."

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://localhost:3000",
            "X-Title": "Autonomous Agent Platform",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"OpenRouter API call error: {e}")
                return LLMFactory._synthetic_triage_response(prompt)

    @staticmethod
    def _synthetic_triage_response(prompt: str) -> str:
        """
        Local fallback when no external LLM keys are configured.
        """
        p_lower = prompt.lower()
        if "email" in p_lower or "send message" in p_lower:
            return '{"intent": "email_dispatch", "confidence": 0.95, "requires_human_approval": true, "reason": "Email dispatch involves external communication."}'
        elif "whatsapp" in p_lower or "text" in p_lower:
            return '{"intent": "whatsapp_dispatch", "confidence": 0.92, "requires_human_approval": true, "reason": "WhatsApp message dispatch requires approval."}'
        else:
            return f"I have processed your query: '{prompt}'. The autonomous agent state graph is active."


llm_factory = LLMFactory()
