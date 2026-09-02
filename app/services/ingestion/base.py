from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class IngestedArticle:
    title: str
    content: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None


class BaseIngestionAdapter(ABC):
    @abstractmethod
    async def ingest(self, source: str, **kwargs) -> List[IngestedArticle]:
        """Ingest one or more articles from the provided source (text, URL, or feed)."""
        pass
