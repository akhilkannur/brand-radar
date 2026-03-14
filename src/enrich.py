#!/usr/bin/env python3
"""
Brand Radar — CLI Intelligence Enrichment Pipeline

Fetches real news from GDELT (free) + optional NewsAPI, then uses OpenAI
to extract structured intelligence (leadership, campaigns, partnerships,
hiring). Updates the JSON files in data/raw/.

Usage:
    # Enrich all brands (GDELT only, free):
    python src/enrich.py

    # Enrich one brand:
    python src/enrich.py --brand "Unilever"

    # With OpenAI for sharper extraction (costs ~$0.01/brand):
    OPENAI_API_KEY=sk-... python src/enrich.py

    # With NewsAPI for more sources (free tier = 100 req/day):
    NEWSAPI_KEY=abc123 python src/enrich.py

    # Dry-run (preview news, don't write files):
    python src/enrich.py --dry-run
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRANDS_CSV = DATA_DIR / "brands.csv"

# ---------------------------------------------------------------------------
# API keys (optional)
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


# ═══════════════════════════════════════════════════════════════════════════
# 1. NEWS FETCHERS
# ═══════════════════════════════════════════════════════════════════════════
def fetch_gdelt(brand_name: str, max_articles: int = 15) -> list[dict]:
    """
    Fetch news from GDELT (free, no API key needed).
    Returns list of {title, url, source, date}.
    """
    # Simple keyword query — GDELT needs minimal URL encoding
    from urllib.parse import quote
    query = quote(f'{brand_name} marketing OR campaign OR agency OR advertising')
    url = (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={query}&mode=artlist&maxrecords={max_articles}"
        f"&format=json&sort=datedesc"
    )
    for attempt in range(3):
        try:
            wait = 6 if attempt == 0 else 15 * attempt
            if attempt > 0:
                print(f"   ⏳ GDELT retry {attempt+1}/3 (waiting {wait}s)...")
            time.sleep(wait)

            resp = requests.get(url, timeout=30)

            if resp.status_code == 429:
                continue  # retry

            resp.raise_for_status()

            # GDELT returns HTML when rate-limited
            ct = resp.headers.get("Content-Type", "")
            if "json" not in ct:
                continue  # retry

            data = resp.json()
            articles = data.get("articles", [])
            return [
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("domain", a.get("source", "")),
                    "date": a.get("seendate", "")[:10],
                }
                for a in articles
                if a.get("title")
            ]
        except requests.exceptions.JSONDecodeError:
            continue  # retry
        except Exception as e:
            print(f"   ⚠️  GDELT failed: {e}")
            return []

    print(f"   ⚠️  GDELT rate-limited after 3 retries")
    return []


def fetch_newsapi(brand_name: str, max_articles: int = 10) -> list[dict]:
    """
    Fetch news from NewsAPI (requires NEWSAPI_KEY env var).
    Free tier: 100 requests/day.
    """
    if not NEWSAPI_KEY:
        return []
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q=%22{brand_name.replace(' ', '%20')}%22"
        f"&sortBy=publishedAt&pageSize={max_articles}"
        f"&language=en&apiKey={NEWSAPI_KEY}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", {}).get("name", ""),
                "date": (a.get("publishedAt") or "")[:10],
            }
            for a in data.get("articles", [])
            if a.get("title") and a["title"] != "[Removed]"
        ]
    except Exception as e:
        print(f"   ⚠️  NewsAPI failed: {e}")
        return []


def fetch_all_news(brand_name: str) -> list[dict]:
    """Combine GDELT + NewsAPI, deduplicate by title."""
    articles = fetch_gdelt(brand_name)
    articles += fetch_newsapi(brand_name)

    # Deduplicate by lowercase title
    seen = set()
    unique = []
    for a in articles:
        key = a["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique


# ═══════════════════════════════════════════════════════════════════════════
# 2. INTELLIGENCE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════
EXTRACTION_PROMPT = """\
You are a business intelligence analyst for advertising agencies.
Given the company name and a batch of recent news headlines about them,
extract structured intelligence that would help an agency pitch services.

