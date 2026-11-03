"""Unit tests for AnnouncementService: normalization, scoring, and window filtering."""

import pytest

from app.core.models import Announcement, AnnouncementCategory, Priority
from app.services.announcements import (
    AnnouncementService,
    NormalizationError,
)


@pytest.fixture
def service():
    return AnnouncementService()


# ── Normalization Tests ──────────────────────────────────────────────────


class TestNormalization:
    def test_normalize_valid_record(self, service):
        raw = {
            "ticker": "INFY",
            "category": "results",
            "title": "Infosys Q3 Results Approved",
            "published_at": "2025-01-16",
            "summary": "Revenue grew 6.1% YoY",
        }
        ann = service.normalize_record(raw)
        assert ann.ticker == "INFY"
        assert ann.company_name == "Infosys Limited"  # Resolved from portfolio
        assert ann.category == AnnouncementCategory.RESULTS
        assert ann.priority == Priority.HIGH
        assert ann.is_fixture is True

    def test_normalize_category_alias(self, service):
        raw = {
            "ticker": "RELIANCE",
            "category": "merger_acquisition",  # Alias for m_and_a
            "title": "RIL announces strategic JV",
            "published_at": "2025-01-20",
        }
        ann = service.normalize_record(raw)
        assert ann.category == AnnouncementCategory.M_AND_A
        assert ann.priority == Priority.HIGH

    def test_normalize_unclassified_category_fallback(self, service):
        raw = {
            "ticker": "TCS",
            "category": "completely_unknown_category_xyz",
            "title": "General notification",
            "published_at": "2025-01-22",
        }
        ann = service.normalize_record(raw)
        assert ann.category == AnnouncementCategory.UNCLASSIFIED
        assert ann.priority == Priority.LOW

    def test_missing_ticker_raises_error(self, service):
        with pytest.raises(NormalizationError, match="Missing required field: 'ticker'"):
            service.normalize_record({
                "category": "results",
                "title": "Test Title",
                "published_at": "2025-01-16",
            })

    def test_missing_title_raises_error(self, service):
        with pytest.raises(NormalizationError, match="Missing required field: 'title'"):
            service.normalize_record({
                "ticker": "INFY",
                "category": "results",
                "published_at": "2025-01-16",
            })

    def test_missing_published_at_raises_error(self, service):
        with pytest.raises(NormalizationError, match="Missing required field: 'published_at'"):
            service.normalize_record({
                "ticker": "INFY",
                "category": "results",
                "title": "Test Title",
            })

    def test_invalid_date_format_raises_error(self, service):
        with pytest.raises(NormalizationError, match="Invalid published_at format"):
            service.normalize_record({
                "ticker": "INFY",
                "category": "results",
                "title": "Test Title",
                "published_at": "not-a-date",
            })


# ── Deduplication and Batch Processing ───────────────────────────────────


class TestBatchAndDeduplication:
    def test_deduplication_filters_identical_filings(self, service):
        records = [
            {
                "ticker": "INFY",
                "category": "results",
                "title": "Infosys Q3 Results Approved",
                "published_at": "2025-01-16",
            },
            {  # Exact duplicate
                "ticker": "INFY",
                "category": "results",
                "title": "Infosys Q3 Results Approved",
                "published_at": "2025-01-16",
            },
            {  # Different announcement
                "ticker": "TCS",
                "category": "dividend",
                "title": "TCS Special Dividend",
                "published_at": "2025-01-18",
            },
        ]
        result = service.process_batch(records)
        assert result.valid_count == 2
        assert result.duplicate_count == 1
        assert result.invalid_count == 0

    def test_batch_captures_invalid_records_without_crashing(self, service):
        records = [
            {"ticker": "INFY", "category": "results", "title": "Good", "published_at": "2025-01-16"},
            {"ticker": "", "category": "results", "title": "Bad Ticker", "published_at": "2025-01-16"},
            {"ticker": "TCS", "category": "results", "title": "", "published_at": "2025-01-16"},
        ]
        result = service.process_batch(records)
        assert result.valid_count == 1
        assert result.invalid_count == 2


