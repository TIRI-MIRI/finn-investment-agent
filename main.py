"""FINN — Financial Investment Intelligence Agent.

FastAPI application entry point with Push workflow services and server-rendered UI.
Start with:  uvicorn main:app --reload
"""

from pathlib import Path
from datetime import date
from pydantic import BaseModel, StrictBool
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.models import (
    AnnouncementCategory,
    CompanyResearch,
    DigestResponse,
    Priority,
    QuarterlyResultSummary,
    SourceEvidence,
)
from app.data.announcements import ANNOUNCEMENTS, REAL_ANNOUNCEMENTS
from app.data.companies import PORTDATA, RESEARCH_DATA
from app.data.prices import PRICE_BARS, PRICE_BARS_BY_TICKER
from app.services.announcements import AnnouncementService
from app.services.anomalies import AnomalyDetector
from app.services.research_service import ResearchService
from app.services.results import ResultsService
from app.services.monitoring import build_monitoring, market_signals
from app.services.monitoring_store import MonitoringStore, MonitoringRules
from app.services.filing_archive import FilingArchive

app = FastAPI(
    title=settings.app_name,
    description=(
        "Mobile-first financial investment intelligence prototype "
        "for Indian listed companies."
    ),
    version="0.1.0",
)

# Mount static assets
_base_dir = Path(__file__).parent
_static_dir = _base_dir / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory=str(_base_dir / "templates"))

# Initialize domain services
announcement_service = AnnouncementService()
results_service = ResultsService()
research_service = ResearchService()
monitoring_store = MonitoringStore(_base_dir / "runtime" / "monitoring.json")
templates.env.globals["event_id"] = AnnouncementService.canonical_id
templates.env.globals["app_settings"] = settings

def active_prices():
    # No genuine market history has been ingested yet.
    return PRICE_BARS_BY_TICKER if settings.demo_mode else {}


def active_announcements():
    if settings.demo_mode:
        return ANNOUNCEMENTS
    verified = {d['id'] for d in FilingArchive(_base_dir / 'data/filings').usable_documents()}
    return [a for a in REAL_ANNOUNCEMENTS if a.source_document_id in verified]


def latest_data_date():
    dates = [a.published_at for a in active_announcements()]
    dates += [b.date for bars in active_prices().values() for b in bars]
    return max(dates) if dates else date.today().isoformat()


def holding_tiles(reference_date):
    signals = {s.ticker: s for s in market_signals(active_prices(), monitoring_store.load()[0].rules, reference_date)}
    tiles = []
    for ticker, history in active_prices().items():
        bars = [b for b in history if b.date <= reference_date]
        if len(bars) < 2 or bars[-2].close <= 0:
            continue
        values = [b.close for b in bars[-20:]]
        low, high = min(values), max(values)
        points = ' '.join(f'{i * 100 / (len(values)-1):.1f},{22 - (v-low) / (high-low or 1)*20:.1f}' for i,v in enumerate(values))
        tiles.append(dict(ticker=ticker, change=(bars[-1].close/bars[-2].close-1)*100, points=points,
                          volume=bool(signals.get(ticker) and signals[ticker].is_volume_anomaly)))
    return tiles


def checked_reference(value):
    try:
        return date.fromisoformat(value or latest_data_date()).isoformat()
    except ValueError:
        raise HTTPException(422, "Reference date must be YYYY-MM-DD")

def monitoring_snapshot(rules=None, window="24h", reference_date=None):
    if window not in {"24h", "3d", "7d", "30d", "all"}:
        raise HTTPException(422, "Invalid window")
    state, warning = monitoring_store.load()
    # In real-data mode, use only verified document-backed announcements.
    # In demo mode, use synthetic fixtures. Never mix them.
    announcement_list = active_announcements()
    result = build_monitoring(announcement_list, active_prices(), rules or state.rules, state.acknowledged, checked_reference(reference_date), window, demo_mode=settings.demo_mode)
    result["warning"] = warning
    result["demo_mode"] = settings.demo_mode
    return result


