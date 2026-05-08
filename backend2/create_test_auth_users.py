from db.supabase_client import get_supabase_admin_client


def create_and_link_caregiver():
    client = get_supabase_admin_client()

    user = client.auth.admin.create_user(
        {
            "email": "caregiver1@example.com",
            "password": "Caregiver123!",
            "email_confirm": True,
        }
    )

    auth_user_id = user.user.id

    result = (
        client.table("caregiver")
        .update({"auth_user_id": auth_user_id})
        .eq("contact_no", "0793000001")
        .execute()
    )

    print("Caregiver linked:", result.data)


def create_and_link_patient():
    client = get_supabase_admin_client()

    user = client.auth.admin.create_user(
        {
            "email": "patient1@example.com",
            "password": "Patient123!",
            "email_confirm": True,
        }
    )

    auth_user_id = user.user.id

    result = (
        client.table("patients")
        .update({"auth_user_id": auth_user_id})
        .eq("contact_no", "0791000001")
        .execute()
    )

    print("Patient linked:", result.data)


if __name__ == "__main__":
    create_and_link_caregiver()
    create_and_link_patient()