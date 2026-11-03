"""Demo announcement fixtures — synthetic corporate announcements.

ALL announcements in this module are SYNTHETIC examples created for
demonstration purposes. They do not represent actual corporate filings
and must be labelled as demo/fixture data in the UI.

In accordance with FINN trustworthiness standards:
Synthetic demo announcements without a genuine corresponding filing have
source_url=None, preventing broken placeholder URLs.
"""

from app.core.models import (
    Announcement,
    AnnouncementCategory,
    CATEGORY_BASE_SCORE,
    CATEGORY_DEFAULT_PRIORITY,
    Priority,
)


def _make(
    *,
    id: str,
    ticker: str,
    company_name: str,
    category: AnnouncementCategory,
    title: str,
    published_at: str,
    summary: str,
    source_url: str | None = None,
    priority_reason: str = "",
    event_details: dict[str, str] | None = None,
) -> Announcement:
    """Create an announcement with auto-computed priority from category."""
    priority = CATEGORY_DEFAULT_PRIORITY.get(category, Priority.LOW)
    score = CATEGORY_BASE_SCORE.get(category, 10.0)
    return Announcement(
        id=id,
        ticker=ticker,
        company_name=company_name,
        category=category,
        title=title,
        published_at=published_at,
        source_url=source_url,
        priority=priority,
        priority_score=score,
        priority_reason=priority_reason or f"Category: {category.value}",
        summary=summary,
        is_fixture=True,
        event_details=event_details or {},
    )


# ── Fixture announcements ────────────────────────────────────────────────
# 10 announcements spanning 10 distinct categories, all clearly synthetic.
# Dates are calibrated to Jan 25 – Feb 5, 2025 so 24h, 3d, and 7d filters have realistic distributions.
# All synthetic fixture announcements have source_url=None to prevent broken placeholder links.

