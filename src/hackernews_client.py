"""
Brand Radar — Hacker News Client (Algolia API)
Monitors tech community buzz for AI companies.
Free, no API key required.
"""

import time
from datetime import datetime
from typing import List, Optional

import requests

# Same signal taxonomy as the rest of the pipeline
SIGNAL_KEYWORDS = {
    "funding": ["funding", "series a", "series b", "series c", "raised", "valuation", "ipo", "venture"],
    "product": ["launch", "released", "announces", "unveils", "generally available", "new model", "open source", "beta"],
    "leadership": ["ceo", "cto", "cmo", "appointed", "steps down", "hire", "chief"],
    "partnership": ["partnership", "acquisition", "acquires", "merged", "alliance"],
    "competitive": ["market share", "overtakes", "surpasses", "versus", "competitor", "comparison"],
    "ad_spend": ["brand campaign", "rebrand", "marketing", "advertising"],
    "hiring": ["hiring", "headcount", "job opening", "recruiting"],
    "regulatory": ["regulation", "ai safety", "policy", "eu ai act", "antitrust"],
    "events": ["keynote", "conference", "demo day", "launch event"],
}


class HackerNewsClient:
    """Fetch signals from Hacker News via the free Algolia API."""

    SEARCH_URL = "https://hn.algolia.com/api/v1/search"

    def __init__(self, pause: float = 0.5):
        self.pause = pause
        self.session = requests.Session()

    def _classify_signal(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return signal_type
        return None

    def _search(self, query: str, max_results: int = 15) -> List[dict]:
        """Search HN stories via Algolia."""
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": max_results,
            "numericFilters": "created_at_i>" + str(int(time.time()) - 30 * 86400),  # last 30 days
        }
        try:
            resp = self.session.get(self.SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json().get("hits", [])
        except requests.RequestException:
            return []

    def collect_signals(self, companies: List[dict], max_per_company: int = 10) -> List[dict]:
        """Collect signals for a list of companies from Hacker News."""
        all_signals = []
        for company in companies:
            name = company["name"]
            hits = self._search(name, max_results=max_per_company)
            for hit in hits:
                title = hit.get("title", "")
                story_url = hit.get("url", "")
                hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                created = hit.get("created_at", "")
                points = hit.get("points", 0) or 0
                num_comments = hit.get("num_comments", 0) or 0

                # Only keep stories with some traction
                if points < 5:
                    continue

                signal_type = self._classify_signal(title)
                if not signal_type:
                    # High-engagement HN posts about a company are still a signal
                    if points >= 50:
                        signal_type = "competitive"  # community buzz = competitive intel
                    else:
                        continue

                all_signals.append({
                    "company_name": name,
                    "signal_type": signal_type,
                    "title": title,
                    "url": story_url or hn_url,
                    "matched_at": created or datetime.now().isoformat(),
                    "summary": f"HN discussion ({points} pts, {num_comments} comments). {story_url}",
                    "source_domain": "news.ycombinator.com",
                })
            time.sleep(self.pause)
        return all_signals