# ── Page Routes (UI Shell & Push Workflow) ────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the Today view."""
    return RedirectResponse(url="/today", status_code=307)


@app.get("/today", response_model=None)
async def page_today(
    request: Request,
    window: str = Query("24h", description="Filter window: 24h, 3d, 7d, all"),
    ref_date: Optional[str] = Query(None, description="Optional reference date (YYYY-MM-DD)"),
):
    """Today screen — prioritised digest, price/volume anomaly alerts, and routine filings."""
    valid_windows = {"24h", "3d", "7d", "30d", "all"}
    active_window = window.lower() if window.lower() in valid_windows else "24h"

    monitor = monitoring_snapshot(window=active_window, reference_date=ref_date)
    material = [a for a in monitor["events"] if a.priority in (Priority.HIGH, Priority.MEDIUM)]
    routine = [a for a in monitor["events"] if a.priority == Priority.LOW]
    tiles = holding_tiles(monitor["reference_date"])
    high = [a for a in material if a.priority == Priority.HIGH]
    acknowledged = monitoring_store.load()[0].acknowledged
    needs = sum(not acknowledged.get(monitor["event_alerts"].get(AnnouncementService.canonical_id(a), "")) for a in high)
    brief = f"{len(high)} important filing{'s' if len(high) != 1 else ''} and {len(routine)} routine update{'s' if len(routine) != 1 else ''} in this window."
    if tiles:
        biggest = max(tiles, key=lambda t: abs(t["change"]))
        brief = f"{sum(t['change'] > 0 for t in tiles)} holdings up and {sum(t['change'] < 0 for t in tiles)} down. " + brief + f" Biggest move: {biggest['ticker']} {biggest['change']:+.1f}%."
    return templates.TemplateResponse(request=request, name="today.html", context={
        "current_tab": "today", "active_window": active_window,
        "reference_date": monitor["reference_date"], "custom_reference": ref_date is not None,
        "portfolio_count": len(PORTDATA), "monitor": monitor,
        "material_announcements": material, "routine_announcements": routine,
        "high_priority_count": sum(a.priority == Priority.HIGH for a in material),
        "medium_priority_count": sum(a.priority == Priority.MEDIUM for a in material),
        "low_priority_count": len(routine),
        "results_map": {r.ticker: r for r in results_service.get_all_summaries()},
        "demo_mode": settings.demo_mode,
        "app_env": settings.app_env,
        # Holdings strip needs the price bars grouped by ticker
        "price_bars_by_ticker": active_prices(),
        "holding_tiles": tiles, "needs_count": needs, "daily_brief": brief,
        "data_as_of": latest_data_date(),
    })


@app.get("/alerts", response_model=None)
async def page_alerts(
    request: Request,
    window: str = Query("24h", description="Filter window: 24h, 3d, 7d, all"),
    ref_date: Optional[str] = Query(None, description="Optional reference date (YYYY-MM-DD)"),
):
    """Alerts screen — triggered price, volume, and filing alerts."""
    valid_windows = {"24h", "3d", "7d", "30d", "all"}
    active_window = window.lower() if window.lower() in valid_windows else "24h"
    monitor = monitoring_snapshot(window=active_window, reference_date=ref_date)
    return templates.TemplateResponse(request=request, name="alerts.html", context={
        "current_tab": "alerts",
        "active_window": active_window,
        "reference_date": monitor["reference_date"],
        "monitor": monitor,
        "demo_mode": settings.demo_mode,
    })


