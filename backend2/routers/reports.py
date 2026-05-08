import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from services.report_service import build_patient_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/patient/{patient_id}/pdf", response_class=FileResponse)
def get_patient_pdf(patient_id: int):
    file_path = build_patient_report_pdf(patient_id)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )
