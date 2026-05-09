from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    DATABASE_URL: str | None = None

    OPENAI_API_KEY: str | None = None

    ELEVENLABS_API_KEY: str | None = None
    ELEVENLABS_VOICE_ID: str | None = None
    ELEVENLABS_VOICE_ID_EN: str | None = None
    ELEVENLABS_VOICE_ID_AR: str | None = None

    SPEECH_MOCK_MODE: str = "false"

    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_PHONE_NUMBER: str | None = None
    TWILIO_MOCK_MODE: str = "true"
    TWILIO_REPLY_TIMEOUT_MINUTES: int = 5
    APP_BASE_URL: str | None = None

    AI_AGENT_URL: str | None = None

    OPENAI_REPORT_MODEL: str = "gpt-5.5"
    REPORT_WINDOW_DAYS: int = 5

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        extra="ignore",
    )


settings = Settings()