# FINN — ENAM AI Engineer Build Challenge
## Step-by-step implementation plan for a VS Code coding agent

> Purpose: Build a mobile-first, working prototype for the ENAM Holdings AI Engineer Build Challenge.
> Treat the two supplied PDFs as the source of truth. This file is designed to be pasted into a repository as `BUILD_PLAN.md` and used by a VS Code coding agent (Copilot, Continue, Cline, Cursor, etc.).
> Deadline in the brief: Sunday, November 1, 2026. Prioritise a reliable, demonstrable product over breadth.

---

## 0. Instructions to the coding agent

You are the senior engineer implementing **FINN**, a mobile-first financial investment intelligence prototype for Indian listed companies.

### Non-negotiable rules
1. **Read this entire file before coding.**
2. Build a thin, working product. Prioritise two excellent workflows:
   - **Push:** portfolio digest with announcement prioritisation and price/volume anomaly alerts.
   - **Pull:** on-demand company research grounded only in primary company sources (annual reports, quarterly results, earnings-call transcripts, investor presentations, and exchange filings).
3. Do not claim an integration works until you have run it and verified the output.
4. Never fabricate financial figures, company announcements, source URLs, dates, or citations. If data cannot be fetched, clearly label it unavailable and provide a graceful fallback/demo fixture.
5. Do not use broker notes, news articles, or research reports as evidence for the **Pull** research analysis. The challenge explicitly requires primary sources only for Pull. Push-side professional-background enrichment for a management appointee is permitted, but optional.
6. Keep secrets on the server. Never expose API keys in frontend code or commit `.env`.
7. Make the UI responsive and mobile-first. Test at a narrow phone width as well as desktop.
8. Do not overbuild. The challenge says thin-but-working beats broad-but-broken.
9. Keep a `README.md`, `.env.example`, and `BUILD_LOG.md`. The latter should record major choices, tests, failures, trade-offs, and AI-assisted build steps.
10. If the repository already contains code, inspect it before replacing anything. Preserve useful existing work.

### Coding-agent operating procedure
Work in small phases. At the end of each phase:
- list files created/changed;
- run the relevant checks;
- report exact command output or errors;
- fix blocking errors before proceeding;
- update `BUILD_LOG.md`;
- do not silently skip a requirement.

Ask the user only when a decision is genuinely blocking. Otherwise choose sensible, low-cost defaults and document them.

---

## 1. Understand the assignment

### Product
Build **FINN**, a mobile-first financial investment agent with two interaction modes:

- **Push:** The app proactively surfaces what changed and why it matters.
- **Pull:** The user requests research or analysis for an NSE/BSE-listed company.

### Required demo universe
- Select a mock portfolio of **15–20 NSE/BSE-listed companies**, spanning sectors and sizes.
- Select **3–5 additional or overlapping companies** for ad-hoc research.
- Research must generalise to any NSE ticker for which source data is available. Do not hard-code research logic to only the demo companies.

### Data inputs in the brief
1. End-of-day prices and volumes, e.g. Yahoo Finance via `yfinance`; NSE tickers commonly use `.NS`, BSE tickers `.BO`.
2. Corporate announcements/filings from NSE/BSE for portfolio companies.
3. Company primary documents: annual reports, quarterly results, earnings-call transcripts, investor presentations, available through company investor-relations pages or Screener links.

### Push workflow ideas from the brief
- Digest over a selectable window (default last 24 hours).
- Prioritise important announcements and collapse/hide routine paperwork.
- Configurable alerts for material announcement types.
- Configurable unusual-move thresholds, e.g. volume greater than ~2× recent average and price move beyond ±X%.
- For results announcements, show Revenue, EBITDA, PBT and PAT for current quarter vs previous quarter (QoQ) and same quarter last year (YoY), when the source supports it.
- For management changes, an incoming person's professional background can be added as optional enrichment.

### Pull research menu from the brief
Choose the features that can be grounded reliably. Recommended initial set:
1. Business snapshot.
2. Financial snapshot and multi-year trajectory.
3. Balance-sheet/leverage and cash-quality view.
4. Narrative vs numbers / guidance vs delivery.
5. Compact bull vs bear case.

The analysis must be grounded in primary company documents. Cite the document, page/section if known, period, and source URL for each material claim. If the page cannot be verified, say so rather than inventing it.

