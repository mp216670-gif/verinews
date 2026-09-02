import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.article import Article, ArticleStatus
from app.models.trust_score import TrustScore
from app.schemas.article import (
    ArticleCreate,
    ArticleIngestUrl,
    ArticleIngestRss,
    ArticleResponse,
    ArticleListResponse,
)
from app.schemas.verification import TrustScoreResponse
from app.api.deps import get_current_user, get_optional_current_user, require_role
from app.services.ingestion.url_scraper import UrlScraperAdapter
from app.services.ingestion.rss_adapter import RssFeedAdapter

router = APIRouter()


def _format_article_response(article: Article, db: Session) -> ArticleResponse:
    latest_score = (
        db.query(TrustScore)
        .filter(TrustScore.article_id == article.id)
        .order_by(TrustScore.calculated_at.desc())
        .first()
    )
    score_resp = None
    if latest_score:
        explanation_data = latest_score.explanation
        if isinstance(explanation_data, str):
            try:
                explanation_data = json.loads(explanation_data)
            except Exception:
                pass

        score_resp = TrustScoreResponse(
            id=latest_score.id,
            article_id=latest_score.article_id,
            overall_score=latest_score.overall_score,
            grade=latest_score.grade,
            source_reliability_score=latest_score.source_reliability_score,
            corroboration_score=latest_score.corroboration_score,
            claim_verification_score=latest_score.claim_verification_score,
            recency_score=latest_score.recency_score,
            reviewer_adjustment=latest_score.reviewer_adjustment,
            explanation=explanation_data,
            calculated_at=latest_score.calculated_at,
        )

    return ArticleResponse(
        id=article.id,
        title=article.title,
        content=article.content,
        summary=article.summary,
        source_url=article.source_url,
        publisher=article.publisher,
        author=article.author,
        category=article.category or "General",
        image_url=article.image_url,
        published_at=article.published_at,
        status=article.status,
        submitter_id=article.submitter_id,
        created_at=article.created_at,
        updated_at=article.updated_at,
        latest_trust_score=score_resp,
    )


@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(
    article_in: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.REPORTER, UserRole.ADMIN])),
):
    """Submit a news article for verification (Reporters and Admins only)."""
    article = Article(
        title=article_in.title,
        content=article_in.content,
        summary=article_in.summary,
        source_url=article_in.source_url,
        publisher=article_in.publisher or "Independent Submission",
        author=article_in.author,
        category=article_in.category or "General",
        image_url=article_in.image_url,
        published_at=article_in.published_at or datetime.now(timezone.utc),
        status=ArticleStatus.PENDING,
        submitter_id=current_user.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return _format_article_response(article, db)


@router.post("/ingest-url", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_url(
    payload: ArticleIngestUrl,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.REPORTER, UserRole.ADMIN])),
):
    """Scrape and ingest an article directly from a live web URL (Reporters and Admins only)."""
    scraper = UrlScraperAdapter()
    try:
        ingested_list = await scraper.ingest(payload.url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to scrape URL: {str(exc)}",
        )

    if not ingested_list:
        raise HTTPException(status_code=400, detail="No article content found at the provided URL.")

    item = ingested_list[0]
    article = Article(
        title=item.title,
        content=item.content,
        summary=item.summary,
        source_url=item.source_url,
        publisher=item.publisher,
        author=item.author,
        category=payload.category or "General",
        image_url=None,
        published_at=item.published_at or datetime.now(timezone.utc),
        status=ArticleStatus.PENDING,
        submitter_id=current_user.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return _format_article_response(article, db)


@router.post("/ingest-rss", response_model=List[ArticleResponse], status_code=status.HTTP_201_CREATED)
async def ingest_from_rss(
    payload: ArticleIngestRss,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.REPORTER, UserRole.ADMIN])),
):
    """Ingest articles in batch from an RSS feed (Reporters and Admins only)."""
    rss_adapter = RssFeedAdapter()
    try:
        items = await rss_adapter.ingest(payload.feed_url, limit=payload.limit or 5)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse RSS feed: {str(exc)}",
        )

    saved_articles = []
    for item in items:
        article = Article(
            title=item.title,
            content=item.content,
            summary=item.summary,
            source_url=item.source_url,
            publisher=item.publisher,
            author=item.author,
            category=payload.category or "General",
            published_at=item.published_at or datetime.now(timezone.utc),
            status=ArticleStatus.PENDING,
            submitter_id=current_user.id,
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        saved_articles.append(_format_article_response(article, db))

    return saved_articles


@router.get("", response_model=ArticleListResponse)
def list_articles(
    status_filter: Optional[ArticleStatus] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    List articles:
    - Readers (or unauthenticated users) can only view published VERIFIED articles.
    - Reporters and Admins can view all articles or filter by status.
    - Supports category filtering and search queries.
    """
    query = db.query(Article)

    # Role enforcement on visibility
    if not current_user or current_user.role == UserRole.READER:
        query = query.filter(Article.status == ArticleStatus.VERIFIED)
    elif status_filter:
        query = query.filter(Article.status == status_filter)

    if category_filter and category_filter.lower() != "all":
        query = query.filter(Article.category.ilike(f"%{category_filter}%"))

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Article.title.ilike(pattern),
                Article.content.ilike(pattern),
                Article.publisher.ilike(pattern),
            )
        )

    total = query.count()
    articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()

    formatted = [_format_article_response(a, db) for a in articles]
    return ArticleListResponse(total=total, articles=formatted)


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieve an article by ID with its latest trust score."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Readers can only view verified articles
    if (not current_user or current_user.role == UserRole.READER) and article.status != ArticleStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="Article is pending verification or not publicly visible")

    return _format_article_response(article, db)