ANNOUNCEMENTS: list[Announcement] = [
    # 1. RELIANCE — results (high) [Feb 5 — in 24h window]
    _make(
        id="ann-001",
        ticker="RELIANCE",
        company_name="Reliance Industries Limited",
        category=AnnouncementCategory.RESULTS,
        title="[DEMO] Reliance Industries Q3 FY2025 Results — Revenue Up 12% YoY",
        published_at="2025-02-05",
        summary=(
            "Reliance Industries reported consolidated revenue of ₹2,43,865 Cr "
            "for Q3 FY2025, up 12% year-on-year. EBITDA rose 8% to ₹43,250 Cr. "
            "PAT stood at ₹18,540 Cr. [SYNTHETIC — not actual results]"
        ),
        source_url=None,
        priority_reason="Quarterly results — material financial disclosure",
    ),
    # 2. TATAMOTORS — m_and_a (high) [Feb 5 — in 24h window]
    _make(
        id="ann-004",
        event_details={"parties": "Tata Motors and an unnamed European battery technology firm (synthetic)", "deal_size": "₹7,500 Cr planned investment over 3 years; transaction consideration not disclosed", "rationale": "Manufacture EV battery packs in Gujarat", "approvals": "Not disclosed"},
        ticker="TATAMOTORS",
        company_name="Tata Motors Limited",
        category=AnnouncementCategory.M_AND_A,
        title="[DEMO] Tata Motors Announces JV for EV Battery Manufacturing",
        published_at="2025-02-05",
        summary=(
            "Tata Motors entered a 51:49 joint venture with a European battery "
            "technology firm to manufacture EV battery packs in Gujarat. "
            "Estimated investment: ₹7,500 Cr over 3 years. "
            "[SYNTHETIC — not an actual JV announcement]"
        ),
        source_url=None,
        priority_reason="M&A / joint venture — material strategic transaction",
    ),
    # 3. HDFCBANK — dividend (medium) [Feb 4 — in 24h window]
    _make(
        id="ann-002",
        ticker="HDFCBANK",
        company_name="HDFC Bank Limited",
        category=AnnouncementCategory.DIVIDEND,
        title="[DEMO] HDFC Bank Declares Final Dividend of ₹18 Per Share",
        published_at="2025-02-04",
        summary=(
            "HDFC Bank Board approved a final dividend of ₹18 per share for "
            "FY 2024-25, subject to shareholder approval at the AGM. "
            "[SYNTHETIC — not an actual declaration]"
        ),
        source_url=None,
        priority_reason="Dividend declaration — direct shareholder impact",
    ),
    # 4. INFY — results (high) [Feb 4 — in 24h window]
    _make(
        id="ann-005",
        ticker="INFY",
        company_name="Infosys Limited",
        category=AnnouncementCategory.RESULTS,
        title="[DEMO] Infosys Q3 FY2025 Results — Margins Improve 40 bps",
        published_at="2025-02-04",
        summary=(
            "Infosys reported Q3 FY2025 revenue of ₹41,764 Cr (up 6.1% YoY). "
            "Operating margin at 21.3%, improving 40 bps sequentially. "
            "Guidance retained at 4-6% CC revenue growth for FY2025. "
            "[SYNTHETIC — not actual results]"
        ),
        source_url=None,
        priority_reason="Quarterly results — material financial disclosure",
    ),
    # 5. SBIN — agm_egm (low / routine) [Feb 5 — in 24h window]
    _make(
        id="ann-010",
        ticker="SBIN",
        company_name="State Bank of India",
        category=AnnouncementCategory.AGM_EGM,
        title="[DEMO] SBI Notice of Annual General Meeting",
        published_at="2025-02-05",
        summary=(
            "State Bank of India issued notice for its Annual General Meeting "
            "to be held on March 15, 2025. Agenda includes adoption of "
            "accounts and appointment of auditors. "
            "[SYNTHETIC — not an actual AGM notice]"
        ),
        source_url=None,
        priority_reason="Routine AGM notice — standard compliance filing",
    ),
    # 6. ITC — bonus_split (medium) [Feb 3 — in 3d window]
    _make(
        id="ann-009",
        ticker="ITC",
        company_name="ITC Limited",
        category=AnnouncementCategory.BONUS_SPLIT,
        title="[DEMO] ITC Board Recommends Bonus Issue in Ratio 1:2",
        published_at="2025-02-03",
        summary=(
            "ITC Limited's Board recommended a bonus issue of equity shares "
            "in the ratio of 1:2 (one bonus share for every two held), "
            "subject to shareholder approval. "
            "[SYNTHETIC — not an actual bonus issue]"
        ),
        source_url=None,
        priority_reason="Bonus issue — share capital restructuring",
    ),
    # 7. LT — capex (medium) [Feb 2 — in 3d window]
    _make(
        id="ann-008",
        ticker="LT",
        company_name="Larsen & Toubro",
        category=AnnouncementCategory.CAPEX,
        title="[DEMO] L&T Announces ₹5,200 Cr Green Hydrogen Plant in Rajasthan",
        published_at="2025-02-02",
        summary=(
            "Larsen & Toubro announced a ₹5,200 Cr investment in a green "
            "hydrogen production facility in Rajasthan, expected to be "
            "operational by H2 FY2027. "
            "[SYNTHETIC — not an actual capex announcement]"
        ),
        source_url=None,
        priority_reason="Capital expenditure — significant capacity investment",
    ),
    # 8. ICICIBANK — fund_raise (high) [Jan 31 — in 7d window]
    _make(
        id="ann-006",
        ticker="ICICIBANK",
        company_name="ICICI Bank Limited",
        category=AnnouncementCategory.FUND_RAISE,
        title="[DEMO] ICICI Bank Board Approves QIP of ₹10,000 Cr",
        published_at="2025-01-31",
        summary=(
            "ICICI Bank's Board of Directors approved a Qualified Institutional "
            "Placement (QIP) to raise up to ₹10,000 Cr to strengthen the "
            "bank's capital adequacy ratio. [SYNTHETIC — not an actual QIP]"
        ),
        source_url=None,
        priority_reason="Fund raise — material capital structure change",
    ),
    # 9. SUNPHARMA — credit_rating (high) [Jan 30 — in 7d window]
    _make(
        id="ann-007",
        ticker="SUNPHARMA",
        company_name="Sun Pharmaceutical Industries",
        category=AnnouncementCategory.CREDIT_RATING,
        title="[DEMO] Sun Pharma Long-Term Rating Upgraded to AA+",
        published_at="2025-01-30",
        summary=(
            "CRISIL upgraded Sun Pharmaceutical Industries' long-term credit "
            "rating to AA+ from AA, citing improved cash flows and reduced "
            "debt levels. Outlook stable. "
            "[SYNTHETIC — not an actual rating action]"
        ),
        source_url=None,
        priority_reason="Credit rating upgrade — improved creditworthiness signal",
    ),
    # 10. TCS — management_change (high) [Jan 25 — in all window]
    _make(
        id="ann-003",
        event_details={"role": "Chief Technology Officer"},
        ticker="TCS",
        company_name="Tata Consultancy Services",
        category=AnnouncementCategory.MANAGEMENT_CHANGE,
        title="[DEMO] TCS Appoints New Chief Technology Officer",
        published_at="2025-01-25",
        summary=(
            "Tata Consultancy Services announced the appointment of a new CTO "
            "to lead its AI and cloud transformation strategy. The appointee "
            "brings 25 years of enterprise technology experience. "
            "[SYNTHETIC — not an actual appointment]"
        ),
        source_url=None,
        priority_reason="Senior management change — strategic leadership impact",
    ),
]


