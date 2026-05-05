"""Simple request/response schemas for the agent."""

from typing import Literal

from pydantic import BaseModel, Field


IntentRoute = Literal["DB", "RAG", "DB_RAG", "LLM", "CLARIFY", "EMERGENCY"]


class VoiceMessageRequest(BaseModel):
    """Voice request after STT."""

    patient_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="en")


class ChatMessageRequest(BaseModel):
    """Chat request from the app."""

    patient_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="en")


class AgentResponse(BaseModel):
    """Final reply to the caller."""

    response: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)


__all__ = [
    "AgentResponse",
    "ChatMessageRequest",
    "IntentRoute",
    "VoiceMessageRequest",
]
