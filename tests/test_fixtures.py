"""Tests for FINN demo fixtures — companies, announcements, prices."""

import pytest

from app.core.models import AnnouncementCategory, Priority
from app.data.announcements import ANNOUNCEMENTS
from app.data.companies import PORTDATA, RESEARCH_DATA
from app.data.prices import PRICE_BARS, PRICE_BARS_BY_TICKER, TRADING_DATES


# ── Company fixtures ─────────────────────────────────────────────────────


class TestPortfolio:
    """Portfolio must have 15–20 companies per BUILD_PLAN."""

    def test_portfolio_count(self):
        assert 15 <= len(PORTDATA) <= 20, (
            f"Portfolio has {len(PORTDATA)} companies, expected 15–20"
        )

    def test_portfolio_tickers_unique(self):
        tickers = [c.ticker for c in PORTDATA]
        assert len(tickers) == len(set(tickers)), "Duplicate tickers in portfolio"

    def test_all_have_name(self):
        for c in PORTDATA:
            assert c.name, f"{c.ticker} has empty name"

    def test_all_have_exchange(self):
        for c in PORTDATA:
            assert c.exchange in ("NSE", "BSE"), (
                f"{c.ticker} has unexpected exchange {c.exchange}"
            )


class TestResearchUniverse:
    """Research universe must have 3–5 companies from the portfolio."""

    def test_research_count(self):
        assert 3 <= len(RESEARCH_DATA) <= 5

    def test_research_subset_of_portfolio(self):
        portfolio_tickers = {c.ticker for c in PORTDATA}
        for c in RESEARCH_DATA:
            assert c.ticker in portfolio_tickers, (
                f"Research company {c.ticker} not in portfolio"
            )


# ── Announcement fixtures ────────────────────────────────────────────────


class TestAnnouncements:
    """Announcement fixtures must be valid and diverse."""

    def test_announcement_count(self):
        assert len(ANNOUNCEMENTS) >= 8, (
            f"Only {len(ANNOUNCEMENTS)} announcements, expected ≥ 8"
        )

    def test_ids_unique(self):
        ids = [a.id for a in ANNOUNCEMENTS]
        assert len(ids) == len(set(ids)), "Duplicate announcement IDs"

    def test_tickers_in_portfolio(self):
        portfolio_tickers = {c.ticker for c in PORTDATA}
        for a in ANNOUNCEMENTS:
            assert a.ticker in portfolio_tickers, (
                f"Announcement {a.id} references unknown ticker {a.ticker}"
            )

    def test_all_marked_fixture(self):
        for a in ANNOUNCEMENTS:
            assert a.is_fixture is True, (
                f"Announcement {a.id} not marked as fixture"
            )

    def test_category_diversity(self):
        categories = {a.category for a in ANNOUNCEMENTS}
        assert len(categories) >= 5, (
            f"Only {len(categories)} distinct categories, expected ≥ 5"
        )

    def test_has_high_priority(self):
        high = [a for a in ANNOUNCEMENTS if a.priority == Priority.HIGH]
        assert len(high) >= 1, "No high-priority announcements in fixtures"

    def test_has_low_priority(self):
        low = [a for a in ANNOUNCEMENTS if a.priority == Priority.LOW]
        assert len(low) >= 1, "No low-priority (routine) announcements"

    def test_dates_valid_format(self):
        import re
        date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for a in ANNOUNCEMENTS:
            assert date_re.match(a.published_at), (
                f"Announcement {a.id} has invalid date {a.published_at}"
            )

    def test_priority_scores_positive(self):
        for a in ANNOUNCEMENTS:
            assert a.priority_score > 0, (
                f"Announcement {a.id} has non-positive priority_score"
            )

    def test_all_have_summary(self):
        for a in ANNOUNCEMENTS:
            assert a.summary, f"Announcement {a.id} has empty summary"


# ── Price-bar fixtures ───────────────────────────────────────────────────


class TestPriceBars:
    """Synthetic price bars must cover the portfolio with ordered dates."""

    def test_total_bar_count(self):
        expected = len(PRICE_BARS_BY_TICKER) * len(TRADING_DATES)
        assert len(PRICE_BARS) == expected

    def test_all_portfolio_tickers_present(self):
        portfolio_tickers = {c.ticker for c in PORTDATA}
        price_tickers = set(PRICE_BARS_BY_TICKER.keys())
        assert portfolio_tickers == price_tickers, (
            f"Missing price data for: {portfolio_tickers - price_tickers}"
        )

    def test_each_ticker_has_enough_history(self):
        """Need ≥ 21 days for 20-day anomaly baseline + current day."""
        for ticker, bars in PRICE_BARS_BY_TICKER.items():
            assert len(bars) >= 21, (
                f"{ticker} has only {len(bars)} bars, need ≥ 21"
            )

    def test_dates_ascending(self):
        for ticker, bars in PRICE_BARS_BY_TICKER.items():
            dates = [b.date for b in bars]
            assert dates == sorted(dates), (
                f"{ticker} price dates are not ascending"
            )

    def test_positive_close_prices(self):
        for bar in PRICE_BARS:
            assert bar.close > 0, (
                f"{bar.ticker} on {bar.date} has non-positive close {bar.close}"
            )

    def test_positive_volumes(self):
        for bar in PRICE_BARS:
            assert bar.volume > 0, (
                f"{bar.ticker} on {bar.date} has non-positive volume"
            )

    def test_high_gte_close_and_open(self):
        for bar in PRICE_BARS:
            assert bar.high >= bar.close, (
                f"{bar.ticker} {bar.date}: high < close"
            )
            assert bar.high >= bar.open, (
                f"{bar.ticker} {bar.date}: high < open"
            )

    def test_low_lte_close_and_open(self):
        for bar in PRICE_BARS:
            assert bar.low <= bar.close, (
                f"{bar.ticker} {bar.date}: low > close"
            )
            assert bar.low <= bar.open, (
                f"{bar.ticker} {bar.date}: low > open"
            )

