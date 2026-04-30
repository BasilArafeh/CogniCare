"""
Request and response shapes for the agent API (e.g. POST /agent/message).
"""

from typing import Literal

from pydantic import BaseModel, Field


IntentRoute = Literal["DB", "RAG", "DB_RAG", "LLM", "CLARIFY", "EMERGENCY"]


class MessageRequest(BaseModel):
    """One message from the client."""

    patient_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=1000)


class AgentResponse(BaseModel):
    """One reply back to the client after a turn."""

    response: str
    intent: IntentRoute
    session_id: str
    patient_id: str
    emergency_escalated: bool = False
    confusion_flag: bool = False


__all__ = ["AgentResponse", "IntentRoute", "MessageRequest"]
