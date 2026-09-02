from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class TrustScore(Base):
    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    verification_report_id = Column(Integer, ForeignKey("verification_reports.id"), nullable=True)

    overall_score = Column(Float, nullable=False)  # 0.0 to 100.0
    grade = Column(String(5), nullable=False)      # A, B, C, D
    source_reliability_score = Column(Float, nullable=False)
    corroboration_score = Column(Float, nullable=False)
    claim_verification_score = Column(Float, nullable=False)
    recency_score = Column(Float, nullable=False)
    reviewer_adjustment = Column(Float, default=0.0, nullable=False)

    explanation = Column(Text, nullable=False)  # JSON-encoded explainable breakdown and audit trail
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    article = relationship("Article", back_populates="trust_scores")
    verification_report = relationship("VerificationReport", back_populates="trust_scores")
