import asyncio
import logging
import os

import requests as http_requests
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from core.config import settings
from schemas.speech import STTResponse, TTSRequest
from services.stt_service import transcribe_audio_file
from services.tts_service import remove_tts_file, synthesize_speech

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])

GENERATED_AUDIO_DIR = "generated_audio"


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
):
    logger.info("[STT] patient_id=%s filename=%s content_type=%s", patient_id, file.filename, file.content_type)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    result = await transcribe_audio_file(file)
    logger.info("[STT] transcript=%r language=%s", result["text"], result.get("language"))

    return {
        "patient_id": patient_id,
        "text": result["text"],
        "language": result.get("language"),
    }


@router.post("/tts")
def text_to_speech(payload: TTSRequest, background_tasks: BackgroundTasks):
    logger.info("[TTS] patient_id=%s language=%s text=%r", payload.patient_id, payload.language, payload.text)

    output_path = synthesize_speech(
        text=payload.text,
        patient_id=payload.patient_id,
        language=payload.language,
    )
    logger.info("[TTS] audio written to %s", output_path)

    background_tasks.add_task(remove_tts_file, output_path)

    media_type = "audio/wav" if output_path.endswith(".wav") else "audio/mpeg"
    filename = "reply.wav" if output_path.endswith(".wav") else "reply.mp3"

    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=filename,
    )


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
    stt_result = await transcribe_audio_file(audio)
    transcript = stt_result["text"]           # always English (for the agent)
    language = stt_result.get("language", "en")
    tts_text = stt_result.get("original_text", transcript)  # original language for TTS
    logger.info("[VOICE] STT done — language=%s transcript=%r tts_text=%r", language, transcript, tts_text)

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

    tts_text = reply_text if language == "en" else stt_result.get("original_text", reply_text)

    logger.info("[VOICE] step 3/3 — running TTS in language=%s tts_text=%r", language, tts_text)
    audio_path = await asyncio.to_thread(synthesize_speech, tts_text, patient_id, language)
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