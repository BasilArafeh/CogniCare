import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str | None = os.getenv("ELEVENLABS_VOICE_ID")
    SPEECH_MOCK_MODE: str = os.getenv("SPEECH_MOCK_MODE", "true")

    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: str | None = os.getenv("TWILIO_PHONE_NUMBER")
    APP_BASE_URL: str | None = os.getenv("APP_BASE_URL")
    TWILIO_MOCK_MODE: str = os.getenv("TWILIO_MOCK_MODE", "true")
    TWILIO_REPLY_TIMEOUT_MINUTES: int = int(os.getenv("TWILIO_REPLY_TIMEOUT_MINUTES", "10"))


settings = Settings()

if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")