@app.get("/watch", response_model=None)
async def page_watch(request: Request):
    """Watch screen — portfolio holdings and monitoring preferences."""
    latest_prices = {ticker: bars[-1].close for ticker, bars in active_prices().items() if bars}
    state, warning = monitoring_store.load()
    verified_documents = FilingArchive(_base_dir / 'data/filings').usable_documents()
    documents_by_ticker = {}
    for document in verified_documents:
        documents_by_ticker.setdefault(document['ticker'], []).append(document)
    return templates.TemplateResponse(request=request, name="watch.html", context={
        "current_tab": "watch",
        "last_data_update": latest_data_date(),
        "documents_by_ticker": documents_by_ticker,
        "verified_documents": verified_documents,
        "companies": PORTDATA,
        "latest_prices": latest_prices,
        "rules": state.rules,
        "settings_warning": warning,
        "event_categories": list(AnnouncementCategory),
        "portfolio_count": len(PORTDATA),
        "announcements_count": len(active_announcements()),
        "price_bars_count": sum(len(b) for b in active_prices().values()),
        "verified_filings_count": len(FilingArchive(_base_dir / 'data/filings').usable_documents()),
    })


@app.get("/portfolio", response_model=None)
async def page_portfolio(request: Request):
    """Portfolio screen — tracked portfolio companies (legacy route, now uses watch layout)."""
    latest_prices = {
        ticker: bars[-1].close
        for ticker, bars in active_prices().items()
        if bars
    }
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={
            "current_tab": "portfolio",
            "companies": PORTDATA,
            "latest_prices": latest_prices,
        },
    )


@app.get("/research", response_model=None)
async def page_research(
    request: Request,
    ticker: Optional[str] = Query(None, description="Target company ticker for research brief"),
):
    """Research screen — company research view (Pull workflow)."""
    selected_ticker = (ticker or "INFY").upper()
    selected_company = research_service.get_company(selected_ticker)

    brief = None
    if selected_company:
        brief = research_service.get_latest_brief(selected_ticker)

    return templates.TemplateResponse(
        request=request,
        name="research.html",
        context={
            "current_tab": "research",
            "research_companies": RESEARCH_DATA,
            "selected_ticker": selected_ticker,
            "selected_company": selected_company,
            "brief": brief,
        },
    )


@app.get("/settings", response_model=None)
async def page_settings(request: Request):
    """Settings screen — threshold preferences and environment info."""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "current_tab": "settings",
            "companies": PORTDATA,
            "portfolio_count": len(PORTDATA),
            "research_count": len(RESEARCH_DATA),
            "announcements_count": len(active_announcements()),
            "price_bars_count": sum(len(b) for b in active_prices().values()),
            "rules": monitoring_store.load()[0].rules,
            "settings_warning": monitoring_store.load()[1],
            "event_categories": list(AnnouncementCategory),
        },
    )


# ── Push Workflow API Endpoints ───────────────────────────────────────────


@app.get("/api/digest", response_model=DigestResponse)
async def get_digest(
    window: str = Query("24h", description="Time window: 24h, 3d, 7d, all"),
    reference_date: Optional[str] = Query(None, description="Optional reference date (YYYY-MM-DD)"),
):
    """Get prioritized announcement digest for a selectable time window."""
    valid_windows = {"24h", "3d", "7d", "30d", "all"}
    if window.lower() not in valid_windows:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid window '{window}'. Allowed values: {sorted(list(valid_windows))}",
        )

    ref = checked_reference(reference_date)

    filtered = announcement_service.filter_by_window(
        active_announcements(),
        window=window.lower(),
        reference_date=ref,
    )
    ranked = announcement_service.score_and_rank(announcement_service.deduplicate(filtered), reference_date=ref)

    material = [a for a in ranked if a.priority in (Priority.HIGH, Priority.MEDIUM)]
    routine = [a for a in ranked if a.priority == Priority.LOW]

    return DigestResponse(
        window=window.lower(),
        reference_date=ref,
        total_count=len(ranked),
        material_count=len(material),
        routine_count=len(routine),
        material_announcements=material,
        routine_announcements=routine,
        is_fixture=settings.demo_mode,
    )


