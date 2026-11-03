"""Quarterly results extraction and comparison service.

Extracts Revenue, EBITDA, PBT, and PAT metrics for current quarter,
QoQ (prior quarter), and YoY (prior year same quarter).
Preserves explicit units (₹ Cr) and reporting basis (consolidated/standalone).
Unavailable figures are represented as None ("Not available in source").
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.core.models import QuarterlyMetric, QuarterlyResultSummary


# ── Structured demo quarterly results repository ──────────────────────────
# Synthetic fixture data matching results announcements in app.data.announcements

DEMO_RESULTS_STORE: Dict[str, QuarterlyResultSummary] = {

    # RELIANCE Q3 FY2025
    "RELIANCE": QuarterlyResultSummary(
        ticker="RELIANCE",
        company_name="Reliance Industries Limited",
        period="Q3 FY2025",
        previous_period="Q2 FY2025",
        previous_year_period="Q3 FY2024",
        filing_id="ann-001",
        unit="₹ Cr",
        basis="consolidated",
        revenue=QuarterlyMetric(
            metric_name="Revenue",
            current=243865.0,
            qoq_prev=235480.0,
            yoy_prev=217730.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        ebitda=QuarterlyMetric(
            metric_name="EBITDA",
            current=43250.0,
            qoq_prev=41800.0,
            yoy_prev=40050.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        pbt=QuarterlyMetric(
            metric_name="PBT",
            current=25120.0,
            qoq_prev=24300.0,
            yoy_prev=23180.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        pat=QuarterlyMetric(
            metric_name="PAT",
            current=18540.0,
            qoq_prev=17890.0,
            yoy_prev=16560.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        is_fixture=True,
    ),
    # INFY Q3 FY2025
    "INFY": QuarterlyResultSummary(
        ticker="INFY",
        company_name="Infosys Limited",
        period="Q3 FY2025",
        previous_period="Q2 FY2025",
        previous_year_period="Q3 FY2024",
        filing_id="ann-005",
        unit="₹ Cr",
        basis="consolidated",
        revenue=QuarterlyMetric(
            metric_name="Revenue",
            current=41764.0,
            qoq_prev=40986.0,
            yoy_prev=39360.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        ebitda=QuarterlyMetric(
            metric_name="EBITDA",
            current=8895.0,
            qoq_prev=8648.0,
            yoy_prev=8383.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        pbt=QuarterlyMetric(
            metric_name="PBT",
            current=8450.0,
            qoq_prev=8190.0,
            yoy_prev=7920.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        pat=QuarterlyMetric(
            metric_name="PAT",
            current=6106.0,
            qoq_prev=5935.0,
            yoy_prev=5730.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        is_fixture=True,
    ),
    # TCS Q3 FY2025 (Partial figures to test missing values handling)
    "TCS": QuarterlyResultSummary(
        ticker="TCS",
        company_name="Tata Consultancy Services",
        period="Q3 FY2025",
        previous_period="Q2 FY2025",
        previous_year_period="Q3 FY2024",
        filing_id="ann-003",
        unit="₹ Cr",
        basis="consolidated",
        revenue=QuarterlyMetric(
            metric_name="Revenue",
            current=64259.0,
            qoq_prev=64259.0,
            yoy_prev=60583.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        ebitda=QuarterlyMetric(
            metric_name="EBITDA",
            current=16080.0,
            qoq_prev=15800.0,
            yoy_prev=None,  # Missing YoY comparison
            unit="₹ Cr",
            basis="consolidated",
        ),
        pbt=None,  # Entirely unavailable in source
        pat=QuarterlyMetric(
            metric_name="PAT",
            current=12434.0,
            qoq_prev=11909.0,
            yoy_prev=11058.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        is_fixture=True,
    ),
}


# ── Real (verified) quarterly results repository ──────────────────────────
# Figures extracted verbatim from Infosys Q3 FY2025 IFRS INR Press Release
# (document doc-2ae36f62af8bd4862f70629b, published 2025-01-16).
# EBITDA is NOT stated in the source — operating profit is reported instead
# and is NOT presented as EBITDA. QoQ absolute comparisons are not available
# in ₹ crore in the source document (only 1.7% CC QoQ growth rate is stated).

REAL_RESULTS_STORE: Dict[str, QuarterlyResultSummary] = {
    "INFY": QuarterlyResultSummary(
        ticker="INFY",
        company_name="Infosys Limited",
        period="Q3 FY2025 (quarter ended December 31, 2024)",
        previous_period=None,  # Q2 FY2025 absolute figures not stated in source
        previous_year_period="Q3 FY2024 (quarter ended December 31, 2023)",
        filing_id="evt-infy-q3fy2025-results",
        unit="₹ Cr",
        basis="consolidated, IFRS–INR",
        revenue=QuarterlyMetric(
            metric_name="Revenue",
            current=41764.0,
            qoq_prev=None,  # Not stated in ₹ crore in source
            yoy_prev=38821.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        ebitda=None,  # NOT stated in source document — do not fabricate
        pbt=QuarterlyMetric(
            metric_name="PBT",
            current=9670.0,
            qoq_prev=None,  # Not stated in ₹ crore in source
            yoy_prev=8619.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        pat=QuarterlyMetric(
            metric_name="PAT",
            current=6806.0,
            qoq_prev=None,  # Not stated in ₹ crore in source
            yoy_prev=6106.0,
            unit="₹ Cr",
            basis="consolidated",
        ),
        is_fixture=False,
    ),
}


class ResultsService:
    """Service for retrieving and formatting quarterly financial performance summaries.

    In demo mode (DEMO_MODE=true) returns synthetic fixture data.
    In real-data mode (DEMO_MODE=false) returns only verified, document-backed
    results. Synthetic and real data are never mixed.
    """

    def __init__(
        self,
        store: Optional[Dict[str, QuarterlyResultSummary]] = None,
        demo_mode: bool = True,
    ):
        if store is not None:
            self.store = store
        elif demo_mode:
            self.store = DEMO_RESULTS_STORE
        else:
            self.store = REAL_RESULTS_STORE

    def get_summary_by_ticker(self, ticker: str) -> Optional[QuarterlyResultSummary]:
        """Fetch quarterly results summary for a ticker if available."""
        return self.store.get(ticker.upper())

    def get_all_summaries(self) -> List[QuarterlyResultSummary]:
        """Return all available quarterly result summaries."""
        return list(self.store.values())

