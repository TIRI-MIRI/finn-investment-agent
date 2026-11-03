"""Citation validation component for FINN Pull Research workflow.

Validates that factual claims in research briefs are genuinely supported
by indexed primary source evidence passages. Enforces strict rules against
hallucinated citations, wrong-ticker evidence contamination, empty passages,
and unsupported numeric claims.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.core.models import (
    Claim,
    Confidence,
    ResearchSection,
    SourceEvidence,
)
from app.services.research_store import ResearchStore


class CitationValidationResult:
    """Outcome of validating a single claim's citations."""

    def __init__(
        self,
        is_valid: bool,
        valid_ids: List[str],
        invalid_ids: List[str],
        warnings: List[str],
        has_numeric_mismatch: bool = False,
        unsupported_numbers: Optional[List[str]] = None,
    ):
        self.is_valid = is_valid
        self.valid_ids = valid_ids
        self.invalid_ids = invalid_ids
        self.warnings = warnings
        self.has_numeric_mismatch = has_numeric_mismatch
        self.unsupported_numbers = unsupported_numbers or []


class CitationValidator:
    """Validates candidate claims against primary source evidence.

    Mandatory validation rules:
    1. Every cited evidence_id must resolve to evidence in the active store.
    2. Every cited evidence item must belong to the requested ticker (no cross-company contamination).
    3. The evidence passage excerpt must be non-empty and non-whitespace.
    4. Key numbers, currencies, and percentages mentioned in factual claims
       are verified against cited excerpts to prevent numerical hallucination.
    5. Distinguishes supported from unsupported claims; downgrades confidence
       to Confidence.LOW or marks unverified when evidence is deficient.
    6. Does not claim perfect semantic truth; reports limitations transparently.
    """

    def __init__(self, store: Optional[ResearchStore] = None):
        self.store = store

    def validate_claim(
        self,
        claim: Claim,
        target_ticker: str,
        available_evidence: Optional[Dict[str, SourceEvidence]] = None,
    ) -> CitationValidationResult:
        """Validate an individual claim against available evidence records."""
        valid_ids: List[str] = []
        invalid_ids: List[str] = []
        warnings: List[str] = []
        target_ticker_upper = target_ticker.upper()

        if not claim.evidence_ids:
            warnings.append("Claim has no evidence citations.")
            return CitationValidationResult(
                is_valid=False,
                valid_ids=[],
                invalid_ids=[],
                warnings=warnings,
            )

        supporting_excerpts: List[str] = []

        for ev_id in claim.evidence_ids:
            # 1. Lookup in provided map or store
            ev: Optional[SourceEvidence] = None
            if available_evidence and ev_id in available_evidence:
                ev = available_evidence[ev_id]
            elif self.store:
                ev = self.store.get_evidence(ev_id)

            if not ev:
                invalid_ids.append(ev_id)
                warnings.append(f"Citation '{ev_id}' not found in active evidence store.")
                continue

            # 2. Cross-company contamination check
            ev_ticker = (ev.ticker or "").upper()
            if ev_ticker and ev_ticker != target_ticker_upper:
                invalid_ids.append(ev_id)
                warnings.append(
                    f"Citation '{ev_id}' belongs to ticker '{ev_ticker}', not requested ticker '{target_ticker_upper}'."
                )
                continue

            # 3. Non-empty excerpt check
            if not ev.excerpt or not ev.excerpt.strip():
                invalid_ids.append(ev_id)
                warnings.append(f"Citation '{ev_id}' has an empty evidence excerpt.")
                continue

            valid_ids.append(ev_id)
            supporting_excerpts.append(ev.excerpt)

        if not valid_ids:
            return CitationValidationResult(
                is_valid=False,
                valid_ids=[],
                invalid_ids=invalid_ids,
                warnings=warnings,
            )

        # 4. Numeric & percentage check
        # Extract numbers, percentages, and financial figures from claim text (e.g. 12.0%, 2,43,865, 41,764)
        combined_excerpts = " ".join(supporting_excerpts).replace(",", "")
        claim_numbers = re.findall(r"\b\d+(?:\.\d+)?%?", claim.text.replace(",", ""))

        has_numeric_mismatch = False
        unsupported_numbers: List[str] = []

        for num in claim_numbers:
            # Skip common small integers like years (2024, 2025) or ordinal numbers
            if num in ("1", "2", "3", "4", "5", "2024", "2025", "2026"):
                continue
            # Strip % for matching
            raw_num = num.rstrip("%")
            if raw_num not in combined_excerpts:
                has_numeric_mismatch = True
                unsupported_numbers.append(num)
                warnings.append(
                    f"Numeric value '{num}' in claim text was not explicitly found in cited evidence excerpts."
                )

        is_valid = len(invalid_ids) == 0 and len(valid_ids) > 0
        return CitationValidationResult(
            is_valid=is_valid,
            valid_ids=valid_ids,
            invalid_ids=invalid_ids,
            warnings=warnings,
            has_numeric_mismatch=has_numeric_mismatch,
            unsupported_numbers=unsupported_numbers,
        )

    def validate_and_filter_sections(
        self,
        sections: List[ResearchSection],
        target_ticker: str,
        available_evidence: Optional[Dict[str, SourceEvidence]] = None,
    ) -> Tuple[List[ResearchSection], List[str]]:
        """Validate all claims across sections, filtering invalid IDs and annotating warnings."""
        all_warnings: List[str] = []
        validated_sections: List[ResearchSection] = []

        for sec in sections:
            validated_claims: List[Claim] = []
            for claim in sec.claims:
                res = self.validate_claim(claim, target_ticker, available_evidence)
                if res.is_valid:
                    if res.has_numeric_mismatch:
                        # Downgrade confidence to LOW if key numbers are unsupported
                        all_warnings.extend(res.warnings)
                        validated_claims.append(
                            Claim(
                                text=claim.text,
                                evidence_ids=res.valid_ids,
                                confidence=Confidence.LOW,
                                claim_type=getattr(claim, "claim_type", "reported_fact"),
                            )
                        )
                    else:
                        # Fully supported claim
                        validated_claims.append(
                            Claim(
                                text=claim.text,
                                evidence_ids=res.valid_ids,
                                confidence=claim.confidence,
                                claim_type=getattr(claim, "claim_type", "reported_fact"),
                            )
                        )
                else:
                    all_warnings.extend(res.warnings)
                    if res.valid_ids:
                        # Partial support: retain valid IDs only, downgrade confidence to LOW
                        validated_claims.append(
                            Claim(
                                text=claim.text,
                                evidence_ids=res.valid_ids,
                                confidence=Confidence.LOW,
                                claim_type=getattr(claim, "claim_type", "reported_fact"),
                            )
                        )
                    else:
                        # Zero valid citations: mark explicitly as unsupported
                        validated_claims.append(
                            Claim(
                                text=f"[UNVERIFIED IN RETRIEVED SOURCES] {claim.text}",
                                evidence_ids=[],
                                confidence=Confidence.LOW,
                                claim_type=getattr(claim, "claim_type", "unsupported"),
                            )
                        )

            validated_sections.append(
                ResearchSection(
                    id=sec.id,
                    title=sec.title,
                    summary=sec.summary,
                    claims=validated_claims,
                )
            )

        return validated_sections, all_warnings

