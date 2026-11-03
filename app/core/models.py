"""FINN data models — validated contracts for the prototype.

Defines Pydantic models and Python enums matching the data contracts in
BUILD_PLAN_FINN_VSCode.md (Phases 2, 4 & 5). All names use Python snake_case;
the build plan's TypeScript camelCase is mapped accordingly.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enumerations ──────────────────────────────────────────────────────────


class DataSourceType(str, Enum):
    """Types of primary source documents used for research evidence."""

    ANNUAL_REPORT = "annual_report"
    QUARTERLY_RESULTS = "quarterly_results"
    EARNINGS_CALL = "earnings_call"
    INVESTOR_PRESENTATION = "investor_presentation"
    EXCHANGE_FILING = "exchange_filing"
    OFFICIAL_RELEASE = "official_release"


class AnnouncementCategory(str, Enum):
    """Normalised categories for corporate announcements.

    Reference: BUILD_PLAN section 4A — announcement normalisation.
    The full taxonomy from the plan is represented here:
      results, M&A, fund_raise, management_change, litigation,
      insider_trading, earnings_call, investor_meetings, credit_rating,
      dividend, bonus_split, capex, press_release, postal_ballot,
      agm_egm, pledging, unclassified.
    """

    RESULTS = "results"
    M_AND_A = "m_and_a"
    FUND_RAISE = "fund_raise"
    MANAGEMENT_CHANGE = "management_change"
    LITIGATION = "litigation"
    INSIDER_TRADING = "insider_trading"
    EARNINGS_CALL = "earnings_call"
    INVESTOR_MEETINGS = "investor_meetings"
    CREDIT_RATING = "credit_rating"
    DIVIDEND = "dividend"
    BONUS_SPLIT = "bonus_split"
    CAPEX = "capex"
    PRESS_RELEASE = "press_release"
    POSTAL_BALLOT = "postal_ballot"
    AGM_EGM = "agm_egm"
    PLEDGING = "pledging"
    UNCLASSIFIED = "unclassified"


class Priority(str, Enum):
    """Announcement priority level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceMode(str, Enum):
    """Whether data comes from live sources or demo fixtures."""

    LIVE = "live"
    DEMO = "demo"


