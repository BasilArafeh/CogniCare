import logging

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

from routers import (
    agent_test,
    auth,
    notifications,
    patients,
    reports,
    speech,
    system,
    twilio_webhooks,
)

app = FastAPI()

from core.config import settings
logger.info("=== STARTUP: SPEECH_MOCK_MODE=%s | ELEVENLABS_VOICE_ID_EN=%s ===",
            settings.SPEECH_MOCK_MODE, settings.ELEVENLABS_VOICE_ID_EN)

app.include_router(system.router)
app.include_router(patients.router)
app.include_router(auth.router)
app.include_router(speech.router)
app.include_router(notifications.router)
app.include_router(twilio_webhooks.router)
app.include_router(agent_test.router)
app.include_router(reports.router)