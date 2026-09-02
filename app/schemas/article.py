from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.article import ArticleStatus
from app.schemas.verification import TrustScoreResponse


class ArticleBase(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = "General"
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None


class ArticleCreate(ArticleBase):
    pass


class ArticleIngestUrl(BaseModel):
    url: str
    category: Optional[str] = "General"


class ArticleIngestRss(BaseModel):
    feed_url: str
    category: Optional[str] = "General"
    limit: Optional[int] = 5


class ArticleResponse(ArticleBase):
    id: int
    status: ArticleStatus
    submitter_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    latest_trust_score: Optional[TrustScoreResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ArticleListResponse(BaseModel):
    total: int
    articles: list[ArticleResponse]
