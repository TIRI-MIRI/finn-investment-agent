"""Unit tests for Research Synthesizer, Citation Validator, and Model Adapters."""

from unittest.mock import MagicMock
import httpx
import pytest

from app.core.models import (
    Claim,
    Confidence,
    ResearchSection,
    SourceEvidence,
    SourceMode,
)
from app.services.research_store import ResearchStore
from app.services.synthesizer import (
    APIModelAdapter,
    CitationValidator,
    DeterministicExtractiveAdapter,
    ResearchSynthesizer,
)


@pytest.fixture
def sample_evidence():
    return [
        SourceEvidence(
            id="ev-ril-01",
            ticker="RELIANCE",
            title="Reliance Q3 Results",
            publisher="Reliance Industries Limited",
            document_type="quarterly_results",
            url="https://investors.ril.com/results/q3.html",
            period="Q3 FY2025",
            page_or_section="Financial Highlights",
            excerpt="Consolidated gross revenue reached ₹2,43,865 Cr for Q3 FY2025, an increase of 12.0% year-on-year.",
            is_fixture=True,
        ),
        SourceEvidence(
            id="ev-ril-02",
            ticker="RELIANCE",
            title="Reliance Q3 Segment Breakdown",
            publisher="Reliance Industries Limited",
            document_type="quarterly_results",
            url="https://investors.ril.com/results/q3.html",
            period="Q3 FY2025",
            page_or_section="Segment Performance",
            excerpt="Jio Platforms digital services revenue stood at ₹32,510 Cr, with EBITDA margin expanding to 50.4%.",
            is_fixture=True,
        ),
        SourceEvidence(
            id="ev-infy-01",
            ticker="INFY",
            title="Infosys Q3 Fact Sheet",
            publisher="Infosys Limited",
            document_type="quarterly_results",
            url="https://www.infosys.com/investors/q3.html",
            period="Q3 FY2025",
            page_or_section="Financial Overview",
            excerpt="Revenues for the quarter stood at ₹41,764 Cr, representing year-on-year growth of 6.1%.",
            is_fixture=True,
        ),
    ]


# ── CitationValidator Tests ──────────────────────────────────────────────


def test_validator_supported_claim(sample_evidence):
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    claim = Claim(
        text="Consolidated gross revenue reached 243865 Cr with 12.0% growth.",
        evidence_ids=["ev-ril-01"],
        confidence=Confidence.HIGH,
    )
    result = validator.validate_claim(claim, "RELIANCE", ev_map)
    assert result.is_valid is True
    assert result.valid_ids == ["ev-ril-01"]
    assert len(result.invalid_ids) == 0


def test_validator_missing_citation(sample_evidence):
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    claim = Claim(
        text="Unverified statement without valid ID.",
        evidence_ids=["ev-nonexistent-99"],
        confidence=Confidence.HIGH,
    )
    result = validator.validate_claim(claim, "RELIANCE", ev_map)
    assert result.is_valid is False
    assert "ev-nonexistent-99" in result.invalid_ids
    assert any("not found" in w for w in result.warnings)


def test_validator_cross_ticker_contamination(sample_evidence):
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    # RELIANCE brief citing an INFY evidence
    claim = Claim(
        text="Revenue was 41764 Cr.",
        evidence_ids=["ev-infy-01"],
        confidence=Confidence.HIGH,
    )
    result = validator.validate_claim(claim, "RELIANCE", ev_map)
    assert result.is_valid is False
    assert "ev-infy-01" in result.invalid_ids
    assert any("belongs to ticker 'INFY'" in w for w in result.warnings)


def test_validator_empty_excerpt():
    empty_ev = SourceEvidence(
        id="ev-empty",
        ticker="TCS",
        title="TCS Filing",
        publisher="TCS Limited",
        document_type="annual_report",
        excerpt="   ",
        url="https://www.tcs.com",
    )
    validator = CitationValidator()
    claim = Claim(text="TCS statement", evidence_ids=["ev-empty"])
    result = validator.validate_claim(claim, "TCS", {"ev-empty": empty_ev})
    assert result.is_valid is False
    assert any("empty evidence excerpt" in w for w in result.warnings)


def test_validator_numeric_mismatch_warning(sample_evidence):
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    # Claim states 99.9% which is not in the cited excerpt (excerpt has 12.0%)
    claim = Claim(
        text="Gross revenue grew by 99.9% in the quarter.",
        evidence_ids=["ev-ril-01"],
        confidence=Confidence.HIGH,
    )
    result = validator.validate_claim(claim, "RELIANCE", ev_map)
    # The citation is valid, but a numeric mismatch warning is added
    assert "ev-ril-01" in result.valid_ids
    assert any("Numeric value '99.9%' in claim text was not explicitly found" in w for w in result.warnings)


