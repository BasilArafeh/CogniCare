from pydantic import BaseModel


class STTRequest(BaseModel):
    audio_base64: str
    mime_type: str | None = None
    language: str | None = None


class TTSRequest(BaseModel):
    text: str
    patient_stage: str | None = None


class TTSInfoResponse(BaseModel):
    message: str
    audio_file: str
    source: str