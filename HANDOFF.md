# Brand Radar — Handoff Brief (March 14, 2026)

## Project Overview
**"Premium Intelligence for AI-Native Agencies"** — A dashboard monitoring 50 AI companies to detect imminent marketing spend. 

## 🚀 Recent Pivot: "Headless Intelligence"
We moved from a Streamlit "data tool" to a professional **Next.js + Tailwind CSS** frontend. 
- **Frontend:** `web/` (Deployed on Vercel).
- **Engine:** Python (`src/`) generating `web/data/intelligence.json`.
- **Data Bridge:** The Python engine runs daily, updates the JSON, and a GitHub push triggers a Vercel rebuild.

## 🛠 Current Engine State

### 1. The Strategy: "Hidden Alpha"
We moved away from general news to a "Triangulated Intelligence" approach:
- **Trade-First:** `src/firehose_client.py` is restricted to ~20 high-signal ad-tech journals (*AdAge, Digiday, etc.*).
- **Deep Target:** `src/active_enricher.py` uses **Crawl4AI** to scan `/blog` and `/careers` for unannounced signals.
- **Job Board Scanning:** New patterns added to detect "Agency management" or "Brand scaling" triggers in Job Descriptions.

### 2. The Brain: `src/signals.py`
- Upgraded to generate **"Strategic Briefs"** (e.g., *"🔴 IMMINENT OPPORTUNITY"*) instead of simple summaries.
- Combines Firehose (Passive) and Crawl4AI (Active) signals into a 0-100 Intent Score.

### 3. Current Blockers / Issues
- **Firehose Stability:** Currently experiencing **502 Bad Gateway** errors from `api.firehose.com`. Needs monitoring or a move to a more stable SSE connection.
- **Data Quality:** OpenAI data was recently "sanitized" with real signals, but the rest of the 50 companies still have "Dummy/Placeholder" data.

## 📂 Key Files
| File | Role |
|------|------|
| `web/app/page.tsx` | Next.js Dashboard (Home + Brand Detail views). |
| `web/data/intelligence.json` | The single source of truth for the frontend. |
| `src/firehose_client.py` | Primary Engine (Lucene queries + Trade Whitelist). |
| `src/active_enricher.py` | Secondary Engine (Crawl4AI Deep Scans). |
| `src/signals.py` | Scoring logic & Agency-focused narrative generator. |

## 🔜 Immediate Next Steps
1. **Sanitize Top 10:** Repeat the "Real Intelligence" injection for Anthropic, Perplexity, and Mistral (ensure 100% verified URLs).
2. **Fix Firehose:** Debug the 502 errors. It may be due to the complex `domain:` whitelist in the Lucene query hitting URI limits.
3. **Automate Update:** Create a simple script/command that runs both engines and performs the `git push` to update the live Vercel site in one go.
4. **Custom Domain:** The user needs to point their custom domain to the Vercel project (Root directory: `web`).

## ⚠️ Hard Rules for Next LLM
- **Verification:** NEVER guess a URL. Every link in the dashboard must be verified by a crawl or a real search result.
- **Lego Blocks:** Stick to the `Firehose -> Crawl4AI -> Signals -> JSON -> Vercel` pipeline.
- **Frontend:** All UI changes happen in the `web/` folder.
