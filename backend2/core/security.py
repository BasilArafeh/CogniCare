from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import (
    verify_access_token,
    get_patient_by_auth_user_id,
    get_caregiver_by_auth_user_id,
)

bearer_scheme = HTTPBearer()


def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    return verify_access_token(credentials.credentials)


def require_patient(current_user=Depends(get_current_auth_user)):
    patient = get_patient_by_auth_user_id(current_user["auth_user_id"])
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required",
        )
    return patient


def require_caregiver(current_user=Depends(get_current_auth_user)):
    caregiver = get_caregiver_by_auth_user_id(current_user["auth_user_id"])
    if not caregiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caregiver access required",
        )
    return caregiver