@app.get("/api/alerts")
async def get_alerts(
    price_threshold: Optional[float] = Query(None, ge=0.1, le=100.0, description="Price change threshold %"),
    volume_threshold: Optional[float] = Query(None, ge=0.5, le=50.0, description="Volume multiple threshold"),
    anomalies_only: bool = Query(True, description="Filter for detected anomalies only"),
):
    """Get price and volume anomaly alerts across the portfolio universe."""
    rules = monitoring_store.load()[0].rules
    overrides = {}
    if price_threshold is not None:
        overrides["price_threshold_pct"] = price_threshold
    if volume_threshold is not None:
        overrides["volume_multiple_threshold"] = volume_threshold
    rules = rules.model_copy(update=overrides)
    alerts = market_signals(active_prices(), rules, latest_data_date())
    if anomalies_only:
        alerts = [a for a in alerts if a.triggered]
    return {"count": len(alerts), "price_threshold_pct": rules.price_threshold_pct,
            "volume_multiple_threshold": rules.volume_multiple_threshold, "trigger_mode": rules.trigger_mode,
            "alerts": [a.model_dump() for a in alerts], "is_fixture": settings.demo_mode}


@app.get("/api/monitoring/settings")
async def get_monitoring_settings():
    state, warning = monitoring_store.load()
    return {"rules": state.rules, "warning": warning}


@app.get("/api/monitoring/defaults")
async def default_monitoring_settings():
    return MonitoringRules()


@app.put("/api/monitoring/settings")
async def save_monitoring_settings(rules: MonitoringRules):
    try:
        monitoring_store.save_rules(rules)
    except OSError:
        raise HTTPException(503, "Unable to save monitoring preferences. Existing settings were not replaced.")
    return {"rules": rules}


@app.post("/api/monitoring/preview")
async def preview_monitoring(rules: MonitoringRules):
    snapshot = monitoring_snapshot(rules, window="all")
    return {"alert_count": len(snapshot["queue"]),
            "event_alerts": len(snapshot["event_alerts"]),
            "market_alerts": len(snapshot["signal_alerts"]),
            "holdings": sorted({a["ticker"] for a in snapshot["queue"]}),
            "reference_date": snapshot["reference_date"]}


@app.get("/api/monitoring")
async def get_monitoring(window: str = "24h", reference_date: Optional[str] = None):
    return monitoring_snapshot(window=window, reference_date=reference_date)


class AcknowledgementRequest(BaseModel):
    acknowledged: StrictBool
    reference_date: Optional[date] = None


@app.put("/api/monitoring/alerts/{alert_id}")
async def acknowledge_alert(alert_id: str, body: AcknowledgementRequest):
    snapshot = monitoring_snapshot(window="all", reference_date=body.reference_date.isoformat() if body.reference_date else None)
    if alert_id not in {a["id"] for a in snapshot["queue"]}:
        raise HTTPException(404, "Alert not found under current monitoring rules")
    try:
        monitoring_store.acknowledge(alert_id, body.acknowledged)
    except OSError as exc:
        raise HTTPException(503, "Unable to save acknowledgement; check monitoring preferences and storage.") from exc
    return {"id": alert_id, "acknowledged": body.acknowledged}


@app.get("/api/results")
async def get_all_results():
    """Get all structured quarterly results summaries available."""
    summaries = ResultsService(demo_mode=settings.demo_mode).get_all_summaries()
    return {
        "count": len(summaries),
        "results": [s.model_dump() for s in summaries],
        "is_fixture": settings.demo_mode,
    }


@app.get("/api/results/{ticker}")
async def get_ticker_results(ticker: str):
    """Get quarterly results summary for a specific company ticker."""
    summary = ResultsService(demo_mode=settings.demo_mode).get_summary_by_ticker(ticker)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"Quarterly results summary for ticker '{ticker.upper()}' not found.",
        )
    return summary.model_dump()


