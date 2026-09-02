import re
from typing import List, Optional, Tuple
from app.models.verification import ClaimVerdict
from app.services.fact_checking.base import BaseFactCheckProvider, ExtractedClaim, FactCheckResult

# Known disinformation tropes and sensationalist red flags
SENSATIONAL_PATTERNS = [
    (r"\b(miracle cure|cures? all (?:diseases|illnesses|cancers)|cures? (?:cancer|everything|all)|doctors don't want you to know)\b", ClaimVerdict.FALSE, 0.95, "Known medical misinformation pattern"),
    (r"\b(secretly controlled by|illuminati|microchips in vaccines|flat earth)\b", ClaimVerdict.FALSE, 0.95, "Debunked conspiracy claim"),
    (r"\b(guaranteed 100%|secret tricks?|shocking (?:revelation|truth) they hid|shocking truth revealed)\b", ClaimVerdict.MISLEADING, 0.85, "Sensationalist clickbait claim"),
    (r"\b(aliens confirmed|time traveler reveals|apocalypse tomorrow)\b", ClaimVerdict.FALSE, 0.90, "Unsubstantiated fringe assertion"),
]

# Credible attribution patterns
CREDIBLE_ATTRIBUTION_PATTERNS = [
    r"\b(according to|published in|confirmed by|reported by|official statement from)\b",
    r"\b(reuters|associated press|bbc|nature|science journal|world health organization|who|cdc|nasa)\b",
    r"\b(stated in a press release|peer-reviewed study|official records show)\b",
]

# Established reputable news organizations & academic publishers
HIGH_CREDIBILITY_PUBLISHERS = {
    "reuters", "associated press", "ap news", "bbc", "bbc news",
    "the guardian", "the new york times", "wall street journal",
    "nature", "science", "bloomberg", "npr", "pbs", "the washington post"
}


class RuleBasedFactCheckProvider(BaseFactCheckProvider):
    """Local, explainable rule-based fact-checking engine."""

    def __init__(self, name: str = "RuleBased-Engine"):
        self.name = name

    async def verify(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        publisher: Optional[str] = None
    ) -> FactCheckResult:
        full_text = f"{title}. {content}"
        claims = self._extract_claims(title, content, publisher)

        # Calculate overall verdict summary
        true_count = sum(1 for c in claims if c.verdict == ClaimVerdict.TRUE)
        false_count = sum(1 for c in claims if c.verdict == ClaimVerdict.FALSE)
        misleading_count = sum(1 for c in claims if c.verdict == ClaimVerdict.MISLEADING)

        if false_count > 0:
            provider_verdict = "Disputed / Likely False"
            summary = f"Detected {false_count} debunked or unsubstantiated claims in the content."
        elif misleading_count > 0:
            provider_verdict = "Questionable / Misleading"
            summary = f"Detected {misleading_count} potentially misleading or exaggerated claims."
        elif true_count >= 2:
            provider_verdict = "Verified / Supported"
            summary = f"Content corroborates with reputable attribution and verifiable assertions ({true_count} verified claims)."
        else:
            provider_verdict = "Unverified / Needs Investigation"
            summary = "Insufficient verifiable claims or source citations detected for independent corroboration."

        return FactCheckResult(
            provider_name=self.name,
            provider_verdict=provider_verdict,
            claims=claims,
            summary=summary,
        )

    def _extract_claims(self, title: str, content: str, publisher: Optional[str]) -> List[ExtractedClaim]:
        # Clean and split into sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if len(s.strip()) > 25]
        
        # Always evaluate the headline/title as a primary claim
        claims: List[ExtractedClaim] = []
        headline_claim = self._evaluate_sentence(title, is_headline=True, publisher=publisher)
        claims.append(headline_claim)

        # Select representative substantive sentences
        candidate_sentences = []
        for s in sentences[:15]:
            # Look for assertions with numbers, quotes, or strong keywords
            has_numbers = bool(re.search(r'\b\d+(?:[.,]\d+)?%?\b', s))
            has_quotes = '"' in s or "'" in s
            has_attribution = any(re.search(pat, s, re.IGNORECASE) for pat in CREDIBLE_ATTRIBUTION_PATTERNS)
            has_sensational = any(re.search(pat[0], s, re.IGNORECASE) for pat in SENSATIONAL_PATTERNS)

            if (has_numbers or has_quotes or has_attribution or has_sensational) and s != title:
                candidate_sentences.append(s)

        # Fallback if no specific trigger sentences found
        if not candidate_sentences:
            candidate_sentences = sentences[:3]

        for s in candidate_sentences[:5]:
            claim = self._evaluate_sentence(s, is_headline=False, publisher=publisher)
            claims.append(claim)

        return claims

    def _evaluate_sentence(self, sentence: str, is_headline: bool, publisher: Optional[str]) -> ExtractedClaim:
        lower = sentence.lower()
        pub_lower = (publisher or "").lower()

        # Check sensational/debunked patterns
        for pattern, verdict, conf, reason in SENSATIONAL_PATTERNS:
            if re.search(pattern, lower):
                return ExtractedClaim(
                    text=sentence,
                    verdict=verdict,
                    confidence=conf,
                    evidence_sources=["FactCheck Common Red Flags Registry"],
                    explanation=f"{'Headline' if is_headline else 'Statement'} matches pattern: {reason}.",
                )

        # Check credible attribution
        has_credible_attr = any(re.search(pat, lower) for pat in CREDIBLE_ATTRIBUTION_PATTERNS)
        is_known_credible_pub = any(p in pub_lower for p in HIGH_CREDIBILITY_PUBLISHERS)

        if has_credible_attr or is_known_credible_pub:
            evidence = []
            if is_known_credible_pub:
                evidence.append(f"Recognized accredited publisher: {publisher}")
            if has_credible_attr:
                evidence.append("Explicit third-party attribution or institutional source cited")

            return ExtractedClaim(
                text=sentence,
                verdict=ClaimVerdict.TRUE,
                confidence=0.88,
                evidence_sources=evidence,
                explanation="Statement includes verifiable institutional attribution or citations to reputable data.",
            )

        # Check for hyperbolic claim words
        if re.search(r"\b(proves once and for all|never before seen|unbelievable|mind-blowing)\b", lower):
            return ExtractedClaim(
                text=sentence,
                verdict=ClaimVerdict.MISLEADING,
                confidence=0.75,
                evidence_sources=["Linguistic Sensationalism Heuristics"],
                explanation="Exaggerated certainty or hyperbolic framing without source corroboration.",
            )

        # Default unverified claim
        return ExtractedClaim(
            text=sentence,
            verdict=ClaimVerdict.UNVERIFIED,
            confidence=0.50,
            evidence_sources=[],
            explanation="Factual proposition requires additional external corroboration.",
        )
