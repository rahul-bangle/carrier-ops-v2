# Career-Ops: Industrial Sourcing Engine (V5) - Master Context

> **CRITICAL RULE FOR GEMINI CLI:** Read this section immediately upon starting a new session in this workspace. This contains the absolute source of truth for the sourcing architecture, overriding default behaviors.

## 1. The Architecture (The "Sovereign" Engine)
We have completely moved away from paid APIs (Apify) and restrictive aggregators (LinkedIn, Naukri) due to "ghost jobs" and high ban risks. 
Our entire pipeline is 100% free, locally executed, and highly stealthy.

*   **Scraping Engine:** `scrapling` (Python). We do NOT use Playwright (too heavy) or requests (blocked).
*   **Target:** ATS JSON APIs ONLY (`api.ashbyhq.com`, `boards-api.greenhouse.io`).
*   **Database:** `data/targets.json` contains 10,000+ API endpoints derived from YC open-source lists.
*   **AI Filter:** Local Windows Proxy Endpoint (`http://172.24.192.1:8317/v1` running `gemini-3.1-flash-lite-preview`). **Zero Cloud Costs.**
*   **Final Output:** Synced to Google Sheets via Composio (`bulk-push.mjs` or CSV fallback).

## 2. Key Operational Rules & Decisions
*   **No "Jack of all Trades" Clusters:** Resumes are clustered by "Work Mode" (0-to-1 Builder, Scale & Ops, Platform) with dynamic "Domain Pulses" (Fintech, SaaS) injected atomically.
*   **Atomic Tailoring:** We do NOT rewrite the whole CV. We use a static `cv-alpha.md` and only inject a tailored 2-line summary and 5 keywords per job.
*   **Strict AI Filtering:** The prompt MUST strictly reject any non-PM roles (Sales, SDR, Engineer, Marketing). Only pure Product Management roles evaluated >7/10 are kept.

## 3. The 7-Day Hybrid Pacing Strategy (The Quota System)
We do not scan 10,000 endpoints at once. We use `industrial_scrape_v5.py` which implements a stateful cycle stored in `data/scraper_state.json`.

*   **The Chunk:** We scan 500 endpoints per day.
*   **The Quota:** The script stops evaluating via AI once it hits **50 Gold Leads** for the day to save compute.
*   **The Refresh (Day 8+):** We scan 500 *new* endpoints AND simultaneously rescan 500 *old* endpoints (from 7 days ago) to catch weekly job postings.

## 4. Troubleshooting & Workarounds
*   **Scrapling Error (`Response object has no attribute status_code`):** Scrapling uses `.status` (not `.status_code`).
*   **Google Dorking Rate Limits:** `HTTP 429` triggered instantly on Google/DuckDuckGo. We abandoned Dorking for discovery.
*   **Discovery Workaround:** We built `build_target_db.py` to pull static company lists from `yc-oss/api` on GitHub, ensuring we hit ATS APIs directly instead of searching Google.

## 5. Daily Execution Protocol (For Gemini)
When the user asks you to "Run the Daily Pipeline" or "Fetch Jobs", execute these exact steps:
1.  Run `python industrial_scrape_v8_supabase.py`.
2.  Wait for the results to sync to Supabase.
3.  Report the number of high-signal leads found. Do NOT ask for permission to run the script, just do it.
