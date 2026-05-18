import asyncio
import logging
import os

import requests as http_requests
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from core.config import settings
from schemas.speech import STTResponse, TTSRequest
from services.stt_service import transcribe
from services.tts_service import remove_tts_file, synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])

GENERATED_AUDIO_DIR = "generated_audio"


async def _delayed_remove(path: str) -> None:
    await asyncio.sleep(120)
    remove_tts_file(path)

@router.post("/voice")
async def voice_pipeline(
    request: Request,
    background_tasks: BackgroundTasks,
    patient_id: int = Form(...),
    audio: UploadFile = File(...),
):
    logger.info("[VOICE] patient_id=%s filename=%s content_type=%s size=%s",
                patient_id, audio.filename, audio.content_type, audio.size)

    logger.info("[VOICE] step 1/3 — running STT")
    stt_result = await transcribe(audio)
    transcript = stt_result["text"]  # for the agent / logging
    language = stt_result.get("language", "en")
    logger.info("[VOICE] STT done — language=%s transcript=%r", language, transcript)

    logger.info("[VOICE] step 2/3 — calling AI agent (url=%s)", settings.AI_AGENT_URL)
    reply_text = transcript
    if settings.AI_AGENT_URL:
        try:
            agent_response = await asyncio.to_thread(
                http_requests.post,
                f"{settings.AI_AGENT_URL}/agent/voice",
                json={"patient_id": patient_id, "message": transcript, "language": language},
                timeout=30,
            )
            agent_response.raise_for_status()
            agent_data = agent_response.json()
            reply_text = agent_data.get("response") or agent_data.get("text") or transcript
            logger.info("[VOICE] agent replied — reply_text=%r", reply_text)
        except Exception as exc:
            logger.warning("[VOICE] agent call failed (%s) — falling back to transcript", exc)
    else:
        logger.info("[VOICE] AI_AGENT_URL not set — skipping agent, echoing transcript")

    # Always synthesize the assistant reply — never the user's raw utterance (original_text).
    logger.info("[VOICE] step 3/3 — running TTS in language=%s reply_text=%r", language, reply_text)
    audio_path = await asyncio.to_thread(synthesize_speech, reply_text, patient_id, language)
    logger.info("[VOICE] TTS done — audio_path=%s", audio_path)

    filename = os.path.basename(audio_path)
    audio_url = str(request.base_url) + f"speech/audio/{filename}"
    logger.info("[VOICE] step 3/3 — returning audio_url=%s", audio_url)

    background_tasks.add_task(_delayed_remove, audio_path)

    return {
        "transcript": transcript,
        "reply_text": reply_text,
        "audio_url": audio_url,
    }


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(GENERATED_AUDIO_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    media_type = "audio/wav" if file_path.endswith(".wav") else "audio/mpeg"
    return FileResponse(file_path, media_type=media_type)