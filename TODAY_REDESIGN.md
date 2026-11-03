# Today monitoring redesign

## Audit and baseline

Inspected Today and its shared layout/CSS, announcement fixtures and normalizer,
priority scoring and date filters, anomaly detection, results fixtures/service,
configuration, Settings, existing routes and tests. Before edits: **219 tests
passed**, one Starlette/httpx deprecation warning.

Existing capabilities: deterministic priority scoring, date-window filtering,
basic title-based deduplication, configurable detector constructor arguments,
20-session EOD volume comparison, synthetic quarterly metrics with QoQ/YoY
properties, working Push/Pull APIs, and reviewed-filing provenance gates.

Missing capabilities: a unified monitoring queue, saved user rules, real settings
controls, acknowledgement state, normalized URL/source-document deduplication,
an actionable pulse, structured management/M&A details, and complete quarterly
comparison columns in Today. The settings page previously displayed constants;
Today and the alert API independently used fixed defaults. The results service
is a structured fixture repository, not a live filing ingestion system.

## Implemented

- Portfolio Pulse: two deterministic sentences with event/signal counts,
  outstanding reviews, affected holdings and the first unacknowledged item.
- Triggered Alerts: one queue ordered by severity and materiality, with exact
  rule reasons, dates, thresholds, cautious implications, and native keyboard
  accessible Review Details disclosures. Acknowledge/mark unread persists.
- Corporate Events & Filings: high-priority unsubscribed events expanded,
  medium-priority events condensed, routine events collapsed. Triggered events
  appear only as cross-references to their original alert card.
- Market Signals: compact measurements separated from alerts, links back to
  triggered reviews, and collapsed non-triggered observations. Baselines report
  the actual number of preceding valid sessions. Historical requests exclude
  future price bars.
- Canonical event IDs use ticker, type, date and normalized title, plus source
  document ID when available. Deduplication also recognizes normalized filing
  URLs (ignoring fragments and tracking parameters) and source-document IDs.
  Distinct same-day filings no longer share an automatically generated ID.
- Same-company/same-date observations link to each other explicitly without
  claiming causality. Market rule revisions produce fresh review identities.
- Results show Revenue, EBITDA, PBT and PAT for current, preceding and prior-year
  quarters, QoQ/YoY, units and basis. Missing values remain unavailable; zero is
  displayed as zero. Results attach only to the matching results filing, not
  another event with the same ticker.
- Management details identify missing names/effective dates and unverified
  backgrounds. M&A details distinguish planned investment from consideration,
  and unknown approvals. No biographies, citations or external URLs invented.
- Existing verified-source link safeguards remain in use. Synthetic records
  retain “Synthetic demo announcement — no external filing.” One persistent
  synthetic-data disclosure remains in the header.

## Rules and persistence

Default price threshold: absolute daily move ≥3%. Default volume threshold:
volume ≥2× the preceding 20-session mean (shorter history is explicitly shown).
Threshold comparisons use unrounded measurements. Zero/absent volume baselines
cannot trigger a volume alert. **OR** is the default because either unusual price
movement or unusual volume merits review; **AND** requires both. Announcement
subscriptions operate independently of market threshold logic.

`runtime/monitoring.json` stores validated preferences and acknowledgements.
Writes use a temporary file and atomic replacement, protected by a process lock.
Missing files use defaults; unreadable/invalid files produce a visible warning
and safe defaults. Failed writes report errors. Runtime data is ignored by git.
This storage design targets one local process/user, not multiple workers/users.
No frontend framework or dependencies were added. Per-company overrides were
optional and are not included; rules apply across the tracked universe.

Settings provides Save preferences, Test with demo data, and Load defaults.
Preview evaluates all fixture events at the February 5, 2025 EOD snapshot without
saving. Existing `/api/alerts` query overrides remain available for compatibility;
without overrides it uses the saved backend rules. The full digest remains
independent of subscriptions.

New routes:

| Route | Purpose |
|---|---|
| GET `/api/monitoring` | Combined snapshot, events, signals, queue and pulse |
| GET/PUT `/api/monitoring/settings` | Read/save validated preferences |
| GET `/api/monitoring/defaults` | Backend defaults for the form |
| POST `/api/monitoring/preview` | Non-persistent rule evaluation |
| PUT `/api/monitoring/alerts/{alert_id}` | Acknowledge or mark unread |

This remains an EOD demo evaluated on visits/refreshes, not a real-time push
notification service. Portfolio implications are qualitative review prompts;
the fixture universe does not provide position weights or exposure calculations.

## Verification

Final full suite: **252 passed, 1 warning**, using installed Python 3.13 and
`python -m pytest -q`. The warning is the existing Starlette/httpx deprecation.
The approved execution outside the sandbox avoids Windows local socket setup
blocking FastAPI's test client. All tests use isolated temporary configuration.
Updated the old Today-title assertions to the requested section hierarchy.

33 added regressions cover threshold boundaries and unrounded comparisons,
OR/AND, short/empty baselines, validation, persistence, corrupt files, atomic-write
failure, preview isolation, API rule propagation, subscriptions, acknowledgements,
historical dates, canonical IDs, URL/source-document deduplication, cross-links,
no duplicate full cards, missing facts, no mismatched results, complete financial
comparisons, and explicit missing/zero values. Existing provenance regressions
continue to pass.

Browser checks: desktop and 390px viewport; native keyboard disclosure;
threshold preview; save/reload; changed alert counts on Today; acknowledgement
and reversal; mobile form; mobile financial table scrolling. Fixed the expanded
results card's minimum-width overflow. No frontend console errors were observed.
Saved screenshots: `artifacts/today-desktop.jpg` and `artifacts/today-mobile.jpg`.
Restored default rules and cleared test acknowledgements after UI checks.

No commit, push or deployment performed. Existing Push/Pull routes and Research
functionality are preserved.
