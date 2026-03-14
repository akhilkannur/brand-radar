"""
Brand Radar — Active Signal Enricher (Crawl4AI)
Fallback/Enrichment layer: specifically targets careers, newsroom, and leadership
pages for AI companies when Firehose signal volume is low.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Path to local venv's python to ensure we use the correct environment
# In a real script, this would just be 'python' if the venv is active.
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from signals import SignalProcessor

# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
COMPANIES_CSV = DATA_DIR / "ai_companies.csv"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
WEB_DATA_DIR = ROOT_DIR / "web" / "data"
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Active Signal Configuration (Mapping keywords to Firehose-compatible tags)
# ---------------------------------------------------------------------------
ACTIVE_SIGNAL_MAP = {
    "leadership": {
        "keywords": [r"(appointed|named|joined).*(chief|cmo|ceo|cfo|presid)", r"new (chief|cmo|ceo|cfo)", r"vp marketing", r"head of marketing"],
        "tag": "leadership"
    },
    "hiring": {
        "keywords": [r"(hiring|joining|seeking).*(marketing|brand|growth|ads)", r"marketing.*careers", r"brand.*manager"],
        "tag": "hiring"
    },
    "product": {
        "keywords": [r"(launch|unveil|introduce|announce).*(product|model|api)", r"new (model|feature|release)"],
        "tag": "product"
    },
    "events": {
        "keywords": [r"(conference|keynote|demo day|summit|booth)", r"exhibiting at"],
        "tag": "events"
    }
}

class ActiveEnricher:
    def __init__(self):
        self.processor = SignalProcessor(str(COMPANIES_CSV))
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True
        )

    def _get_target_urls(self, company: dict) -> List[str]:
        """Generate high-intent subpages to check."""
        base = company["website"].rstrip("/")
        # We target the most likely signal-rich pages
        return [
            f"{base}/newsroom",
            f"{base}/news",
            f"{base}/press",
            f"{base}/careers",
            f"{base}/about",
            base # Homepage as fallback
        ]

    def _extract_signals_from_text(self, text: str, company_name: str, url: str) -> List[dict]:
        """Convert raw text findings into structured signal dicts compatible with signals.py."""
        signals = []
        text_lower = text.lower()
        
        for category, config in ACTIVE_SIGNAL_MAP.items():
            for pattern in config["keywords"]:
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Create a dummy "event" compatible with SignalProcessor.process_event
                    # but marked as an "active" source
                    signals.append({
                        "company_name": company_name,
                        "signal_type": config["tag"],
                        "title": f"Active detection: {category.title()} signal found on site",
                        "url": url,
                        "matched_at": datetime.now().isoformat(),
                        "summary": f"Detected via Crawl4AI on {url}. Content snippet: {text[:200]}...",
                        "source_domain": "company_website_crawl"
                    })
                    break # One signal per category per page is enough for enrichment
        
        return signals

    async def enrich_company(self, company: dict) -> List[dict]:
        """Crawl a single company's high-intent pages and return signals."""
        urls = self._get_target_urls(company)
        all_active_signals = []
        
        print(f"🕷️  Checking {company['name']} via Crawl4AI...")
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # We check up to 3 URLs to be efficient
            for url in urls[:3]:
                try:
                    result = await crawler.arun(url=url, config=self.crawler_config)
                    if result.success and result.markdown:
                        found = self._extract_signals_from_text(result.markdown, company["name"], url)
                        if found:
                            print(f"   ✅ Found {len(found)} active signals on {url}")
                            all_active_signals.extend(found)
                except Exception as e:
                    print(f"   ⚠️  Failed to crawl {url}: {e}")
        
        return all_active_signals

    async def run_full_enrichment(self, limit: int = 50):
        """Run enrichment for all companies and save a combined snapshot."""
        companies = list(self.processor.companies.values())[:limit]
        all_signals = {}
        
        # Load existing signals from latest snapshot to avoid starting from zero
        latest_snap = self._get_latest_snapshot()
        if latest_snap:
            print(f"📂 Loading baseline signals from {latest_snap.name}")
            with open(latest_snap, "r") as f:
                snap_data = json.load(f)
                for s in snap_data.get("scores", []):
                    # We map back top_signals to our signal list
                    all_signals[s["company"]] = s.get("top_signals", [])

        # Add Active Signals
        for comp in companies:
            # Only enrich if Firehose volume is low (e.g. < 2 signals)
            if len(all_signals.get(comp["name"], [])) < 2:
                active_sigs = await self.enrich_company(comp)
                processed = []
                for s in active_sigs:
                    p = self.processor.process_event(s)
                    if p: processed.append(p)
                
                if comp["name"] not in all_signals:
                    all_signals[comp["name"]] = []
                all_signals[comp["name"]].extend(processed)
            else:
                print(f"⏩ Skipping {comp['name']} (Firehose already has sufficient signals)")

        # Recalculate and Save
        scores = self.processor.get_all_scores(all_signals)
        snap_path = self.processor.save_snapshot(scores, str(SNAPSHOTS_DIR))
        
        # Save to web frontend
        with open(WEB_DATA_DIR / "intelligence.json", "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "company_count": len(scores),
                "scores": scores
            }, f, indent=2)
            
        print(f"🚀 Enrichment Complete! New snapshot: {snap_path}")
        print(f"📡 Data updated for Next.js frontend in {WEB_DATA_DIR}/intelligence.json")

    def _get_latest_snapshot(self) -> Optional[Path]:
        snaps = sorted(SNAPSHOTS_DIR.glob("scores_*.json"), reverse=True)
        return snaps[0] if snaps else None

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    enricher = ActiveEnricher()
    asyncio.run(enricher.run_full_enrichment())
