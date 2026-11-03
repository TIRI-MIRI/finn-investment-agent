"""In-memory research and evidence store.

Provides storage and retrieval for primary documents, extracted evidence passages,
and generated research briefs.
NOTE: This store is ephemeral and in-memory; it resets whenever the application restarts.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.core.models import CompanyResearch, RetrievedDocument, SourceEvidence


class ResearchStore:
    """Ephemeral in-memory store for research documents, evidence, and briefs."""

    def __init__(self):
        self._documents: Dict[str, RetrievedDocument] = {}
        self._evidence: Dict[str, SourceEvidence] = {}
        self._research: Dict[str, CompanyResearch] = {}
        # Ticker index: ticker.upper() -> list of research IDs (newest first)
        self._ticker_research_index: Dict[str, List[str]] = {}

    # ── Document Methods ──────────────────────────────────────────────────

    def save_document(self, doc: RetrievedDocument) -> str:
        """Store a RetrievedDocument and return its ID."""
        self._documents[doc.id] = doc
        return doc.id

    def get_document(self, doc_id: str) -> Optional[RetrievedDocument]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    def list_documents(self, ticker: Optional[str] = None) -> List[RetrievedDocument]:
        """List documents, optionally filtered by ticker."""
        if not ticker:
            return list(self._documents.values())
        ticker_upper = ticker.upper()
        return [d for d in self._documents.values() if d.ticker.upper() == ticker_upper]

    # ── Evidence Methods ──────────────────────────────────────────────────

    def save_evidence(self, evidence_list: List[SourceEvidence]) -> List[str]:
        """Store a batch of SourceEvidence records, returning their IDs."""
        saved_ids: List[str] = []
        for ev in evidence_list:
            self._evidence[ev.id] = ev
            saved_ids.append(ev.id)
        return saved_ids

    def get_evidence(self, evidence_id: str) -> Optional[SourceEvidence]:
        """Lookup an evidence record by ID."""
        return self._evidence.get(evidence_id)

    def list_evidence(
        self,
        ticker: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> List[SourceEvidence]:
        """List evidence passages, optionally filtered by ticker or parent document ID."""
        results = list(self._evidence.values())
        if ticker:
            ticker_upper = ticker.upper()
            results = [e for e in results if (e.ticker or "").upper() == ticker_upper]
        if document_id:
            results = [e for e in results if e.document_id == document_id]
        return results

    # ── Research Brief Methods ────────────────────────────────────────────

    def save_research(self, research: CompanyResearch) -> str:
        """Store a completed CompanyResearch brief."""
        self._research[research.id] = research
        ticker_upper = research.ticker.upper()
        if ticker_upper not in self._ticker_research_index:
            self._ticker_research_index[ticker_upper] = []
        # Prepend so newest is first
        self._ticker_research_index[ticker_upper].insert(0, research.id)
        return research.id

    def get_research(self, research_id: str) -> Optional[CompanyResearch]:
        """Lookup a research brief by its research ID."""
        return self._research.get(research_id)

    def get_latest_research(self, ticker: str) -> Optional[CompanyResearch]:
        """Fetch the most recent research brief for a ticker."""
        ticker_upper = ticker.upper()
        ids = self._ticker_research_index.get(ticker_upper, [])
        if ids:
            return self._research.get(ids[0])
        return None

    # ── Store Management ──────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all in-memory records (useful for test resets)."""
        self._documents.clear()
        self._evidence.clear()
        self._research.clear()
        self._ticker_research_index.clear()