# ── Real (verified) announcements ─────────────────────────────────────────
# These are backed by genuine, reviewed primary-source documents stored in
# data/filings/. They are NOT synthetic and must not be mixed with demo fixtures
# in real-data mode (DEMO_MODE=false).
#
# All figures below are extracted verbatim from the Infosys Q3 FY2025 IFRS INR
# Press Release (document doc-2ae36f62af8bd4862f70629b, published 2025-01-16).
# EBITDA is NOT stated in the source document; operating profit is reported
# instead and is not presented as EBITDA.

REAL_ANNOUNCEMENTS: list[Announcement] = [
    Announcement(
        id="evt-infy-q3fy2025-results",
        ticker="INFY",
        company_name="Infosys Limited",
        category=AnnouncementCategory.RESULTS,
        title="Infosys Limited — Q3 FY2025 IFRS Results Press Release",
        published_at="2025-01-16",
        source_url=(
            "https://www.infosys.com/investors/reports-filings/"
            "quarterly-results/2024-2025/q3/documents/"
            "ifrs-inr-press-release.pdf"
        ),
        source_document_id="doc-2ae36f62af8bd4862f70629b",
        verification_note=(
            "SHA-256 31f57c686486f19e78e60061e65fe7eef005daefffbc87f82e7adb093bc3d048 "
            "matches data/filings/manifest.json. Document verified as genuine "
            "Infosys Limited Q3 FY2025 IFRS INR Press Release."
        ),
        priority=Priority.HIGH,
        priority_score=90.0,
        priority_reason=(
            "Quarterly results — material financial disclosure. Revenue "
            "₹41,764 crore (+7.6% YoY), PAT ₹6,806 crore (+11.4% YoY EPS)."
        ),
        summary=(
            "Infosys reported Q3 FY2025 revenues of ₹41,764 crore, growth of "
            "7.6% year on year. Operating margin was 21.3%, up 0.2% QoQ and "
            "0.8% YoY. PAT was ₹6,806 crore. Basic EPS ₹16.43, up 11.4% YoY. "
            "Free cash flow was ₹10,647 crore, up 91.9% YoY."
        ),
        event_details={
            "revenues_current": "₹41,764 crore",
            "revenues_yoy_prior": "₹38,821 crore",
            "revenues_yoy_growth": "+7.6%",
            "operating_profit_current": "₹8,912 crore",
            "operating_profit_yoy_prior": "₹7,961 crore",
            "operating_margin_current": "21.3%",
            "operating_margin_qoq_change": "+0.2%",
            "operating_margin_yoy_change": "+0.8%",
            "pbt_current": "₹9,670 crore",
            "pbt_yoy_prior": "₹8,619 crore",
            "pat_current": "₹6,806 crore",
            "pat_yoy_prior": "₹6,106 crore",
            "basic_eps_current": "₹16.43",
            "basic_eps_yoy_prior": "₹14.76",
            "basic_eps_yoy_growth": "+11.4%",
            "fcf_current": "₹10,647 crore",
            "fcf_yoy_prior": "₹5,546 crore",
            "fcf_yoy_growth": "+91.9%",
            "period": "Quarter ended December 31, 2024 (Q3 FY2025)",
            "basis": "consolidated, IFRS–INR",
            "unit": "₹ Cr",
            "ebitda": "Not stated in source document — operating profit reported instead",
        },
        is_fixture=False,
    ),
]
