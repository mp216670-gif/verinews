from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ClaimVerdict(str, enum.Enum):
    TRUE = "true"
    FALSE = "false"
    MISLEADING = "misleading"
    UNVERIFIED = "unverified"


class ReviewerDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    verdict = Column(Enum(ClaimVerdict), default=ClaimVerdict.UNVERIFIED, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    evidence_sources = Column(Text, nullable=True)  # JSON-formatted or comma-separated list of evidence URLs
    explanation = Column(Text, nullable=True)

    article = relationship("Article", back_populates="claims")


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    provider_name = Column(String(100), nullable=False)
    provider_verdict = Column(String(50), nullable=False)
    claims_count = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=True)

    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewer_decision = Column(Enum(ReviewerDecision), default=ReviewerDecision.PENDING, nullable=False)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    article = relationship("Article", back_populates="verification_reports")
    reviewer = relationship("User", back_populates="reviewed_reports")
    trust_scores = relationship("TrustScore", back_populates="verification_report", cascade="all, delete-orphan")
