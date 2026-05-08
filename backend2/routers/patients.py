from fastapi import APIRouter

from db.supabase_client import get_supabase_client
from schemas.patient import PatientCreate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("/")
def add_patient(patient: PatientCreate):
    client = get_supabase_client()

    try:
        data = patient.model_dump(mode="json")
        result = client.table("patients").insert(data).execute()
        return {
            "message": "Patient added successfully",
            "data": result.data,
        }
    except Exception as e:
        return {
            "message": "Failed to add patient",
            "error": str(e),
        }


@router.delete("/{patient_id}")
def delete_patient(patient_id: int):
    client = get_supabase_client()

    try:
        existing_patient = (
            client.table("patients")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )

        if not existing_patient.data:
            return {"message": "Patient not found"}

        client.table("patients").delete().eq("patient_id", patient_id).execute()

        return {
            "message": f"Patient with ID {patient_id} deleted successfully"
        }
    except Exception as e:
        return {
            "message": "Failed to delete patient",
            "error": str(e),
        }