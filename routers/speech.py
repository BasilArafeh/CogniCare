from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

from schemas.speech import STTRequest, TTSRequest
from services.stt_service import transcribe_audio
from services.tts_service import remove_tts_file, synthesize_speech

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post("/stt")
def speech_to_text(payload: STTRequest):
    return transcribe_audio(
        audio_base64=payload.audio_base64,
        mime_type=payload.mime_type,
        language=payload.language,
    )


@router.post("/tts")
def text_to_speech(payload: TTSRequest, background_tasks: BackgroundTasks):
    output_path = synthesize_speech(
        text=payload.text,
        patient_stage=payload.patient_stage,
    )

    background_tasks.add_task(remove_tts_file, output_path)

    media_type = "audio/wav" if output_path.endswith(".wav") else "audio/mpeg"
    filename = "reply.wav" if output_path.endswith(".wav") else "reply.mp3"

    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=filename,
    )