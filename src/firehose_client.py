"""
Brand Radar - Firehose API Client
Real-time web monitoring for AI company intent signals via Firehose SSE streams.
"""

import csv
import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
AI_COMPANIES_FILE = DATA_DIR / "ai_companies.csv"

BASE_URL = "https://api.firehose.com"

# --- High-signal 'Trade Whisper' Whitelist ---
TRADE_SOURCES = [
    "adage.com", "adweek.com", "campaignlive.com", "digiday.com",
    "marketingweek.com", "thedrum.com", "mediapost.com", 
    "martechcube.com", "marketingbrew.com", "socialsamosa.com",
    "exchange4media.com", "marketing-interactive.com"
]

# Signal type definitions: (tag, keywords, extra_filters)
_NO_FILTER = ""

SIGNAL_TYPES = [
    ("agency_review", ["agency of record", "AOR", "media review", "creative review", "agency pitch", "RFP", "request for proposal", "media agency", "creative agency", "agency search", "media buy"], _NO_FILTER),
    ("ad_spend", ["ad campaign", "brand campaign", "advertising campaign", "marketing budget", "media spend", "brand awareness", "paid media", "brand launch", "rebrand", "go-to-market", "GTM campaign"], _NO_FILTER),
    ("funding", ["funding round", "series A", "series B", "series C", "series D", "raises", "raised", "valuation", "fundraise", "venture capital", "IPO", "going public"], _NO_FILTER),
    ("revenue", ["revenue", "ARR", "annual recurring", "run rate", "million users", "billion users", "profitability", "profitable", "revenue milestone", "enterprise customers"], _NO_FILTER),
    ("leadership", ["CMO", "chief marketing", "VP marketing", "head of marketing", "CEO", "CTO", "CFO", "CRO", "chief revenue", "appointed", "steps down", "departs"], _NO_FILTER),
    ("product", ["launches", "released", "announces", "unveils", "generally available", "new model", "new API", "open source", "enterprise edition"], _NO_FILTER),
    ("hiring", ["hiring spree", "headcount", "job openings", "head of growth", "growth marketing", "marketing director", "VP growth", "head of comms"], _NO_FILTER),
    ("partnership", ["partnership", "partners with", "acquisition", "acquires", "merged", "joint venture", "strategic alliance", "distribution deal"], _NO_FILTER),
    ("competitive", ["market share", "overtakes", "surpasses", "gains ground", "market leader", "displaces"], _NO_FILTER),
    ("events", ["keynote", "developer conference", "dev day", "launch event", "demo day", "product showcase"], _NO_FILTER),
    ("regulatory", ["AI regulation", "AI safety", "AI policy", "government contract", "EU AI Act", "executive order", "antitrust"], _NO_FILTER),
]

# Max rules allowed by Firehose per org
MAX_RULES = 25