---

## 2. Recommended MVP and product point of view

### Product concept: “Signal first, evidence one tap away”
Design FINN as a quiet, high-signal investor cockpit rather than a generic chatbot.

### Main navigation
Use a bottom navigation bar on mobile:
- **Today** — prioritised digest, alert cards, portfolio pulse.
- **Research** — ticker search and evidence-backed company brief.
- **Portfolio** — selected companies, recent moves, alert settings.
- **Settings** — thresholds, source status, demo/live mode.

On desktop, use a compact left sidebar or top navigation while keeping the same information architecture.

### The two flows to perfect
**Flow A — Today / Push**
1. User opens Today.
2. Sees the most important items first, with priority and reason.
3. Can filter digest window: 24 hours, 3 days, 7 days, custom if feasible.
4. Can expand a filing to read its summary and open the primary filing.
5. Sees price/volume anomalies with thresholds shown.
6. Routine announcements are grouped in a collapsed “Routine filings” section.

**Flow B — Research / Pull**
1. User enters a valid NSE ticker or company name.
2. App resolves the company and fetches available primary documents.
3. App displays source status and the periods covered.
4. It produces a concise research brief with explicit evidence references.
5. Each claim links back to its source; missing evidence is shown as “Not found in retrieved sources.”
6. The user can inspect source snippets / document excerpts supporting claims.

### Prioritisation rubric
Create a simple transparent score, not an unexplained AI ranking:
- Base score by announcement category.
- Recency boost.
- Portfolio relevance.
- Optional keyword/materiality boost.
- Deduplicate identical filings.
- Keep the score and rationale visible in code and, where useful, the UI.

Suggested initial priorities (tune and document):
- High: results, M&A, fund_raise, management_change, litigation, credit_rating.
- Medium: capex, dividend, pledging, insider_trading, bonus_split, investor_meetings, earnings_call.
- Low/routine: compliance paperwork and unclassified items.
This is a product choice, not a rule mandated by the challenge. Make the mapping configurable.

---

## 3. Tech stack: choose the simplest reliable option

### Default recommendation
Use a **responsive web app** unless an existing repository or user preference makes another option clearly better. A web app is easy to deploy and open on a phone.

Suggested stack:
- Frontend: Next.js + TypeScript + Tailwind CSS.
- UI primitives: a small accessible component set; avoid adding a huge design system.
- Backend: Next.js route handlers or a small Python FastAPI service. Prefer one backend initially to reduce deployment complexity.
- Data validation: Zod (TypeScript) or Pydantic (Python).
- Storage/cache: SQLite for local development or a lightweight hosted database if deployment needs it. If no persistent database is needed for the demo, start with a file-backed/mock-data layer and document the limitation.
- Price data: `yfinance` in a Python service, or a supported equivalent.
- LLM: provider-agnostic adapter. Use a low-cost model for extraction and a stronger model only for synthesis if available. The app must still run in demo mode without an API key.
- Document processing: PDF text extraction, chunking, and source metadata. Do not begin with a complex vector database unless needed.
- Testing: unit tests for calculations/prioritisation and smoke tests for core routes.

If the repository already has a working stack, keep it unless there is a strong reason to change it. Avoid adding Python and Node services simultaneously unless necessary.

### Modes
- **Live mode:** uses configured data sources and model key(s).
- **Demo mode:** uses clearly labelled fixture data, deterministic calculations, and sample source references. Never represent fixtures as current real-world events.
- Display a visible “Demo data” label whenever fixture data is being shown.

---

## 4. Detailed implementation phases

## Phase 1 — Inspect and plan the repository
1. Inspect the current directory, files, package scripts, README, and Git status.
2. Identify the existing framework and determine whether it already runs.
3. Do not overwrite existing code before understanding it.
4. Create or update:
   - `BUILD_PLAN.md` (this file)
   - `BUILD_LOG.md`
   - `README.md`
   - `.env.example`
   - `.gitignore`
5. Write a short architecture note and a task checklist.
6. Run the existing test/build command if available to establish a baseline.

**Acceptance criteria**
- Existing project understood.
- Baseline commands and errors recorded.
- No secrets exposed or committed.

