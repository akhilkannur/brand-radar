"""
Brand Radar — Reddit Client (public JSON API)
Monitors AI-focused subreddits for company mentions and sentiment.
Free, no API key required (uses public .json endpoints).
"""

import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import requests

# Subreddits with high-signal AI discussion
TARGET_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "LocalLLaMA",
    "singularity",
    "ChatGPT",
    "OpenAI",
    "ClaudeAI",
    "StableDiffusion",
]

SIGNAL_KEYWORDS = {
    "funding": ["funding", "series a", "series b", "series c", "raised", "valuation", "ipo"],
    "product": ["launch", "released", "announces", "new model", "new version", "open source", "beta", "api"],
    "leadership": ["ceo", "cto", "cmo", "appointed", "steps down", "hire"],
    "partnership": ["partnership", "acquisition", "acquires", "merged"],
    "competitive": ["market share", "overtakes", "better than", "comparison", "versus", "switch from", "moved to"],
    "ad_spend": ["rebrand", "marketing", "advertising", "brand campaign"],
    "hiring": ["hiring", "job opening", "recruiting", "careers"],
    "regulatory": ["regulation", "ai safety", "policy", "banned", "lawsuit"],
}


class RedditClient:
    """Fetch signals from Reddit public JSON endpoints — no auth needed."""

    def __init__(self, pause: float = 2.0):
        self.pause = pause
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BrandRadar/1.0 (AI company monitoring)"
        })

    def _classify_signal(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return signal_type
        return None

    def _search_subreddit(self, subreddit: str, query: str, limit: int = 10) -> List[dict]:
        """Search a subreddit using Reddit's public JSON API."""
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "restrict_sr": "on",
            "sort": "new",
            "t": "month",
            "limit": limit,
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return [child["data"] for child in data.get("data", {}).get("children", [])]
        except (requests.RequestException, ValueError, KeyError):
            return []

    def collect_signals(self, companies: List[dict], max_per_company: int = 10) -> List[dict]:
        """Collect signals for companies across target subreddits."""
        all_signals = []
        for company in companies:
            name = company["name"]
            seen_urls = set()
            for subreddit in TARGET_SUBREDDITS:
                posts = self._search_subreddit(subreddit, name, limit=5)
                for post in posts:
                    title = post.get("title", "")
                    selftext = post.get("selftext", "")[:300]
                    permalink = post.get("permalink", "")
                    url = f"https://www.reddit.com{permalink}" if permalink else ""
                    score = post.get("score", 0)
                    num_comments = post.get("num_comments", 0)
                    created_utc = post.get("created_utc", 0)

                    if url in seen_urls or score < 5:
                        continue
                    seen_urls.add(url)

                    combined = f"{title} {selftext}"
                    signal_type = self._classify_signal(combined)
                    if not signal_type:
                        if score >= 100:
                            signal_type = "competitive"
                        else:
                            continue

                    matched_at = datetime.utcfromtimestamp(created_utc).isoformat() if created_utc else datetime.now().isoformat()

                    all_signals.append({
                        "company_name": name,
                        "signal_type": signal_type,
                        "title": title[:200],
                        "url": url,
                        "matched_at": matched_at,
                        "summary": f"r/{post.get('subreddit', subreddit)} ({score} upvotes, {num_comments} comments). {selftext[:200]}",
                        "source_domain": "reddit.com",
                    })

                    if len([s for s in all_signals if s["company_name"] == name]) >= max_per_company:
                        break
                time.sleep(self.pause)
        return all_signals
