"""Pydantic models for request/response payloads."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ClaimRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Financial claim to verify")


class EvidenceChunk(BaseModel):
    text: str
    source: str
    chunk_index: Optional[int]
    score: float


class VerdictResult(BaseModel):
    verdict: str
    confidence: float
    reasoning: str
    citations: List[str]


class ClaimResponse(BaseModel):
    claim: str
    result: VerdictResult
    evidence: List[EvidenceChunk]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=3)
    session_id: str | None = Field(None, description="Client-provided session id for continuity")
    expand_online: bool | None = Field(True, description="Allow online fallback retrieval")
    days: int | None = Field(None, description="Limit online search to last N days")
    context: str | None = Field(
        None,
        description=(
            "Optional context string from the client (e.g., original claim and verdict) to help disambiguate vague follow-ups."
        ),
    )
    keywords: List[str] | None = Field(
        None,
        description="Optional keyword overrides to narrow live news search (e.g., tickers, entities)",
    )


class ChatResult(BaseModel):
    answer: str
    citations: List[str] = []


class ChatResponse(BaseModel):
    session_id: str
    result: ChatResult
    evidence: List[EvidenceChunk]
