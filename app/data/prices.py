"""Synthetic price-bar fixtures for the demo portfolio.

ALL data in this module is SYNTHETIC and does not represent actual
market prices or volumes. It is generated deterministically for
testing and demonstration purposes only.
"""

import hashlib
from typing import Dict, List

from app.core.models import PriceBar

# Approximate base prices (INR) for synthetic generation.
# These are NOT current market prices and must not be presented as such.
_BASE_PRICES: Dict[str, float] = {
    "RELIANCE": 2500.0,
    "HDFCBANK": 1600.0,
    "ICICIBANK": 1050.0,
    "SBIN": 620.0,
    "INFY": 1500.0,
    "TCS": 3600.0,
    "WIPRO": 460.0,
    "BHARTARTL": 1200.0,
    "LT": 3100.0,
    "TATAMOTORS": 720.0,
    "M&M": 1850.0,
    "ITC": 440.0,
    "HINDUNILVR": 2400.0,
    "SUNPHARMA": 1250.0,
    "DRREDDY": 5600.0,
    "TATASTEEL": 135.0,
    "NTPC": 360.0,
    "POWERGRID": 285.0,
    "ASIANPAINT": 2900.0,
}

# Approximate daily traded volumes (shares) for synthetic generation.
_BASE_VOLUMES: Dict[str, int] = {
    "RELIANCE": 8_000_000,
    "HDFCBANK": 12_000_000,
    "ICICIBANK": 15_000_000,
    "SBIN": 25_000_000,
    "INFY": 10_000_000,
    "TCS": 3_000_000,
    "WIPRO": 8_000_000,
    "BHARTARTL": 5_000_000,
    "LT": 2_500_000,
    "TATAMOTORS": 18_000_000,
    "M&M": 4_000_000,
    "ITC": 15_000_000,
    "HINDUNILVR": 3_000_000,
    "SUNPHARMA": 6_000_000,
    "DRREDDY": 1_500_000,
    "TATASTEEL": 20_000_000,
    "NTPC": 12_000_000,
    "POWERGRID": 10_000_000,
    "ASIANPAINT": 2_000_000,
}

# 25 synthetic trading days — weekdays in Jan–Feb 2025.
TRADING_DATES: List[str] = [
    "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08",
    "2025-01-09", "2025-01-10", "2025-01-13", "2025-01-14", "2025-01-15",
    "2025-01-16", "2025-01-17", "2025-01-20", "2025-01-21", "2025-01-22",
    "2025-01-23", "2025-01-24", "2025-01-27", "2025-01-28", "2025-01-29",
    "2025-01-30", "2025-01-31", "2025-02-03", "2025-02-04", "2025-02-05",
]


def _deterministic_factor(seed: str, amplitude: float = 0.03) -> float:
    """Return a deterministic multiplicative factor in [1-amp, 1+amp].

    Uses SHA-256 of the seed to produce a repeatable pseudo-random number.
    """
    h = hashlib.sha256(seed.encode()).hexdigest()
    frac = int(h[:8], 16) / 0xFFFFFFFF  # maps to [0, 1)
    return 1.0 + (frac - 0.5) * 2 * amplitude


def _generate_bars() -> List[PriceBar]:
    """Generate synthetic daily OHLCV bars for every portfolio company."""
    bars: List[PriceBar] = []

    for ticker, base_price in _BASE_PRICES.items():
        price = base_price
        base_vol = _BASE_VOLUMES.get(ticker, 5_000_000)

        for idx, date_str in enumerate(TRADING_DATES):
            seed = f"{ticker}:{date_str}"
            is_final_day = (idx == len(TRADING_DATES) - 1)

            # Check for simulated demo anomalies on final trading day
            if is_final_day and ticker == "TATAMOTORS":
                # Simulated breakout: +4.2% price move, 2.85x volume
                factor = 1.042
                vol_factor = 2.85
            elif is_final_day and ticker == "INFY":
                # Simulated earnings move: +3.2% price move, 2.30x volume
                factor = 1.032
                vol_factor = 2.30
            else:
                factor = _deterministic_factor(seed, amplitude=0.025)
                vol_factor = _deterministic_factor(seed + ":vol", amplitude=0.4)

            close = round(price * factor, 2)
            open_price = round(price * _deterministic_factor(seed + ":open", 0.008), 2)

            high = round(max(open_price, close) * _deterministic_factor(seed + ":high", 0.005), 2)
            high = max(high, open_price, close)

            low = round(min(open_price, close) * _deterministic_factor(seed + ":low", 0.005), 2)
            low = min(low, open_price, close)

            volume = max(100_000, int(base_vol * vol_factor))

            bars.append(
                PriceBar(
                    ticker=ticker,
                    date=date_str,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )

            # Walk forward for the next day
            price = close

    return bars


# ── Module-level fixtures (generated once on import) ─────────────────────

PRICE_BARS: List[PriceBar] = _generate_bars()

# Convenience: bars grouped by ticker
PRICE_BARS_BY_TICKER: Dict[str, List[PriceBar]] = {}
for _bar in PRICE_BARS:
    PRICE_BARS_BY_TICKER.setdefault(_bar.ticker, []).append(_bar)
