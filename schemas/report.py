from pydantic import BaseModel


class ReportGenerateResponse(BaseModel):
    file_name: str
    file_type: str = "application/pdf"