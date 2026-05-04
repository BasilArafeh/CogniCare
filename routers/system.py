from fastapi import APIRouter

from db.supabase_client import get_supabase_client

router = APIRouter(tags=["system"])


@router.get("/")
def home():
    return {"message": "FastAPI is working"}


@router.get("/test-db")
def test_db():
    client = get_supabase_client()

    try:
        result = client.table("patients").select("*").execute()
        return {
            "message": "Supabase connection is working",
            "data": result.data,
        }
    except Exception as e:
        return {
            "message": "Supabase connection failed",
            "error": str(e),
        }