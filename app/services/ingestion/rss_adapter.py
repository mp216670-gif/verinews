import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List
from urllib.parse import urlparse
import httpx
from app.services.ingestion.base import BaseIngestionAdapter, IngestedArticle


class RssFeedAdapter(BaseIngestionAdapter):
    """Adapter to parse and ingest articles from an RSS feed URL."""

    async def ingest(self, source: str, limit: int = 5, **kwargs) -> List[IngestedArticle]:
        feed_url = source.strip()
        parsed = urlparse(feed_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid RSS feed URL: {feed_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 NewsAuthIngester/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(feed_url)
            response.raise_for_status()
            content = response.content

        root = ET.fromstring(content)
        # Handle standard RSS 2.0 channel/item structure
        channel = root.find("channel")
        publisher_name = channel.findtext("title", default=parsed.netloc) if channel is not None else parsed.netloc

        items = root.findall(".//item")
        results: List[IngestedArticle] = []

        for item in items[:limit]:
            title = item.findtext("title", default="Untitled RSS Article").strip()
            link = item.findtext("link", default="").strip()
            description = item.findtext("description", default="").strip()
            pub_date_str = item.findtext("pubDate")
            author = item.findtext("author") or item.findtext("{http://purl.org/dc/elements/1.1/}creator")

            # Clean HTML from description
            clean_text = re.sub(r"<[^>]+>", "", description).strip()

            published_at = datetime.now(timezone.utc)
            if pub_date_str:
                try:
                    published_at = parsedate_to_datetime(pub_date_str)
                except Exception:
                    pass

            results.append(
                IngestedArticle(
                    title=title,
                    content=clean_text or f"Article content from {link}",
                    summary=clean_text[:250] if clean_text else title,
                    source_url=link or feed_url,
                    publisher=publisher_name,
                    author=author,
                    published_at=published_at,
                )
            )

        return results