class FirehoseClient:
    """Client for the Firehose real-time web monitoring API."""

    def __init__(
        self,
        tap_token: Optional[str] = None,
        mgmt_key: Optional[str] = None,
    ):
        self.tap_token = tap_token or os.environ.get("FIREHOSE_TAP_TOKEN", "")
        self.mgmt_key = mgmt_key or os.environ.get("FIREHOSE_MGMT_KEY", "")
        if not self.tap_token:
            raise ValueError("Tap token required — set FIREHOSE_TAP_TOKEN env var")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.tap_token}",
            "Content-Type": "application/json",
        })

    def list_rules(self) -> List[dict]:
        resp = self.session.get(f"{BASE_URL}/v1/rules")
        resp.raise_for_status()
        return resp.json()

    def _create_rule(self, value: str, tag: str) -> dict:
        resp = self.session.post(
            f"{BASE_URL}/v1/rules",
            json={"value": value, "tag": tag, "quality": True},
        )
        resp.raise_for_status()
        return resp.json()

    def _delete_rule(self, rule_id: str) -> None:
        resp = self.session.delete(f"{BASE_URL}/v1/rules/{rule_id}")
        resp.raise_for_status()

    @staticmethod
    def _build_company_or_clause(names: List[str]) -> str:
        quoted = [f'"{n}"' for n in names]
        return f"({' OR '.join(quoted)})"

    @staticmethod
    def _build_keyword_or_clause(keywords: List[str]) -> str:
        quoted = [f'"{k}"' for k in keywords]
        return f"({' OR '.join(quoted)})"

    def _plan_rules(self, companies: List[dict]) -> List[dict]:
        """Plan 'Hidden Alpha' rules: Company + Keywords + Trade Whitelist."""
        names = [c["name"] for c in companies]
        chunk_size = 25
        name_chunks = [names[i : i + chunk_size] for i in range(0, len(names), chunk_size)]
        
        # Fixed: Avoid backslash in f-string expression for compatibility
        trade_items = [f'"{s}"' for s in TRADE_SOURCES]
        trade_clause = f"domain:({' OR '.join(trade_items)})"
        
        planned: List[dict] = []
        for tag, keywords, extra_filters in SIGNAL_TYPES:
            for idx, chunk in enumerate(name_chunks):
                company_clause = self._build_company_or_clause(chunk)
                keyword_clause = self._build_keyword_or_clause(keywords)
                query = f"{company_clause} AND {keyword_clause} AND {trade_clause} AND language:\"en\" AND recent:30d"
                suffix = f"_{idx + 1}" if len(name_chunks) > 1 else ""
                planned.append({"value": query, "tag": f"{tag}{suffix}"})
        if len(planned) > MAX_RULES:
            planned = planned[:MAX_RULES]
        return planned

    def setup_ai_company_rules(self, companies: List[dict]) -> List[dict]:
        existing = self.list_rules()
        if existing:
            rules_data = existing.get("data", existing) if isinstance(existing, dict) else existing
            if rules_data:
                for rule in rules_data:
                    self._delete_rule(rule["id"])
        planned = self._plan_rules(companies)
        created: List[dict] = []
        self.rule_id_to_tag: Dict[str, str] = {}
        for rule_spec in planned:
            result = self._create_rule(rule_spec["value"], rule_spec["tag"])
            rule_data = result.get("data", result)
            created.append(rule_data)
            self.rule_id_to_tag[rule_data["id"]] = rule_spec["tag"]
        return created

    @staticmethod
    def _match_company(text: str, companies: List[dict]) -> Optional[str]:
        text_lower = text.lower()
        for company in companies:
            if company["name"].lower() in text_lower:
                return company["name"]
        return None

    @staticmethod
    def _parse_sse_event(raw: str) -> Optional[dict]:
        event_type = None
        data_lines: List[str] = []
        for line in raw.split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
        if event_type != "update" or not data_lines:
            return None
        try:
            return json.loads("".join(data_lines))
        except json.JSONDecodeError:
            return None

    def _extract_event(self, raw_event: dict, companies: List[dict]) -> dict:
        doc = raw_event.get("document", {})
        summary = ""
        diff = doc.get("diff", {})
        if diff and diff.get("chunks"):
            parts = [chunk.get("text", "") for chunk in diff["chunks"] if chunk.get("typ") == "ins"]
            summary = " ".join(parts)[:500]
        if not summary:
            summary = (doc.get("markdown") or "")[:500]
        title = doc.get("title", "")
        combined_text = f"{title} {summary}"
        source_url = doc.get("url", "")
        source_domain = urlparse(source_url).netloc if source_url else ""
        query_id = raw_event.get("query_id", "")
        tag = getattr(self, "rule_id_to_tag", {}).get(query_id, query_id)
        signal_type = tag.rsplit("_", 1)[0] if tag and tag[-1].isdigit() else tag
        return {
            "company_name": self._match_company(combined_text, companies),
            "signal_type": signal_type,
            "title": title,
            "url": source_url,
            "matched_at": raw_event.get("matched_at", ""),
            "summary": summary,
            "source_domain": source_domain,
        }

    def stream_events(self, callback: Callable[[dict], None], companies: Optional[List[dict]] = None, duration: int = 300) -> None:
        companies = companies or []
        url = f"{BASE_URL}/v1/stream?timeout=60&since=30m&limit=100"
        end_time = time.time() + duration
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            if remaining <= 0: break
            try:
                with self.session.get(url, stream=True, timeout=remaining + 5) as resp:
                    resp.raise_for_status()
                    buffer = ""
                    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                        if time.time() >= end_time: break
                        buffer += chunk
                        while "\n\n" in buffer:
                            frame, buffer = buffer.split("\n\n", 1)
                            raw_event = self._parse_sse_event(frame)
                            if raw_event:
                                event = self._extract_event(raw_event, companies)
                                callback(event)
            except requests.exceptions.Timeout: continue
            except requests.exceptions.ConnectionError:
                time.sleep(2)

    def collect_events(self, companies: Optional[List[dict]] = None, duration: int = 60) -> List[dict]:
        events: List[dict] = []
        def _collect(event: dict) -> None:
            if event.get("company_name"):
                events.append(event)
        self.stream_events(_collect, companies=companies, duration=duration)
        return events
