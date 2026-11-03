"""Research orchestrator service for the FINN Pull research workflow.

Coordinates primary document retrieval, document parsing, evidence extraction,
and citation-validated research brief synthesis.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.models import Company, CompanyResearch, SourceEvidence
from app.data.companies import RESEARCH_DATA
from app.data.research_fixtures import RESEARCH_FIXTURE_DOCS
from app.services.document_processor import DocumentProcessor
from app.services.research_store import ResearchStore
from app.services.retrieval import PrimarySourceRetriever
from app.services.synthesizer import ResearchSynthesizer

logger = logging.getLogger(__name__)


class ResearchService:
    """Orchestrates document ingestion, evidence extraction, and brief generation."""

    def __init__(
        self,
        store: Optional[ResearchStore] = None,
        processor: Optional[DocumentProcessor] = None,
        synthesizer: Optional[ResearchSynthesizer] = None,
        retriever: Optional[PrimarySourceRetriever] = None,
    ):
        self.store = store or ResearchStore()
        self.processor = processor or DocumentProcessor()
        self.synthesizer = synthesizer or ResearchSynthesizer(store=self.store)
        self.retriever = retriever or PrimarySourceRetriever()
        self._companies_by_ticker: Dict[str, Company] = {c.ticker.upper(): c for c in RESEARCH_DATA}

    def list_companies(self) -> List[Company]:
        """Return the list of companies in the research universe."""
        return list(self._companies_by_ticker.values())

    def get_company(self, ticker: str) -> Optional[Company]:
        """Get company details by ticker."""
        return self._companies_by_ticker.get(ticker.upper())

    def is_valid_ticker(self, ticker: str) -> bool:
        """Check if ticker is in the research universe."""
        return ticker.upper() in self._companies_by_ticker

    def load_fixture_evidence(self, ticker: str) -> List[SourceEvidence]:
        """Process and store primary document fixtures for a research company."""
        ticker_upper = ticker.upper()
        fixture_docs = RESEARCH_FIXTURE_DOCS.get(ticker_upper, [])
        all_evidence: List[SourceEvidence] = []

        for doc in fixture_docs:
            self.store.save_document(doc)
            evidence_items = self.processor.process_document(doc)
            self.store.save_evidence(evidence_items)
            all_evidence.extend(evidence_items)

        return all_evidence

    def generate_brief(
        self,
        ticker: str,
        force_refresh: bool = False,
    ) -> CompanyResearch:
        """Generate or retrieve a validated research brief for a target ticker.

        If force_refresh is False and a cached brief exists, returns the cached brief.
        Otherwise, processes primary documents and generates an evidence-grounded brief.
        """
        ticker_upper = ticker.upper()
        company = self.get_company(ticker_upper)
        if not company:
            raise KeyError(f"Ticker '{ticker_upper}' is not in the research universe.")

        if not force_refresh:
            cached = self.store.get_latest_research(ticker_upper)
            if cached:
                return cached

        # Fetch or extract evidence
        evidence = self.store.list_evidence(ticker=ticker_upper)
        if not evidence or force_refresh:
            evidence = self.load_fixture_evidence(ticker_upper)

        brief = self.synthesizer.generate_brief(
            ticker=ticker_upper,
            company_name=company.name,
            evidence=evidence,
        )

        return brief

    def get_brief_by_id(self, research_id: str) -> Optional[CompanyResearch]:
        """Lookup a research brief by its unique ID."""
        return self.store.get_research(research_id)

    def get_latest_brief(self, ticker: str) -> Optional[CompanyResearch]:
        """Get latest brief for a ticker, generating it on demand if needed."""
        ticker_upper = ticker.upper()
        if not self.is_valid_ticker(ticker_upper):
            return None
        return self.generate_brief(ticker_upper, force_refresh=False)

    def get_evidence(self, ticker: str) -> List[SourceEvidence]:
        """Get all stored evidence passages for a company ticker."""
        ticker_upper = ticker.upper()
        if not self.is_valid_ticker(ticker_upper):
            return []
        # Ensure evidence is loaded
        ev = self.store.list_evidence(ticker=ticker_upper)
        if not ev:
            ev = self.load_fixture_evidence(ticker_upper)
        return ev
