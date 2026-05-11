# Career-Ops — AI Job Search Pipeline (Gemini CLI)

> This file is auto-loaded by the Gemini CLI as persistent context.
> It is the Gemini equivalent of CLAUDE.md.
> All slash commands are defined in `.gemini/commands/`.

## What is career-ops

AI-powered job search automation: pipeline tracking, offer evaluation, CV generation, portal scanning, batch processing. Originally built on Claude Code, now fully supported on Gemini CLI and OpenCode.

## Data Contract (CRITICAL)

**User Layer (NEVER auto-updated — your personalizations live here):**
- `cv.md`, `config/profile.yml`, `modes/_profile.md`, `article-digest.md`, `portals.yml`
- `data/*`, `reports/*`, `output/*`, `interview-prep/*`

**System Layer (auto-updatable — do NOT put user data here):**
- `modes/_shared.md`, `modes/oferta.md`, all other modes
- `GEMINI.md`, `CLAUDE.md`, `*.mjs` scripts, `templates/*`, `batch/*`

**THE RULE:** When the user asks to customize anything (archetypes, narrative, negotiation scripts, proof points, location policy, comp targets), ALWAYS write to `modes/_profile.md` or `config/profile.yml`. NEVER edit `modes/_shared.md` for user-specific content.

## Update Check

On the first message of each session, run the update checker silently:

```bash
node update-system.mjs check
```

Parse the JSON output:
- `{"status": "update-available", ...}` → tell the user an update is available and ask if they want to apply it (`node update-system.mjs apply`)
- `{"status": "up-to-date"}` → say nothing
- `{"status": "dismissed"}` or `{"status": "offline"}` → say nothing

## Gemini CLI Commands

