from pydantic import BaseModel, HttpUrl


class SendCaregiverAlertRequest(BaseModel):
    patient_id: int
    message: str
    callback_url: HttpUrl


class AgentAlertSessionResponse(BaseModel):
    patient_id: int
    caregiver_id: int | None = None
    responded: bool