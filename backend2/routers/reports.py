from fastapi import APIRouter
from fastapi.responses import FileResponse

from schemas.report import ReportGenerateResponse
from services.report_service import (
    build_patient_report_pdf,
    build_report_metadata,
    get_report_file_path,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/patient/{patient_id}/generate", response_model=ReportGenerateResponse)
def generate_patient_report(patient_id: int):
    file_path = build_patient_report_pdf(patient_id)
    return build_report_metadata(file_path)


@router.get("/files/{file_name}")
def get_report_file(file_name: str):
    file_path = get_report_file_path(file_name)

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_name,
    )