## Phase 2 — Define data contracts and fixtures
Define typed contracts before connecting sources. Suggested shapes:

```ts
type AnnouncementCategory =
  | "results" | "M&A" | "fund_raise" | "management_change"
  | "litigation" | "insider_trading" | "earnings_call"
  | "investor_meetings" | "credit_rating" | "dividend"
  | "bonus_split" | "capex" | "press_release"
  | "postal_ballot" | "agm_egm" | "pledging" | "unclassified";

type SourceEvidence = {
  title: string;
  publisher: string;
  documentType: string;
  period?: string;
  url?: string;
  pageOrSection?: string;
  excerpt?: string;
  retrievedAt?: string;
  isPrimary: boolean;
};

type Announcement = {
  id: string;
  ticker: string;
  companyName: string;
  category: AnnouncementCategory;
  title: string;
  publishedAt: string;
  sourceUrl?: string;
  priority: "high" | "medium" | "low";
  priorityScore: number;
  priorityReason: string;
  summary?: string;
  isFixture: boolean;
};

type PriceBar = {
  ticker: string;
  date: string;
  close: number;
  volume: number;
};

type CompanyResearch = {
  ticker: string;
  companyName: string;
  generatedAt: string;
  sourceMode: "live" | "demo";
  coverage: { documentsFound: number; periods: string[]; warnings: string[] };
  sections: Array<{
    id: string;
    title: string;
    summary: string;
    claims: Array<{
      text: string;
      evidenceIds: string[];
      confidence: "high" | "medium" | "low";
    }>;
  }>;
  evidence: SourceEvidence[];
};
```

Implement schema validation and fixtures for:
- portfolio of 15–20 stocks across sectors;
- several announcement categories and priorities;
- enough daily price/volume observations to test anomaly calculations;
- 3–5 research-company examples with sample primary-document evidence clearly marked as fixtures.

Do not invent real current announcements. Fixture entries must say they are fictional/sample data.

**Acceptance criteria**
- Type checks pass.
- Demo screens render without network access.
- Fixture content is unmistakably labelled.

## Phase 3 — Build the mobile-first UI shell
Implement the navigation and reusable components:
- Today / digest.
- Research / ticker search.
- Portfolio.
- Settings / thresholds.
- Announcement card, priority pill, evidence link, source status, empty/loading/error states.
- Responsive layout with keyboard-accessible controls and readable typography.

Design direction:
- Restrained, premium financial terminal.
- High information density without clutter.
- Strong hierarchy: what happened → why it matters → evidence.
- Avoid generic gradients, excessive rounded cards, fake charts, and decorative AI chat filler.
- Use real charts only when backed by actual or explicitly fixture data.
- Ensure the main action is obvious on a phone.

**Acceptance criteria**
- Works at 360–390 px width.
- Navigation is usable by touch and keyboard.
- No horizontal overflow.
- Loading, error, empty, and demo states exist.

## Phase 4 — Implement Push: digest and alerts
### 4A. Announcement normalisation
Create a source adapter interface for exchange announcements. Each source adapter should return a common `Announcement` structure and retain the original filing URL.

Implement category mapping based on the companion reference:
- `results`: quarterly/annual results, board meetings approving results, results decks, shareholder letters and confirmation notices.
- `M&A`: acquisitions, mergers, demergers, joint ventures, investment in or sale of a subsidiary stake.
- `fund_raise`: rights issues, QIPs, preferential allotments, buybacks, commercial paper and similar fundraising.
- `management_change`: CEO/CFO/MD/director joining, resignation or retirement.
- `litigation`: lawsuits, regulatory orders, fines, warnings, insolvency/restructuring.
- `insider_trading`: promoter/insider buying or selling personal holdings.
- `earnings_call`: investor-call notices, transcripts and recordings.
- `investor_meetings`: one-to-one/group investor meetings and conference attendance.
- `credit_rating`: rating assignment, upgrade, downgrade or reaffirmation.
- `dividend`: cash dividend and record date.
- `bonus_split`: bonus issue or stock split.
- `capex`: new plant/facility/capacity spending.
- `press_release`: general order wins, products, partnerships, rumour clarification not covered elsewhere.
- `postal_ballot`, `agm_egm`, `pledging`, `unclassified`: as defined in the companion reference.

