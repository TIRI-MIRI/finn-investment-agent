"""Immutable original documents, content-bound reviews and traceable real events.

Downloading a document never marks its claims as verified. A separate review
must bind the bytes, metadata and exact supporting passages before publication.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from threading import RLock
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from app.core.models import AnnouncementCategory
from app.services.retrieval import ALLOWED_PRIMARY_DOMAINS, EXCHANGE_ALLOWED_DOMAINS, PrimarySourceRetriever


def fingerprint(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized(value: str) -> str:
    return " ".join(value.split())


class FilingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    publisher: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published_date: date
    document_type: str = "quarterly_results"
    period: str = Field(min_length=1)
    source_url: str


def official_url(url, ticker):
    parts = urlsplit(url)
    roots = ALLOWED_PRIMARY_DOMAINS.get(ticker, set()) | EXCHANGE_ALLOWED_DOMAINS
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError("An HTTPS official source URL without credentials is required")
    if not any(host == root or host.endswith("." + root) for root in roots):
        raise ValueError("Source hostname is not approved for this issuer")


class FilingArchive:
    MAX_BYTES = 10 * 1024 * 1024

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.lock = RLock()

    def manifest(self):
        path = self.root / "manifest.json"
        if not path.exists():
            return {"version": 1, "documents": {}, "attempts": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
                name = file.name
                json.dump(value, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(name, path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    @staticmethod
    def pages(data, media_type):
        if media_type == "application/pdf":
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("Encrypted documents are not supported")
            return [p.extract_text() or "" for p in reader.pages]
        soup = BeautifulSoup(data, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        return [soup.get_text(" ", strip=True)]

    def ingest_bytes(self, metadata: FilingMetadata, data: bytes, method="manual", final_url=None):
        official_url(metadata.source_url, metadata.ticker)
        official_url(final_url or metadata.source_url, metadata.ticker)
        if not data or len(data) > self.MAX_BYTES:
            raise ValueError("Document empty or exceeds 10 MB limit")
        if data.startswith(b"%PDF-"):
            media_type, extension = "application/pdf", "pdf"
        elif b"<html" in data[:2000].lower() or b"<!doctype html" in data[:2000].lower():
            media_type, extension = "text/html", "html"
        else:
            raise ValueError("Only genuine PDF or HTML documents are accepted")
        pages = self.pages(data, media_type)
        if not any(p.strip() for p in pages):
            raise ValueError("No extractable text; manual OCR/review is required")
        digest = fingerprint(data)
        doc_id = "doc-" + fingerprint((metadata.ticker + "|" + digest).encode())[:24]
        with self.lock:
            manifest = self.manifest()
            if doc_id in manifest["documents"]:
                existing = manifest["documents"][doc_id]
                if any(existing[k] != v for k, v in metadata.model_dump(mode="json").items()):
                    raise ValueError("Identical document has conflicting metadata; review instead of overwriting")
                return existing
            self.root.mkdir(parents=True, exist_ok=True)
            path = self.root / f"{doc_id}.{extension}"
            # Existing originals are never replaced, including after an interrupted import.
            if path.exists() and fingerprint(path.read_bytes()) != digest:
                raise ValueError("Original document checksum conflict")
            if not path.exists():
                path.write_bytes(data)
            record = {**metadata.model_dump(mode="json"), "id": doc_id, "sha256": digest,
                "filename": path.name, "content_type": media_type, "byte_count": len(data),
                "page_count": len(pages), "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "retrieval_method": method, "retrieval_status": "success", "final_url": final_url or metadata.source_url,
                "review_status": "pending", "review": None}
            manifest["documents"][doc_id] = record
            self._write_json(self.root / "manifest.json", manifest)
            return record

    def fetch(self, metadata, retriever=None):
        retriever = retriever or PrimarySourceRetriever(timeout=20)
        doc = retriever.retrieve_document(url=metadata.source_url, ticker=metadata.ticker,
            title=metadata.title, publisher=metadata.publisher, document_type=metadata.document_type, period=metadata.period)
        if doc.status != "success":
            with self.lock:
                manifest = self.manifest()
                manifest["attempts"].append({**metadata.model_dump(mode="json"), "status": doc.status,
                    "error": doc.error_message, "attempted_at": doc.retrieved_at})
                self._write_json(self.root / "manifest.json", manifest)
            raise ValueError(f"Retrieval unavailable: {doc.error_message}")
        return self.ingest_bytes(metadata, doc.raw_bytes or b"", "official HTTPS download", doc.url)

    def document(self, doc_id):
        if not re.fullmatch(r"doc-[a-f0-9]{24}", doc_id):
            raise KeyError("Unknown document")
        record = self.manifest()["documents"].get(doc_id)
        if not record:
            raise KeyError("Unknown document")
        return record

    def original_path(self, doc_id):
        record = self.document(doc_id)
        path = (self.root / record["filename"]).resolve()
        if path.parent != self.root or path.name != f"{doc_id}.{'pdf' if record['content_type'] == 'application/pdf' else 'html'}":
            raise ValueError("Unsafe archive path")
        if not path.is_file() or fingerprint(path.read_bytes()) != record["sha256"]:
            raise ValueError("Original missing or checksum mismatch")
        return path

    def apply_review(self, doc_id, review):
        """Apply a locally authored review only to the exact inspected original."""
        record = self.document(doc_id)
        data = self.original_path(doc_id).read_bytes()
        if review.get("sha256") != record["sha256"]:
            raise ValueError("Review does not match original bytes")
        if review.get("metadata") != {k: record[k] for k in FilingMetadata.model_fields}:
            raise ValueError("Review does not match document metadata")
        if not review.get("reviewed_at") or not review.get("checks"):
            raise ValueError("Document metadata and content review required")
        pages = self.pages(data, record["content_type"])
        evidence = []
        for item in review.get("evidence", []):
            page = item["page"]
            excerpt = normalized(item["excerpt"])
            if page < 1 or page > len(pages) or len(excerpt) < 20 or excerpt not in normalized(pages[page - 1]):
                raise ValueError("Supporting passage not found on specified page")
            ev_id = "ev-" + fingerprint(f"{doc_id}|{page}|{excerpt}".encode())[:24]
            evidence.append({"id": ev_id, "document_id": doc_id, "page": page, "excerpt": excerpt})
        if not evidence or not review.get("event"):
            raise ValueError("An event and supporting evidence are required")
        event = review["event"]
        AnnouncementCategory(event["category"])
        if not event.get("summary") or not event.get("title"):
            raise ValueError("Reviewed event title and summary required")
        # The review records the semantic check; these checks bind numbers/passages to bytes.
        evidence_text = " ".join(e["excerpt"] for e in evidence)
        for number in re.findall(r"\d[\d,]*(?:\.\d+)?", event["summary"]):
            if number.replace(",", "") not in evidence_text.replace(",", ""):
                raise ValueError(f"Summary number {number} not present in evidence")
        with self.lock:
            manifest = self.manifest()
            record = manifest["documents"][doc_id]
            record.update(review_status="reviewed", review=review, evidence=evidence)
            self._write_json(self.root / "manifest.json", manifest)
        return record

    def usable_documents(self):
        usable = []
        for record in self.manifest()["documents"].values():
            if record["review_status"] != "reviewed":
                continue
            try:
                self.original_path(record["id"])
            except (ValueError, KeyError):
                continue
            usable.append(record)
        return usable
