from pydantic import BaseModel


class STTResponse(BaseModel):
    patient_id: int
    text: str
    language: str | None = None


class TTSRequest(BaseModel):
    patient_id: int
    text: str
    language: str