Keep classification deterministic where possible; use an LLM only for ambiguous cases. Store the original title and source URL.

### 4B. Digest
- Default window: last 24 hours.
- Allow selecting a wider window (at minimum 24 hours, 3 days, 7 days).
- Filter to portfolio companies.
- Sort by priority, then recency.
- Show high-priority items first.
- Group low-priority routine paperwork under a collapsible section.
- Add a brief “Why it matters” rationale that is cautious and evidence-based.
- Provide a link to the original filing.

### 4C. Price/volume anomaly alerts
Use end-of-day data. Suggested initial configurable defaults:
- volume alert when today's volume is > 2.0 × average daily volume over the previous 20 trading sessions;
- price alert when absolute daily close-to-close move is > 3.0%.
These defaults are product decisions; users must be able to change them.

Formula:
- `priceChangePct = ((todayClose - previousClose) / previousClose) * 100`
- `volumeRatio = todayVolume / mean(previous 20 sessions' volume)`
- Avoid look-ahead bias: calculate the baseline using only sessions before today.
- Handle missing data, zero volume average, and short history without crashing.
- Explain that an unusual move is a monitoring signal, not a prediction or recommendation.

### 4D. Results announcement summary
If a primary results filing is available, extract Revenue, EBITDA, PBT, PAT for:
- current quarter;
- immediately previous quarter (QoQ comparison);
- same quarter a year earlier (YoY comparison).
Preserve units and consolidated/standalone basis. Never mix bases silently. If a figure is missing, show “Not available in source.” Prefer extracted source values over model-generated guesses.

### 4E. Optional management-change enrichment
Only if time remains: for an incoming senior executive, show a short professional bio from a suitable professional source. Keep this separate from primary-source Pull research. Do not scrape behind login walls or imply a person's profile was verified when it was not.

**Acceptance criteria**
- Digest filtering and ranking are tested.
- Price/volume calculations are unit-tested.
- Filing URLs remain attached to cards.
- Demo/live labels are visible.
- Failures in one source do not take down the entire digest.

## Phase 5 — Implement Pull: primary-source company research
### 5A. Ticker input and source discovery
- Accept NSE ticker and company name; normalise common input forms.
- Resolve to a canonical company/ticker.
- Search for primary sources only: company investor-relations pages, annual reports, quarterly results, earnings-call transcripts, investor presentations, NSE/BSE filings.
- Screener may be used as a convenient index to these primary company documents, but do not use third-party commentary as evidence.
- Preserve source URL, title, period, document type, retrieval time, and whether the source is primary.

If live source discovery is not reliable in the available time, implement a provider interface plus a transparent demo fixture and document which source adapter remains incomplete.

### 5B. Download and parse
- Support PDF text extraction first.
- Store source metadata and text excerpts.
- Chunk documents by heading/page/section; keep page numbers if the parser exposes them.
- Do not send entire large annual reports to an LLM in one request.
- Cache fetched documents and parsed text to reduce cost and latency.
- Add request timeouts, size limits, retries with backoff, and per-source error handling.
- Respect site access constraints and avoid bypassing access controls.

### 5C. Evidence-first synthesis
Use this pipeline:
1. Retrieve primary documents.
2. Extract candidate facts and guidance with their source/page references.
3. Calculate ratios and period comparisons in code where possible.
4. Ask the LLM to synthesise only from retrieved evidence.
5. Validate that each generated claim has at least one evidence ID.
6. Drop or flag unsupported claims.
7. Render citations inline, linked to the source document.

Required prompt policy for the research model:
- Use only supplied primary-source excerpts.
- Do not use prior knowledge or outside sources.
- If evidence is missing, state that it is missing.
- Preserve reporting period, currency, units, and consolidated/standalone basis.
- Separate management claims/guidance from reported results.
- Distinguish facts, calculations, and interpretations.
- Every factual claim must cite an evidence ID.
- Never produce buy/sell recommendations or imply guaranteed returns.

### 5D. MVP research sections
Implement at least three reliable sections:
1. **Business snapshot** — business and segment mix only where source evidence supports it.
2. **Financial trajectory** — reported revenue, EBITDA/PAT and margins across available periods; calculate margins in code.
3. **Cash and balance-sheet quality** — debt, cash flow, working capital, contingent liabilities, auditor qualifications or related-party transactions when disclosed.
4. If time allows, **Guidance vs delivery** — compare explicit management statements from transcripts/presentations with subsequent reported outcomes.
5. If time allows, **Bull vs bear** — concise, balanced, evidence-backed arguments; clearly label interpretations.

