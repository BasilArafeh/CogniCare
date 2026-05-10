from pydantic import BaseModel


class STTResponse(BaseModel):
    patient_id: int
    text: str
    language: str 


class TTSRequest(BaseModel):
    patient_id: int
    text: str
    language: str
