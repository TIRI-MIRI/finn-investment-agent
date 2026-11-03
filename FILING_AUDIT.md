# Filing provenance audit — 2026-11-03

## Today

All ten announcement records in `app/data/announcements.py` are explicitly synthetic. On inspection, all already had `source_url=None`. No official filing substantiates their exact date and content. Keep the non-link label “Synthetic demo announcement — no external filing.” for both material and routine records.

| Record | Company | Synthetic subject |
|---|---|---|
| ann-001 | RELIANCE | Results |
| ann-004 | TATAMOTORS | Battery JV |
| ann-002 | HDFCBANK | Dividend |
| ann-005 | INFY | Results |
| ann-010 | SBIN | AGM |
| ann-009 | ITC | Bonus |
| ann-008 | LT | Hydrogen capex |
| ann-006 | ICICIBANK | QIP |
| ann-007 | SUNPHARMA | Rating |
| ann-003 | TCS | CTO appointment |

User-reported legacy URLs (not present in current fixture data):

- https://www.tatamotors.com/press/ev-battery-jv-2025 — reported 403; availability unconfirmed, synthetic claim.
- https://www.ril.com/investor-relations/results/q3-fy2025 — reported 404; synthetic claim.
- https://www.infosys.com/investors/reports/q3-fy2025 — reported 404; synthetic claim.
- https://www.hdfcbank.com/investor/dividend/2025 — reported 403; availability unconfirmed, synthetic claim.

403 is not evidence that a document does not exist. No replacement URL was invented for these records.

## Research — complete external URL inventory in app/data

Five external URLs were found, all in `research_fixtures.py`. Each official PDF was opened and its title, date and the retained summary content checked. Earlier hand-authored text was not a faithful verbatim extract: it contained unsupported details and mismatched values. Replaced it with bounded, checked paraphrases, explicitly labeled as such. These are stored summaries, not live retrievals. No Research PDF is substituted for a synthetic Today event.

### RELIANCE

- Official document: [Consolidated results for quarter ended 31st December, 2024](https://www.ril.com/sites/default/files/2025-01/16012025-Media_Release-RIL_Q3_FY2024-25Financial_and_Operational_Performance.pdf)
- Publication date: 2025-01-16
- Verification: Reviewed 2026-11-03: 2025-01-16; PDF page 1, consolidated financial highlights. PAT includes the share of profit/loss of associates and joint ventures.

### INFY

- Official document: [Fact Sheet — Consolidated Financial Data — Third Quarter, Fiscal 2025](https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q3/documents/fact-sheet.pdf)
- Publication date: 2025-01-16
- Verification: Reviewed 2026-11-03: 2025-01-16 release date confirmed on official Q3 results index; PDF pages 1 and 4, IFRS financial data.

### TCS

- Official document: [TCS Financial Results — Quarter III Ended FY 2024-25](https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2024-25/q3/Presentations/Q3%202024-25%20Fact%20Sheet.pdf)
- Publication date: 2025-01-09
- Verification: Reviewed 2026-11-03: 2025-01-09 on PDF cover; page 20 consolidated Ind AS income statement.

### HDFCBANK

- Official document: [HDFC Bank Limited — Financial Results (Indian GAAP) for the Quarter and Nine Months Ended December 31, 2024](https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/press-release/2025/q1-jan-mar/january/press-release-december-2024.pdf)
- Publication date: 2025-01-22
- Verification: Reviewed 2026-11-03: 2025-01-22 board approval on PDF page 1; consolidated results distinguished from standalone results.

### TATAMOTORS

- Official document: [Tata Motors Group Results Q3 FY25](https://www.tatamotors.com/wp-content/uploads/2025/01/Q3FY25-Results-Press-Release.pdf)
- Publication date: 2025-01-29
- Verification: Reviewed 2026-11-03: 2025-01-29 on PDF page 1; consolidated financial highlights. Values retain source rounding.

Infosys publication date also checked against the [official Q3 index](https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q3.html), which links the fact sheet and states January 16, 2025.

Removed unverified segment, balance-sheet, strategic and guidance claims instead of attaching citations that did not substantiate them. Corrected Infosys sequential margin comparison to 21.3% versus 21.1%; TCS net profit to the explicitly identified Ind AS value; and Reliance PAT basis to include associates/JVs.

## Regression controls

Official-source links require explicit review metadata, a non-synthetic primary record, and a safe HTTPS URL. The same gate controls Research inspector URL data and badges and both Today sections. Non-synthetic records without review show an unverified label. Successful HTTP retrieval or an official-looking domain is insufficient.

`tests/reviewed_filings.json` locks the entire reviewed Research records (including exact URLs, dates, titles and content). Changes require source re-review and deliberate snapshot updates. Tests inject synthetic and unreviewed URLs into both page templates, verify the absence of links and official badges, and exercise the positive reviewed path. Network checks are intentionally separate from deterministic regressions.

## Validation

Full suite: `python -m pytest -q` using installed Python 3.13 — **219 passed, 1 warning** (Starlette/httpx deprecation), 2.35 seconds. Sandbox execution blocked in Windows asyncio local socket-pair creation; the approved unsandboxed run completed. No commits, pushes or deployments.