**Acceptance criteria**
- Research can be requested for an arbitrary supported ticker, not just fixtures.
- Every material claim has evidence links or is labelled unsupported/missing.
- The system displays document coverage and warnings.
- No secondary commentary enters the Pull synthesis context.

## Phase 6 — Tests and reliability
Add tests for:
- announcement category mapping;
- priority scoring and ordering;
- digest date-window filters;
- price percentage change and volume ratio;
- missing/short price histories;
- ratio/margin calculations;
- evidence ID validation;
- ticker normalisation;
- source errors and demo fallback.

Run:
- formatter/linter;
- type checker;
- unit tests;
- production build;
- a mobile-width smoke test.

Never claim tests passed if they were not run. Record exact results in `BUILD_LOG.md`.

## Phase 7 — Deployment and repository hygiene
- Add clear setup steps to `README.md`.
- Include `.env.example` with variable names and placeholder values only.
- Ensure `.env`, API keys, tokens, downloaded private data, and local databases are ignored where appropriate.
- Add a visible demo mode so reviewers can test without secrets.
- Deploy to a stable URL if time allows. Confirm the deployed URL opens on a phone.
- Confirm GitHub repository contains source code, setup instructions, tests, and a concise architecture explanation.
- Include screenshots only if they reflect the actual running product.
- Add known limitations and next steps to README.

**Acceptance criteria**
- Fresh clone setup works from README.
- Demo works without API credentials.
- Production build succeeds.
- No secrets committed.
- Deployed link is reachable if a deployment is claimed.

## Phase 8 — Final submission package
The challenge asks for:
1. Mobile-first working prototype (deployed link, Expo/TestFlight, or responsive web).
2. GitHub repository.
3. AI build history (coding-agent/LLM conversations or share links/exports).
4. Short covering email describing what was built, key decisions/trade-offs, deliberate omissions, and next steps.

Submission details in the brief:
- Email: `assessment@enam.com`
- Subject: `ENAM - IIT screening - 2027`
- Deadline: Sunday, November 1, 2026

Before submitting:
- [ ] Test deployed app on a phone-sized viewport.
- [ ] Verify every major button and navigation item.
- [ ] Confirm demo fixtures are labelled.
- [ ] Confirm citations point to original documents.
- [ ] Confirm Pull does not use secondary commentary.
- [ ] Run all checks and record results.
- [ ] Push final code to GitHub.
- [ ] Collect AI build history.
- [ ] Write covering note with live links and honest limitations.
- [ ] Send the email before the deadline.

---

## 5. Suggested repository layout

Adapt to the existing project; do not force this structure if the current framework has a better convention.

```text
finn/
├── app/ or src/
│   ├── (routes/pages for Today, Research, Portfolio, Settings)
│   ├── api/                  # source and research endpoints
│   ├── components/            # cards, navigation, evidence display
│   ├── lib/
│   │   ├── announcements/     # adapters, normalisation, classification
│   │   ├── prices/             # price provider, anomaly calculations
│   │   ├── research/           # retrieval, parsing, evidence, synthesis
│   │   ├── scoring/            # priority rules
│   │   └── validation/         # schemas
│   └── ...
├── tests/
├── public/
├── .env.example
├── .gitignore
├── README.md
├── BUILD_PLAN.md
├── BUILD_LOG.md
└── package.json / pyproject.toml
```

---

## 6. Build order if time is short

Use this order; do not start with the hardest integration.

1. **Day 1 / first pass:** inspect repo, build shell, navigation, strong visual design, fixtures, responsive layout.
2. **Second pass:** portfolio digest, categories, priority ranking, expandable filing cards.
3. **Third pass:** deterministic price/volume alerts and threshold settings.
4. **Fourth pass:** research screen with ticker input, evidence model, and 2–3 useful research sections.
5. **Fifth pass:** connect at least one real primary-source provider and one real price provider; keep graceful fallback.
6. **Final pass:** test, polish, deploy, document, collect AI build history and submit.

