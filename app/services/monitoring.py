"""Deterministic monitoring inbox, using the same rules for UI and API."""
import hashlib
import json

from app.core.models import AnnouncementCategory as Category
from app.services.announcements import AnnouncementService
from app.services.anomalies import AnomalyDetector
from app.services.results import ResultsService


IMPLICATIONS = {
    "results": ("Results update the earnings and cash-generation picture.", "Compare profitability and cash conversion with your holding thesis; one quarter alone may not change it."),
    "m_and_a": ("A transaction can change capital needs and execution risk.", "Review funding, approvals and integration assumptions; the eventual effect on this holding is uncertain."),
    "management_change": ("Leadership changes can affect continuity and oversight.", "Review succession and governance disclosures; operating impact cannot yet be established."),
    "dividend": ("A dividend changes expected shareholder cash distributions.", "Check eligibility and approvals; a proposed distribution does not establish future returns."),
    "bonus_split": ("Corporate actions can change share counts and per-share comparisons.", "Check record dates and adjust comparisons; a bonus or split alone does not create economic value."),
    "fund_raise": ("New funding can change capital structure.", "Review dilution and use of proceeds; the benefit depends on terms and deployment."),
    "credit_rating": ("Credit assessments inform financing-risk review.", "Read the rating rationale and outlook; a rating action does not predict equity performance."),
    "capex": ("Investment plans can change funding needs and future capacity.", "Review project funding and execution milestones; returns on the investment are uncertain."),
}


def event_label(category):
    return {"m_and_a": "M&A", "bonus_split": "Corporate action", "agm_egm": "AGM / EGM"}.get(category, category.replace("_", " "))


def intelligence(ann):
    why, implication = IMPLICATIONS.get(ann.category.value, (
        "This disclosure may update assumptions about the holding.",
        "Check the disclosure for changes to your thesis; the portfolio effect is not yet established.",
    ))
    labels = {}
    if ann.category == Category.MANAGEMENT_CHANGE:
        labels = {"outgoing": "Outgoing executive", "incoming": "Incoming executive", "role": "Role", "effective_date": "Effective date", "background": "Verified background"}
    elif ann.category == Category.M_AND_A:
        labels = {"parties": "Parties", "deal_size": "Deal size", "rationale": "Rationale", "approvals": "Approvals"}
    fields = {label: ann.event_details.get(key, "Not disclosed") for key, label in labels.items()}
    if "Verified background" in fields:
        # A synthetic appointment cannot supply a verified biography.
        fields["Verified background"] = "Not verified from an official source" if not ann.has_verified_filing else ann.event_details.get("background", "Not disclosed")
    summary = ann.summary or ann.title
    if ann.is_fixture:
        summary = summary.split("[SYNTHETIC")[0].strip()
    return {"summary": summary, "why": why, "implication": implication, "fields": fields}


def market_signals(prices, rules, reference_date):
    detector = AnomalyDetector(
        price_threshold_pct=rules.price_threshold_pct,
        volume_multiple_threshold=rules.volume_multiple_threshold,
        trigger_mode=rules.trigger_mode,
    )
    # Historical views must not leak later price bars.
    return detector.scan_universe({t: [b for b in bars if b.date <= reference_date] for t, bars in prices.items()
                                  if rules.monitored_tickers is None or t in rules.monitored_tickers}, anomalies_only=False)


def build_monitoring(announcements, prices, rules, acknowledged, reference_date, window="24h", demo_mode=True):
    svc = AnnouncementService()
    events = svc.score_and_rank(svc.deduplicate(svc.filter_by_window(announcements, window, reference_date)), reference_date)
    signals = market_signals(prices, rules, reference_date)
    alerts = []
    event_alerts = {}
    event_info = {}
    results = ResultsService(demo_mode=demo_mode)
    for ann in events:
        event_id = svc.canonical_id(ann)
        info = intelligence(ann)
        summary = results.get_summary_by_ticker(ann.ticker)
        # Never attach another event's quarterly results merely by matching ticker.
        info["results"] = summary if ann.category == Category.RESULTS and summary and summary.filing_id == ann.id else None
        event_info[event_id] = info
        if ann.category in rules.event_types and (rules.monitored_tickers is None or ann.ticker in rules.monitored_tickers):
            alert_id = "alert-" + event_id
            event_alerts[event_id] = alert_id
            alerts.append({"id": alert_id, "event_id": event_id, "ann": ann, "signal": None,
                "ticker": ann.ticker, "company": ann.company_name, "event_type": event_label(ann.category.value),
                "title": ann.title.removeprefix("[DEMO] "), "date": ann.published_at, "severity": ann.priority.value,
                "reason": f"Subscribed event type: {event_label(ann.category.value)}; filing dated {ann.published_at}.",
                "why": info["why"], "implication": info["implication"], "score": ann.priority_score})
    signal_alerts = {}
    # Rule revisions create a fresh market evaluation; acknowledgement does not hide new triggers.
    market_rule_key = json.dumps([rules.price_threshold_pct, rules.volume_multiple_threshold, rules.trigger_mode])
    for signal in signals:
        if not signal.triggered:
            continue
        key = f"{signal.ticker}|{signal.date}|{signal.close}|{signal.volume}|{market_rule_key}"
        alert_id = "signal-" + hashlib.sha256(key.encode()).hexdigest()[:20]
        signal_alerts[signal.ticker] = alert_id
        alerts.append({"id": alert_id, "event_id": None, "ann": None, "signal": signal,
            "ticker": signal.ticker, "company": signal.company_name, "event_type": "Price / volume",
            "title": "EOD threshold crossed", "date": signal.date, "severity": signal.severity.value,
            "reason": signal.explanation.split("Monitoring signal only")[0].strip() + f" Rule: {rules.trigger_mode}.",
            "why": "An unusual session warrants a check of disclosures and liquidity.",
            "implication": "Review the holding's exposure; the cause and persistence of the move are unknown.",
            "score": 90 if signal.severity.value == "high" else 60})
    order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (order[a["severity"]], -a["score"], a["ticker"], a["id"]))
    for alert in alerts:
        alert["acknowledged"] = bool(acknowledged.get(alert["id"]))
        alert["related"] = [{"id": a["id"], "label": a["event_type"]} for a in alerts
                            if a["ticker"] == alert["ticker"] and a["date"] == alert["date"] and a["id"] != alert["id"]]
    unread = [a for a in alerts if not a["acknowledged"]]
    holdings = sorted({a["ticker"] for a in unread})
    pulse = f"{len(events)} corporate events and {len(signal_alerts)} triggered market signals in this snapshot; {len(unread)} alerts need review across {len(holdings)} holdings."
    if unread:
        first = unread[0]
        pulse += f" Start with {first['ticker']}: {first['event_type']} ({first['severity']} severity)."
    else:
        pulse += " No unacknowledged alerts require attention under your saved rules."
    return {"queue": alerts, "unread_count": len(unread), "affected_holdings": holdings, "pulse": pulse,
            "events": events, "event_info": event_info, "event_alerts": event_alerts,
            "signals": signals, "signal_alerts": signal_alerts, "rules": rules,
            "reference_date": reference_date, "window": window}