When using [Gemini CLI](https://github.com/google-gemini/gemini-cli), the following slash commands are available (defined in `.gemini/commands/`):

| Command | Claude Code Equivalent | Description |
|---------|------------------------|-------------|
| `/career-ops` | `/career-ops` | Show menu or evaluate JD |
| `/career-ops-pipeline` | `/career-ops pipeline` | Process pending URLs from inbox |
| `/career-ops-evaluate` | `/career-ops oferta` | Evaluate job offer (A-G scoring) |
| `/career-ops-compare` | `/career-ops ofertas` | Compare and rank multiple offers |
| `/career-ops-contact` | `/career-ops contacto` | LinkedIn outreach |
| `/career-ops-deep` | `/career-ops deep` | Deep company research |
| `/career-ops-pdf` | `/career-ops pdf` | Generate ATS-optimized CV |
| `/career-ops-training` | `/career-ops training` | Evaluate course/cert |
| `/career-ops-project` | `/career-ops project` | Evaluate portfolio project |
| `/career-ops-tracker` | `/career-ops tracker` | Application status overview |
| `/career-ops-apply` | `/career-ops apply` | Live application assistant |
| `/career-ops-scan` | `/career-ops scan` | Scan portals for new offers |
| `/career-ops-batch` | `/career-ops batch` | Batch processing |
| `/career-ops-patterns` | `/career-ops patterns` | Analyze rejection patterns |
| `/career-ops-followup` | `/career-ops followup` | Follow-up cadence tracker |

**All commands share the same evaluation logic** in `modes/*.md`. The `modes/` files are shared between Claude Code, OpenCode, and Gemini CLI.

## First Run — Onboarding

**Before doing anything else, check if the system is set up.** Run silently every session:

1. Does `cv.md` exist?
2. Does `config/profile.yml` exist (not just profile.example.yml)?
3. Does `modes/_profile.md` exist (not just _profile.template.md)?
4. Does `portals.yml` exist (not just templates/portals.example.yml)?

If `modes/_profile.md` is missing, copy from `modes/_profile.template.md` silently.

**If ANY of these is missing, enter onboarding mode.** Guide the user step by step — ask for their CV, fill the profile, set up the tracker. See `CLAUDE.md` for the full onboarding script (identical logic applies here).

## Skill Modes

| If the user... | Mode to load |
|----------------|-------------|
| Pastes JD or URL | auto-pipeline → read `modes/_shared.md` + `modes/auto-pipeline.md` |
| Asks to evaluate offer | read `modes/_shared.md` + `modes/oferta.md` |
| Asks to compare offers | read `modes/_shared.md` + `modes/ofertas.md` |
| Wants LinkedIn outreach | read `modes/_shared.md` + `modes/contacto.md` |
| Asks for company research | read `modes/deep.md` |
| Preps for interview | read `modes/interview-prep.md` |
| Wants to generate CV/PDF | read `modes/_shared.md` + `modes/pdf.md` |
| Evaluates a course/cert | read `modes/training.md` |
| Evaluates portfolio project | read `modes/project.md` |
| Asks about application status | read `modes/tracker.md` |
| Fills out application form | read `modes/_shared.md` + `modes/apply.md` |
| Searches for new offers | read `modes/_shared.md` + `modes/scan.md` |
| Processes pending URLs | read `modes/_shared.md` + `modes/pipeline.md` |
| Batch processes offers | read `modes/_shared.md` + `modes/batch.md` |
| Asks about rejection patterns | read `modes/patterns.md` |
| Asks about follow-ups | read `modes/followup.md` |

## Main Files

| File | Function |
|------|----------|
| `data/applications.md` | Application tracker |
| `data/pipeline.md` | Inbox of pending URLs |
| `portals.yml` | Query and company config |
| `templates/cv-template.html` | HTML template for CVs |
| `generate-pdf.mjs` | Playwright: HTML to PDF |
| `article-digest.md` | Proof points from portfolio (optional) |
| `interview-prep/story-bank.md` | Accumulated STAR+R stories |
| `gemini-eval.mjs` | Standalone Gemini API evaluator (no CLI required) |

## Ethical Use — CRITICAL

- **NEVER submit an application without the user reviewing it first.** Fill forms, draft answers, generate PDFs — but always STOP before clicking Submit. The user makes the final call.
- **Strongly discourage low-fit applications.** If a score is below 4.0/5, explicitly recommend against applying.
- **Quality over speed.** A well-targeted application to 5 companies beats a generic blast to 50.

## Pipeline Integrity

1. **NEVER edit applications.md to ADD new entries** — Write TSV in `batch/tracker-additions/` and `node merge-tracker.mjs` handles the merge.
2. Run `node verify-pipeline.mjs` to check health.
3. All reports MUST include `**URL:**` and `**Legitimacy:**` in the header.
4. All statuses MUST be canonical (see `templates/states.yml`).



### Memory.md


    1 ## Career-Ops: Industrial Sourcing Engine (V5) - Master Context
    2
    3 > **CRITICAL RULE FOR GEMINI CLI:** Read this section immediately upon starting a new session in this workspace. This contains
      the absolute source of truth for the sourcing architecture, overriding default behaviors.
    4
    5 ### 1. The Architecture (The "Sovereign" Engine)
    6 We have completely moved away from paid APIs (Apify) and restrictive aggregators (LinkedIn, Naukri) due to "ghost jobs" and
      high ban risks. 
    7 Our entire pipeline is 100% free, locally executed, and highly stealthy.
    8
    9 *   **Scraping Engine:** `scrapling` (Python). We do NOT use Playwright (too heavy) or requests (blocked).
   10 *   **Target:** ATS JSON APIs ONLY (`api.ashbyhq.com`, `boards-api.greenhouse.io`).
   11 *   **Database:** `data/targets.json` contains 10,000+ API endpoints derived from YC open-source lists.
   12 *   **AI Filter:** Local Windows Proxy Endpoint (`http://172.24.192.1:8317/v1` running `gemini-3.1-flash-lite-preview`).
      **Zero Cloud Costs.**
   13 *   **Final Output:** Synced to Google Sheets via Composio (`bulk-push.mjs` or CSV fallback).
   14
   15 ### 2. Key Operational Rules & Decisions
   16 *   **No "Jack of all Trades" Clusters:** Resumes are clustered by "Work Mode" (0-to-1 Builder, Scale & Ops, Platform) with
      dynamic "Domain Pulses" (Fintech, SaaS) injected atomically.
   17 *   **Atomic Tailoring:** We do NOT rewrite the whole CV. We use a static `cv-alpha.md` and only inject a tailored 2-line
      summary and 5 keywords per job.
   18 *   **Strict AI Filtering:** The prompt MUST strictly reject any non-PM roles (Sales, SDR, Engineer, Marketing). Only pure
      Product Management roles evaluated >7/10 are kept.
   19
   20 ### 3. The 7-Day Hybrid Pacing Strategy (The Quota System)
   21 We do not scan 10,000 endpoints at once. We use `industrial_scrape_v5.py` which implements a stateful cycle stored in
      `data/scraper_state.json`.
   22
   23 *   **The Chunk:** We scan 500 endpoints per day.
   24 *   **The Quota:** The script stops evaluating via AI once it hits **50 Gold Leads** for the day to save compute.
   25 *   **The Refresh (Day 8+):** We scan 500 *new* endpoints AND simultaneously rescan 500 *old* endpoints (from 7 days ago) to
      catch weekly job postings.
   26
   27 ### 4. Troubleshooting & Workarounds
   28 *   **Scrapling Error (`Response object has no attribute status_code`):** Scrapling uses `.status` (not `.status_code`).
   29 *   **Google Dorking Rate Limits:** `HTTP 429` triggered instantly on Google/DuckDuckGo. We abandoned Dorking for discovery.
   30 *   **Discovery Workaround:** We built `build_target_db.py` to pull static company lists from `yc-oss/api` on GitHub, ensuring
      we hit ATS APIs directly instead of searching Google.
   31
   32 ### 5. Daily Execution Protocol (For Gemini)
   33 When the user asks you to "Run the Daily Pipeline" or "Fetch Jobs", execute these exact steps:
   34 1.  Run `python industrial_scrape_v5.py`.
   35 2.  Wait for the CSV (`industrial_leads_YYYYMMDD.csv`) to be generated.
   36 3.  *(If Composio is active)* Read the CSV and use the Composio Google Sheets tool to append the rows to the user's tracker
      (`1oA81zi_TIVwzSH61YGoeRcuVYSQ6L_Sjg0rtVUrbuUQ`).
   37 4.  Report the number of high-signal leads found. Do NOT ask for permission to run the script, just do it.

       1 # Career-Ops: Industrial Sourcing Engine (V5) - Master Context
       2
       3 > **CRITICAL RULE FOR GEMINI CLI:** Read this section immediately upon starting a new session in
         this workspace. This contains the absolute source of truth for the sourcing architecture, overriding
         default behaviors.
       4
       5 ## 1. The Architecture (The "Sovereign" Engine)
       6 We have completely moved away from paid APIs (Apify) and restrictive aggregators (LinkedIn, Naukri)
         due to "ghost jobs" and high ban risks. 
       7 Our entire pipeline is 100% free, locally executed, and highly stealthy.
       8
       9 *   **Scraping Engine:** `scrapling` (Python). We do NOT use Playwright (too heavy) or requests
         (blocked).
      10 *   **Target:** ATS JSON APIs ONLY (`api.ashbyhq.com`, `boards-api.greenhouse.io`).
      11 *   **Database:** `data/targets.json` contains 10,000+ API endpoints derived from YC open-source
         lists.
      12 *   **AI Filter:** Local Windows Proxy Endpoint (`http://172.24.192.1:8317/v1` running
         `gemini-3.1-flash-lite-preview`). **Zero Cloud Costs.**
      13 *   **Final Output:** Synced to Google Sheets via Composio (`bulk-push.mjs` or CSV fallback).
      14
      15 ## 2. Key Operational Rules & Decisions
      16 *   **No "Jack of all Trades" Clusters:** Resumes are clustered by "Work Mode" (0-to-1 Builder,
         Scale & Ops, Platform) with dynamic "Domain Pulses" (Fintech, SaaS) injected atomically.
      17 *   **Atomic Tailoring:** We do NOT rewrite the whole CV. We use a static `cv-alpha.md` and only
         inject a tailored 2-line summary and 5 keywords per job.
      18 *   **Strict AI Filtering:** The prompt MUST strictly reject any non-PM roles (Sales, SDR, Engineer,
         Marketing). Only pure Product Management roles evaluated >7/10 are kept.
      19
      20 ## 3. The 7-Day Hybrid Pacing Strategy (The Quota System)
      21 We do not scan 10,000 endpoints at once. We use `industrial_scrape_v5.py` which implements a
         stateful cycle stored in `data/scraper_state.json`.
      22
      23 *   **The Chunk:** We scan 500 endpoints per day.
      24 *   **The Quota:** The script stops evaluating via AI once it hits **50 Gold Leads** for the day to
         save compute.
      25 *   **The Refresh (Day 8+):** We scan 500 *new* endpoints AND simultaneously rescan 500 *old*
         endpoints (from 7 days ago) to catch weekly job postings.
      26
      27 ## 4. Troubleshooting & Workarounds
      28 *   **Scrapling Error (`Response object has no attribute status_code`):** Scrapling uses `.status`
         (not `.status_code`).
      29 *   **Google Dorking Rate Limits:** `HTTP 429` triggered instantly on Google/DuckDuckGo. We
         abandoned Dorking for discovery.
      30 *   **Discovery Workaround:** We built `build_target_db.py` to pull static company lists from
         `yc-oss/api` on GitHub, ensuring we hit ATS APIs directly instead of searching Google.
      31
      32 ## 5. Daily Execution Protocol (For Gemini)
      33 When the user asks you to "Run the Daily Pipeline" or "Fetch Jobs", execute these exact steps:
      34 1.  Run `python industrial_scrape_v8_supabase.py`.
      35 2.  Wait for the results to sync to Supabase.
      36 3.  Report the number of high-signal leads found. Do NOT ask for permission to run the script, just
         do it.

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
