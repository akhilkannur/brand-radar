# Brand Radar — Handoff Brief

## What This Project Is

**"Winmo for AI companies"** — a real-time intent signal dashboard that monitors 50 AI companies using [Firehose](https://firehose.com/) (by Ahrefs) to detect which ones are about to spend on advertising/marketing.

## Current State (as of March 14, 2026)

### ✅ Done

1. **Company list**: `data/ai_companies.csv` — 50 AI companies across 4 categories (Foundation Models, Applications, Infrastructure, Hardware)

2. **Firehose client**: `src/firehose_client.py`
   - Connects to Firehose API (`https://api.firehose.com`)
   - Builds Lucene query rules grouped by signal type (11 types)
   - Splits 50 companies into 2 chunks of 25 → 22 rules total (max 25 allowed)
   - Streams SSE events and maps them to companies
   - Maps rule UUIDs (`query_id`) back to tag names via `self.rule_id_to_tag`
   - All rules enforce `language:"en" AND recent:7d` to filter noise (learned from real testing)

3. **Signal processor**: `src/signals.py`
   - 11 signal types with weighted scoring (agency_review=10 highest, regulatory=3 lowest)
   - Source credibility tiers (TechCrunch=high, Reddit=low, ad trade press like AdAge added)
   - Deduplication via URL+company+signal_type hash
   - "Why it matters" context on every signal
   - Combo insight detection (funding+hiring = "building for launch", etc.)
   - Trend detection (rising/stable/declining based on 7-day vs 14-day signal volume)
   - Snapshot persistence to `data/snapshots/`

4. **Firehose token verified working**: Connected, created rules, streamed real events. Token is in `.env` file.

### 🔜 Next Steps

1. **Deploy full ruleset**: Run `python src/firehose_client.py` (needs `FIREHOSE_TAP_TOKEN` env var set from `.env`). This will create all 22 rules on Firehose and start streaming.

2. **Update Streamlit dashboard** (`dashboard/app.py`): Currently built for the old brand/Crawl4AI architecture. Needs to be updated to:
   - Show AI company scores from `data/snapshots/` JSON files
   - Display signal feed (real-time event log)
   - Show score breakdown charts per company
   - Filter by category (Foundation Model, Application, etc.)

3. **Historical tracking**: Save snapshots on a schedule (cron or similar) and show score trajectories over time.

4. **Firecrawl as backup/enrichment layer**: Firehose monitors the web passively (news articles mentioning companies). But for companies with few news mentions, we should **actively crawl their websites** using Firecrawl (`src/firecrawl_extractor.py` already exists) to extract:
   - Careers/jobs pages → hiring signals directly from source
   - Newsroom/press pages → announcements Firehose might miss
   - About/leadership pages → detect exec changes
   - Homepage changes → rebrand, new messaging, product launches
   
   **Strategy**: Run Firecrawl as a weekly scheduled crawl for all 50 companies. Merge those signals with Firehose real-time signals before scoring. Firehose = real-time from across the web, Firecrawl = periodic deep-dive on company sites directly. The existing `firecrawl_extractor.py` and `crawler_hybrid.py` have the crawling logic — just needs to output events in the same format as Firehose events so `signals.py` can process both.

## Key Files

| File | Purpose |
|------|---------|
| `src/firehose_client.py` | Firehose API client — rules, streaming, company matching |
| `src/signals.py` | Signal processing, intent scoring, snapshots |
| `data/ai_companies.csv` | 50 AI companies (name, website, category, stage, notable) |
| `data/snapshots/` | Historical score JSON files |
| `dashboard/app.py` | Streamlit dashboard (needs updating) |
| `.env` | `FIREHOSE_TAP_TOKEN` (gitignored) |
| `src/crawler.py` | Legacy — Crawl4AI crawler (old architecture) |
| `src/crawler_hybrid.py` | Legacy — Crawl4AI + Firecrawl hybrid (old architecture) |
| `src/firecrawl_extractor.py` | Legacy — Firecrawl module (old architecture) |

## Signal Types (11 total)

```
agency_review  (weight=10, cap=20) — Agency review / RFP / AOR search
ad_spend       (weight=9,  cap=15) — Active ad/brand campaign
funding        (weight=8,  cap=15) — Funding rounds, valuations
revenue        (weight=7,  cap=10) — Revenue milestones, user growth
leadership     (weight=7,  cap=12) — CMO/CEO changes, executive hires
product        (weight=6,  cap=10) — Product launches, new models
hiring         (weight=6,  cap=8)  — Marketing hiring, headcount growth
partnership    (weight=5,  cap=8)  — Partnerships, acquisitions
competitive    (weight=5,  cap=5)  — Market share, competitive pressure
events         (weight=4,  cap=5)  — Conferences, keynotes, demo days
regulatory     (weight=3,  cap=2)  — AI regulation, policy, government
```

## Firehose API Quick Reference

- **Base URL**: `https://api.firehose.com`
- **Auth**: `Authorization: Bearer fh_...` (tap token from `.env`)
- **List rules**: `GET /v1/rules`
- **Create rule**: `POST /v1/rules` body: `{"value": "lucene query", "tag": "label"}`
- **Delete rule**: `DELETE /v1/rules/:id`
- **Stream**: `GET /v1/stream?timeout=60&since=24h&limit=100` (SSE)
- **Max 25 rules per org**
- **Docs**: `https://firehose.com/api-docs`

## Lessons from Real Testing

- Without `language:"en"`, you get tons of French, Chinese, Farsi noise
- Without `page_category:"/News"`, you get random blog posts mentioning "OpenAI" in passing
- Firehose `query_id` returns the rule UUID, not the tag — need the `rule_id_to_tag` mapping
- Events are buffered ~24h, so `since=24h` replays recent matches
- The broad rule `"OpenAI"` without filters is way too noisy — always pair company names with signal keywords
