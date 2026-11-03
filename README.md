# FINN — Financial Investment Intelligence Agent

A mobile-first financial investment intelligence prototype for Indian listed companies, built for the ENAM AI Engineer Build Challenge.

## Web Application Overview

FINN is designed as a quiet, high-signal financial cockpit. The interface is mobile-first, responsive, and adheres to a restrained dark financial terminal theme:

- **Today (`/today`):** Investor digest with selectable time windows (**24h**, **3d**, **7d**, **All Filings**). Features:
  - **Priority Scoring & Normalization:** Deterministic ranking based on announcement materiality (results, M&A, fund raises ranked highest) with clear "Why it matters" rationales.
  - **Price & Volume Anomaly Alerts:** Flags unusual single-day close-to-close price jumps (default ±3.0%) and volume surges relative to a 20-session baseline (default 2.0× mean).
  - **Extracted Quarterly Results:** Structured Revenue, EBITDA, and PAT comparison table (current quarter vs QoQ and YoY growth rates) embedded directly on results cards.
  - **Routine Filings Drawer:** Collapsible section grouping routine compliance filings (AGM notices, paperwork) to maintain a clean signal-first feed.
- **Research (`/research`):** On-demand company research workspace (Pull workflow). Features:
  - **Interactive Research Selection:** Quick-access pills for research universe tickers (`INFY`, `RELIANCE`, `TCS`, `HDFCBANK`, `TATAMOTORS`) and ticker search.
  - **Five Structured Brief Sections:**
    1. Company Overview & Operating Segments
    2. Financial Trajectory & Margins
    3. Cash & Balance Sheet Quality
    4. Management Outlook & Strategic Guidance
    5. Risks & Data Coverage Limitations
  - **Mandatory Citation Grounding:** Every factual claim includes a confidence rating (`HIGH`, `MEDIUM`, `LOW`) and verifiable evidence chips (`[ev-...]`). Claims lacking evidence are explicitly flagged.
  - **Traceable Primary Source Evidence Drawer:** Full excerpt view displaying exact quotes, publisher, document type, period, section reference, and direct link to the primary source document.
  - **Citation Jump & Highlight:** Clicking any citation chip smoothly scrolls to and highlights the cited source passage.
- **Portfolio (`/portfolio`):** Complete listing of the 19 tracked NSE/BSE listed companies across sectors, with synthetic EOD price snapshots and client-side instant search filtering.
- **Settings (`/settings`):** Threshold configurations (volume anomaly, price change triggers, digest window), demo mode verification, and system environment counts.

All fixture data is explicitly tagged as synthetic for demonstration purposes.

---

## Primary-Source Retrieval, Synthesis & Citation Validation (Phase 5)

FINN enforces a strict **primary-sources-only** standard for research evidence:

- **Centralized Domain Allowlist:** Only official investor relations portals for research companies (`*.ril.com`, `*.hdfcbank.com`, `*.infosys.com`, `*.tcs.com`, `*.tatamotors.com`) and official stock exchanges (`*.bseindia.com`, `*.nseindia.com`) can be requested. Broker research, news aggregators, and blog posts are prohibited.
- **SSRF & Host Protections:** Complete rejection of loopback, private, link-local, and reserved IP ranges (both directly and after DNS resolution), non-HTTP(S) schemes, and embedded URL credentials. Suffix and lookalike domain attacks (e.g. `ril.com.attacker.com`) are rejected via strict domain boundary matching.
- **Safe Manual Redirects:** Automatic redirect following is disabled; each redirect hop is manually inspected and validated against the allowlist and SSRF checks before requesting (max 3 hops).
- **Streaming Size & Timeouts:** Strict 10-second timeout and 10 MB maximum streaming response limit to guard against oversized files and memory exhaustion.
- **Document Processing (`DocumentProcessor`):**
  - **HTML:** Strips non-content markup (`<script>`, `<style>`, `<nav>`, `<footer>`) using `BeautifulSoup`, extracts headings as section references (`page_or_section`), and chunks clean paragraphs (page number `None`).
  - **PDF:** Extracts text page-by-page using `pypdf`, preserving exact 1-indexed page references (`Page 1`, `Page 2`).
  - **Deterministic Evidence IDs:** Generates stable SHA-256 fingerprints (`ev-{hash[:12]}`) from URL, period, section, and normalized passage text.
  - **Deduplication:** Identical passages within a document are deduplicated while preserving distinct passages across different reporting periods or sources.
