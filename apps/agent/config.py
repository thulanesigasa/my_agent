"""
Pydantic Settings & Environment Variable Secrets Management Module.
"""
import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

logger = logging.getLogger("agent.config")


class Settings(BaseSettings):
    """
    Application Settings & Secret Credentials Manager.
    """
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    SECRET_KEY: str = "super-secret-agent-key"

    # API Security & Authentication
    API_KEY_REQUIRED: bool = False
    AGENT_API_KEY: str = "agent-secret-api-key"

    # Supabase Vector Store & Database
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_SERVICE_ROLE_KEY: str = "your-supabase-service-role-key"
    SUPABASE_DB_URL: Optional[str] = None

    # AI Model API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "groq/compound-mini"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"

    # Lead Discovery / Web Search
    TAVILY_API_KEY: Optional[str] = None

    # Audio Voice Output
    DEFAULT_TTS_VOICE: str = "en-US-AriaNeural"

    # Tools: Gmail & WhatsApp/Twilio
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_USER_EMAIL: Optional[str] = None

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """
        Validate credentials and warn or raise error if critical secrets are missing in production.
        """
        if self.ENV == "production":
            missing = []
            if not self.GROQ_API_KEY and not self.GEMINI_API_KEY and not self.OPENROUTER_API_KEY:
                missing.append("LLM_API_KEYS (GROQ_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY)")
            if not self.SUPABASE_SERVICE_ROLE_KEY:
                missing.append("SUPABASE_SERVICE_ROLE_KEY")

            if missing:
                logger.error(f"CRITICAL PRODUCTION SECURITY WARNING: Missing secrets: {', '.join(missing)}")
                if self.API_KEY_REQUIRED and not self.AGENT_API_KEY:
                    raise ValueError("AGENT_API_KEY must be configured in production when API_KEY_REQUIRED=true")

        return self


settings = Settings()
