"""
agent/schemas/agent_schemas.py
--------------------------------
Pydantic models for FastAPI request and response validation.
Used exclusively by api/main.py.

Models:
  - MessageRequest  → validates incoming patient messages (POST /agent/message)
  - AgentResponse   → structures the response sent back to the frontend
"""

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """
    Incoming request from the frontend when a patient sends a message.
    """
    patient_id: int = Field(..., gt=0, description="The active patient's ID.")
    session_id: str = Field(..., min_length=1, description="Unique session identifier for this conversation sitting.")
    message: str = Field(..., min_length=1, max_length=1000, description="The patient's message text.")


class AgentResponse(BaseModel):
    """
    Response sent back to the frontend after every agent turn.
    """
    response: str = Field(..., description="The agent's reply in patient-friendly language.")
    intent: str = Field(..., description="The detected route — DB, RAG, DB_RAG, LLM, CLARIFY, or EMERGENCY.")
    session_id: str = Field(..., description="Echoed back so the frontend can continue the session.")