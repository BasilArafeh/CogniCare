import logging
import os
from contextlib import asynccontextmanager

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

import routers.agent_test as agent_test
import routers.auth as auth
import routers.patients as patients
import routers.reports as reports
import routers.speech as speech
import routers.system as system
import routers.twilio_router as twilio_router
import routers.twilio_webhooks as twilio_webhooks
from services.twilio_service import escalate_stale_alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(
        timezone=pytz.timezone((os.getenv("SCHEDULER_TIMEZONE") or "Asia/Amman").strip())
    )
    scheduler.add_job(escalate_stale_alerts, IntervalTrigger(seconds=10))
    scheduler.start()
    logger.info("Twilio escalation scheduler started")
    yield
    scheduler.shutdown(wait=True)
    logger.info("Twilio escalation scheduler stopped")


app = FastAPI(lifespan=lifespan)

from core.config import settings

logger.info(
    "=== STARTUP: SPEECH_MOCK_MODE=%s | ELEVENLABS_VOICE_ID_EN=%s ===",
    settings.SPEECH_MOCK_MODE,
    settings.ELEVENLABS_VOICE_ID_EN,
)

app.include_router(system.router)
app.include_router(twilio_router.router)
app.include_router(twilio_router.internal_router)
app.include_router(patients.router)
app.include_router(auth.router)
app.include_router(speech.router)
app.include_router(twilio_webhooks.router)
app.include_router(agent_test.router)
app.include_router(reports.router)
