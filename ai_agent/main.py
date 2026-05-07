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

from orchestration.agent_executor import run_agent
from orchestration.orchestrator import orchestrate_message
from routers.agent import router as agent_router
from scheduler.scheduler import shutdown_scheduler, start_scheduler
from schemas.agent_schemas import AgentResponse, ChatMessageRequest, VoiceMessageRequest

logger = logging.getLogger(__name__)


def _normalize_patient_id(raw: str | int) -> str:
    pid = str(raw).strip()
    if not pid:
        raise ValueError("patient_id must not be empty")
    return pid


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


@app.post("/voice", response_model=AgentResponse, include_in_schema=False)
async def legacy_voice(req: VoiceMessageRequest) -> AgentResponse:
    return await orchestrate_message(
        patient_id=_normalize_patient_id(req.patient_id),
        message=req.message,
        language=req.language,
        run_agent=run_agent,
    )


@app.post("/chat", include_in_schema=False)
async def legacy_chat(req: ChatMessageRequest) -> dict[str, str]:
    """
    Backward-compatible frontend contract:
    returns { "reply": "<text>" } while also exposing modern fields.
    """
    result = await orchestrate_message(
        patient_id=_normalize_patient_id(req.patient_id),
        message=req.message,
        language=req.language,
        run_agent=run_agent,
    )
    return {
        "reply": result.response,
        "response": result.response,
        "patient_id": result.patient_id,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)