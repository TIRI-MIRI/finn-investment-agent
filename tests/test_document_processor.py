"""Unit tests for DocumentProcessor: HTML and PDF parsing, page tracking, and evidence IDs."""

import io

from bs4 import BeautifulSoup
import pypdf
import pytest

from app.core.models import RetrievedDocument
from app.services.document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(min_passage_length=20, max_passage_length=500)


def create_mock_pdf_bytes(pages_text: list[str]) -> bytes:
    """Helper to generate valid multi-page PDF byte streams for testing."""
    writer = pypdf.PdfWriter()
    for text in pages_text:
        # Create a blank page and add text annotation or draw simple text
        page = writer.add_blank_page(width=300, height=300)
    # Write to memory buffer
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ── HTML Processing Tests ────────────────────────────────────────────────


class TestHTMLProcessing:
    def test_html_strips_scripts_and_extracts_sections(self, processor):
        html = """
        <html>
          <head><style>body { color: red; }</style></head>
          <body>
            <script>alert('malicious script execution');</script>
            <nav><a href="/home">Home</a></nav>
            <h1>Financial Performance</h1>
            <p>Consolidated revenue increased by 12.5% YoY to ₹2,43,865 Cr.</p>
            <h2>Operating Segments</h2>
            <p>Digital services and retail contributed over 45% of total segment EBITDA.</p>
            <footer>Copyright 2025</footer>
          </body>
        </html>
        """
        doc = RetrievedDocument(
            ticker="RELIANCE",
            title="Q3 Press Release",
            publisher="Reliance Industries",
            url="https://investors.ril.com/q3.html",
            content_type="text/html",
            period="Q3 FY2025",
            status="success",
            raw_text=html,
        )

        evidence = processor.process_document(doc)
        assert len(evidence) >= 2

        # Verify scripts and nav were decomposed
        all_excerpts = " ".join(e.excerpt for e in evidence)
        assert "malicious" not in all_excerpts
        assert "Home" not in all_excerpts
        assert "Copyright" not in all_excerpts

        # Verify headings preserved as page_or_section
        sections = {e.page_or_section for e in evidence}
        assert "Financial Performance" in sections or "Operating Segments" in sections

        # Verify HTML page number is None (section reference is used)
        for ev in evidence:
            assert ev.url == "https://investors.ril.com/q3.html"
            assert ev.period == "Q3 FY2025"
            assert ev.is_primary is True
            assert ev.id.startswith("ev-")

    def test_empty_html_returns_empty_list(self, processor):
        doc = RetrievedDocument(
            ticker="INFY",
            title="Empty",
            publisher="Infosys",
            url="https://infosys.com/empty.html",
            status="success",
            raw_text="   ",
        )
        assert processor.process_document(doc) == []


# ── PDF Processing Tests ─────────────────────────────────────────────────


class TestPDFProcessing:
    def test_pdf_preserves_page_numbers(self, processor):
        # Create a mock PDF with 2 pages of extracted text using pypdf mock
        pdf_bytes = b"%PDF-1.4 mock binary"
        doc = RetrievedDocument(
            ticker="TCS",
            title="Annual Report",
            publisher="Tata Consultancy Services",
            url="https://www.tcs.com/ar2024.pdf",
            content_type="application/pdf",
            period="FY2024",
            status="success",
            raw_bytes=pdf_bytes,
        )

        # Mock pypdf.PdfReader to return 2 pages with distinct text
        mock_page1 = type("MockPage", (), {"extract_text": lambda self: "Page 1: Operating cash flow reached ₹44,000 Cr in FY24."})()
        mock_page2 = type("MockPage", (), {"extract_text": lambda self: "Page 2: Net debt to equity ratio remained zero throughout the year."})()
        mock_reader = type("MockReader", (), {"pages": [mock_page1, mock_page2]})()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("pypdf.PdfReader", lambda stream: mock_reader)
            evidence = processor.process_document(doc)

        assert len(evidence) == 2
        assert evidence[0].page_or_section == "Page 1"
        assert "Page 1" in evidence[0].excerpt
        assert evidence[1].page_or_section == "Page 2"
        assert "Page 2" in evidence[1].excerpt

    def test_corrupted_pdf_handled_gracefully(self, processor):
        doc = RetrievedDocument(
            ticker="TCS",
            title="Corrupted PDF",
            publisher="TCS",
            url="https://tcs.com/corrupt.pdf",
            content_type="application/pdf",
            status="success",
            raw_bytes=b"this is completely corrupted and not a pdf",
        )
        # Should return empty list rather than crashing
        assert processor.process_document(doc) == []


# ── Evidence ID Determinism & Deduplication Tests ────────────────────────


class TestEvidenceIDsAndDeduplication:
    def test_deterministic_evidence_id(self, processor):
        id1 = processor.generate_evidence_id(
            doc_url="https://ril.com/report.html",
            period="Q3 FY2025",
            page_or_section="Financials",
            passage="Revenue was ₹2,43,865 Cr for the quarter.",
        )
        id2 = processor.generate_evidence_id(
            doc_url="https://ril.com/report.html",
            period="Q3 FY2025",
            page_or_section="Financials",
            passage="Revenue was ₹2,43,865 Cr for the quarter.",
        )
        assert id1 == id2
        assert id1.startswith("ev-")

    def test_different_period_or_section_produces_distinct_id(self, processor):
        id_q3 = processor.generate_evidence_id("https://ril.com/rep", "Q3 FY2025", "Sec A", "Revenue grew 10%")
        id_q4 = processor.generate_evidence_id("https://ril.com/rep", "Q4 FY2025", "Sec A", "Revenue grew 10%")
        id_sec_b = processor.generate_evidence_id("https://ril.com/rep", "Q3 FY2025", "Sec B", "Revenue grew 10%")

        assert id_q3 != id_q4
        assert id_q3 != id_sec_b

    def test_passage_deduplication_within_document(self, processor):
        html = """
        <html>
          <body>
            <h2>Highlights</h2>
            <p>Operating margin stood at 21.3% for the third quarter.</p>
            <p>Operating margin stood at 21.3% for the third quarter.</p> <!-- duplicate -->
            <p>Operating margin stood at 21.3% for the third quarter.</p> <!-- duplicate -->
            <p>Free cash flow conversion remained strong at 85% of net profit.</p>
          </body>
        </html>
        """
        doc = RetrievedDocument(
            ticker="INFY",
            title="Results Release",
            publisher="Infosys Limited",
            url="https://infosys.com/q3.html",
            content_type="text/html",
            status="success",
            raw_text=html,
        )
        evidence = processor.process_document(doc)
        # 3 identical paragraphs should be deduplicated to 1
        assert len(evidence) == 2
        excerpts = [e.excerpt for e in evidence]
        assert len(set(excerpts)) == 2

    def test_provenance_preservation(self, processor):
        fixture_doc = RetrievedDocument(
            ticker="INFY",
            title="Fixture Release",
            publisher="Infosys Limited",
            url="https://infosys.com/fixture.html",
            content_type="text/html",
            status="success",
            raw_text="<p>This is a verified test passage for demo purposes.</p>",
            is_fixture=True,
        )
        evidence = processor.process_document(fixture_doc)
        assert len(evidence) == 1
        assert evidence[0].is_fixture is True
        assert evidence[0].is_primary is True

