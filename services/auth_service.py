from fastapi import HTTPException, status

from db.supabase_client import get_supabase_admin_client, get_supabase_client
from schemas.auth import CaregiverSignupRequest


def _first_or_none(rows):
    return rows[0] if rows else None


def _login_with_email(email: str, password: str):
    client = get_supabase_client()

    try:
        response = client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from e

    if not getattr(response, "user", None) or not getattr(response, "session", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed",
        )

    return response


def get_patient_by_auth_user_id(auth_user_id: str):
    client = get_supabase_client()
    result = (
        client.table("patients")
        .select("*")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
    )
    return _first_or_none(result.data)


def get_caregiver_by_auth_user_id(auth_user_id: str):
    client = get_supabase_client()
    result = (
        client.table("caregiver")
        .select("*")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
    )
    return _first_or_none(result.data)


def verify_access_token(token: str):
    client = get_supabase_client()

    try:
        response = client.auth.get_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from e

    user = getattr(response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user token",
        )

    return {
        "auth_user_id": user.id,
        "phone": getattr(user, "phone", None),
        "email": getattr(user, "email", None),
    }


def login_patient(email: str, password: str):
    auth_response = _login_with_email(email, password)
    user = auth_response.user
    session = auth_response.session

    patient = get_patient_by_auth_user_id(user.id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not linked to a patient profile",
        )

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "role": "patient",
        "profile_id": patient["patient_id"],
        "patient_id": patient["patient_id"],
        "full_name": f"{patient['first_name']} {patient['last_name']}",
    }


def login_caregiver(email: str, password: str):
    auth_response = _login_with_email(email, password)
    user = auth_response.user
    session = auth_response.session

    caregiver = get_caregiver_by_auth_user_id(user.id)
    if not caregiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not linked to a caregiver profile",
        )

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "role": "caregiver",
        "profile_id": caregiver["caregiver_id"],
        "patient_id": caregiver["patient_id"],
        "full_name": f"{caregiver['first_name']} {caregiver['last_name']}",
    }

def signup_caregiver(payload: CaregiverSignupRequest) -> dict:
    admin_client = get_supabase_admin_client()
    db_client = get_supabase_client()

    # Check that patient exists
    patient_result = (
        db_client.table("patients")
        .select("*")
        .eq("patient_id", payload.patient_id)
        .limit(1)
        .execute()
    )

    if not patient_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Optional duplicate caregiver check
    existing_caregiver = (
        db_client.table("caregiver")
        .select("*")
        .eq("contact_no", payload.contact_no)
        .eq("patient_id", payload.patient_id)
        .limit(1)
        .execute()
    )

    if existing_caregiver.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A caregiver with this contact number is already registered for this patient",
        )

    # Create Supabase Auth user
    try:
        auth_response = admin_client.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.password,
                "email_confirm": True,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create caregiver auth account: {str(e)}",
        )

    user = getattr(auth_response, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase did not return a created auth user",
        )

    auth_user_id = user.id

    # Create caregiver profile row
    try:
        caregiver_result = (
            db_client.table("caregiver")
            .insert(
                {
                    "patient_id": payload.patient_id,
                    "first_name": payload.first_name,
                    "last_name": payload.last_name,
                    "contact_no": payload.contact_no,
                    "role": payload.role,
                    "auth_user_id": auth_user_id,
                }
            )
            .execute()
        )
    except Exception as e:
        # Cleanup auth user if profile insert fails
        try:
            admin_client.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create caregiver profile: {str(e)}",
        )

    if not caregiver_result.data:
        try:
            admin_client.auth.admin.delete_user(auth_user_id)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Caregiver profile creation failed",
        )

    caregiver = caregiver_result.data[0]

    return {
        "message": "Caregiver account created successfully. The caregiver can now log in.",
        "caregiver_id": caregiver["caregiver_id"],
        "auth_user_id": auth_user_id,
    }