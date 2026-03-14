# Brand Radar 🔍

**Winmo for AI companies** — discover which AI startups are about to spend on advertising, before they issue RFPs.

A real-time intent signal dashboard that monitors 50 AI companies using [Firehose](https://firehose.com/) (by Ahrefs) for live web signals — funding rounds, leadership changes, product launches, hiring surges, and agency/marketing activity.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Real-time Monitoring** | Firehose SSE streams deliver signals the moment they appear on the web |
| **Intent Scoring** | 0-100 score based on funding, leadership, product, hiring, partnerships, marketing signals |
| **Signal Strength** | Each signal rated 1-10 based on source credibility + recency |
| **Trend Detection** | Rising / Stable / Declining based on signal velocity |
| **AI Company Focus** | 50 companies across Foundation Models, Applications, Infrastructure, Hardware |

---

## Tech Stack

- **Firehose** (by Ahrefs): Real-time web monitoring via SSE streams + Lucene query rules
- **Backend**: Python 3.11+
- **Database**: JSON snapshots → SQLite (future)
- **Frontend**: Streamlit (MVP) → Next.js (production)

---

## Project Structure

```
brand-radar/
├── src/
│   ├── firehose_client.py     # Firehose API client (rules + SSE streaming)
│   ├── signals.py             # Signal processing + intent scoring
│   ├── crawler.py             # Legacy: Crawl4AI crawler
│   ├── crawler_hybrid.py      # Legacy: Crawl4AI + Firecrawl hybrid
│   └── firecrawl_extractor.py # Legacy: Firecrawl module
├── dashboard/
│   └── app.py                 # Streamlit dashboard
├── data/
│   ├── ai_companies.csv       # 50 AI companies to monitor
│   ├── snapshots/             # Historical score snapshots
│   └── raw/                   # Legacy crawled data
├── summary.py
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Setup

```bash
cd /home/akhilnairmk/brand-radar
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up Firehose (free during beta)

1. Sign up at [firehose.com](https://firehose.com/) — free, no credit card
2. Create a tap and get your tap token
3. Set environment variable:

```bash
export FIREHOSE_TAP_TOKEN="fh_your_tap_token_here"
```

### 3. Run

```bash
# Set up monitoring rules + stream events
python src/firehose_client.py

# Run signal scoring demo (with sample data)
python src/signals.py

# Dashboard
streamlit run dashboard/app.py
```

---

## How It Works

### Firehose Rules (max 25)

Companies are grouped into signal-type rules using Lucene queries:

| Rule | Query Pattern |
|------|--------------|
| **Funding** | `("OpenAI" OR "Anthropic" OR ...) AND ("funding" OR "raises" OR "valuation") AND page_category:"/News"` |
| **Leadership** | `(companies) AND ("CEO" OR "CMO" OR "appointed") AND page_category:"/News"` |
| **Product Launches** | `(companies) AND ("launch" OR "released" OR "announces") AND page_category:"/News"` |
| **Hiring** | `(companies) AND ("hiring" OR "headcount" OR "job openings")` |
| **Partnerships** | `(companies) AND ("partnership" OR "acquisition") AND page_category:"/News"` |
| **Agency/Marketing** | `(companies) AND ("agency" OR "ad campaign" OR "RFP" OR "media buy")` |

### Intent Score Formula

```
Score (0-100) =
  Funding signals      (max 25)  — rounds, valuations, investments
  Leadership signals   (max 20)  — CMO/CEO changes, executive hires
  Product signals      (max 15)  — launches, releases, GA announcements
  Hiring signals       (max 15)  — marketing roles, headcount growth
  Marketing signals    (max 15)  — agency hires, ad campaigns, RFPs ← core signal
  Partnership signals  (max 10)  — integrations, acquisitions

Signal strength (1-10) modified by:
  + Source credibility (TechCrunch, Bloomberg = high; Reddit = low)
  + Recency (< 3 days = bonus; > 30 days = penalty)
```

---

## AI Companies Tracked (50)

| Category | Count | Examples |
|----------|-------|---------|
| Foundation Models | 13 | OpenAI, Anthropic, Mistral, xAI, Cohere |
| AI Applications | 19 | Perplexity, Cursor, Harvey, Runway, Midjourney |
| AI Infrastructure | 14 | Scale AI, Hugging Face, Pinecone, Databricks |
| AI Hardware | 4 | Cerebras, Groq, SambaNova, d-Matrix |

---

## Comparison: Brand Radar vs Winmo

| Feature | Winmo | Brand Radar |
|---------|-------|-------------|
| **Segment** | Fortune 500 advertisers | AI companies & startups |
| **Data source** | Proprietary database | Real-time web signals (Firehose) |
| **Update speed** | Periodic | Real-time (SSE streaming) |
| **Primary UX** | CRM search | Visual discovery + alerts |
| **User goal** | "Find who to pitch" | "Spot AI companies about to spend" |
| **Pricing** | $99+/mo | Free (open source) |

---

## Roadmap

### Phase 1: Core ✅
- [x] AI company list (50 companies)
- [x] Firehose API client (rules + streaming)
- [x] Signal processing + intent scoring
- [x] Score snapshots

### Phase 2: Dashboard (Next)
- [ ] Update Streamlit dashboard for AI companies
- [ ] Trajectory charts (score over time)
- [ ] Signal feed (real-time event log)
- [ ] Email alerts for score spikes

### Phase 3: Scale
- [ ] Expand to 500+ AI companies
- [ ] Historical trend tracking
- [ ] API for agencies
- [ ] Slack/webhook alerts

---

## License

MIT

---

## Credits

- **Firehose**: https://firehose.com/ (by Ahrefs)
- **Inspiration**: Winmo, Exploding Topics, Glimpse
