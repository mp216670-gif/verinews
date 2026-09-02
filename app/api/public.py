"""
Public-facing endpoints — no authentication required.
Mounted at /api/v1/public so there is no collision with /articles/{article_id}.
"""
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article, ArticleStatus
from app.models.verification import Claim, VerificationReport, ReviewerDecision
from app.models.trust_score import TrustScore
from app.schemas.verification import (
    ClaimResponse,
    InstantVerifyRequest,
    InstantVerifyResponse,
)
from app.services.fact_checking.provider import FactCheckManager
from app.services.trust_scoring.scorer import TrustScoringEngine
from app.services.ingestion.url_scraper import UrlScraperAdapter

router = APIRouter()
fact_check_manager = FactCheckManager()
scoring_engine = TrustScoringEngine()
url_scraper = UrlScraperAdapter()


@router.post("/verify", response_model=InstantVerifyResponse)
async def public_instant_verify(
    payload: InstantVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    🌐 Public Instant Fact-Check — No login required.
    
    Accepts a news URL or raw headline/content and returns a full explainable
    trust score with claim-by-claim verdicts in a single request.
    """
    url = (payload.url or "").strip()
    content = (payload.content or "").strip()
    title = (payload.title or "").strip()
    publisher = (payload.publisher or "").strip()
    category = payload.category or "General"
    author: Optional[str] = None
    published_at = datetime.now(timezone.utc)

    if not url and not content and not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a news article URL, a headline, or text content to verify.",
        )

    # 1. Scrape if URL provided
    if url:
        try:
            ingested = await url_scraper.ingest(url)
            if ingested:
                item = ingested[0]
                title = item.title or title or f"Article from {url}"
                content = item.content or content
                publisher = item.publisher or publisher or "Web Source"
                author = item.author or author
                published_at = item.published_at or published_at
        except Exception as exc:
            if not content and not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not fetch news from the provided URL: {str(exc)}",
                )

    # 2. Text fallback defaults
    if not title:
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        title = lines[0][:150] if lines else "Submitted News Proposition"
    if not publisher:
        publisher = "Public Submission"
    if not content:
        content = title  # use the headline itself as content for headline-only checks

    summary = content[:260] + "..." if len(content) > 260 else content

    # 3. Persist article record
    article = Article(
        title=title,
        content=content,
        summary=summary,
        source_url=url or None,
        publisher=publisher,
        author=author,
        category=category,
        published_at=published_at,
        status=ArticleStatus.PENDING,
    )
    db.add(article)
    db.flush()

    # 4. Claim extraction & automated fact-checking
    result = await fact_check_manager.run_verification(
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        publisher=article.publisher,
        provider_preference="hybrid",
    )

    saved_claims = []
    for c in result.claims:
        claim_obj = Claim(
            article_id=article.id,
            claim_text=c.text,
            verdict=c.verdict,
            confidence=c.confidence,
            evidence_sources="; ".join(c.evidence_sources) if c.evidence_sources else None,
            explanation=c.explanation,
        )
        db.add(claim_obj)
        saved_claims.append(claim_obj)
    db.flush()

    # 5. Verification report
    report = VerificationReport(
        article_id=article.id,
        provider_name=result.provider_name,
        provider_verdict=result.provider_verdict,
        claims_count=len(result.claims),
        summary=result.summary,
        reviewer_decision=ReviewerDecision.APPROVED
        if result.provider_verdict.startswith("Verified")
        else ReviewerDecision.PENDING,
    )
    db.add(report)
    db.flush()

    # 6. Multi-pillar trust score
    score_data = scoring_engine.compute_score(
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        publisher=article.publisher,
        author=article.author,
        published_at=article.published_at,
        claims=saved_claims,
    )

    trust_score = TrustScore(
        article_id=article.id,
        verification_report_id=report.id,
        overall_score=score_data["overall_score"],
        grade=score_data["grade"],
        source_reliability_score=score_data["source_reliability_score"],
        corroboration_score=score_data["corroboration_score"],
        claim_verification_score=score_data["claim_verification_score"],
        recency_score=score_data["recency_score"],
        reviewer_adjustment=0.0,
        explanation=json.dumps(score_data["explanation"]),
    )
    db.add(trust_score)

    article.status = (
        ArticleStatus.VERIFIED if score_data["overall_score"] >= 50.0 else ArticleStatus.FLAGGED
    )

    db.commit()

    claim_responses = [
        ClaimResponse(
            id=c.id,
            claim_text=c.claim_text,
            verdict=c.verdict,
            confidence=c.confidence,
            evidence_sources=c.evidence_sources,
            explanation=c.explanation,
        )
        for c in saved_claims
    ]

    return InstantVerifyResponse(
        article_id=article.id,
        title=article.title,
        publisher=article.publisher,
        source_url=article.source_url,
        category=article.category,
        summary=article.summary,
        overall_score=score_data["overall_score"],
        grade=score_data["grade"],
        provider_verdict=result.provider_verdict,
        explanation=score_data["explanation"],
        claims=claim_responses,
    )
