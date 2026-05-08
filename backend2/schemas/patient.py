from datetime import date

from pydantic import BaseModel


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    gender: str
    dob: date
    address: str
    contact_no: str
    emergency_contact: str
    diagnosis_stage: str