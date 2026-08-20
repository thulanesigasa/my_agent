"""
LLM Factory & Resilient Provider Integration for T.s Industries Agent.
Provides model instantiations for Groq (Llama 3.3 70B), Gemini 1.5 Pro, and OpenRouter with automatic fallbacks.
Loads T.s Industries company knowledge context dynamically from root knowledge/ directory.
"""
import os
import logging
from pathlib import Path
from typing import Any, Optional

try:
    from langchain_core.language_models.chat_models import BaseChatModel  # type: ignore
except ImportError:
    BaseChatModel = Any  # type: ignore


class _DummyChatOpenAI:
    """Fallback dummy class for static typing and environment safety when langchain is uninstalled."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        class _DummyResponse:
            content = "AI Provider unavailable."
        return _DummyResponse()


try:
    from langchain_openai import ChatOpenAI  # type: ignore
except ImportError:
    try:
        from langchain_community.chat_models import ChatOpenAI  # type: ignore
    except ImportError:
        ChatOpenAI = _DummyChatOpenAI  # type: ignore

from config import settings

logger = logging.getLogger("agent.llm_factory")

_SYSTEM_CONTEXT_CACHE: Optional[str] = None


def _create_openai_compatible_chat(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 2048
) -> Any:
    """
    Helper function to instantiate ChatOpenAI seamlessly across both langchain_openai
    and langchain_community parameter contracts.
    """
    if ChatOpenAI is _DummyChatOpenAI:
        logger.warning("ChatOpenAI class is unavailable.")
        return _DummyChatOpenAI()

    try:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except (TypeError, Exception):
        try:
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"Failed to instantiate ChatOpenAI model '{model}': {e}")
            return _DummyChatOpenAI()


def load_system_context(knowledge_dir: Optional[str] = None) -> str:
    """
    Reads all Markdown files in the knowledge/ directory and concatenates them into a single
    SYSTEM_PROMPT string representing T.s Industries identity, services, and communication rules.
    Caches in memory for fast retrieval.
    """
    global _SYSTEM_CONTEXT_CACHE
    if _SYSTEM_CONTEXT_CACHE is not None and not knowledge_dir:
        return _SYSTEM_CONTEXT_CACHE

    possible_dirs = []
    if knowledge_dir:
        possible_dirs.append(Path(knowledge_dir))

    # Search for root knowledge directory relative to repository structure
    module_root = Path(__file__).resolve().parent.parent.parent.parent
    possible_dirs.extend([
        module_root / "knowledge",
        Path.cwd() / "knowledge",
        Path.cwd().parent / "knowledge",
        Path.cwd().parent.parent / "knowledge",
    ])

    target_dir = None
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            target_dir = d
            break

    if not target_dir:
        logger.warning("Knowledge directory not found. System prompt context will be empty.")
        _SYSTEM_CONTEXT_CACHE = ""
        return _SYSTEM_CONTEXT_CACHE

    context_parts = []
    md_files = sorted(list(target_dir.glob("*.md")))
    for md_path in md_files:
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    context_parts.append(f"=== KNOWLEDGE SOURCE: {md_path.name} ===\n{content}")
        except Exception as e:
            logger.error(f"Error reading knowledge file {md_path}: {e}")

    _SYSTEM_CONTEXT_CACHE = "\n\n".join(context_parts)
    logger.info(f"Loaded {len(md_files)} knowledge context files from {target_dir}")
    return _SYSTEM_CONTEXT_CACHE


def get_triage_llm() -> BaseChatModel:
    """
    Returns ChatOpenAI pointed to Groq's OpenAI-compatible API endpoint
    using Llama 3.3 70B for fast intent triage and routing.
    """
    if settings.GROQ_API_KEY:
        try:
            return _create_openai_compatible_chat(
                model=settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Groq Triage LLM: {e}. Falling back to OpenRouter.")

    return get_fallback_llm()


def get_drafting_llm() -> BaseChatModel:
    """
    Returns high-speed Groq LLM for fast reasoning and sub-second response synthesis.
    Falls back to Gemini or OpenRouter if Groq is unavailable.
    """
    if settings.GROQ_API_KEY:
        try:
            return get_triage_llm()
        except Exception as e:
            logger.warning(f"Groq drafting LLM init warning: {e}")

    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.7,
                max_output_tokens=2048,
            )
        except Exception as e:
            logger.warning(f"langchain_google_genai import/init warning: {e}")

    return get_fallback_llm()



def get_fallback_llm() -> BaseChatModel:
    """
    Returns ChatOpenAI pointed to OpenRouter API endpoint as universal fallback model.
    """
    if settings.OPENROUTER_API_KEY:
        try:
            return _create_openai_compatible_chat(
                model=settings.OPENROUTER_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.7,
                max_tokens=2048,
            )
        except Exception as e:
            logger.error(f"OpenRouter Fallback LLM error: {e}")

    # Default baseline instance
    return _create_openai_compatible_chat(
        model="gpt-3.5-turbo",
        api_key=settings.OPENAI_API_KEY or "dummy_key",
        base_url="https://api.openai.com/v1",
        temperature=0.7,
        max_tokens=2048
    )


class LLMFactory:
    """
    Unified execution helper with T.s Industries system context injection,
    handling model initialization, system context building, and fallbacks.
    """

    async def invoke_triage(self, prompt: str, system_override: Optional[str] = None) -> str:
        """
        Execute triage invocation using Groq Llama 3.3 70B with T.s Industries knowledge context injection.
        """
        system = system_override if system_override else load_system_context()
        try:
            llm = get_triage_llm()
            res = await llm.ainvoke([
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ])
            return res.content if hasattr(res, "content") else str(res)
        except Exception as e:
            logger.error(f"Primary triage LLM failed: {e}. Executing fallback LLM...")
            try:
                fallback_llm = get_fallback_llm()
                res = await fallback_llm.ainvoke([
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ])
                return res.content if hasattr(res, "content") else str(res)
            except Exception as fb_err:
                logger.error(f"Fallback LLM failed: {fb_err}")
                return '{"intent": "general", "needs_human_approval": false, "reason": "Fallback mode"}'

    async def invoke_drafter(self, prompt: str, system_override: Optional[str] = None) -> str:
        """
        Execute drafting invocation using Gemini 1.5 Pro with T.s Industries knowledge context injection.
        """
        system = system_override if system_override else load_system_context()
        try:
            llm = get_drafting_llm()
            res = await llm.ainvoke([
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ])
            return res.content if hasattr(res, "content") else str(res)
        except Exception as e:
            logger.error(f"Primary drafting LLM failed: {e}. Executing fallback LLM...")
            try:
                fallback_llm = get_fallback_llm()
                res = await fallback_llm.ainvoke([
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ])
                return res.content if hasattr(res, "content") else str(res)
            except Exception as fb_err:
                logger.error(f"Fallback LLM failed: {fb_err}")
                return "Thank you for contacting T.s Industries. We build high-performance web and mobile applications. Please visit ts-industries.co.za to request a quotation."


llm_factory = LLMFactory()
