import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from app.models.verification import ClaimVerdict, ReviewerDecision
from app.services.trust_scoring.rules import (
    WEIGHT_SOURCE_RELIABILITY,
    WEIGHT_CLAIM_ACCURACY,
    WEIGHT_CORROBORATION,
    WEIGHT_RECENCY,
    GRADE_A_THRESHOLD,
    GRADE_B_THRESHOLD,
    GRADE_C_THRESHOLD,
    GRADE_DESCRIPTIONS,
    ACCREDITED_DOMAINS,
)


class TrustScoringEngine:
    """Computes explainable, multi-dimensional news trust scores with full audit trail."""

    def compute_score(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        publisher: Optional[str] = None,
        author: Optional[str] = None,
        published_at: Optional[datetime] = None,
        claims: Optional[List[Any]] = None,
        reviewer_adjustment: float = 0.0,
        reviewer_decision: ReviewerDecision = ReviewerDecision.PENDING,
        reviewer_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        claims = claims or []

        # 1. Source Reliability (0 to 100)
        source_score, source_positives, source_risks = self._evaluate_source_reliability(
            source_url=source_url,
            publisher=publisher,
            author=author,
        )

        # 2. Claim Accuracy (0 to 100)
        claim_score, claim_positives, claim_risks = self._evaluate_claim_accuracy(claims)

        # 3. Corroboration & Citations (0 to 100)
        corrob_score, corrob_positives, corrob_risks = self._evaluate_corroboration(
            content=content,
            source_url=source_url,
            claims=claims,
        )

        # 4. Recency & Freshness (0 to 100)
        recency_score, recency_positives, recency_risks = self._evaluate_recency(published_at)

        # Weighted calculation
        raw_weighted = (
            (source_score * WEIGHT_SOURCE_RELIABILITY)
            + (claim_score * WEIGHT_CLAIM_ACCURACY)
            + (corrob_score * WEIGHT_CORROBORATION)
            + (recency_score * WEIGHT_RECENCY)
        )

        # Apply reviewer adjustment
        adjusted_score = raw_weighted + reviewer_adjustment
        final_score = max(0.0, min(100.0, round(adjusted_score, 1)))

        # Assign grade
        if final_score >= GRADE_A_THRESHOLD:
            grade = "A"
        elif final_score >= GRADE_B_THRESHOLD:
            grade = "B"
        elif final_score >= GRADE_C_THRESHOLD:
            grade = "C"
        else:
            grade = "D"

        positive_signals = source_positives + claim_positives + corrob_positives + recency_positives
        risk_factors = source_risks + claim_risks + corrob_risks + recency_risks

        if reviewer_adjustment != 0.0:
            positive_signals.append(f"Reviewer adjustment applied: {reviewer_adjustment:+.1f} points ({reviewer_decision.value})")

        explanation = {
            "version": "1.0.0",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "grade": grade,
            "overall_score": final_score,
            "grade_description": GRADE_DESCRIPTIONS[grade],
            "weights": {
                "source_reliability": WEIGHT_SOURCE_RELIABILITY,
                "claim_accuracy": WEIGHT_CLAIM_ACCURACY,
                "corroboration": WEIGHT_CORROBORATION,
                "recency": WEIGHT_RECENCY,
            },
            "sub_scores": {
                "source_reliability": round(source_score, 1),
                "claim_accuracy": round(claim_score, 1),
                "corroboration": round(corrob_score, 1),
                "recency": round(recency_score, 1),
                "reviewer_adjustment": round(reviewer_adjustment, 1),
            },
            "contributions": {
                "source_reliability_pts": round(source_score * WEIGHT_SOURCE_RELIABILITY, 1),
                "claim_accuracy_pts": round(claim_score * WEIGHT_CLAIM_ACCURACY, 1),
                "corroboration_pts": round(corrob_score * WEIGHT_CORROBORATION, 1),
                "recency_pts": round(recency_score * WEIGHT_RECENCY, 1),
                "reviewer_adjustment_pts": round(reviewer_adjustment, 1),
            },
            "positive_signals": positive_signals,
            "risk_factors": risk_factors,
            "reviewer_notes": reviewer_notes,
            "summary": (
                f"Article achieved a Trust Score of {final_score}/100 (Grade {grade}). "
                f"Source reliability rated {source_score:.0f}/100, claim accuracy {claim_score:.0f}/100, "
                f"corroboration {corrob_score:.0f}/100, and freshness {recency_score:.0f}/100."
            ),
        }

        return {
            "overall_score": final_score,
            "grade": grade,
            "source_reliability_score": round(source_score, 1),
            "corroboration_score": round(corrob_score, 1),
            "claim_verification_score": round(claim_score, 1),
            "recency_score": round(recency_score, 1),
            "reviewer_adjustment": round(reviewer_adjustment, 1),
            "explanation": explanation,
        }

    def _evaluate_source_reliability(
        self,
        source_url: Optional[str],
        publisher: Optional[str],
        author: Optional[str]
    ) -> tuple[float, list[str], list[str]]:
        score = 40.0  # Base neutral score
        positives = []
        risks = []

        if source_url:
            parsed = urlparse(source_url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]

            if parsed.scheme == "https":
                score += 10.0
                positives.append("Secure HTTPS connection verified")

            if any(domain == acc or domain.endswith("." + acc) for acc in ACCREDITED_DOMAINS):
                score += 35.0
                positives.append(f"Accredited major publisher domain verified: {domain}")
            elif domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".org"):
                score += 25.0
                positives.append(f"Institutional top-level domain: {domain}")
            elif domain:
                score += 15.0
                positives.append(f"Standard public web domain: {domain}")
        else:
            risks.append("No canonical source URL provided for origin validation")

        if publisher and publisher.strip() and publisher.lower() != "direct submission":
            score += 10.0
            positives.append(f"Identified publisher: {publisher.strip()}")
        else:
            risks.append("Unspecified or anonymous publishing entity")

        if author and author.strip():
            score += 10.0
            positives.append(f"Byline author attribution present: {author.strip()}")
        else:
            risks.append("No individual author byline found")

        return max(0.0, min(100.0, score)), positives, risks

    def _evaluate_claim_accuracy(self, claims: list) -> tuple[float, list[str], list[str]]:
        if not claims:
            return 50.0, [], ["No discrete claims could be extracted for formal verification"]

        total_weight = 0.0
        weighted_sum = 0.0
        false_count = 0
        misleading_count = 0
        true_count = 0
        positives = []
        risks = []

        for c in claims:
            verdict = getattr(c, "verdict", None) or (c.get("verdict") if isinstance(c, dict) else None)
            confidence = getattr(c, "confidence", 0.7) or (c.get("confidence", 0.7) if isinstance(c, dict) else 0.7)

            if verdict == ClaimVerdict.TRUE or verdict == "true":
                weighted_sum += 100.0 * confidence
                true_count += 1
            elif verdict == ClaimVerdict.MISLEADING or verdict == "misleading":
                weighted_sum += 25.0 * confidence
                misleading_count += 1
            elif verdict == ClaimVerdict.FALSE or verdict == "false":
                weighted_sum += 0.0
                false_count += 1
            else:  # UNVERIFIED
                weighted_sum += 50.0 * confidence

            total_weight += confidence

        base_claim_score = (weighted_sum / total_weight) if total_weight > 0 else 50.0

        # Heavy penalty for false claims
        penalty = (false_count * 25.0) + (misleading_count * 10.0)
        final_claim_score = max(0.0, base_claim_score - penalty)

        if true_count > 0:
            positives.append(f"{true_count} verified true claim(s) confirmed by facts/sources")
        if false_count > 0:
            risks.append(f"Critical flag: {false_count} claim(s) determined to be FALSE")
        if misleading_count > 0:
            risks.append(f"Warning: {misleading_count} claim(s) assessed as MISLEADING or exaggerated")

        return max(0.0, min(100.0, final_claim_score)), positives, risks

    def _evaluate_corroboration(
        self,
        content: str,
        source_url: Optional[str],
        claims: list
    ) -> tuple[float, list[str], list[str]]:
        score = 30.0
        positives = []
        risks = []

        # Quotes detection
        quotes = re.findall(r'["\u201c\u201d](.*?)["\u201c\u201d]', content)
        if len(quotes) >= 2:
            score += 25.0
            positives.append(f"Direct quotations present ({len(quotes)} quoted statements)")
        elif len(quotes) == 1:
            score += 15.0
            positives.append("Direct quote from source included")
        else:
            risks.append("No direct quotations or attributed witness statements found")

        # Numerical/data statistics citation
        has_stats = bool(re.search(r'\b\d+(?:\.\d+)?%|\b\$\d+|\b\d+\s+(?:million|billion|thousand|people|cases|votes)\b', content, re.IGNORECASE))
        if has_stats:
            score += 20.0
            positives.append("Empirical or statistical data points cited in the report")

        # Check evidence sources across claims
        has_evidence = any(
            bool(getattr(c, "evidence_sources", None) or (c.get("evidence_sources") if isinstance(c, dict) else None))
            for c in claims
        )
        if has_evidence:
            score += 25.0
            positives.append("Independent third-party evidence registries corroborate statements")

        return max(0.0, min(100.0, score)), positives, risks

    def _evaluate_recency(self, published_at: Optional[datetime]) -> tuple[float, list[str], list[str]]:
        if not published_at:
            return 60.0, [], ["Publication timestamp missing; defaulted to neutral recency score"]

        now = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            pub = published_at.replace(tzinfo=timezone.utc)
        else:
            pub = published_at

        diff_hours = (now - pub).total_seconds() / 3600.0

        if diff_hours < 48:
            return 95.0, ["Breaking/fresh news: published within 48 hours"], []
        elif diff_hours < 720:  # 30 days
            return 85.0, ["Recent news: published within past 30 days"], []
        elif diff_hours < 8760:  # 1 year
            return 70.0, ["Archived news item: published within current year"], []
        else:
            return 50.0, [], ["Historical article: published more than 1 year ago"]
