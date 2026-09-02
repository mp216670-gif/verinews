import re
from datetime import datetime, timezone
from typing import List, Optional
from app.services.ingestion.base import BaseIngestionAdapter, IngestedArticle


class TextIngestionAdapter(BaseIngestionAdapter):
    """Adapter for manually entered or pasted news text."""

    async def ingest(
        self,
        source: str,
        title: Optional[str] = None,
        publisher: Optional[str] = None,
        author: Optional[str] = None,
        source_url: Optional[str] = None,
        **kwargs
    ) -> List[IngestedArticle]:
        content = source.strip()
        if not content:
            raise ValueError("Article content cannot be empty.")

        # If title is not provided, extract the first non-empty line
        if not title:
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            title = lines[0][:120] if lines else "Untitled News Article"

        # Generate a short summary from the first 2-3 sentences
        sentences = re.split(r'(?<=[.!?]) +', content)
        summary = " ".join(sentences[:2]) if len(sentences) >= 2 else content[:200]

        article = IngestedArticle(
            title=title,
            content=content,
            summary=summary,
            source_url=source_url,
            publisher=publisher or "Direct Submission",
            author=author,
            published_at=datetime.now(timezone.utc),
        )
        return [article]
