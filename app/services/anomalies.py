"""Price and volume anomaly detection service.

Detects unusual daily close-to-close price movements and volume spikes
against a rolling 20-trading-session historical baseline.
All signals are strictly monitoring indicators; no forecast or advice is implied.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional

from app.core.models import AnomalySeverity, PriceAnomalyAlert, PriceBar
from app.data.companies import PORTDATA

# Map tickers to names for friendly alert titles
TICKER_NAME_MAP: Dict[str, str] = {c.ticker.upper(): c.name for c in PORTDATA}


class AnomalyDetector:
    """Detects end-of-day price and volume anomalies for Indian equities."""

    def __init__(
        self,
        price_threshold_pct: float = 3.0,
        volume_multiple_threshold: float = 2.0,
        baseline_sessions: int = 20,
        trigger_mode: str = "OR",
    ):
        """Initialize detector with configurable thresholds.

        Args:
            price_threshold_pct: Absolute price movement trigger (default ±3.0%).
            volume_multiple_threshold: Volume multiplier trigger vs baseline (default 2.0×).
            baseline_sessions: Number of historical trading sessions for volume baseline (default 20).
        """
        if trigger_mode not in {"OR", "AND"}:
            raise ValueError("trigger_mode must be OR or AND")
        self.trigger_mode = trigger_mode
        self.price_threshold_pct = abs(price_threshold_pct)
        self.volume_multiple_threshold = abs(volume_multiple_threshold)
        self.baseline_sessions = baseline_sessions

    def detect_ticker_anomaly(
        self,
        ticker: str,
        bars: List[PriceBar],
    ) -> Optional[PriceAnomalyAlert]:
        """Analyze the latest price bar for a ticker against preceding history.

        Requires at least 2 bars (today and previous close).
        If history has >= baseline_sessions + 1 bars, a full 20-session baseline is used.
        """
        if not bars or len(bars) < 2:
            return None

        # Ensure bars are sorted chronologically
        sorted_bars = sorted(bars, key=lambda b: b.date)
        today = sorted_bars[-1]
        yesterday = sorted_bars[-2]

        company_name = TICKER_NAME_MAP.get(ticker.upper(), ticker)

        # 1. Price movement calculation
        if yesterday.close <= 0:
            raw_price_change_pct = 0.0
        else:
            raw_price_change_pct = ((today.close - yesterday.close) / yesterday.close) * 100
        price_change_pct = round(raw_price_change_pct, 4)

        is_price_anomaly = abs(raw_price_change_pct) >= self.price_threshold_pct

        # 2. Historical volume baseline (sessions strictly BEFORE today)
        prior_sessions = sorted_bars[:-1]
        if len(prior_sessions) >= self.baseline_sessions:
            baseline_window = prior_sessions[-self.baseline_sessions:]
        else:
            baseline_window = prior_sessions

        baseline_volumes = [b.volume for b in baseline_window if b.volume > 0]

        if baseline_volumes:
            mean_volume = statistics.mean(baseline_volumes)
        else:
            mean_volume = 0.0

        if mean_volume > 0:
            raw_volume_ratio = today.volume / mean_volume
        else:
            raw_volume_ratio = 1.0
        volume_ratio = round(raw_volume_ratio, 4)

        is_volume_anomaly = mean_volume > 0 and raw_volume_ratio >= self.volume_multiple_threshold
        triggered = (is_price_anomaly or is_volume_anomaly) if self.trigger_mode == "OR" else (is_price_anomaly and is_volume_anomaly)

        # 3. Severity classification
        if is_price_anomaly and is_volume_anomaly:
            severity = AnomalySeverity.HIGH
        elif is_price_anomaly or is_volume_anomaly:
            # If price moved > 2x threshold or volume > 2x threshold, elevate to high
            if abs(price_change_pct) >= (2 * self.price_threshold_pct) or volume_ratio >= (2 * self.volume_multiple_threshold):
                severity = AnomalySeverity.HIGH
            else:
                severity = AnomalySeverity.MEDIUM
        else:
            severity = AnomalySeverity.NONE

        if not triggered:
            severity = AnomalySeverity.NONE

        # 4. Human-readable explanation
        sign = "+" if price_change_pct >= 0 else ""
        expl_parts = []
        if is_price_anomaly:
            expl_parts.append(
                f"Price moved {sign}{price_change_pct}% from ₹{yesterday.close:.2f} to ₹{today.close:.2f} "
                f"(threshold ±{self.price_threshold_pct}%)."
            )
        if is_volume_anomaly:
            expl_parts.append(
                f"Volume {today.volume:,} is {volume_ratio}× the {len(baseline_volumes)}-session baseline mean "
                f"({int(mean_volume):,} shares; threshold {self.volume_multiple_threshold}×)."
            )
        if not is_price_anomaly and not is_volume_anomaly:
            expl_parts.append(
                f"Normal session: price {sign}{price_change_pct}%, volume {volume_ratio}× baseline."
            )

        expl_parts.append("Monitoring signal only; not a performance forecast or trade recommendation.")
        explanation = " ".join(expl_parts)

        return PriceAnomalyAlert(
            ticker=ticker.upper(),
            company_name=company_name,
            date=today.date,
            close=today.close,
            previous_close=yesterday.close,
            price_change_pct=price_change_pct,
            volume=today.volume,
            baseline_volume_mean=round(mean_volume, 1),
            volume_ratio=volume_ratio,
            is_price_anomaly=is_price_anomaly,
            is_volume_anomaly=is_volume_anomaly,
            severity=severity,
            explanation=explanation,
            is_fixture=True,
            baseline_sessions=len(baseline_volumes),
            price_threshold_pct=self.price_threshold_pct,
            volume_multiple_threshold=self.volume_multiple_threshold,
            trigger_mode=self.trigger_mode,
            triggered=triggered,
        )

    def scan_universe(
        self,
        bars_by_ticker: Dict[str, List[PriceBar]],
        anomalies_only: bool = True,
    ) -> List[PriceAnomalyAlert]:
        """Scan all tickers and return detected alerts ordered by severity and volume ratio."""
        alerts: List[PriceAnomalyAlert] = []

        for ticker, bars in bars_by_ticker.items():
            alert = self.detect_ticker_anomaly(ticker, bars)
            if alert:
                if not anomalies_only or alert.triggered:
                    alerts.append(alert)

        # Sort: HIGH severity first, then by volume ratio descending, then absolute price change descending
        severity_order = {AnomalySeverity.HIGH: 0, AnomalySeverity.MEDIUM: 1, AnomalySeverity.NONE: 2}
        alerts.sort(
            key=lambda a: (
                severity_order.get(a.severity, 99),
                -a.volume_ratio,
                -abs(a.price_change_pct),
                a.ticker,
            )
        )

        return alerts

