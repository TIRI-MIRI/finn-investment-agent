"""Document processing and evidence extraction service.

Parses primary source documents (HTML and PDF), extracts clean text passages,
preserves page and section references, and generates stable deterministic evidence IDs.
"""

from __future__ import annotations

import hashlib
import io
import re
from typing import List, Optional, Set

from bs4 import BeautifulSoup
import pypdf

from app.core.models import RetrievedDocument, SourceEvidence


class DocumentProcessingError(Exception):
    """Raised when an unrecoverable document parsing error occurs."""


class DocumentProcessor:
    """Processes retrieved primary documents into granular, traceable SourceEvidence records."""

    def __init__(self, min_passage_length: int = 40, max_passage_length: int = 800):
        self.min_passage_length = min_passage_length
        self.max_passage_length = max_passage_length

    # ── Entrypoint ────────────────────────────────────────────────────────

    def process_document(self, doc: RetrievedDocument) -> List[SourceEvidence]:
        """Process a RetrievedDocument into a list of deduplicated SourceEvidence passages.

        Handles HTML and PDF content types. Corrupted or unparseable documents return an empty list
        without crashing the caller.
        """
        if doc.status != "success":
            return []

        if not doc.raw_bytes and not doc.raw_text:
            return []

        raw_bytes = doc.raw_bytes or (doc.raw_text.encode("utf-8") if doc.raw_text else b"")
        content_type = (doc.content_type or "").lower()

        if "pdf" in content_type and doc.raw_bytes and doc.raw_bytes.startswith(b"%PDF"):
            return self.process_pdf(doc.raw_bytes, doc)
        elif "html" in content_type or "xml" in content_type or (doc.raw_text and "<" in doc.raw_text):
            text = doc.raw_text or raw_bytes.decode("utf-8", errors="replace")
            return self.process_html(text, doc)
        elif "pdf" in content_type and doc.raw_bytes:
            return self.process_pdf(doc.raw_bytes, doc)
        else:
            # Fallback text parsing
            text = doc.raw_text or raw_bytes.decode("utf-8", errors="replace")
            return self._chunk_plain_text(text, doc)

    # ── HTML Processing ───────────────────────────────────────────────────

    def process_html(self, html_content: str, doc: RetrievedDocument) -> List[SourceEvidence]:
        """Parse HTML, strip irrelevant markup, extract headings and paragraphs.

        For HTML, page_or_section preserves the active section heading (page number is None).
        """
        if not html_content or not html_content.strip():
            return []

        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as exc:
            # Malformed HTML fallback
            return self._chunk_plain_text(html_content, doc)

        # Strip non-content tags
        for unwanted in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
            unwanted.decompose()

        evidence_list: List[SourceEvidence] = []
        seen_passages: Set[str] = set()
        current_section = "Overview"

        # Walk through meaningful structural elements
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
            name = elem.name.lower()
            text = elem.get_text(separator=" ", strip=True)
            if not text:
                continue

            if name in ("h1", "h2", "h3", "h4"):
                current_section = text[:120].strip()
                continue

            # Skip very short fragments
            if len(text) < self.min_passage_length:
                continue

            # Split paragraph into chunks if overly long
            chunks = self._split_text_to_chunks(text)
            for chunk in chunks:
                norm_chunk = re.sub(r"\s+", " ", chunk).strip().lower()
                if norm_chunk in seen_passages:
                    continue
                seen_passages.add(norm_chunk)

                # Generate deterministic evidence ID
                ev_id = self.generate_evidence_id(
                    doc_url=doc.url,
                    period=doc.period or "",
                    page_or_section=current_section,
                    passage=chunk,
                )

                evidence_list.append(
                    SourceEvidence(
                        id=ev_id,
                        title=doc.title,
                        publisher=doc.publisher,
                        document_type=doc.document_type,
                        period=doc.period,
                        url=doc.url,
                        page_or_section=current_section,  # HTML preserves section name
                        excerpt=chunk,
                        retrieved_at=doc.retrieved_at,
                        is_primary=doc.is_primary,
                        is_fixture=doc.is_fixture,
                        verification_note=doc.verification_note,
                        document_id=doc.id,
                        ticker=doc.ticker,
                    )
                )

        return evidence_list

    # ── PDF Processing ────────────────────────────────────────────────────

    def process_pdf(self, pdf_bytes: bytes, doc: RetrievedDocument) -> List[SourceEvidence]:
        """Parse PDF byte stream using pypdf, extracting text per page and tracking page numbers."""
        if not pdf_bytes:
            return []

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception:
            # Corrupted PDF or invalid binary stream
            return []

        evidence_list: List[SourceEvidence] = []
        seen_passages: Set[str] = set()

        try:
            total_pages = len(reader.pages)
        except Exception:
            return []

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            section_ref = f"Page {page_num}"

            try:
                page = reader.pages[page_idx]
                page_text = page.extract_text() or ""
            except Exception:
                continue

            page_text = page_text.strip()
            if not page_text or len(page_text) < self.min_passage_length:
                continue

            chunks = self._split_text_to_chunks(page_text)
            for chunk in chunks:
                norm_chunk = re.sub(r"\s+", " ", chunk).strip().lower()
                if norm_chunk in seen_passages:
                    continue
                seen_passages.add(norm_chunk)

                ev_id = self.generate_evidence_id(
                    doc_url=doc.url,
                    period=doc.period or "",
                    page_or_section=section_ref,
                    passage=chunk,
                )

                evidence_list.append(
                    SourceEvidence(
                        id=ev_id,
                        title=doc.title,
                        publisher=doc.publisher,
                        document_type=doc.document_type,
                        period=doc.period,
                        url=doc.url,
                        page_or_section=section_ref,  # PDF preserves 1-indexed page number
                        excerpt=chunk,
                        retrieved_at=doc.retrieved_at,
                        is_primary=doc.is_primary,
                        is_fixture=doc.is_fixture,
                        verification_note=doc.verification_note,
                        document_id=doc.id,
                        ticker=doc.ticker,
                    )
                )

        return evidence_list

    # ── Helper Utilities ──────────────────────────────────────────────────

    def _chunk_plain_text(self, text: str, doc: RetrievedDocument) -> List[SourceEvidence]:
        """Fallback chunker for plain text files."""
        chunks = self._split_text_to_chunks(text)
        evidence_list: List[SourceEvidence] = []
        seen: Set[str] = set()

        for chunk in chunks:
            norm = chunk.strip().lower()
            if norm in seen or len(chunk) < self.min_passage_length:
                continue
            seen.add(norm)

            ev_id = self.generate_evidence_id(doc.url, doc.period or "", "Section", chunk)
            evidence_list.append(
                SourceEvidence(
                    id=ev_id,
                    title=doc.title,
                    publisher=doc.publisher,
                    document_type=doc.document_type,
                    period=doc.period,
                    url=doc.url,
                    page_or_section="Document Body",
                    excerpt=chunk,
                    retrieved_at=doc.retrieved_at,
                    is_primary=doc.is_primary,
                    is_fixture=doc.is_fixture,
                    verification_note=doc.verification_note,
                    document_id=doc.id,
                    ticker=doc.ticker,
                )
            )
        return evidence_list

    def _split_text_to_chunks(self, text: str) -> List[str]:
        """Split text into sentences/paragraphs bounded by max_passage_length."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []

        for p in paragraphs:
            if len(p) <= self.max_passage_length:
                if len(p) >= self.min_passage_length:
                    chunks.append(p)
            else:
                # Split paragraph into sentence clusters
                sentences = re.split(r"(?<=[.!?])\s+", p)
                current_chunk: List[str] = []
                current_len = 0

                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if current_len + len(s) > self.max_passage_length and current_chunk:
                        chunk_str = " ".join(current_chunk)
                        if len(chunk_str) >= self.min_passage_length:
                            chunks.append(chunk_str)
                        current_chunk = [s]
                        current_len = len(s)
                    else:
                        current_chunk.append(s)
                        current_len += len(s) + 1

                if current_chunk:
                    chunk_str = " ".join(current_chunk)
                    if len(chunk_str) >= self.min_passage_length:
                        chunks.append(chunk_str)

        return chunks

    @staticmethod
    def generate_evidence_id(doc_url: str, period: str, page_or_section: str, passage: str) -> str:
        """Generate a deterministic evidence ID based on stable document attributes and passage text.

        The same passage from the same URL and section always produces the exact same ID.
        Different reporting periods or different passages produce distinct IDs.
        """
        norm_passage = re.sub(r"\s+", " ", passage).strip().lower()
        key = f"{doc_url.strip().lower()}|{period.strip().lower()}|{page_or_section.strip().lower()}|{norm_passage}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
        return f"ev-{digest}"

