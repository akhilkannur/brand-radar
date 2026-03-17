"""
Brand Radar — Google News RSS Client
Fetches recent press coverage for AI companies via Google News RSS feeds.
Free, no API key required.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote, urlparse

import requests

# Signal keywords mapped to signal types (reuse firehose taxonomy)
SIGNAL_KEYWORDS = {
    "agency_review": ["agency of record", "media review", "creative review", "agency pitch", "rfp", "agency search"],
    "ad_spend": ["ad campaign", "brand campaign", "marketing budget", "media spend", "brand launch", "rebrand"],
    "funding": ["funding round", "series a", "series b", "series c", "series d", "raises", "raised", "valuation", "venture capital", "ipo"],
    "revenue": ["revenue", "arr", "annual recurring", "run rate", "million users", "profitability"],
    "leadership": ["cmo", "chief marketing", "vp marketing", "head of marketing", "ceo", "cto", "appointed", "steps down"],
    "product": ["launches", "released", "announces", "unveils", "generally available", "new model", "new api", "open source"],
    "hiring": ["hiring spree", "headcount", "job openings", "growth marketing"],
    "partnership": ["partnership", "partners with", "acquisition", "acquires", "joint venture", "strategic alliance"],
    "competitive": ["market share", "overtakes", "surpasses", "market leader"],
    "events": ["keynote", "developer conference", "dev day", "launch event"],
    "regulatory": ["ai regulation", "ai safety", "ai policy", "government contract", "eu ai act"],
}


class GNewsClient:
    """Fetch signals from Google News RSS — completely free, no auth."""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, pause: float = 1.5):
        self.pause = pause
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; BrandRadar/1.0)"
        })

    def _classify_signal(self, text: str) -> Optional[str]:
        """Match article text against signal keywords, return best signal type."""
        text_lower = text.lower()
        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return signal_type
        return None

    def _fetch_rss(self, query: str, max_results: int = 20) -> List[dict]:
        """Fetch and parse a Google News RSS feed for a query."""
        url = f"{self.BASE_URL}?q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException:
            return []

        items = []
        try:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:max_results]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")
                # Strip HTML from description
                description = re.sub(r"<[^>]+>", "", description)
                items.append({
                    "title": title,
                    "url": link,
                    "pub_date": pub_date,
                    "description": description,
                })
        except ET.ParseError:
            pass
        return items

    def _parse_pub_date(self, pub_date: str) -> str:
        """Convert RSS pubDate to ISO format."""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            return dt.isoformat()
        except Exception:
            return datetime.now().isoformat()

    def collect_signals(self, companies: List[dict], max_per_company: int = 10) -> List[dict]:
        """Collect signals for a list of companies from Google News."""
        all_signals = []
        for company in companies:
            name = company["name"]
            items = self._fetch_rss(f'"{name}" AI', max_results=max_per_company)
            for item in items:
                combined = f"{item['title']} {item['description']}"
                signal_type = self._classify_signal(combined)
                if not signal_type:
                    continue
                source_domain = urlparse(item["url"]).netloc
                all_signals.append({
                    "company_name": name,
                    "signal_type": signal_type,
                    "title": item["title"],
                    "url": item["url"],
                    "matched_at": self._parse_pub_date(item["pub_date"]),
                    "summary": item["description"][:500],
                    "source_domain": source_domain,
                })
            time.sleep(self.pause)
        return all_signals
