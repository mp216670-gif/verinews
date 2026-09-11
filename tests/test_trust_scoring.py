from datetime import datetime, timezone
from app.services.trust_scoring.scorer import TrustScoringEngine
from app.models.verification import ClaimVerdict, ReviewerDecision


def test_trust_scoring_high_credibility():
    engine = TrustScoringEngine()
    claims = [
        {"verdict": ClaimVerdict.TRUE, "confidence": 0.90, "evidence_sources": ["Reuters Wire"]},
        {"verdict": ClaimVerdict.TRUE, "confidence": 0.85, "evidence_sources": ["AP News"]},
    ]
    res = engine.compute_score(
        title="Major Energy Breakthrough Confirmed by National Laboratory",
        content='Dr. Jane Thorne stated: "This result marks a 40% efficiency jump." Researchers published the benchmark today.',
        source_url="https://reuters.com/business/energy-breakthrough",
        publisher="Reuters",
        author="David Miller",
        published_at=datetime.now(timezone.utc),
        claims=claims,
    )

    assert res["overall_score"] >= 80.0
    assert res["grade"] in ("A", "B")
    assert "explanation" in res
    assert "sub_scores" in res["explanation"]
    assert res["source_reliability_score"] >= 70.0
    assert len(res["explanation"]["positive_signals"]) >= 2


def test_trust_scoring_low_credibility_false_claims():
    engine = TrustScoringEngine()
    claims = [
        {"verdict": ClaimVerdict.FALSE, "confidence": 0.95, "evidence_sources": []},
        {"verdict": ClaimVerdict.FALSE, "confidence": 0.90, "evidence_sources": []},
    ]
    res = engine.compute_score(
        title="Unbelievable Conspiracy Exposed",
        content="Mind blowing revelation that is guaranteed 100% true without doubt.",
        source_url="http://sketchy-free-site.xyz/post",
        publisher=None,
        author=None,
        published_at=None,
        claims=claims,
    )

    assert res["overall_score"] < 50.0
    assert res["grade"] == "D"
    assert len(res["explanation"]["risk_factors"]) >= 1


def test_reviewer_calibration_adjustment():
    engine = TrustScoringEngine()
    claims = [{"verdict": ClaimVerdict.TRUE, "confidence": 0.80}]
    base_res = engine.compute_score(
        title="Standard Community Notice",
        content="Town council approved library refurbishment project.",
        source_url="https://localnews.org/library",
        publisher="Local Gazette",
        author="Staff",
        claims=claims,
        reviewer_adjustment=0.0,
    )

    calibrated_res = engine.compute_score(
        title="Standard Community Notice",
        content="Town council approved library refurbishment project.",
        source_url="https://localnews.org/library",
        publisher="Local Gazette",
        author="Staff",
        claims=claims,
        reviewer_adjustment=10.0,
        reviewer_decision=ReviewerDecision.APPROVED,
        reviewer_notes="Verified directly with town hall clerk.",
    )

    assert calibrated_res["overall_score"] == min(100.0, round(base_res["overall_score"] + 10.0, 1))
    assert calibrated_res["reviewer_adjustment"] == 10.0
