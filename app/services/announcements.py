"""Announcement normalization, priority scoring, and date-window filtering service.

Deterministic, transparent Push workflow engine.
All logic avoids LLM hallucinations and produces reproducible scores.
"""

from __future__ import annotations

import datetime
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.models import (
    Announcement,
    AnnouncementCategory,
    CATEGORY_BASE_SCORE,
    CATEGORY_DEFAULT_PRIORITY,
    Priority,
)
from app.data.companies import PORTDATA

# Index portfolio companies by ticker for fast canonical resolution
PORTFOLIO_TICKER_MAP: Dict[str, str] = {c.ticker.upper(): c.name for c in PORTDATA}


class NormalizationError(Exception):
    """Raised when an announcement fails required schema validation."""


class NormalizationResult:
    """Result of normalizing a batch of raw announcement records."""

    def __init__(
        self,
        valid: List[Announcement],
        invalid: List[Dict[str, Any]],
        duplicates: List[Dict[str, Any]],
    ):
        self.valid = valid
        self.invalid = invalid
        self.duplicates = duplicates

    @property
    def valid_count(self) -> int:
        return len(self.valid)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicates)


class AnnouncementService:
    """Service for normalizing, deduplicating, scoring, and filtering corporate announcements."""

    def __init__(self, ticker_map: Optional[Dict[str, str]] = None):
        self.ticker_map = ticker_map or PORTFOLIO_TICKER_MAP

    @staticmethod
    def canonical_id(ann: Announcement) -> str:
        title = " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", ann.title).casefold()))
        key = f"{ann.ticker.upper()}|{ann.category.value}|{ann.published_at}|{title}"
        if ann.source_document_id:
            key += "|" + ann.source_document_id
        return "event-" + hashlib.sha256(key.encode()).hexdigest()[:20]

    @classmethod
    def identity_keys(cls, ann):
        keys = {cls.canonical_id(ann), cls.canonical_id(ann.model_copy(update={"source_document_id": None}))}
        if ann.source_document_id:
            keys.add(f"doc:{ann.ticker.upper()}:{ann.source_document_id}")
        if ann.source_url:
            parts = urlsplit(ann.source_url.strip())
            query = sorted((k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"})
            url = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))
            keys.add("url:" + url)
        return keys

    @classmethod
    def deduplicate(cls, announcements):
        seen = set()
        unique = []
        for ann in announcements:
            keys = cls.identity_keys(ann)
            if not seen.intersection(keys):
                unique.append(ann)
            seen.update(keys)
        return unique

    def normalize_record(self, raw: Dict[str, Any]) -> Announcement:
        """Validate and normalize a single raw announcement record into an Announcement model.

        Raises:
            NormalizationError if required fields are missing or invalid.
        """
        # 1. Validate ticker
        raw_ticker = str(raw.get("ticker", "")).strip().upper()
        if not raw_ticker:
            raise NormalizationError("Missing required field: 'ticker'")

        canonical_company_name = self.ticker_map.get(raw_ticker)
        if not canonical_company_name:
            company_name = str(raw.get("company_name", "")).strip()
            if not company_name:
                raise NormalizationError(f"Unknown ticker '{raw_ticker}' and no company_name provided")
        else:
            company_name = canonical_company_name

        # 2. Validate category
        raw_cat = raw.get("category")
        if isinstance(raw_cat, AnnouncementCategory):
            category = raw_cat
        else:
            cat_str = str(raw_cat or "").strip().lower().replace("-", "_").replace(" ", "_")
            # Handle common category aliases
            cat_alias_map = {
                "merger_acquisition": AnnouncementCategory.M_AND_A,
                "mergers_and_acquisitions": AnnouncementCategory.M_AND_A,
                "m&a": AnnouncementCategory.M_AND_A,
                "capital_market": AnnouncementCategory.FUND_RAISE,
                "qip": AnnouncementCategory.FUND_RAISE,
                "buyback": AnnouncementCategory.FUND_RAISE,
                "bonus": AnnouncementCategory.BONUS_SPLIT,
                "split": AnnouncementCategory.BONUS_SPLIT,
                "agm": AnnouncementCategory.AGM_EGM,
                "egm": AnnouncementCategory.AGM_EGM,
            }
            if cat_str in cat_alias_map:
                category = cat_alias_map[cat_str]
            else:
                try:
                    category = AnnouncementCategory(cat_str)
                except ValueError:
                    category = AnnouncementCategory.UNCLASSIFIED

        # 3. Validate title
        title = str(raw.get("title", "")).strip()
        if not title:
            raise NormalizationError("Missing required field: 'title'")

        # 4. Validate & normalize published date (ISO YYYY-MM-DD)
        raw_date = raw.get("published_at")
        if not raw_date:
            raise NormalizationError("Missing required field: 'published_at'")

        try:
            if isinstance(raw_date, datetime.date):
                published_at = raw_date.strftime("%Y-%m-%d")
            else:
                dt = datetime.datetime.fromisoformat(str(raw_date)[:10])
                published_at = dt.strftime("%Y-%m-%d")
        except Exception as exc:
            raise NormalizationError(f"Invalid published_at format: '{raw_date}' (expected YYYY-MM-DD)") from exc

        # 5. Stable ID
        ann_id = str(raw.get("id") or raw.get("announcement_id") or "")

        # 6. Priority & score
        priority = raw.get("priority")
        if not isinstance(priority, Priority):
            priority = CATEGORY_DEFAULT_PRIORITY.get(category, Priority.LOW)

        score = float(raw.get("priority_score") or CATEGORY_BASE_SCORE.get(category, 10.0))
        reason = str(raw.get("priority_reason") or f"Category: {category.value}")

        announcement = Announcement(
            id=ann_id,
            ticker=raw_ticker,
            company_name=company_name,
            category=category,
            title=title,
            published_at=published_at,
            source_url=raw.get("source_url"),
            source_document_id=raw.get("source_document_id"),
            event_details=raw.get("event_details") or {},
            priority=priority,
            priority_score=score,
            priority_reason=reason,
            summary=raw.get("summary") or title,
            is_fixture=bool(raw.get("is_fixture", True)),
        )

        if not announcement.id:
            announcement.id = self.canonical_id(announcement)
        return announcement

    def process_batch(self, records: List[Dict[str, Any]]) -> NormalizationResult:
        """Process, validate, and deduplicate a batch of raw records."""
        valid: List[Announcement] = []
        invalid: List[Dict[str, Any]] = []
        duplicates: List[Dict[str, Any]] = []
        seen_keys: Set[str] = set()

        for rec in records:
            try:
                ann = self.normalize_record(rec)
                # Deduplication key: ticker + category + date + lowercase title
                keys = self.identity_keys(ann)
                dedup_key = self.canonical_id(ann)
                if seen_keys.intersection(keys):
                    duplicates.append({"record": rec, "reason": f"Duplicate of {dedup_key}"})
                else:
                    valid.append(ann)
                seen_keys.update(keys)
            except NormalizationError as err:
                invalid.append({"record": rec, "error": str(err)})

        return NormalizationResult(valid=valid, invalid=invalid, duplicates=duplicates)

    @staticmethod
    def score_and_rank(
        announcements: List[Announcement],
        reference_date: Optional[str] = None,
    ) -> List[Announcement]:
        """Score announcements deterministically with recency and stable tie-breaking.

        Returns a sorted list: highest score first, ties broken by recency, ticker, id.
        """
        ref_dt: Optional[datetime.date] = None
        if reference_date:
            try:
                ref_dt = datetime.date.fromisoformat(reference_date[:10])
            except ValueError:
                ref_dt = None

        scored: List[Tuple[float, str, str, str, Announcement]] = []

        for ann in announcements:
            base_score = CATEGORY_BASE_SCORE.get(ann.category, ann.priority_score)

            # Recency boost: up to +5 points if filing is on or 1 day from reference date
            recency_boost = 0.0
            if ref_dt:
                try:
                    ann_dt = datetime.date.fromisoformat(ann.published_at)
                    delta_days = (ref_dt - ann_dt).days
                    if delta_days == 0:
                        recency_boost = 5.0
                    elif delta_days == 1:
                        recency_boost = 3.0
                    elif 0 <= delta_days <= 3:
                        recency_boost = 1.0
                except ValueError:
                    pass

            final_score = base_score + recency_boost

            # Stable tie-breaker tuple: (-final_score, -published_at, ticker, id)
            # Higher score first, newer date first, alphabetical ticker, id
            scored.append((final_score, ann.published_at, ann.ticker, ann.id, ann))

        # Sort: score descending, date descending, ticker ascending, id ascending
        scored.sort(key=lambda x: (-x[0], -datetime.date.fromisoformat(x[1]).toordinal(), x[2], x[3]), reverse=False)

        # Return updated Announcement objects
        result: List[Announcement] = []
        for score, _, _, _, ann in scored:
            ann_copy = ann.model_copy(update={"priority_score": score})
            result.append(ann_copy)

        return result

    @staticmethod
    def filter_by_window(
        announcements: List[Announcement],
        window: str = "24h",
        reference_date: Optional[str] = None,
    ) -> List[Announcement]:
        """Filter announcements within a specified date window relative to reference_date.

        Supported windows:
          - "24h" (1 day: reference_date - 1 day <= pub_date <= reference_date)
          - "3d"  (3 days: reference_date - 3 days <= pub_date <= reference_date)
          - "7d"  (7 days: reference_date - 7 days <= pub_date <= reference_date)
          - "all" (all historical announcements up to reference_date)

        Future announcements beyond reference_date are excluded.
        """
        if not announcements:
            return []

        # Determine reference date
        if reference_date:
            ref_dt = datetime.date.fromisoformat(reference_date[:10])
        else:
            # Default to latest announcement date in the dataset
            valid_dates = [
                datetime.date.fromisoformat(a.published_at)
                for a in announcements
                if a.published_at
            ]
            ref_dt = max(valid_dates) if valid_dates else datetime.date.today()

        window_days = {
            "24h": 1,
            "3d": 3,
            "7d": 7,
            "30d": 30,
            "all": 36500,  # 100 years
        }.get(window.lower(), 1)

        start_dt = ref_dt - datetime.timedelta(days=window_days)

        filtered: List[Announcement] = []
        for ann in announcements:
            try:
                ann_dt = datetime.date.fromisoformat(ann.published_at)
                # Boundary check: start_dt <= ann_dt <= ref_dt
                if start_dt <= ann_dt <= ref_dt:
                    filtered.append(ann)
            except ValueError:
                continue

        return filtered