Because the deadline is close, do not attempt to fully automate every NSE/BSE feed and parse every annual report before you have a working demo.

---

## 7. Finance glossary quick reference

Use the companion reference PDF for the complete glossary. Key terms:
- Revenue: total sales.
- EBITDA: operating-profit proxy before interest, tax, depreciation and amortisation.
- PBT: profit before tax.
- PAT: profit after tax / net profit.
- QoQ: versus immediately previous quarter.
- YoY: versus same quarter one year earlier.
- FCF: cash from operations minus capital spending.
- D/E: total debt divided by shareholders' equity.
- ROCE/ROE: returns on capital employed/equity.
- RPT: related-party transaction.
- Capex: spending on long-term assets.
- Primary sources for Pull: company reports, quarterly results, earnings-call transcripts, investor presentations, and exchange filings.

---

## 8. Coding-agent prompts (run one at a time)

### Prompt 1 — Repository reconnaissance
“Read `BUILD_PLAN.md` fully. Inspect the existing repository, identify the stack, scripts, current state, and risks. Do not modify source files yet. Return a concise plan and run the existing baseline checks if safe. Record findings in `BUILD_LOG.md`.”

### Prompt 2 — Architecture and fixtures
“Implement Phase 2 from `BUILD_PLAN.md` using the existing stack. Define validated data contracts and clearly labelled fictional demo fixtures for a 15–20 company multi-sector portfolio, announcements, price history, and research evidence. Do not invent current events. Run checks and update `BUILD_LOG.md`.”

### Prompt 3 — Mobile-first UI
“Implement Phase 3 from `BUILD_PLAN.md`. Build a polished responsive FINN interface with Today, Research, Portfolio, and Settings. Use demo fixtures and visibly label them. Focus on signal hierarchy and phone usability. Do not add fake functionality. Run a production build and report results.”

### Prompt 4 — Push workflow
“Implement Phase 4 from `BUILD_PLAN.md`: announcement normalisation/classification, digest date filters and prioritisation, collapsible routine items, configurable price/volume anomaly thresholds, and results metrics only where source data exists. Add tests. Keep original source URLs and label demo data. Run tests and update the build log.”

### Prompt 5 — Pull workflow
“Implement Phase 5 from `BUILD_PLAN.md`. Build ticker/company input and an evidence-first research flow grounded exclusively in primary company documents. Every factual claim must reference an evidence item. Implement graceful ‘not found’ states and clearly labelled demo fixtures. Do not use news, broker notes, or model prior knowledge as evidence. Add tests and report source-provider limitations honestly.”

### Prompt 6 — Quality and deployment
“Complete Phases 6–8 from `BUILD_PLAN.md`. Run formatter/linter, type check, tests, and production build. Fix failures where feasible. Review mobile layout and repository secrets. Update README and BUILD_LOG with exact commands/results, deployment status, limitations, and submission checklist. Never claim a check or deployment succeeded unless verified.”

### Prompt 7 — Independent final audit
“Act as a strict reviewer of this repository against `BUILD_PLAN.md` and the ENAM challenge. Do not immediately rewrite code. First produce a requirement-by-requirement audit with evidence from files/tests, identify P0/P1/P2 issues, and then fix only the highest-impact issues. Re-run affected checks and give me the exact remaining gaps.”

---

## 9. Definition of done

The project is ready to submit only when:
- [ ] It launches reliably from documented commands.
- [ ] The main Push workflow works end-to-end in demo mode.
- [ ] The main Pull workflow works end-to-end for at least one supported live company or transparently in demo mode with source-backed fixtures.
- [ ] Mobile layout works without horizontal overflow.
- [ ] Important claims link to evidence.
- [ ] Pull synthesis uses primary sources only.
- [ ] Price/volume calculations and prioritisation have tests.
- [ ] No secret keys are committed.
- [ ] README explains setup, demo/live behaviour, architecture, limitations, and deployment.
- [ ] AI build history is collected.
- [ ] The covering email and links are ready before the deadline.

## 10. Final reminder

The challenge is explicitly evaluating building ability, product instinct, creativity, judgment, architecture, and design. Do not optimise for the number of features. Optimise for a product that quickly answers:

**“What changed, why should I care, and what primary evidence supports that?”**