Company: {brand_name}

Headlines:
{headlines_text}

Return ONLY valid JSON (no markdown fences) with this exact structure:
{{
  "events": [
    {{
      "type": "leadership|campaign|partnership|hiring|product|funding|restructuring",
      "title": "Short event title",
      "detail": "One-sentence detail with names/numbers",
      "pitch_angle": "Why an agency should care + what to pitch",
      "services": ["Service 1", "Service 2", "Service 3"],
      "urgency": "high|medium|low",
      "source_headline": "The headline this came from"
    }}
  ],
  "leadership": ["Person Name - Title"],
  "campaigns": ["Campaign Name"],
  "partnerships": ["Partner Name"],
  "hiring": ["Role title"],
  "is_recent": true
}}

Rules:
- Only include events you can actually infer from the headlines.
- If no relevant signals exist, return empty arrays.
- "urgency" = "high" for leadership changes, agency reviews, big campaigns.
- Be specific in "detail" — use real names, dollar amounts, dates if mentioned.
- Keep events to max 5 most important ones.
"""


def extract_with_openai(brand_name: str, articles: list[dict]) -> Optional[dict]:
    """Use OpenAI API to extract structured intelligence from headlines."""
    if not OPENAI_API_KEY:
        return None

    headlines_text = "\n".join(
        f"- [{a['date']}] {a['title']} (source: {a['source']})"
        for a in articles[:20]
    )

    if not headlines_text.strip():
        return None

    prompt = EXTRACTION_PROMPT.format(
        brand_name=brand_name, headlines_text=headlines_text
    )

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"   ⚠️  OpenAI returned invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"   ⚠️  OpenAI API failed: {e}")
        return None


def extract_with_heuristics(brand_name: str, articles: list[dict]) -> dict:
    """
    Fallback: extract intelligence from headlines using keyword heuristics.
    Not as good as LLM but free and works offline.
    """
    intel = {
        "events": [],
        "leadership": [],
        "campaigns": [],
        "partnerships": [],
        "hiring": [],
        "is_recent": bool(articles),
    }

    for a in articles[:20]:
        title = a["title"]
        title_lower = title.lower()

        # Leadership
        if any(kw in title_lower for kw in [
            "cmo", "ceo", "cfo", "chief", "president", "appoint",
            "named", "hires", "hired", "steps down", "departs",
            "leadership", "executive",
        ]):
            intel["events"].append({
                "type": "leadership",
                "title": "Leadership Change Detected",
                "detail": title,
                "pitch_angle": "New leaders review agency relationships in 60-90 days",
                "services": ["Brand Strategy", "Creative Agency", "Media Planning"],
                "urgency": "high",
                "source_headline": title,
            })

        # Campaign
        elif any(kw in title_lower for kw in [
            "campaign", "launch", "launches", "unveil", "ad ",
            "advertising", "super bowl", "commercial", "spot",
            "brand refresh", "rebrand",
        ]):
            intel["events"].append({
                "type": "campaign",
                "title": "Campaign Activity",
                "detail": title,
                "pitch_angle": "Active campaign = active budget. Pitch amplification",
                "services": ["Campaign Amplification", "Social Media", "Performance Marketing"],
                "urgency": "medium",
                "source_headline": title,
            })

        # Partnership
        elif any(kw in title_lower for kw in [
            "partner", "partnership", "collaborat", "sponsor",
            "deal", "agreement", "alliance", "team up",
        ]):
            intel["events"].append({
                "type": "partnership",
                "title": "Partnership Announced",
                "detail": title,
                "pitch_angle": "Partnerships need activation — pitch co-marketing",
                "services": ["Co-marketing", "Event Activation", "PR"],
                "urgency": "medium",
                "source_headline": title,
            })

        # Hiring
        elif any(kw in title_lower for kw in [
            "hiring", "job", "recruit", "talent", "workforce",
            "layoff", "cut", "restructur",
        ]):
            intel["events"].append({
                "type": "hiring",
                "title": "Workforce Signal",
                "detail": title,
                "pitch_angle": "Team changes = capability gaps agencies can fill",
                "services": ["Staff Augmentation", "Consulting", "Specialized Services"],
                "urgency": "low",
                "source_headline": title,
            })

        # Product
        elif any(kw in title_lower for kw in [
            "product", "release", "new ", "innovation", "introduce",
        ]):
            intel["events"].append({
                "type": "product",
                "title": "Product Activity",
                "detail": title,
                "pitch_angle": "New products need launch marketing support",
                "services": ["Product Launch", "Go-to-market", "Performance Creative"],
                "urgency": "medium",
                "source_headline": title,
            })

    # Dedupe events and cap at 5
    seen_titles = set()
    unique_events = []
    for ev in intel["events"]:
        if ev["detail"] not in seen_titles:
            seen_titles.add(ev["detail"])
            unique_events.append(ev)
    intel["events"] = unique_events[:5]

    return intel


# ═══════════════════════════════════════════════════════════════════════════
# 3. JSON UPDATE
# ═══════════════════════════════════════════════════════════════════════════
def update_brand_json(brand_name: str, intel: dict, articles: list[dict],
                      dry_run: bool = False) -> Path:
    """
    Update (or create) the brand's JSON file with new intelligence.
    Preserves existing crawl data; replaces intelligence + adds news sources.
    """
    slug = brand_name.lower().replace(" ", "_").replace("&", "&")
    fp = RAW_DIR / f"{slug}.json"

    # Load existing data if present
    if fp.exists():
        existing = json.loads(fp.read_text())
    else:
        existing = {
            "name": brand_name,
            "url": "",
            "success": True,
            "crawled_at": datetime.now().isoformat(),
            "crawled_urls": [],
            "pages_crawled": 0,
            "signals": {
                "leadership": 0, "hiring": 0, "campaigns": 0,
                "tech": 0, "partnerships": 0, "freshness": 0
            },
            "raw_content_sample": "",
            "intent_score": 0,
        }

    # Update intelligence
    existing["intelligence"] = intel
    existing["name"] = brand_name
    existing["enriched_at"] = datetime.now().isoformat()

    # Add news source URLs to crawled_urls (keep originals)
    existing_urls = set(existing.get("crawled_urls", []))
    news_urls = [a["url"] for a in articles[:5] if a.get("url")]
    combined_urls = list(existing_urls) + [u for u in news_urls if u not in existing_urls]
    existing["crawled_urls"] = combined_urls

    # Update signal counts from intelligence
    events = intel.get("events", [])
    type_counts = {}
    for ev in events:
        t = ev.get("type", "")
        type_counts[t] = type_counts.get(t, 0) + 1

    sig = existing.get("signals", {})
    sig["leadership"] = max(sig.get("leadership", 0), type_counts.get("leadership", 0))
    sig["hiring"] = max(sig.get("hiring", 0), type_counts.get("hiring", 0))
    sig["campaigns"] = max(sig.get("campaigns", 0),
                           type_counts.get("campaign", 0) + type_counts.get("product", 0))
    sig["partnerships"] = max(sig.get("partnerships", 0), type_counts.get("partnership", 0))
    if intel.get("is_recent"):
        sig["freshness"] = 10
    existing["signals"] = sig

    # Recalculate intent score
    s = sig
    score = (
        min(s.get("leadership", 0) * 8, 30) +
        min(s.get("hiring", 0) * 4, 25) +
        min(s.get("campaigns", 0) * 5, 20) +
        min(s.get("tech", 0) * 5, 15) +
        min(s.get("partnerships", 0) * 4, 10) +
        min(s.get("freshness", 0), 10)
    )
    existing["intent_score"] = int(min(score, 100))

    if not dry_run:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

    return fp


# ═══════════════════════════════════════════════════════════════════════════
# 4. CLI
# ═══════════════════════════════════════════════════════════════════════════
def load_brand_list() -> list[dict]:
    """Load brands from brands.csv."""
    brands = []
    if not BRANDS_CSV.exists():
        return brands
    for line in BRANDS_CSV.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[1].startswith("http"):
            brands.append({
                "name": parts[0],
                "url": parts[1],
                "category": parts[2] if len(parts) >= 3 else "Other",
            })
    return brands


def main():
    parser = argparse.ArgumentParser(
        description="Brand Radar — Enrich brand intelligence from news sources"
    )
    parser.add_argument("--brand", type=str, help="Enrich a single brand by name")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max brands to enrich (0 = all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview results without writing files")
    args = parser.parse_args()

    # Mode info
    print("=" * 64)
    print("🔍 Brand Radar — Intelligence Enrichment Pipeline")
    print("=" * 64)
    print(f"  GDELT:   ✅ Free (no key needed)")
    print(f"  NewsAPI: {'✅ ' + NEWSAPI_KEY[:8] + '...' if NEWSAPI_KEY else '⬚  Set NEWSAPI_KEY for more sources'}")
    print(f"  OpenAI:  {'✅ ' + OPENAI_API_KEY[:8] + '... (gpt-4o-mini)' if OPENAI_API_KEY else '⬚  Set OPENAI_API_KEY for LLM extraction (falls back to heuristics)'}")
    if args.dry_run:
        print(f"  Mode:    🔎 DRY RUN (no files written)")
    print()

    # Load brands
    all_brands = load_brand_list()
    if not all_brands:
        print("❌ No brands found in data/brands.csv")
        sys.exit(1)

    if args.brand:
        brands = [b for b in all_brands if b["name"].lower() == args.brand.lower()]
        if not brands:
            print(f"❌ Brand '{args.brand}' not found in brands.csv")
            print(f"   Available: {', '.join(b['name'] for b in all_brands[:10])}...")
            sys.exit(1)
    else:
        brands = all_brands
        if args.limit > 0:
            brands = brands[:args.limit]

    print(f"📋 Enriching {len(brands)} brand(s)...\n")

    stats = {"enriched": 0, "no_news": 0, "errors": 0}

    for i, brand in enumerate(brands, 1):
        name = brand["name"]
        print(f"[{i}/{len(brands)}] {name}")
        print(f"   📡 Fetching news...")

        articles = fetch_all_news(name)
        print(f"   📰 Found {len(articles)} article(s)")

        if not articles:
            print(f"   ⚠️  No news found — skipping")
            stats["no_news"] += 1
            continue

        # Show top headlines
        for a in articles[:3]:
            print(f"      • [{a['date']}] {a['title'][:80]}")
        if len(articles) > 3:
            print(f"      ... +{len(articles) - 3} more")

        # Extract intelligence
        print(f"   🧠 Extracting intelligence...")
        intel = None

        if OPENAI_API_KEY:
            intel = extract_with_openai(name, articles)
            if intel:
                print(f"   ✅ OpenAI extracted {len(intel.get('events', []))} events")

        if intel is None:
            intel = extract_with_heuristics(name, articles)
            print(f"   📊 Heuristics extracted {len(intel.get('events', []))} events")

        # Update JSON
        fp = update_brand_json(name, intel, articles, dry_run=args.dry_run)
        n_events = len(intel.get("events", []))

        if args.dry_run:
            print(f"   🔎 Would write to {fp.name}")
        else:
            print(f"   💾 Saved → {fp.name}")

        # Summary
        if intel.get("events"):
            for ev in intel["events"][:3]:
                urg = ev.get("urgency", "low")
                icon = "🔴" if urg == "high" else "🟡" if urg == "medium" else "🟢"
                print(f"      {icon} {ev.get('title', '')}: {ev.get('detail', '')[:60]}")

        stats["enriched"] += 1
        print()

        # Rate limit politeness
        if i < len(brands):
            time.sleep(1)

    # Final summary
    print("=" * 64)
    print("✅ ENRICHMENT COMPLETE")
    print("=" * 64)
    print(f"   Enriched:  {stats['enriched']}")
    print(f"   No news:   {stats['no_news']}")
    print(f"   Errors:    {stats['errors']}")
    print()
    if not args.dry_run:
        print("   Run the dashboard to see results:")
        print("   streamlit run dashboard/app.py")
    print()


if __name__ == "__main__":
    main()
