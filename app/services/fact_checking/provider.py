import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.models.verification import ClaimVerdict
from app.services.fact_checking.base import BaseFactCheckProvider, ExtractedClaim, FactCheckResult
from app.services.fact_checking.rule_engine import RuleBasedFactCheckProvider

logger = logging.getLogger(__name__)


class ExternalFactCheckProvider(BaseFactCheckProvider):
    """Adapter for external Fact Check APIs (e.g., Google Fact Check Tools API)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    async def verify(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        publisher: Optional[str] = None
    ) -> FactCheckResult:
        query = title[:150]
        params = {"query": query, "key": self.api_key}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

        claims_data = data.get("claims", [])
        if not claims_data:
            # No direct claims in external registry
            return FactCheckResult(
                provider_name="GoogleFactCheckTools",
                provider_verdict="No Prior Fact-Check Record",
                claims=[],
                summary="No previous fact-checking records found in the external registry for this query.",
            )

        extracted_claims = []
        for c in claims_data[:5]:
            text = c.get("text", "")
            claim_reviews = c.get("claimReview", [])
            verdict = ClaimVerdict.UNVERIFIED
            evidence = []
            explanation = ""

            if claim_reviews:
                review = claim_reviews[0]
                textual_rating = (review.get("textualRating") or "").lower()
                evidence.append(review.get("url", ""))
                publisher_info = review.get("publisher", {}).get("name", "External Fact Checker")
                explanation = f"Reviewed by {publisher_info}: rated '{textual_rating}'."

                if any(w in textual_rating for w in ["false", "incorrect", "pants on fire", "fake"]):
                    verdict = ClaimVerdict.FALSE
                elif any(w in textual_rating for w in ["true", "correct", "accurate"]):
                    verdict = ClaimVerdict.TRUE
                elif any(w in textual_rating for w in ["misleading", "half true", "partly", "exaggerated"]):
                    verdict = ClaimVerdict.MISLEADING

            extracted_claims.append(
                ExtractedClaim(
                    text=text,
                    verdict=verdict,
                    confidence=0.90 if verdict != ClaimVerdict.UNVERIFIED else 0.5,
                    evidence_sources=[e for e in evidence if e],
                    explanation=explanation or "Matched external fact-checking registry.",
                )
            )

        return FactCheckResult(
            provider_name="GoogleFactCheckTools",
            provider_verdict="Claims Evaluated via External Registry",
            claims=extracted_claims,
            summary=f"Found {len(extracted_claims)} matching claim assessments from external fact-checking organizations.",
        )


class FactCheckManager:
    """Manages fact checking by delegating to requested providers with fallback."""

    def __init__(self):
        self.rule_engine = RuleBasedFactCheckProvider()

    async def run_verification(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        publisher: Optional[str] = None,
        provider_preference: str = "hybrid"
    ) -> FactCheckResult:
        # Check if external provider is explicitly configured and requested
        is_mock_key = not settings.fact_check_api_key or "mock" in settings.fact_check_api_key.lower() or "replace" in settings.fact_check_api_key.lower()

        if provider_preference in ("external", "hybrid") and not is_mock_key:
            try:
                external_provider = ExternalFactCheckProvider(api_key=settings.fact_check_api_key)
                result = await external_provider.verify(title, content, source_url, publisher)
                if result.claims:
                    return result
            except Exception as exc:
                logger.warning(f"External fact check provider failed ({exc}), falling back to rule engine.")

        # Default / Fallback to RuleBased engine
        return await self.rule_engine.verify(title, content, source_url, publisher)