- **Citation Validation Engine (`app/services/citation_validator.py`):**
  - Standalone validation engine enforcing non-empty excerpts, target ticker scoping, and cross-company contamination rejection.
  - Inspects key numbers and percentages in claim text against evidence passages to detect numerical hallucinations, automatically downgrading confidence to `Confidence.LOW`.
  - Flags unsupported statements with `[UNVERIFIED IN RETRIEVED SOURCES]`.
  - Formally distinguishes claim types: reported facts, management statements, calculations, and interpretations.
  - Transparently reports lexical/numerical verification boundaries.
- **Interactive Evidence Inspector & UI States (`templates/research.html`):**
  - Interactive Modal Evidence Inspector showing all 8 core fields: source title, publisher, URL, reporting period, page/section reference, excerpt, retrieval status, and fixture/live provenance.
  - Robust UI states: Loading indicator during retrieval/synthesis, Partial-Coverage banner for incomplete filings, Empty state with company selectors, and Error state on unrecognized tickers.
- **Pluggable Model Adapters (`BaseLLMAdapter`):**
  - `DeterministicExtractiveAdapter`: 100% offline, zero-cost rule-based extractor producing complete 5-section briefs strictly from primary evidence.
  - `APIModelAdapter`: OpenAI-compatible structured JSON endpoint caller with automatic fallback to deterministic extraction on network timeout or provider errors.
- **ResearchStore Abstraction (`ResearchStore`):** In-memory storage for primary documents, extracted evidence records, and research briefs. Note: this store is ephemeral and resets on application restart.

---

## API Endpoints

| Endpoint | Method | Description | Example Query |
|---|---|---|---|
| `/api/digest` | GET | Prioritised announcement digest with window filtering | `?window=24h` or `?window=7d` |
| `/api/alerts` | GET | Price and volume anomaly alerts across the portfolio | `?price_threshold=3.0&volume_threshold=2.0` |
| `/api/results` | GET | All available structured quarterly results summaries | `/api/results` |
| `/api/results/{ticker}` | GET | Extracted quarterly metrics for a specific ticker | `/api/results/RELIANCE` |
| `/api/research/companies` | GET | List available companies in research universe | `/api/research/companies` |
| `/api/research/{ticker}` | POST | Generate or refresh evidence-grounded research brief | `POST /api/research/INFY?force_refresh=true` |
| `/api/research/{ticker}` | GET | Retrieve latest research brief by ticker or ID | `/api/research/INFY` or `/api/research/res-1234abcd` |
| `/api/research/{ticker}/evidence` | GET | Retrieve supporting primary source evidence passages | `/api/research/RELIANCE/evidence` |
| `/api/portfolio` | GET | Full portfolio universe (19 companies) | `/api/portfolio` |
| `/api/announcements` | GET | All raw corporate announcement fixtures | `/api/announcements` |
| `/health` | GET | System health check and mode status | `/health` |

---

## Quick Start

### 1. Prerequisites
- Python 3.11+ (Python 3.13 tested)

### 2. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration runs in deterministic **demo mode** (`DEMO_MODE=true`), requiring no external API keys or credentials.

### 4. Running the Web Application
Start the FastAPI server:
```bash
uvicorn main:app --reload
```
Open your browser to:
- **Web App Home:** `http://localhost:8000/` (redirects to `/today`)
- **Today Screen (with 24h/3d/7d filters):** `http://localhost:8000/today`
- **Portfolio Screen:** `http://localhost:8000/portfolio`
- **Research Screen (with interactive briefs):** `http://localhost:8000/research`
- **Settings Screen:** `http://localhost:8000/settings`
- **API Documentation (Swagger UI):** `http://localhost:8000/docs`

### 5. Running the Automated Tests
Run the complete test suite (203 tests):
```bash
pytest
```
Or with verbose output:
```bash
pytest -v
```
