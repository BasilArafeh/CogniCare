from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from schemas.speech import STTResponse, TTSRequest
from services.stt_service import transcribe_audio_file
from services.tts_service import remove_tts_file, synthesize_speech

router = APIRouter(prefix="/speech", tags=["speech"])


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    result = await transcribe_audio_file(file)

    return {
        "patient_id": patient_id,
        "text": result["text"],
        "language": result.get("language"),
    }


@router.post("/tts")
def text_to_speech(payload: TTSRequest, background_tasks: BackgroundTasks):
    output_path = synthesize_speech(
        text=payload.text,
        patient_id=payload.patient_id,
        language=payload.language,
    )

    background_tasks.add_task(remove_tts_file, output_path)

    media_type = "audio/wav" if output_path.endswith(".wav") else "audio/mpeg"
    filename = "reply.wav" if output_path.endswith(".wav") else "reply.mp3"

    return FileResponse(
        path=output_path,
        media_type=media_type,
        filename=filename,
    )