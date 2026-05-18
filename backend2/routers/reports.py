import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from db.supabase_client import get_supabase_client
from services.report_service import build_patient_report_pdf, get_report_file_path

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/patient/{patient_id}/pdf", response_class=FileResponse)
def get_patient_pdf(patient_id: int):
    file_path = build_patient_report_pdf(patient_id)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )


@router.get("/{report_id}/pdf", response_class=FileResponse)
def get_report_by_id(report_id: int):
    client = get_supabase_client()
    result = client.table("report").select("*").eq("report_id", report_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found.")

    row = result.data[0]
    desc = row.get("description") or "{}"
    if isinstance(desc, str):
        desc = json.loads(desc)

    # Prefer storage URL — persists across server restarts
    storage_url = desc.get("storage_url", "")
    if storage_url:
        return RedirectResponse(url=storage_url)

    # Fall back to local disk
    file_name = desc.get("file_name", "")
    if file_name:
        try:
            file_path = get_report_file_path(file_name)
            return FileResponse(path=file_path, media_type="application/pdf", filename=file_name)
        except HTTPException:
            pass

    # File missing — find patient_id via caregiver_priority and regenerate
    caregiver_id = row.get("caregiver_id")
    if not caregiver_id:
        raise HTTPException(status_code=404, detail="Cannot regenerate: no caregiver_id on report.")
    cp = client.table("caregiver_priority").select("patient_id").eq("caregiver_id", caregiver_id).limit(1).execute()
    if not cp.data:
        raise HTTPException(status_code=404, detail="Cannot regenerate: no patient linked to caregiver.")
    patient_id = cp.data[0]["patient_id"]
    file_path = build_patient_report_pdf(patient_id)
    return FileResponse(path=file_path, media_type="application/pdf", filename=os.path.basename(file_path))
