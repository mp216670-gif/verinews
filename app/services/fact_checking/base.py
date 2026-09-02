from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from app.models.verification import ClaimVerdict


@dataclass
class ExtractedClaim:
    text: str
    verdict: ClaimVerdict
    confidence: float  # 0.0 to 1.0
    evidence_sources: List[str] = field(default_factory=list)
    explanation: Optional[str] = None


@dataclass
class FactCheckResult:
    provider_name: str
    provider_verdict: str
    claims: List[ExtractedClaim]
    summary: str


class BaseFactCheckProvider(ABC):
    @abstractmethod
    async def verify(self, title: str, content: str, source_url: Optional[str] = None, publisher: Optional[str] = None) -> FactCheckResult:
        """Analyze text, extract core verifiable claims, and return verification findings."""
        pass
