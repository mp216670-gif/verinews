import pytest
from app.services.fact_checking.rule_engine import RuleBasedFactCheckProvider
from app.models.verification import ClaimVerdict


@pytest.mark.anyio
async def test_fact_check_credible_article():
    engine = RuleBasedFactCheckProvider()
    title = "WHO Confirms Eradication of Wild Poliovirus Strain in Central Region"
    content = (
        "According to an official statement from the World Health Organization, global health surveillance teams confirmed "
        "the complete cessation of wild transmission. Over 15 million children received scheduled vaccinations. "
        "The data was verified and published in official records by international epidemiological panels."
    )
    result = await engine.verify(title=title, content=content, publisher="Reuters")

    assert result.provider_name == "RuleBased-Engine"
    assert "Verified" in result.provider_verdict or "Supported" in result.provider_verdict
    assert len(result.claims) >= 2

    # Verify at least one claim has TRUE verdict
    true_claims = [c for c in result.claims if c.verdict == ClaimVerdict.TRUE]
    assert len(true_claims) >= 1


@pytest.mark.anyio
async def test_fact_check_disinformation_detection():
    engine = RuleBasedFactCheckProvider()
    title = "Miracle cure revealed: Secret herbs cure all diseases guaranteed 100%!"
    content = (
        "Doctors don't want you to know the shocking revelation they hid for generations. "
        "This mind-blowing substance cures all diseases without any medical intervention."
    )
    result = await engine.verify(title=title, content=content, publisher="Unverified Blog")

    assert "Disputed" in result.provider_verdict or "Likely False" in result.provider_verdict or "Questionable" in result.provider_verdict
    false_or_misleading = [c for c in result.claims if c.verdict in (ClaimVerdict.FALSE, ClaimVerdict.MISLEADING)]
    assert len(false_or_misleading) >= 1
