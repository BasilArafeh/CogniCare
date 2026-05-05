"""
FastAPI entry for CogniCare agent (voice + chat).
Run from ``ai_agent/`` (so package imports resolve): ``python main.py``
or: ``uvicorn main:app --host 0.0.0.0 --port 8000``
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.agent import router as agent_router
from scheduler.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("[app] Starting background scheduler…")
    start_scheduler()
    try:
        yield

    finally:
        logger.info("[app] Shutting down scheduler…")

        shutdown_scheduler()

app = FastAPI(title="CogniCare Agent", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agent_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)