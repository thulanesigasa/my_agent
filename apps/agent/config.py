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
    WEBHOOK_SECRET: str = ""
    ENABLE_SCHEDULER: bool = False
    STATE_DB_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "agent.sqlite3"
    )

    # Supabase Vector Store & Database
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: Optional[str] = None

    # AI Model API Keys
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
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
        env_file=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """
        Validate credentials and warn or raise error if critical secrets are missing in production.
        """
        if bool(self.SUPABASE_URL) != bool(self.SUPABASE_SERVICE_ROLE_KEY):
            raise ValueError(
                "Configure both Supabase URL and service role key, or leave both empty for local storage"
            )
        if self.ENV == "production" and (
            not self.API_KEY_REQUIRED
            or self.AGENT_API_KEY in ("", "agent-secret-api-key", "your-agent-api-key")
        ):
            raise ValueError(
                "Production requires API_KEY_REQUIRED=true and a non-default AGENT_API_KEY"
            )

        return self


settings = Settings()
