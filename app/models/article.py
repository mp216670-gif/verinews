from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ArticleStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    VERIFIED = "verified"
    FLAGGED = "flagged"


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    source_url = Column(String(1024), nullable=True)
    publisher = Column(String(150), nullable=True, index=True)
    author = Column(String(150), nullable=True)
    category = Column(String(80), default="General", nullable=True, index=True)
    image_url = Column(String(1024), nullable=True)
    published_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT, nullable=False, index=True)

    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    submitter = relationship("User", back_populates="articles")
    claims = relationship("Claim", back_populates="article", cascade="all, delete-orphan")
    verification_reports = relationship("VerificationReport", back_populates="article", cascade="all, delete-orphan")
    trust_scores = relationship("TrustScore", back_populates="article", cascade="all, delete-orphan")