# ── Priority Scoring & Ordering ──────────────────────────────────────────


class TestPriorityScoring:
    def test_scoring_places_results_above_routine(self, service):
        high_ann = Announcement(
            id="1", ticker="INFY", company_name="Infosys",
            category=AnnouncementCategory.RESULTS,
            title="Q3 Results", published_at="2025-01-16",
        )
        low_ann = Announcement(
            id="2", ticker="SBIN", company_name="SBI",
            category=AnnouncementCategory.AGM_EGM,
            title="AGM Notice", published_at="2025-01-16",
        )
        ranked = service.score_and_rank([low_ann, high_ann])
        assert ranked[0].id == "1"
        assert ranked[1].id == "2"

    def test_deterministic_tie_breaking(self, service):
        ann1 = Announcement(
            id="b-ann", ticker="TCS", company_name="TCS",
            category=AnnouncementCategory.RESULTS,
            title="Results B", published_at="2025-01-16",
        )
        ann2 = Announcement(
            id="a-ann", ticker="INFY", company_name="Infosys",
            category=AnnouncementCategory.RESULTS,
            title="Results A", published_at="2025-01-16",
        )
        # INFY comes alphabetically before TCS when score and date are tied
        ranked = service.score_and_rank([ann1, ann2])
        assert ranked[0].ticker == "INFY"
        assert ranked[1].ticker == "TCS"


# ── Date Window Filtering ────────────────────────────────────────────────


class TestDateWindowFiltering:
    @pytest.fixture
    def test_announcements(self):
        return [
            Announcement(id="1", ticker="A", company_name="A", category=AnnouncementCategory.RESULTS, title="Today", published_at="2025-02-05"),
            Announcement(id="2", ticker="B", company_name="B", category=AnnouncementCategory.RESULTS, title="Yesterday", published_at="2025-02-04"),
            Announcement(id="3", ticker="C", company_name="C", category=AnnouncementCategory.RESULTS, title="3 days ago", published_at="2025-02-02"),
            Announcement(id="4", ticker="D", company_name="D", category=AnnouncementCategory.RESULTS, title="6 days ago", published_at="2025-01-30"),
            Announcement(id="5", ticker="E", company_name="E", category=AnnouncementCategory.RESULTS, title="20 days ago", published_at="2025-01-16"),
            Announcement(id="6", ticker="F", company_name="F", category=AnnouncementCategory.RESULTS, title="Future", published_at="2025-02-10"),
        ]

    def test_filter_24h_window(self, service, test_announcements):
        # Ref: 2025-02-05 -> 24h window (1 day delta: 2025-02-04 to 2025-02-05)
        filtered = service.filter_by_window(test_announcements, window="24h", reference_date="2025-02-05")
        ids = {a.id for a in filtered}
        assert ids == {"1", "2"}

    def test_filter_3d_window(self, service, test_announcements):
        # Ref: 2025-02-05 -> 3d window (2025-02-02 to 2025-02-05)
        filtered = service.filter_by_window(test_announcements, window="3d", reference_date="2025-02-05")
        ids = {a.id for a in filtered}
        assert ids == {"1", "2", "3"}

    def test_filter_7d_window(self, service, test_announcements):
        # Ref: 2025-02-05 -> 7d window (2025-01-29 to 2025-02-05)
        filtered = service.filter_by_window(test_announcements, window="7d", reference_date="2025-02-05")
        ids = {a.id for a in filtered}
        assert ids == {"1", "2", "3", "4"}

    def test_filter_excludes_future_filings(self, service, test_announcements):
        filtered = service.filter_by_window(test_announcements, window="all", reference_date="2025-02-05")
        ids = {a.id for a in filtered}
        assert "6" not in ids  # Future filing (2025-02-10) is excluded
        assert len(filtered) == 5