def test_validator_filter_sections(sample_evidence):
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    sections = [
        ResearchSection(
            id="sec1",
            title="Section 1",
            summary="Test Summary",
            claims=[
                Claim(text="Valid claim", evidence_ids=["ev-ril-01"], confidence=Confidence.HIGH),
                Claim(text="Cross-ticker claim", evidence_ids=["ev-infy-01"], confidence=Confidence.HIGH),
                Claim(text="Zero evidence claim", evidence_ids=[], confidence=Confidence.HIGH),
            ],
        )
    ]

    validated_sections, warnings = validator.validate_and_filter_sections(sections, "RELIANCE", ev_map)
    assert len(validated_sections) == 1
    claims = validated_sections[0].claims
    assert len(claims) == 3

    # First claim valid
    assert claims[0].evidence_ids == ["ev-ril-01"]
    assert claims[0].confidence == Confidence.HIGH

    # Second claim has zero valid citations -> unverified tag and LOW confidence
    assert claims[1].evidence_ids == []
    assert claims[1].confidence == Confidence.LOW
    assert "[UNVERIFIED IN RETRIEVED SOURCES]" in claims[1].text

    # Third claim had no evidence -> unverified tag and LOW confidence
    assert claims[2].confidence == Confidence.LOW


# ── DeterministicExtractiveAdapter Tests ─────────────────────────────────


def test_extractive_adapter_sections(sample_evidence):
    adapter = DeterministicExtractiveAdapter()
    ril_evidence = [e for e in sample_evidence if e.ticker == "RELIANCE"]

    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries Limited", ril_evidence)
    assert len(sections) == 5

    section_ids = [s.id for s in sections]
    assert section_ids == [
        "company_overview",
        "financial_trajectory",
        "cash_and_balance_sheet",
        "management_outlook",
        "risks_and_limitations",
    ]

    # Every section must have a non-empty summary and claims
    for s in sections:
        assert s.summary
        assert len(s.claims) > 0


def test_extractive_adapter_empty_evidence():
    adapter = DeterministicExtractiveAdapter()
    sections = adapter.synthesize_sections("UNKNOWN", "Unknown Co", [])
    assert len(sections) == 5
    for s in sections:
        for c in s.claims:
            assert c.confidence == Confidence.LOW


# ── APIModelAdapter Tests ────────────────────────────────────────────────


def test_api_adapter_no_key_fallback(sample_evidence):
    adapter = APIModelAdapter(api_key=None)
    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries", sample_evidence)
    assert len(sections) == 5
    assert sections[0].id == "company_overview"