@app.get("/filings/{doc_id}")
async def serve_filing(doc_id: str):
    """Serve a locally stored verified filing document by document ID."""
    import json
    from pathlib import Path
    from fastapi.responses import FileResponse

    manifest_path = Path(__file__).parent / "data" / "filings" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        raise HTTPException(404, "Filing manifest not available")

    doc_info = manifest.get("documents", {}).get(doc_id)
    if not doc_info:
        raise HTTPException(404, f"Filing document '{doc_id}' not found")

    archive = FilingArchive(_base_dir / 'data/filings')
    try:
        if doc_info.get('review_status') != 'reviewed':
            raise ValueError('Document review incomplete')
        pdf_path = archive.original_path(doc_id)
    except (KeyError, ValueError, OSError):
        raise HTTPException(404, 'Verified filing unavailable')

    return FileResponse(
        path=str(pdf_path),
        media_type=doc_info.get("content_type", "application/pdf"),
        filename=doc_info["filename"],
        content_disposition_type="inline",
    )


# ── Preserved Health and Legacy API Endpoints ─────────────────────────────


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "mode": "demo" if settings.demo_mode else "live",
        "version": "0.1.0",
    }


@app.get("/api/portfolio")
async def get_portfolio():
    """Return the demo portfolio companies."""
    return {
        "count": len(PORTDATA),
        "companies": [c.model_dump() for c in PORTDATA],
        "is_fixture": True,
    }


@app.get("/api/announcements")
async def get_announcements():
    """Return demo announcement fixtures."""
    return {
        "count": len(active_announcements()),
        "announcements": [a.model_dump() for a in active_announcements()],
        "is_fixture": settings.demo_mode,
    }


# ── Pull Research Workflow API Endpoints ─────────────────────────────────


@app.get("/api/research/companies")
async def get_research_companies():
    """Return available companies in the primary research universe."""
    companies = research_service.list_companies()
    return {
        "count": len(companies),
        "companies": [c.model_dump() for c in companies],
        "is_fixture": True,
    }


@app.post("/api/research/{ticker}")
async def create_research_brief(
    ticker: str,
    force_refresh: bool = Query(False, description="Force re-generation of research brief"),
):
    """Generate or refresh an evidence-grounded research brief for a company."""
    ticker_upper = ticker.upper()
    if not research_service.is_valid_ticker(ticker_upper):
        raise HTTPException(
            status_code=404,
            detail=f"Company ticker '{ticker_upper}' not found in research universe.",
        )
    brief = research_service.generate_brief(ticker_upper, force_refresh=force_refresh)
    return brief.model_dump()


@app.get("/api/research/{ticker}")
async def get_research_brief(ticker: str):
    """Get the latest research brief for a ticker or by research ID."""
    ticker_upper = ticker.upper()
    if ticker_upper.lower().startswith("res-"):
        brief = research_service.get_brief_by_id(ticker)
        if brief:
            return brief.model_dump()

    if not research_service.is_valid_ticker(ticker_upper):
        raise HTTPException(
            status_code=404,
            detail=f"Research brief for ticker '{ticker_upper}' not found.",
        )
    brief = research_service.get_latest_brief(ticker_upper)
    if not brief:
        raise HTTPException(
            status_code=404,
            detail=f"No research brief generated yet for '{ticker_upper}'.",
        )
    return brief.model_dump()


@app.get("/api/research/{ticker}/evidence")
async def get_research_evidence(ticker: str):
    """Get all primary source evidence passages for a company ticker."""
    ticker_upper = ticker.upper()
    if not research_service.is_valid_ticker(ticker_upper):
        raise HTTPException(
            status_code=404,
            detail=f"Company ticker '{ticker_upper}' not found in research universe.",
        )
    evidence = research_service.get_evidence(ticker_upper)
    return {
        "count": len(evidence),
        "ticker": ticker_upper,
        "evidence": [e.model_dump() for e in evidence],
        "is_fixture": True,
    }

