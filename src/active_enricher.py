"""
Brand Radar — Active Signal Enricher (Multi-Source)
Combines Crawl4AI direct scans with Google News, Hacker News, Reddit,
and SEC EDGAR to triangulate intent signals across free public sources.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from signals import SignalProcessor
from gnews_client import GNewsClient
from hackernews_client import HackerNewsClient
from reddit_client import RedditClient
from sec_client import SECClient

# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
COMPANIES_CSV = DATA_DIR / "ai_companies.csv"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
WEB_DATA_DIR = ROOT_DIR / "web" / "data"
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
class ActiveEnricher:
    def __init__(self):
        self.processor = SignalProcessor(str(COMPANIES_CSV))
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True
        )

    def _get_target_urls(self, company: dict) -> List[str]:
        """Generate high-intent subpages to check (including Hidden Alpha targets)."""
        base = company["website"].rstrip("/")
        return [
            f"{base}/blog",
            f"{base}/news",
            f"{base}/careers",
            f"{base}/about",
            base
        ]

    def _extract_signals_from_text(self, text: str, company_name: str, url: str) -> List[dict]:
        """Convert raw text findings into structured signal dicts (High Precision)."""
        signals = []
        text_lower = text.lower()
        
        ACTIVE_PATTERNS = {
            "agency_review": [r"manage.*external.*agency", r"agency.*partnership", r"rfp", r"agency.*selection", r"manage.*creative.*partner"],
            "leadership": [r"new (chief|cmo|ceo|cfo|head of marketing)", r"vp (marketing|brand|growth)", r"director of (brand|growth|performance)"],
            "ad_spend": [r"scale.*brand.*campaign", r"marketing.*budget.*management", r"global.*brand.*launch", r"scaling.*paid.*media"],
            "hiring": [r"hiring.*marketing.*team", r"seeking.*growth.*lead", r"performance.*marketing.*manager"],
            "product": [r"(launch|unveil|announce).*(product|model|api)", r"new (model|version|beta)"]
        }
        
        for category, patterns in ACTIVE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    signals.append({
                        "company_name": company_name,
                        "signal_type": category,
                        "title": f"Hidden Alpha: {category.title()} trigger detected in source text",
                        "url": url,
                        "matched_at": datetime.now().isoformat(),
                        "summary": f"Detected via Crawl4AI on {url}. Direct company signal.",
                        "source_domain": "direct_scan"
                    })
                    break 
        return signals

    async def enrich_company(self, company: dict) -> List[dict]:
        urls = self._get_target_urls(company)
        all_active_signals = []
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            for url in urls[:3]:
                try:
                    result = await crawler.arun(url=url, config=self.crawler_config)
                    if result.success and result.markdown:
                        found = self._extract_signals_from_text(result.markdown, company["name"], url)
                        if found:
                            all_active_signals.extend(found)
                except Exception: pass
        return all_active_signals

    def _collect_external_signals(self, companies: list) -> List[dict]:
        """Gather signals from all free external sources."""
        print("[+] Fetching Google News signals...")
        gnews = GNewsClient()
        gnews_signals = gnews.collect_signals(companies)
        print(f"    -> {len(gnews_signals)} signals from Google News")

        print("[+] Fetching Hacker News signals...")
        hn = HackerNewsClient()
        hn_signals = hn.collect_signals(companies)
        print(f"    -> {len(hn_signals)} signals from Hacker News")

        print("[+] Fetching Reddit signals...")
        reddit = RedditClient()
        reddit_signals = reddit.collect_signals(companies)
        print(f"    -> {len(reddit_signals)} signals from Reddit")

        print("[+] Fetching SEC EDGAR signals...")
        sec = SECClient()
        sec_signals = sec.collect_signals(companies)
        print(f"    -> {len(sec_signals)} signals from SEC EDGAR")

        return gnews_signals + hn_signals + reddit_signals + sec_signals

    async def run_full_enrichment(self, limit: int = 50):
        companies = list(self.processor.companies.values())[:limit]
        all_signals = {}
        latest_snap = self._get_latest_snapshot()
        if latest_snap:
            with open(latest_snap, "r") as f:
                snap_data = json.load(f)
                for s in snap_data.get("scores", []):
                    all_signals[s["company"]] = s.get("top_signals", [])

        # --- External sources (Google News, HN, Reddit, SEC) ---
        external_raw = self._collect_external_signals(companies)
        for sig in external_raw:
            processed = self.processor.process_event(sig)
            if processed:
                name = processed["company"]
                all_signals.setdefault(name, []).append(processed)

        # --- Crawl4AI direct scans (fill gaps for companies with few signals) ---
        print("[+] Running Crawl4AI deep scans for low-signal companies...")
        crawl_count = 0
        for comp in companies:
            if len(all_signals.get(comp["name"], [])) < 2:
                active_sigs = await self.enrich_company(comp)
                processed = [self.processor.process_event(s) for s in active_sigs if s]
                all_signals[comp["name"]] = all_signals.get(comp["name"], []) + [p for p in processed if p]
                crawl_count += 1
        print(f"    -> Deep-scanned {crawl_count} low-signal companies")

        scores = self.processor.get_all_scores(all_signals)
        self.processor.save_snapshot(scores, str(SNAPSHOTS_DIR))
        with open(WEB_DATA_DIR / "intelligence.json", "w") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "company_count": len(scores), "scores": scores}, f, indent=2)
        print(f"[✓] Done. {len(scores)} companies scored, written to intelligence.json")

    def _get_latest_snapshot(self) -> Optional[Path]:
        snaps = sorted(SNAPSHOTS_DIR.glob("scores_*.json"), reverse=True)
        return snaps[0] if snaps else None

if __name__ == "__main__":
    enricher = ActiveEnricher()
    asyncio.run(enricher.run_full_enrichment())
