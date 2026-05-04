from fastapi import APIRouter

router = APIRouter(prefix="/agent-test", tags=["agent-test"])


@router.post("/caregiver-response")
def caregiver_response(payload: dict):
    print("AGENT CALLBACK RECEIVED:", payload)
    return {"ok": True, "received": payload}