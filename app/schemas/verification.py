from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.verification import ClaimVerdict, ReviewerDecision


class ClaimResponse(BaseModel):
    id: int
    claim_text: str
    verdict: ClaimVerdict
    confidence: float
    evidence_sources: Optional[str] = None
    explanation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VerificationTrigger(BaseModel):
    provider_name: Optional[str] = "hybrid"


class ReviewDecisionRequest(BaseModel):
    decision: ReviewerDecision
    notes: Optional[str] = None
    score_adjustment: Optional[float] = Field(default=0.0, ge=-25.0, le=25.0)


class VerificationReportResponse(BaseModel):
    id: int
    article_id: int
    provider_name: str
    provider_verdict: str
    claims_count: int
    summary: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_decision: ReviewerDecision
    reviewer_notes: Optional[str] = None
    created_at: datetime
    claims: list[ClaimResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TrustScoreResponse(BaseModel):
    id: int
    article_id: int
    overall_score: float
    grade: str
    source_reliability_score: float
    corroboration_score: float
    claim_verification_score: float
    recency_score: float
    reviewer_adjustment: float
    explanation: Any
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstantVerifyRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    publisher: Optional[str] = None
    category: Optional[str] = "General"


class InstantVerifyResponse(BaseModel):
    article_id: int
    title: str
    publisher: Optional[str] = None
    source_url: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    overall_score: float
    grade: str
    provider_verdict: str
    explanation: Any
    claims: list[ClaimResponse] = []