class Confidence(str, Enum):
    """Confidence level for research claims."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnomalySeverity(str, Enum):
    """Severity of a detected price or volume anomaly."""

    HIGH = "high"
    MEDIUM = "medium"
    NONE = "none"


class DigestWindow(str, Enum):
    """Supported time windows for the announcement digest."""

    WINDOW_24H = "24h"
    WINDOW_3D = "3d"
    WINDOW_7D = "7d"
    ALL = "all"


# ── Priority defaults ────────────────────────────────────────────────────
# Product choice from BUILD_PLAN section 2 — configurable, not mandated.

CATEGORY_DEFAULT_PRIORITY: Dict[AnnouncementCategory, Priority] = {
    # High: results, M&A, fund_raise, management_change, litigation, credit_rating
    AnnouncementCategory.RESULTS: Priority.HIGH,
    AnnouncementCategory.M_AND_A: Priority.HIGH,
    AnnouncementCategory.FUND_RAISE: Priority.HIGH,
    AnnouncementCategory.MANAGEMENT_CHANGE: Priority.HIGH,
    AnnouncementCategory.LITIGATION: Priority.HIGH,
    AnnouncementCategory.CREDIT_RATING: Priority.HIGH,
    # Medium: capex, dividend, pledging, insider_trading, bonus_split,
    #         investor_meetings, earnings_call
    AnnouncementCategory.CAPEX: Priority.MEDIUM,
    AnnouncementCategory.DIVIDEND: Priority.MEDIUM,
    AnnouncementCategory.PLEDGING: Priority.MEDIUM,
    AnnouncementCategory.INSIDER_TRADING: Priority.MEDIUM,
    AnnouncementCategory.BONUS_SPLIT: Priority.MEDIUM,
    AnnouncementCategory.INVESTOR_MEETINGS: Priority.MEDIUM,
    AnnouncementCategory.EARNINGS_CALL: Priority.MEDIUM,
    # Low / routine
    AnnouncementCategory.PRESS_RELEASE: Priority.LOW,
    AnnouncementCategory.POSTAL_BALLOT: Priority.LOW,
    AnnouncementCategory.AGM_EGM: Priority.LOW,
    AnnouncementCategory.UNCLASSIFIED: Priority.LOW,
}

CATEGORY_BASE_SCORE: Dict[AnnouncementCategory, float] = {
    AnnouncementCategory.RESULTS: 90.0,
    AnnouncementCategory.M_AND_A: 95.0,
    AnnouncementCategory.FUND_RAISE: 85.0,
    AnnouncementCategory.MANAGEMENT_CHANGE: 80.0,
    AnnouncementCategory.LITIGATION: 88.0,
    AnnouncementCategory.CREDIT_RATING: 82.0,
    AnnouncementCategory.CAPEX: 55.0,
    AnnouncementCategory.DIVIDEND: 60.0,
    AnnouncementCategory.PLEDGING: 50.0,
    AnnouncementCategory.INSIDER_TRADING: 65.0,
    AnnouncementCategory.BONUS_SPLIT: 58.0,
    AnnouncementCategory.INVESTOR_MEETINGS: 45.0,
    AnnouncementCategory.EARNINGS_CALL: 62.0,
    AnnouncementCategory.PRESS_RELEASE: 25.0,
    AnnouncementCategory.POSTAL_BALLOT: 15.0,
    AnnouncementCategory.AGM_EGM: 20.0,
    AnnouncementCategory.UNCLASSIFIED: 10.0,
}


# ── Core data models ─────────────────────────────────────────────────────


class Company(BaseModel):
    """An NSE/BSE-listed company in the portfolio or research universe."""

    ticker: str
    name: str
    exchange: str = "NSE"
    sector: str = ""
    industry: str = ""


class FilingProvenance(BaseModel):
    """Explicit review of the exact URL, title, date and supporting content.

    A successful HTTP fetch or an official hostname alone is not verification.
    """

    verification_note: Optional[str] = None

    @property
    def has_verified_filing(self) -> bool:
        from urllib.parse import urlsplit
        url = getattr(self, "source_url", None) or getattr(self, "url", None) or ""
        parsed = urlsplit(url)
        return bool(
            self.verification_note and self.verification_note.strip()
            and not getattr(self, "is_fixture", True)
            and getattr(self, "is_primary", True)
            and parsed.scheme == "https" and parsed.hostname
            and not parsed.username and not parsed.password
        )


class SourceEvidence(FilingProvenance):
    """A single piece of evidence from a primary source document.

    Used in the Pull (research) workflow. Every material claim must
    reference at least one evidence item or be marked unsupported.
    """

    id: str = Field(default_factory=lambda: f"ev-{uuid4().hex[:8]}")
    title: str
    publisher: str
    document_type: str
    period: Optional[str] = None
    url: Optional[str] = None
    page_or_section: Optional[str] = None
    excerpt: Optional[str] = None
    retrieved_at: Optional[str] = None
    is_primary: bool = True
    is_fixture: bool = False
    document_id: Optional[str] = None
    ticker: Optional[str] = None


class Claim(BaseModel):
    """A single factual claim within a research section."""

    text: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    claim_type: str = "reported_fact"  # reported_fact, management_statement, calculation, interpretation


class ResearchSection(BaseModel):
    """One section of a company research brief."""

    id: str
    title: str
    summary: str
    claims: List[Claim] = Field(default_factory=list)


class ResearchCoverage(BaseModel):
    """Documents-found summary for a research brief."""

    documents_found: int = 0
    periods: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CompanyResearch(BaseModel):
    """Full research output for a company — the Pull workflow result."""

    id: str = Field(default_factory=lambda: f"res-{uuid4().hex[:8]}")
    ticker: str
    company_name: str
    generated_at: str
    source_mode: SourceMode = SourceMode.DEMO
    coverage: ResearchCoverage = Field(default_factory=ResearchCoverage)
    sections: List[ResearchSection] = Field(default_factory=list)
    evidence: List[SourceEvidence] = Field(default_factory=list)


class Announcement(FilingProvenance):
    """A normalised corporate announcement / filing.

    Maps to the Announcement contract in BUILD_PLAN Phase 2.
    """

    id: str
    ticker: str
    company_name: str
    category: AnnouncementCategory
    title: str
    published_at: str  # ISO date string YYYY-MM-DD
    source_url: Optional[str] = None
    source_document_id: Optional[str] = None
    event_details: Dict[str, str] = Field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    priority_score: float = 0.0
    priority_reason: str = ""
    summary: Optional[str] = None
    is_fixture: bool = True


class PriceBar(BaseModel):
    """End-of-day price and volume for one ticker on one date."""

    ticker: str
    date: str  # ISO date string YYYY-MM-DD
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float
    volume: int


# ── Phase 4 Push Workflow Models ─────────────────────────────────────────


class PriceAnomalyAlert(BaseModel):
    """A detected end-of-day price or volume anomaly alert.

    Signals unusual price moves or volume spikes against historical baseline.
    Monitoring signal only, not a forecast or recommendation.
    """

    ticker: str
    company_name: str
    date: str
    close: float
    previous_close: float
    price_change_pct: float
    volume: int
    baseline_volume_mean: float
    volume_ratio: float
    is_price_anomaly: bool
    is_volume_anomaly: bool
    severity: AnomalySeverity = AnomalySeverity.NONE
    explanation: str
    is_fixture: bool = True
    baseline_sessions: int = 20
    price_threshold_pct: float = 3.0
    volume_multiple_threshold: float = 2.0
    trigger_mode: str = "OR"
    triggered: bool = False


class QuarterlyMetric(BaseModel):
    """A single quarterly financial metric (e.g. Revenue, EBITDA, PBT, PAT).

    Supports QoQ (previous quarter) and YoY (same quarter last year) comparisons.
    Missing figures are represented as None ("Not available in source").
    """

    metric_name: str
    current: Optional[float] = None
    qoq_prev: Optional[float] = None
    yoy_prev: Optional[float] = None
    unit: str = "₹ Cr"
    basis: str = "consolidated"

    @property
    def qoq_growth_pct(self) -> Optional[float]:
        if self.current is not None and self.qoq_prev and self.qoq_prev > 0:
            return round(((self.current - self.qoq_prev) / self.qoq_prev) * 100, 2)
        return None

    @property
    def yoy_growth_pct(self) -> Optional[float]:
        if self.current is not None and self.yoy_prev and self.yoy_prev > 0:
            return round(((self.current - self.yoy_prev) / self.yoy_prev) * 100, 2)
        return None


class QuarterlyResultSummary(BaseModel):
    """Extracted quarterly results summary for a company filing.

    Covers Revenue, EBITDA, PBT, and PAT preserving units and reporting basis.
    """

    ticker: str
    company_name: str
    period: str
    previous_period: Optional[str] = None
    previous_year_period: Optional[str] = None
    filing_id: Optional[str] = None
    unit: str = "₹ Cr"
    basis: str = "consolidated"
    revenue: Optional[QuarterlyMetric] = None
    ebitda: Optional[QuarterlyMetric] = None
    pbt: Optional[QuarterlyMetric] = None
    pat: Optional[QuarterlyMetric] = None
    is_fixture: bool = True


class DigestResponse(BaseModel):
    """API response model for the prioritized announcement digest."""

    window: str
    reference_date: str
    total_count: int
    material_count: int
    routine_count: int
    material_announcements: List[Announcement]
    routine_announcements: List[Announcement]
    is_fixture: bool = True


# ── Phase 5 Pull Research Models ─────────────────────────────────────────


class RetrievedDocument(FilingProvenance):
    """A primary source document retrieved via live HTTP or loaded from fixtures."""

    id: str = Field(default_factory=lambda: f"doc-{uuid4().hex[:8]}")
    ticker: str
    title: str
    publisher: str
    url: str
    document_type: str = "annual_report"
    period: Optional[str] = None
    published_date: Optional[str] = None
    content_type: str = "text/html"
    retrieved_at: str = ""
    status: str = "success"  # success, failed, unsupported_type, oversized, timeout
    error_message: Optional[str] = None
    raw_text: Optional[str] = None
    raw_bytes: Optional[bytes] = None
    page_count: Optional[int] = None
    is_primary: bool = True
    is_fixture: bool = False
