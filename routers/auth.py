from fastapi import APIRouter, Depends
from schemas.auth import LoginRequest
from services.auth_service import login_patient, login_caregiver
from core.security import get_current_auth_user, require_patient, require_caregiver
from schemas.auth import CaregiverSignupRequest, CaregiverSignupResponse
from services.auth_service import signup_caregiver

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/patient/login")
def patient_login(payload: LoginRequest):
    return login_patient(payload.email, payload.password)


@router.post("/caregiver/login")
def caregiver_login(payload: LoginRequest):
    return login_caregiver(payload.email, payload.password)

@router.post("/caregiver/signup", response_model=CaregiverSignupResponse)
def caregiver_signup(payload: CaregiverSignupRequest):
    return signup_caregiver(payload)


@router.get("/me")
def me(current_user=Depends(get_current_auth_user)):
    return current_user


@router.get("/patient/me")
def patient_me(patient=Depends(require_patient)):
    return patient


@router.get("/caregiver/me")
def caregiver_me(caregiver=Depends(require_caregiver)):
    return caregiver