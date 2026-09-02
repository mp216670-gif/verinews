import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.article import Article, ArticleStatus
from app.models.verification import Claim, VerificationReport, ReviewerDecision
from app.models.trust_score import TrustScore
from app.schemas.verification import (
    ClaimResponse,
    VerificationTrigger,
    VerificationReportResponse,
    ReviewDecisionRequest,
    TrustScoreResponse,
    InstantVerifyRequest,
    InstantVerifyResponse,
)
from app.api.deps import get_current_user, get_optional_current_user, require_role
from app.services.fact_checking.provider import FactCheckManager
from app.services.trust_scoring.scorer import TrustScoringEngine
from app.services.ingestion.url_scraper import UrlScraperAdapter
from app.services.ingestion.text_adapter import TextIngestionAdapter

router = APIRouter()
fact_check_manager = FactCheckManager()
scoring_engine = TrustScoringEngine()
url_scraper = UrlScraperAdapter()
text_adapter = TextIngestionAdapter()


@router.post("/verify-instant", response_model=InstantVerifyResponse)
async def verify_instant_public(
    payload: InstantVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Public Instant Fact-Checking & Verification Endpoint for the General Public:
    - No login, credentials, or API tokens required.
    - Accepts either a web URL or raw news headline & content.
    - Scrapes, analyzes claims, computes transparent trust score, and returns the full verdict in one step.
    """
    url = (payload.url or "").strip()
    content = (payload.content or "").strip()
    title = (payload.title or "").strip()
    publisher = (payload.publisher or "").strip()
    category = payload.category or "General"
    author = None
    published_at = datetime.now(timezone.utc)

    if not url and not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide either an article URL or text content to verify.",
        )

    # 1. Scrape if URL provided
    if url:
        try:
            ingested_items = await url_scraper.ingest(url)
            if ingested_items:
                item = ingested_items[0]
                title = item.title or title or f"Article from {url}"
                content = item.content or content
                publisher = item.publisher or publisher
                author = item.author or author
                published_at = item.published_at or published_at
        except Exception as exc:
            # If scraping fails, continue with fallback if content was supplied
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not retrieve news from the provided URL: {str(exc)}",
                )
    else:
        # 2. Text submission fallback
        if not title:
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            title = lines[0][:120] if lines else "Submitted News Proposition"
        if not publisher:
            publisher = "Public Submission"

    summary = content[:260] + "..." if len(content) > 260 else content

    # 3. Save article record
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

    # 4. Execute claim extraction & fact-checking
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

    # 5. Create Verification Report
    report = VerificationReport(
        article_id=article.id,
        provider_name=result.provider_name,
        provider_verdict=result.provider_verdict,
        claims_count=len(result.claims),
        summary=result.summary,
        reviewer_decision=ReviewerDecision.APPROVED if result.provider_verdict.startswith("Verified") else ReviewerDecision.PENDING,
    )
    db.add(report)
    db.flush()

    # 6. Compute explainable multi-pillar trust score
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

    # Set status
    if score_data["overall_score"] >= 50.0:
        article.status = ArticleStatus.VERIFIED
    else:
        article.status = ArticleStatus.FLAGGED

    db.commit()
    db.refresh(article)

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


@router.post("/{article_id}/verify", response_model=VerificationReportResponse)
async def verify_article(
    article_id: int,
    trigger: Optional[VerificationTrigger] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.REPORTER, UserRole.ADMIN])),
):
    """Run automated fact-checking and calculate an explainable trust score for an article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    provider_name = trigger.provider_name if trigger else "hybrid"

    result = await fact_check_manager.run_verification(
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        publisher=article.publisher,
        provider_preference=provider_name,
    )

    db.query(Claim).filter(Claim.article_id == article.id).delete()
    db.query(TrustScore).filter(TrustScore.article_id == article.id).delete()
    db.query(VerificationReport).filter(VerificationReport.article_id == article.id).delete()

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

    report = VerificationReport(
        article_id=article.id,
        provider_name=result.provider_name,
        provider_verdict=result.provider_verdict,
        claims_count=len(result.claims),
        summary=result.summary,
        reviewer_id=current_user.id,
        reviewer_decision=ReviewerDecision.PENDING,
    )
    db.add(report)
    db.flush()

    score_data = scoring_engine.compute_score(
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        publisher=article.publisher,
        author=article.author,
        published_at=article.published_at,
        claims=saved_claims,
        reviewer_adjustment=0.0,
        reviewer_decision=ReviewerDecision.PENDING,
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

    if score_data["overall_score"] >= 50.0:
        article.status = ArticleStatus.VERIFIED
    else:
        article.status = ArticleStatus.FLAGGED

    db.commit()
    db.refresh(report)

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

    return VerificationReportResponse(
        id=report.id,
        article_id=report.article_id,
        provider_name=report.provider_name,
        provider_verdict=report.provider_verdict,
        claims_count=report.claims_count,
        summary=report.summary,
        reviewer_id=report.reviewer_id,
        reviewer_decision=report.reviewer_decision,
        reviewer_notes=report.reviewer_notes,
        created_at=report.created_at,
        claims=claim_responses,
    )


@router.get("/{article_id}/report", response_model=VerificationReportResponse)
def get_verification_report(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieve the verification report and claims for an article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    report = (
        db.query(VerificationReport)
        .filter(VerificationReport.article_id == article_id)
        .order_by(VerificationReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found for this article")

    claims = db.query(Claim).filter(Claim.article_id == article_id).all()
    claim_responses = [
        ClaimResponse(
            id=c.id,
            claim_text=c.claim_text,
            verdict=c.verdict,
            confidence=c.confidence,
            evidence_sources=c.evidence_sources,
            explanation=c.explanation,
        )
        for c in claims
    ]

    return VerificationReportResponse(
        id=report.id,
        article_id=report.article_id,
        provider_name=report.provider_name,
        provider_verdict=report.provider_verdict,
        claims_count=report.claims_count,
        summary=report.summary,
        reviewer_id=report.reviewer_id,
        reviewer_decision=report.reviewer_decision,
        reviewer_notes=report.reviewer_notes,
        created_at=report.created_at,
        claims=claim_responses,
    )


@router.get("/{article_id}/trust-score", response_model=TrustScoreResponse)
def get_trust_score(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieve the explainable trust score and audit trail for an article."""
    score = (
        db.query(TrustScore)
        .filter(TrustScore.article_id == article_id)
        .order_by(TrustScore.calculated_at.desc())
        .first()
    )
    if not score:
        raise HTTPException(status_code=404, detail="Trust score not yet computed for this article")

    explanation_data = score.explanation
    if isinstance(explanation_data, str):
        try:
            explanation_data = json.loads(explanation_data)
        except Exception:
            pass

    return TrustScoreResponse(
        id=score.id,
        article_id=score.article_id,
        overall_score=score.overall_score,
        grade=score.grade,
        source_reliability_score=score.source_reliability_score,
        corroboration_score=score.corroboration_score,
        claim_verification_score=score.claim_verification_score,
        recency_score=score.recency_score,
        reviewer_adjustment=score.reviewer_adjustment,
        explanation=explanation_data,
        calculated_at=score.calculated_at,
    )


@router.post("/{article_id}/review", response_model=TrustScoreResponse)
def review_article_verification(
    article_id: int,
    review_in: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.REPORTER, UserRole.ADMIN])),
):
    """Human-in-the-loop review: Approve, override, or adjust the verification verdict."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    report = (
        db.query(VerificationReport)
        .filter(VerificationReport.article_id == article_id)
        .order_by(VerificationReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=400, detail="Run verification before submitting a review")

    report.reviewer_id = current_user.id
    report.reviewer_decision = review_in.decision
    report.reviewer_notes = review_in.notes

    if review_in.decision == ReviewerDecision.APPROVED:
        article.status = ArticleStatus.VERIFIED
    elif review_in.decision == ReviewerDecision.REJECTED:
        article.status = ArticleStatus.FLAGGED

    claims = db.query(Claim).filter(Claim.article_id == article_id).all()
    score_data = scoring_engine.compute_score(
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        publisher=article.publisher,
        author=article.author,
        published_at=article.published_at,
        claims=claims,
        reviewer_adjustment=review_in.score_adjustment or 0.0,
        reviewer_decision=review_in.decision,
        reviewer_notes=review_in.notes,
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
        reviewer_adjustment=review_in.score_adjustment or 0.0,
        explanation=json.dumps(score_data["explanation"]),
    )
    db.add(trust_score)
    db.commit()
    db.refresh(trust_score)

    return TrustScoreResponse(
        id=trust_score.id,
        article_id=trust_score.article_id,
        overall_score=trust_score.overall_score,
        grade=trust_score.grade,
        source_reliability_score=trust_score.source_reliability_score,
        corroboration_score=trust_score.corroboration_score,
        claim_verification_score=trust_score.claim_verification_score,
        recency_score=trust_score.recency_score,
        reviewer_adjustment=trust_score.reviewer_adjustment,
        explanation=score_data["explanation"],
        calculated_at=trust_score.calculated_at,
    )