def test_api_adapter_mocked_success(sample_evidence):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": """
                    {
                        "sections": [
                            {
                                "id": "company_overview",
                                "title": "1. Company Overview",
                                "summary": "Diverse conglomerate.",
                                "claims": [
                                    {"text": "Digital revenue was 32510 Cr.", "evidence_ids": ["ev-ril-02"], "confidence": "high"}
                                ]
                            },
                            {
                                "id": "financial_trajectory",
                                "title": "2. Financial Trajectory",
                                "summary": "Strong growth.",
                                "claims": [
                                    {"text": "Gross revenue was 243865 Cr.", "evidence_ids": ["ev-ril-01"], "confidence": "high"}
                                ]
                            },
                            {
                                "id": "cash_and_balance_sheet",
                                "title": "3. Cash & Balance Sheet",
                                "summary": "Liquidity overview.",
                                "claims": []
                            }
                        ]
                    }
                    """
                }
            }
        ]
    }
    mock_client.post.return_value = mock_response

    adapter = APIModelAdapter(api_key="sk-fake-key", client=mock_client)
    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries", sample_evidence)
    assert len(sections) == 3
    assert sections[0].id == "company_overview"
    assert sections[0].claims[0].evidence_ids == ["ev-ril-02"]


def test_api_adapter_mocked_error_fallback(sample_evidence):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_client.post.return_value = mock_response

    adapter = APIModelAdapter(api_key="sk-fake-key", client=mock_client)
    # On 500 error, falls back to deterministic extractive adapter
    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries", sample_evidence)
    assert len(sections) == 5
    assert sections[0].id == "company_overview"


# ── ResearchSynthesizer Tests ────────────────────────────────────────────


def test_research_synthesizer_flow(sample_evidence):
    store = ResearchStore()
    synthesizer = ResearchSynthesizer(store=store)

    ril_evidence = [e for e in sample_evidence if e.ticker == "RELIANCE"]
    brief = synthesizer.generate_brief(
        ticker="RELIANCE",
        company_name="Reliance Industries Limited",
        evidence=ril_evidence,
    )

    assert brief.ticker == "RELIANCE"
    assert brief.company_name == "Reliance Industries Limited"
    assert brief.source_mode == SourceMode.DEMO
    assert len(brief.sections) == 5
    assert brief.coverage.documents_found >= 1
    assert "Q3 FY2025" in brief.coverage.periods

    # Ensure saved to store
    stored = store.get_latest_research("RELIANCE")
    assert stored is not None
    assert stored.ticker == "RELIANCE"


def test_validator_unsupported_numeric_claim(sample_evidence):
    """Verify that unsupported numbers downgrade confidence and trigger warnings."""
    validator = CitationValidator()
    ev_map = {e.id: e for e in sample_evidence}

    claim = Claim(
        text="Revenue jumped by 88.5% to ₹9,99,999 Cr.",
        evidence_ids=["ev-ril-01"],
        confidence=Confidence.HIGH,
    )
    res = validator.validate_claim(claim, "RELIANCE", ev_map)
    assert res.has_numeric_mismatch is True
    assert "88.5%" in res.unsupported_numbers
    assert "999999" in res.unsupported_numbers

    # Verify validate_and_filter_sections downgrades confidence to LOW
    section = ResearchSection(
        id="financial_trajectory",
        title="Financial Trajectory",
        summary="Summary",
        claims=[claim],
    )
    validated_sections, warnings = validator.validate_and_filter_sections([section], "RELIANCE", ev_map)
    assert validated_sections[0].claims[0].confidence == Confidence.LOW
    assert any("88.5%" in w for w in warnings)


def test_research_synthesizer_live_provenance(sample_evidence):
    """Verify that live official source evidence produces SourceMode.LIVE."""
    store = ResearchStore()
    synthesizer = ResearchSynthesizer(store=store)

    live_evidence = [
        SourceEvidence(
            id="ev-live-01",
            ticker="INFY",
            title="Infosys Official Filing",
            publisher="Infosys Limited",
            document_type="exchange_filing",
            url="https://www.infosys.com/investors/filing.html",
            excerpt="Quarterly net profit reached ₹6,500 Cr.",
            is_fixture=False,  # Live official source
        )
    ]

    brief = synthesizer.generate_brief(
        ticker="INFY",
        company_name="Infosys Limited",
        evidence=live_evidence,
    )
    assert brief.source_mode == SourceMode.LIVE
    assert not any("synthetic demo fixtures" in w.lower() for w in brief.coverage.warnings)


def test_api_adapter_malformed_json_fallback(sample_evidence):
    """Verify that malformed or non-JSON model output triggers graceful fallback."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "MALFORMED NON-JSON RESPONSE {{invalid json..."
                }
            }
        ]
    }
    mock_client.post.return_value = mock_response

    adapter = APIModelAdapter(api_key="sk-test", client=mock_client)
    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries", sample_evidence)
    # Falls back gracefully to deterministic adapter with 5 sections
    assert len(sections) == 5
    assert sections[0].id == "company_overview"


def test_api_adapter_timeout_fallback(sample_evidence):
    """Verify that network timeout raises no exception and falls back to deterministic adapter."""
    mock_client = MagicMock()
    mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")

    adapter = APIModelAdapter(api_key="sk-test", client=mock_client)
    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries", sample_evidence)
    assert len(sections) == 5
    assert sections[0].id == "company_overview"


def test_claim_type_distinction(sample_evidence):
    """Verify that research sections distinguish reported facts, management statements, calculations, and interpretations."""
    adapter = DeterministicExtractiveAdapter()
    ril_evidence = [e for e in sample_evidence if e.ticker == "RELIANCE"]

    sections = adapter.synthesize_sections("RELIANCE", "Reliance Industries Limited", ril_evidence)
    sec_map = {s.id: s for s in sections}

    # Overview claims should be reported_fact
    assert all(c.claim_type == "reported_fact" for c in sec_map["company_overview"].claims)

    # Management outlook claims should be management_statement
    assert any(c.claim_type == "management_statement" for c in sec_map["management_outlook"].claims)

    # Cash & balance sheet claims should distinguish calculations/reported_fact
    assert any(c.claim_type in ("calculation", "reported_fact") for c in sec_map["cash_and_balance_sheet"].claims)

    # Risks & limitations claims should be interpretation
    assert any(c.claim_type == "interpretation" for c in sec_map["risks_and_limitations"].claims)

