"""Unit tests for ResultsService: quarterly results summaries and metrics."""

import pytest

from app.services.results import ResultsService


@pytest.fixture
def service():
    return ResultsService()


class TestResultsService:
    def test_get_reliance_results(self, service):
        summary = service.get_summary_by_ticker("RELIANCE")
        assert summary is not None
        assert summary.ticker == "RELIANCE"
        assert summary.period == "Q3 FY2025"
        assert summary.unit == "₹ Cr"
        assert summary.basis == "consolidated"

        # Revenue
        assert summary.revenue is not None
        assert summary.revenue.current == 243865.0
        assert summary.revenue.yoy_prev == 217730.0
        assert summary.revenue.yoy_growth_pct == round(((243865.0 - 217730.0) / 217730.0) * 100, 2)

        # EBITDA & PAT
        assert summary.ebitda is not None
        assert summary.ebitda.current == 43250.0
        assert summary.pat is not None
        assert summary.pat.current == 18540.0

    def test_get_infy_results(self, service):
        summary = service.get_summary_by_ticker("INFY")
        assert summary is not None
        assert summary.ticker == "INFY"
        assert summary.revenue is not None
        assert summary.revenue.current == 41764.0

    def test_missing_metrics_represented_as_none(self, service):
        summary = service.get_summary_by_ticker("TCS")
        assert summary is not None
        assert summary.pbt is None  # Unavailable in source
        assert summary.ebitda is not None
        assert summary.ebitda.yoy_prev is None  # Missing YoY comparison
        assert summary.ebitda.yoy_growth_pct is None  # Growth cannot be computed

    def test_unknown_ticker_returns_none(self, service):
        summary = service.get_summary_by_ticker("UNKNOWN_TICKER")
        assert summary is None

    def test_get_all_summaries(self, service):
        summaries = service.get_all_summaries()
        assert len(summaries) >= 3
        tickers = {s.ticker for s in summaries}
        assert {"RELIANCE", "INFY", "TCS"}.issubset(tickers)

