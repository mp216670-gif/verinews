import re
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse
import httpx
from app.services.ingestion.base import BaseIngestionAdapter, IngestedArticle


class UrlScraperAdapter(BaseIngestionAdapter):
    """Adapter to fetch and extract news articles from live URLs."""

    async def ingest(self, source: str, **kwargs) -> List[IngestedArticle]:
        url = source.strip()
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        title = self._extract_title(html) or f"News Article from {domain}"
        publisher = self._extract_meta(html, "og:site_name") or domain
        author = self._extract_meta(html, "author") or self._extract_meta(html, "article:author")
        content = self._extract_content(html)
        if not content:
            content = f"Article content retrieved from {url}"

        # Generate summary
        sentences = re.split(r'(?<=[.!?]) +', content)
        summary = " ".join(sentences[:2]) if len(sentences) >= 2 else content[:250]

        article = IngestedArticle(
            title=title,
            content=content,
            summary=summary,
            source_url=url,
            publisher=publisher,
            author=author,
            published_at=datetime.now(timezone.utc),
        )
        return [article]

    def _extract_title(self, html: str) -> Optional[str]:
        og_title = self._extract_meta(html, "og:title")
        if og_title:
            return og_title.strip()
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            clean = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return clean
        return None

    def _extract_meta(self, html: str, property_name: str) -> Optional[str]:
        # Matches property="og:..." or name="..."
        pattern = rf'<meta\s+(?:[^>]*?\s+)?(?:property|name)=["\']{re.escape(property_name)}["\']\s+content=["\']([^"\']*)["\']'
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Try alternate attribute order: content="..." property="..."
        pattern_rev = rf'<meta\s+content=["\']([^"\']*)["\']\s+(?:property|name)=["\']{re.escape(property_name)}["\']'
        match_rev = re.search(pattern_rev, html, re.IGNORECASE)
        if match_rev:
            return match_rev.group(1).strip()
        return None

    def _extract_content(self, html: str) -> str:
        # Strip script and style tags
        cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
        # Find paragraphs
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned_paragraphs = []
        for p in paragraphs:
            text = re.sub(r"<[^>]+>", "", p).strip()
            # Filter out short or boilerplate paragraphs
            if len(text) > 40 and "cookie" not in text.lower() and "subscribe" not in text.lower():
                cleaned_paragraphs.append(text)
        return "\n\n".join(cleaned_paragraphs)
