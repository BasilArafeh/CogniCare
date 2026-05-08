from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    role: str
    profile_id: int
    patient_id: int | None = None
    full_name: str

class CaregiverSignupRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    contact_no: str
    role: str
    patient_id: int


class CaregiverSignupResponse(BaseModel):
    message: str
    caregiver_id: int
    auth_user_id: str