"""Tests for FINN data models — enum values and Pydantic validation."""

import pytest
from pydantic import ValidationError

from app.core.models import (
    Announcement,
    AnnouncementCategory,
    CATEGORY_BASE_SCORE,
    CATEGORY_DEFAULT_PRIORITY,
    Claim,
    Company,
    CompanyResearch,
    Confidence,
    DataSourceType,
    PriceBar,
    Priority,
    ResearchCoverage,
    ResearchSection,
    SourceEvidence,
    SourceMode,
)


# ── Enum completeness ────────────────────────────────────────────────────


class TestAnnouncementCategory:
    """AnnouncementCategory must cover the full BUILD_PLAN taxonomy."""

    EXPECTED = {
        "results", "m_and_a", "fund_raise", "management_change",
        "litigation", "insider_trading", "earnings_call",
        "investor_meetings", "credit_rating", "dividend",
        "bonus_split", "capex", "press_release", "postal_ballot",
        "agm_egm", "pledging", "unclassified",
    }

    def test_all_categories_present(self):
        actual = {c.value for c in AnnouncementCategory}
        assert actual == self.EXPECTED

    def test_category_count(self):
        assert len(AnnouncementCategory) == 17


class TestDataSourceType:
    def test_source_types(self):
        expected = {
            "annual_report", "quarterly_results", "earnings_call",
            "investor_presentation", "exchange_filing", "official_release",
        }
        actual = {s.value for s in DataSourceType}
        assert actual == expected


class TestPriority:
    def test_levels(self):
        assert {p.value for p in Priority} == {"high", "medium", "low"}


class TestConfidence:
    def test_levels(self):
        assert {c.value for c in Confidence} == {"high", "medium", "low"}


class TestSourceMode:
    def test_modes(self):
        assert {m.value for m in SourceMode} == {"live", "demo"}


# ── Priority mappings ────────────────────────────────────────────────────


class TestPriorityMappings:
    def test_every_category_has_default_priority(self):
        for cat in AnnouncementCategory:
            assert cat in CATEGORY_DEFAULT_PRIORITY, (
                f"{cat.value} missing from CATEGORY_DEFAULT_PRIORITY"
            )

    def test_every_category_has_base_score(self):
        for cat in AnnouncementCategory:
            assert cat in CATEGORY_BASE_SCORE, (
                f"{cat.value} missing from CATEGORY_BASE_SCORE"
            )

    def test_high_priority_categories(self):
        high_cats = {
            AnnouncementCategory.RESULTS,
            AnnouncementCategory.M_AND_A,
            AnnouncementCategory.FUND_RAISE,
            AnnouncementCategory.MANAGEMENT_CHANGE,
            AnnouncementCategory.LITIGATION,
            AnnouncementCategory.CREDIT_RATING,
        }
        for cat in high_cats:
            assert CATEGORY_DEFAULT_PRIORITY[cat] == Priority.HIGH

    def test_base_scores_positive(self):
        for cat, score in CATEGORY_BASE_SCORE.items():
            assert score > 0, f"{cat.value} has non-positive score {score}"


# ── Pydantic model validation ────────────────────────────────────────────


class TestCompanyModel:
    def test_valid_company(self):
        c = Company(ticker="INFY", name="Infosys Limited")
        assert c.ticker == "INFY"
        assert c.exchange == "NSE"  # default

    def test_company_with_all_fields(self):
        c = Company(
            ticker="RELIANCE",
            name="Reliance Industries Limited",
            exchange="BSE",
            sector="Energy",
            industry="Oil & Gas",
        )
        assert c.exchange == "BSE"
        assert c.sector == "Energy"

    def test_company_requires_ticker(self):
        with pytest.raises(ValidationError):
            Company(name="Missing Ticker Corp")  # type: ignore[call-arg]

    def test_company_requires_name(self):
        with pytest.raises(ValidationError):
            Company(ticker="NOPE")  # type: ignore[call-arg]


class TestAnnouncementModel:
    def test_valid_announcement(self):
        a = Announcement(
            id="test-001",
            ticker="INFY",
            company_name="Infosys Limited",
            category=AnnouncementCategory.RESULTS,
            title="Q3 Results",
            published_at="2025-01-16",
        )
        assert a.priority == Priority.MEDIUM  # default
        assert a.is_fixture is True  # default

    def test_invalid_category_rejected(self):
        with pytest.raises(ValidationError):
            Announcement(
                id="bad",
                ticker="X",
                company_name="X",
                category="not_a_category",  # type: ignore[arg-type]
                title="Bad",
                published_at="2025-01-01",
            )


class TestPriceBarModel:
    def test_valid_bar(self):
        bar = PriceBar(
            ticker="INFY", date="2025-01-02", close=1500.0, volume=10_000_000,
        )
        assert bar.open == 0.0  # default
        assert bar.volume == 10_000_000

    def test_bar_requires_close(self):
        with pytest.raises(ValidationError):
            PriceBar(ticker="X", date="2025-01-01", volume=100)  # type: ignore[call-arg]

    def test_bar_requires_volume(self):
        with pytest.raises(ValidationError):
            PriceBar(ticker="X", date="2025-01-01", close=100.0)  # type: ignore[call-arg]


class TestSourceEvidenceModel:
    def test_auto_id(self):
        ev = SourceEvidence(
            title="Annual Report FY2024",
            publisher="Infosys Limited",
            document_type="annual_report",
        )
        assert ev.id.startswith("ev-")
        assert ev.is_primary is True

    def test_explicit_id(self):
        ev = SourceEvidence(
            id="ev-custom",
            title="Test",
            publisher="Test",
            document_type="exchange_filing",
        )
        assert ev.id == "ev-custom"


class TestCompanyResearch:
    def test_default_coverage(self):
        r = CompanyResearch(
            ticker="INFY",
            company_name="Infosys Limited",
            generated_at="2025-01-20T10:00:00",
        )
        assert r.source_mode == SourceMode.DEMO
        assert r.coverage.documents_found == 0
        assert r.sections == []
        assert r.evidence == []

