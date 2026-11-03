"""Unit tests for AnomalyDetector service: price and volume calculations."""

import pytest

from app.core.models import AnomalySeverity, PriceBar
from app.services.anomalies import AnomalyDetector


@pytest.fixture
def detector():
    return AnomalyDetector(price_threshold_pct=3.0, volume_multiple_threshold=2.0, baseline_sessions=5)


# Helper to generate bars
def make_bars(ticker: str, prices: list[float], volumes: list[int]) -> list[PriceBar]:
    assert len(prices) == len(volumes)
    bars = []
    for i, (p, v) in enumerate(zip(prices, volumes)):
        date_str = f"2025-01-{i+1:02d}"
        bars.append(PriceBar(ticker=ticker, date=date_str, close=p, volume=v))
    return bars


class TestAnomalyDetectionCalculations:
    def test_price_jump_triggers_anomaly(self, detector):
        # 5 normal sessions around 100, then day 6 jumps to 105 (+5% > 3% threshold)
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 100.0, 100.0, 100.0, 105.0],
            volumes=[1_000, 1_000, 1_000, 1_000, 1_000, 1_000],
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert alert.is_price_anomaly is True
        assert alert.is_volume_anomaly is False
        assert alert.price_change_pct == 5.0
        assert alert.volume_ratio == 1.0
        assert alert.severity == AnomalySeverity.MEDIUM

    def test_volume_surge_triggers_anomaly(self, detector):
        # 5 sessions with 1,000 volume, day 6 volume surges to 2,500 (2.5x > 2.0x threshold)
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 100.0, 100.0, 100.0, 100.5],
            volumes=[1_000, 1_000, 1_000, 1_000, 1_000, 2_500],
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert alert.is_price_anomaly is False
        assert alert.is_volume_anomaly is True
        assert alert.volume_ratio == 2.5
        assert alert.severity == AnomalySeverity.MEDIUM

    def test_both_price_and_volume_trigger_high_severity(self, detector):
        # Both jump: price +4% and volume 2.5x
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 100.0, 100.0, 100.0, 104.0],
            volumes=[1_000, 1_000, 1_000, 1_000, 1_000, 2_500],
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert alert.is_price_anomaly is True
        assert alert.is_volume_anomaly is True
        assert alert.severity == AnomalySeverity.HIGH

    def test_normal_session_has_none_severity(self, detector):
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 100.0, 100.0, 100.0, 101.0],  # +1% < 3%
            volumes=[1_000, 1_000, 1_000, 1_000, 1_000, 1_200],  # 1.2x < 2.0x
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert alert.is_price_anomaly is False
        assert alert.is_volume_anomaly is False
        assert alert.severity == AnomalySeverity.NONE

    def test_insufficient_history_returns_none(self, detector):
        bars = [PriceBar(ticker="TEST", date="2025-01-01", close=100.0, volume=1_000)]
        assert detector.detect_ticker_anomaly("TEST", bars) is None
        assert detector.detect_ticker_anomaly("TEST", []) is None

    def test_zero_baseline_volume_handled_without_error(self, detector):
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 105.0],
            volumes=[0, 0, 1_000],
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert alert.volume_ratio == 1.0  # Safe fallback without zero division

    def test_explanation_contains_required_metrics_and_disclaimer(self, detector):
        bars = make_bars(
            ticker="TEST",
            prices=[100.0, 100.0, 100.0, 100.0, 100.0, 104.0],
            volumes=[1_000, 1_000, 1_000, 1_000, 1_000, 2_500],
        )
        alert = detector.detect_ticker_anomaly("TEST", bars)
        assert alert is not None
        assert "+4.0%" in alert.explanation or "4.0%" in alert.explanation
        assert "2.5" in alert.explanation
        assert "Monitoring signal only" in alert.explanation


class TestUniverseScanning:
    def test_scan_universe_filters_anomalies_only(self, detector):
        universe = {
            "ANOMALOUS": make_bars("ANOMALOUS", [100.0, 100.0, 100.0, 105.0], [1_000, 1_000, 1_000, 3_000]),
            "NORMAL": make_bars("NORMAL", [100.0, 100.0, 100.0, 100.5], [1_000, 1_000, 1_000, 1_050]),
        }
        alerts = detector.scan_universe(universe, anomalies_only=True)
        assert len(alerts) == 1
        assert alerts[0].ticker == "ANOMALOUS"

    def test_scan_universe_returns_all_when_flag_false(self, detector):
        universe = {
            "ANOMALOUS": make_bars("ANOMALOUS", [100.0, 100.0, 100.0, 105.0], [1_000, 1_000, 1_000, 3_000]),
            "NORMAL": make_bars("NORMAL", [100.0, 100.0, 100.0, 100.5], [1_000, 1_000, 1_000, 1_050]),
        }
        alerts = detector.scan_universe(universe, anomalies_only=False)
        assert len(alerts) == 2

