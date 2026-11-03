"""Primary source document filings and genuine references for research universe companies.

Provides official Q3 FY2024-25 investor relations and exchange filings for the 5 research companies:
- RELIANCE (Reliance Industries Limited)
- INFY (Infosys Limited)
- TCS (Tata Consultancy Services)
- HDFCBANK (HDFC Bank Limited)
- TATAMOTORS (Tata Motors Limited)

Each record contains genuine official publication metadata, verifiable direct URLs,
and bounded, paraphrased summaries checked on 2026-11-03. These are offline
curated summaries, not verbatim extracts or a live retrieval. See FILING_AUDIT.md.
"""

from typing import Dict, List

from app.core.models import DataSourceType, RetrievedDocument

# ── Primary Document Filings for Research Companies ──────────────────────

RESEARCH_FIXTURE_DOCS: Dict[str, List[RetrievedDocument]] = {
    # 1. RELIANCE (Energy, Retail, Digital Services)
    "RELIANCE": [
        RetrievedDocument(
            id="doc-ril-q3-2025",
            ticker="RELIANCE",
            title="Consolidated results for quarter ended 31st December, 2024",
            publisher="Reliance Industries Limited",
            url="https://www.ril.com/sites/default/files/2025-01/16012025-Media_Release-RIL_Q3_FY2024-25Financial_and_Operational_Performance.pdf",
            document_type=DataSourceType.QUARTERLY_RESULTS.value,
            period="Q3 FY2025",
            published_date="2025-01-16",
            content_type="text/html",
            status="success",
            is_primary=True,
            is_fixture=False,
            verification_note="Reviewed 2026-11-03: 2025-01-16; PDF page 1, consolidated financial highlights. PAT includes the share of profit/loss of associates and joint ventures.",
            raw_text="""<h1>Financial Highlights (PDF page 1)</h1><p>Consolidated gross revenue for Q3 FY25 was ₹267,186 crore, growing 7.7% year on year.</p><p>Consolidated EBITDA reached ₹48,003 crore, an increase of 7.8% year on year.</p><p>Profit after tax including the share of profit/loss of associates and joint ventures was ₹21,930 crore, up 11.7% year on year.</p><p>Consolidated profit before tax was ₹28,643 crore for the quarter.</p>""",
        ),
    ],

    # 2. INFY (IT Services)
    "INFY": [
        RetrievedDocument(
            id="doc-infy-q3-2025",
            ticker="INFY",
            title="Fact Sheet — Consolidated Financial Data — Third Quarter, Fiscal 2025",
            publisher="Infosys Limited",
            url="https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q3/documents/fact-sheet.pdf",
            document_type=DataSourceType.QUARTERLY_RESULTS.value,
            period="Q3 FY2025",
            published_date="2025-01-16",
            content_type="text/html",
            status="success",
            is_primary=True,
            is_fixture=False,
            verification_note="Reviewed 2026-11-03: 2025-01-16 release date confirmed on official Q3 results index; PDF pages 1 and 4, IFRS financial data.",
            raw_text="""<h1>Financial Highlights (PDF pages 1 and 4)</h1><p>Q3 FY25 consolidated IFRS revenue was ₹41,764 crore, up 7.6% year on year.</p><p>Operating margin was 21.3%, compared with 21.1% in the previous quarter and 20.5% a year earlier.</p><p>Net profit after minority interest was ₹6,806 crore, up 11.4% year on year.</p><p>Large deal total contract value was $2.5 billion and free cash flow was $1.3 billion.</p>""",
        ),
    ],

    # 3. TCS (IT Services)
    "TCS": [
        RetrievedDocument(
            id="doc-tcs-q3-2025",
            ticker="TCS",
            title="TCS Financial Results — Quarter III Ended FY 2024-25",
            publisher="Tata Consultancy Services",
            url="https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q3/Presentations/Q3%202024-25%20Fact%20Sheet.pdf",
            document_type=DataSourceType.QUARTERLY_RESULTS.value,
            period="Q3 FY2025",
            published_date="2025-01-09",
            content_type="text/html",
            status="success",
            is_primary=True,
            is_fixture=False,
            verification_note="Reviewed 2026-11-03: 2025-01-09 on PDF cover; page 20 consolidated Ind AS income statement.",
            raw_text="""<h1>Financial Highlights (PDF page 20, Ind AS)</h1><p>Consolidated Q3 FY25 revenue was ₹63,973 crore, compared with ₹60,583 crore a year earlier.</p><p>Profit before taxes was ₹16,666 crore for Q3 FY25.</p><p>Profit after taxes before non-controlling interests was ₹12,444 crore.</p><p>Net profit after non-controlling interests was ₹12,380 crore, with earnings per share of ₹34.21.</p>""",
        ),
    ],

    # 4. HDFCBANK (Private Banking)
    "HDFCBANK": [
        RetrievedDocument(
            id="doc-hdfc-q3-2025",
            ticker="HDFCBANK",
            title="HDFC Bank Limited — Financial Results (Indian GAAP) for the Quarter and Nine Months Ended December 31, 2024",
            publisher="HDFC Bank Limited",
            url="https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/press-release/2025/q1-jan-mar/january/press-release-december-2024.pdf",
            document_type=DataSourceType.QUARTERLY_RESULTS.value,
            period="Q3 FY2025",
            published_date="2025-01-22",
            content_type="text/html",
            status="success",
            is_primary=True,
            is_fixture=False,
            verification_note="Reviewed 2026-11-03: 2025-01-22 board approval on PDF page 1; consolidated results distinguished from standalone results.",
            raw_text="""<h1>Financial Highlights (PDF page 1)</h1><p>Consolidated net revenue for the quarter ended December 31, 2024 was ₹652.8 billion.</p><p>Consolidated profit after tax for the quarter was ₹176.6 billion.</p><p>Consolidated profit after tax for the nine months ended December 31, 2024 was ₹519.6 billion.</p><p>Standalone net revenue was ₹421.1 billion, growing 6.3% year on year.</p>""",
        ),
    ],

    # 5. TATAMOTORS (Automotive & Commercial Vehicles)
    "TATAMOTORS": [
        RetrievedDocument(
            id="doc-tatamotors-q3-2025",
            ticker="TATAMOTORS",
            title="Tata Motors Group Results Q3 FY25",
            publisher="Tata Motors Limited",
            url="https://www.tatamotors.com/wp-content/uploads/2025/01/Q3FY25-Results-Press-Release.pdf",
            document_type=DataSourceType.QUARTERLY_RESULTS.value,
            period="Q3 FY2025",
            published_date="2025-01-29",
            content_type="text/html",
            status="success",
            is_primary=True,
            is_fixture=False,
            verification_note="Reviewed 2026-11-03: 2025-01-29 on PDF page 1; consolidated financial highlights. Values retain source rounding.",
            raw_text="""<h1>Financial Highlights (PDF page 1)</h1><p>Q3 FY25 consolidated revenue was ₹113.6K Cr, up 2.7% year on year.</p><p>Consolidated EBITDA was ₹15,500 crore with a margin of 13.7%, down 60 basis points year on year.</p><p>Consolidated EBIT was ₹10.0K Cr with a margin of 8.9%, up 60 basis points.</p><p>Profit before tax excluding exceptional items was ₹7.7K Cr; net profit was ₹5.6K Cr.</p>""",
        ),
    ],
}
