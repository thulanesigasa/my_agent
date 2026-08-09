"""
LLM Factory Module: Provides Chat Model initializers for Groq, Gemini 1.5 Pro, and OpenRouter fallback.
"""
import logging
from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.chat_models import ChatOpenAI
from config import settings

logger = logging.getLogger("agent.llm_factory")


def get_triage_llm() -> BaseChatModel:
    """
    Returns ChatOpenAI pointed to Groq's OpenAI-compatible API endpoint
    using Llama 3.3 70B for fast intent triage and routing.
    """
    if settings.GROQ_API_KEY:
        try:
            return ChatOpenAI(
                model=settings.GROQ_MODEL,
                openai_api_key=settings.GROQ_API_KEY,
                openai_api_base="https://api.groq.com/openai/v1",
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Groq Triage LLM: {e}. Falling back to OpenRouter.")

    return get_fallback_llm()


def get_drafting_llm() -> BaseChatModel:
    """
    Returns ChatGoogleGenerativeAI (or ChatOpenAI fallback) using model Gemini 1.5 Pro
    for long-context reasoning and response synthesis.
    """
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_output_tokens=2048,
            )
        except Exception as e:
            logger.warning(f"langchain_google_genai import/init warning: {e}. Using ChatOpenAI / Groq endpoint for drafting.")
            if settings.GROQ_API_KEY:
                return get_triage_llm()

    return get_fallback_llm()


def get_fallback_llm() -> BaseChatModel:
    """
    Returns ChatOpenAI pointed to OpenRouter API endpoint as universal fallback model.
    """
    if settings.OPENROUTER_API_KEY:
        try:
            return ChatOpenAI(
                model=settings.OPENROUTER_MODEL,
                openai_api_key=settings.OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.5,
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter LLM: {e}")

    # Fallback to local default ChatOpenAI instance
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        openai_api_key="mock-key",
        temperature=0.3
    )


class LLMFactory:
    """
    Unified execution helper with exception handling and fallback mechanism.
    """

    @staticmethod
    async def invoke_triage(prompt: str, system_prompt: str = "") -> str:
        """
        Execute triage invocation using Groq Llama 3.3 70B with fallback handling.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            llm = get_triage_llm()
            res = await llm.ainvoke(messages)
            return res.content if hasattr(res, "content") else str(res)
        except Exception as e:
            logger.error(f"Primary triage LLM failed: {e}. Executing fallback LLM...")
            try:
                fallback_llm = get_fallback_llm()
                res = await fallback_llm.ainvoke(messages)
                return res.content if hasattr(res, "content") else str(res)
            except Exception as fb_err:
                logger.error(f"Fallback LLM failed: {fb_err}")
                return '{"intent": "general", "needs_human_approval": false, "reason": "Fallback triage executed"}'

    @staticmethod
    async def invoke_drafter(prompt: str, system_prompt: str = "") -> str:
        """
        Execute drafting invocation using Gemini 1.5 Pro with fallback handling.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            llm = get_drafting_llm()
            res = await llm.ainvoke(messages)
            return res.content if hasattr(res, "content") else str(res)
        except Exception as e:
            logger.error(f"Primary drafting LLM failed: {e}. Executing fallback LLM...")
            try:
                fallback_llm = get_fallback_llm()
                res = await fallback_llm.ainvoke(messages)
                return res.content if hasattr(res, "content") else str(res)
            except Exception as fb_err:
                logger.error(f"Fallback LLM failed: {fb_err}")
                return "Thank you for reaching out. Our autonomous agent system is processing your inquiry."


llm_factory = LLMFactory()
