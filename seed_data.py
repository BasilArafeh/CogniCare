from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


patients_data = [
    {
        "patient": {
            "first_name": "Ahmad",
            "last_name": "Khalil",
            "gender": "Male",
            "dob": "1952-03-14",
            "address": "Amman, Jordan",
            "contact_no": "0791000001",
            "emergency_contact": "0792000001",
            "diagnosis_stage": "Moderate"
        },
        "caregiver": {
            "first_name": "Lina",
            "last_name": "Khalil",
            "contact_no": "0793000001",
            "role": "Primary Caregiver"
        },
        "family_member": {
            "first_name": "Omar",
            "last_name": "Khalil",
            "relationship": "Son",
            "contact_no": "0794000001"
        }
    },
    {
        "patient": {
            "first_name": "Fatima",
            "last_name": "Hassan",
            "gender": "Female",
            "dob": "1948-11-02",
            "address": "Zarqa, Jordan",
            "contact_no": "0791000002",
            "emergency_contact": "0792000002",
            "diagnosis_stage": "Early"
        },
        "caregiver": {
            "first_name": "Maya",
            "last_name": "Hassan",
            "contact_no": "0793000002",
            "role": "Daughter"
        },
        "family_member": {
            "first_name": "Sami",
            "last_name": "Hassan",
            "relationship": "Son",
            "contact_no": "0794000002"
        }
    },
    {
        "patient": {
            "first_name": "Yousef",
            "last_name": "Nasser",
            "gender": "Male",
            "dob": "1945-07-21",
            "address": "Irbid, Jordan",
            "contact_no": "0791000003",
            "emergency_contact": "0792000003",
            "diagnosis_stage": "Severe"
        },
        "caregiver": {
            "first_name": "Rana",
            "last_name": "Nasser",
            "contact_no": "0793000003",
            "role": "Wife"
        },
        "family_member": {
            "first_name": "Hadi",
            "last_name": "Nasser",
            "relationship": "Grandson"
            ,
            "contact_no": "0794000003"
        }
    }
]


def insert_one(table_name: str, payload: dict):
    response = supabase.table(table_name).insert(payload).execute()
    if not response.data:
        raise Exception(f"Insert failed for table {table_name}")
    return response.data[0]


def seed_profile(profile: dict):
    patient = insert_one("patients", profile["patient"])
    patient_id = patient["patient_id"]

    caregiver_payload = {
        **profile["caregiver"],
        "patient_id": patient_id
    }
    insert_one("caregiver", caregiver_payload)

    family_member_payload = {
        **profile["family_member"],
        "patient_id": patient_id
    }
    insert_one("family_member", family_member_payload)

    print(f"Inserted patient_id={patient_id} - {patient['first_name']} {patient['last_name']}")


def main():
    for profile in patients_data:
        seed_profile(profile)
    print("Synthetic data inserted successfully.")


if __name__ == "__main__":
    main()