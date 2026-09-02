from app.services.ingestion.base import BaseIngestionAdapter, IngestedArticle
from app.services.ingestion.text_adapter import TextIngestionAdapter
from app.services.ingestion.url_scraper import UrlScraperAdapter
from app.services.ingestion.rss_adapter import RssFeedAdapter

__all__ = [
    "BaseIngestionAdapter",
    "IngestedArticle",
    "TextIngestionAdapter",
    "UrlScraperAdapter",
    "RssFeedAdapter",
]
