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

# Signal type definitions: (tag, keywords, extra_filters)
# Ordered by priority — if we hit the 25-rule cap, lower ones get dropped.
# extra_filters is appended to the Lucene query after company + keyword clauses.
# language:"en" AND recent:7d is ALWAYS added (learned from real data: without
# language filter we get tons of non-English noise).
_NEWS_FILTER = 'AND page_category:"/News"'
_ARTICLE_FILTER = 'AND (page_category:"/News" OR page_type:"/Article")'

SIGNAL_TYPES = [
    # --- Highest priority: direct ad-spend intent ---
    (
        "agency_review",
        [
            "agency of record", "AOR", "media review", "creative review",
            "agency pitch", "RFP", "request for proposal", "media agency",
            "creative agency", "agency search", "media buy",
        ],
        _ARTICLE_FILTER,
    ),
    (
        "ad_spend",
        [
            "ad campaign", "brand campaign", "advertising campaign",
            "marketing budget", "media spend", "brand awareness",
            "paid media", "brand launch", "rebrand",
            "go-to-market", "GTM campaign",
        ],
        _NEWS_FILTER,
    ),
    # --- High priority: strong spend predictors ---
    (
        "funding",
        [
            "funding round", "series A", "series B", "series C", "series D",
            "raises", "raised", "valuation", "fundraise",
            "venture capital", "IPO", "going public",
        ],
        _NEWS_FILTER,
    ),
    (
        "revenue",
        [
            "revenue", "ARR", "annual recurring", "run rate",
            "million users", "billion users",
            "profitability", "profitable", "revenue milestone",
            "enterprise customers",
        ],
        _NEWS_FILTER,
    ),
    (
        "leadership",
        [
            "CMO", "chief marketing", "VP marketing", "head of marketing",
            "CEO", "CTO", "CFO", "CRO", "chief revenue",
            "appointed", "steps down", "departs",
        ],
        _NEWS_FILTER,
    ),
    # --- Medium priority ---
    (
        "product",
        [
            "launches", "released", "announces", "unveils",
            "generally available", "new model", "new API",
            "open source", "enterprise edition",
        ],
        _NEWS_FILTER,
    ),
    (
        "hiring",
        [
            "hiring spree", "headcount", "job openings",
            "head of growth", "growth marketing",
            "marketing director", "VP growth", "head of comms",
        ],
        _ARTICLE_FILTER,
    ),
    (
        "partnership",
        [
            "partnership", "partners with", "acquisition",
            "acquires", "merged", "joint venture",
            "strategic alliance", "distribution deal",
        ],
        _NEWS_FILTER,
    ),
    # --- Contextual signals ---
    (
        "competitive",
        [
            "market share", "overtakes", "surpasses",
            "gains ground", "market leader", "displaces",
        ],
        _NEWS_FILTER,
    ),
    (
        "events",
        [
            "keynote", "developer conference", "dev day",
            "launch event", "demo day", "product showcase",
        ],
        _NEWS_FILTER,
    ),
    (
        "regulatory",
        [
            "AI regulation", "AI safety", "AI policy",
            "government contract", "EU AI Act",
            "executive order", "antitrust",
        ],
        _NEWS_FILTER,
    ),
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

    # ------------------------------------------------------------------
    # Rules management
    # ------------------------------------------------------------------

    def list_rules(self) -> List[dict]:
        """List all current rules on the tap."""
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

    # ------------------------------------------------------------------
    # Rule builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_company_or_clause(names: List[str]) -> str:
        """Build a Lucene OR clause for company names."""
        quoted = [f'"{n}"' for n in names]
        return f"({' OR '.join(quoted)})"

    @staticmethod
    def _build_keyword_or_clause(keywords: List[str]) -> str:
        quoted = [f'"{k}"' for k in keywords]
        return f"({' OR '.join(quoted)})"

    def _plan_rules(self, companies: List[dict]) -> List[dict]:
        """
        Plan the set of rules to create, staying within MAX_RULES.

        Companies are split into chunks so each chunk + signal type fits in one
        rule.  If the total exceeds MAX_RULES, lower-priority signal types are
        dropped.
        """
        names = [c["name"] for c in companies]
        chunk_size = 25
        name_chunks = [
            names[i : i + chunk_size]
            for i in range(0, len(names), chunk_size)
        ]

        planned: List[dict] = []
        for tag, keywords, extra_filters in SIGNAL_TYPES:
            for idx, chunk in enumerate(name_chunks):
                company_clause = self._build_company_or_clause(chunk)
                keyword_clause = self._build_keyword_or_clause(keywords)
                parts = [company_clause, "AND", keyword_clause]
                if extra_filters:
                    parts.append(extra_filters)
                parts.append('AND language:"en" AND recent:7d')
                query = " ".join(parts)
                suffix = f"_{idx + 1}" if len(name_chunks) > 1 else ""
                planned.append({"value": query, "tag": f"{tag}{suffix}"})

        # Trim to MAX_RULES — keep earlier (higher-priority) rules
        if len(planned) > MAX_RULES:
            print(f"⚠️  {len(planned)} rules planned, trimming to {MAX_RULES}")
            planned = planned[:MAX_RULES]

        return planned

    def setup_ai_company_rules(self, companies: List[dict]) -> List[dict]:
        """
        Replace all existing rules with intent-signal rules for *companies*.

        Returns the list of created rules.  Also populates self.rule_id_to_tag
        so we can map query_id UUIDs back to tag names during streaming.
        """
        # 1. Delete existing rules
        existing = self.list_rules()
        if existing:
            rules_data = existing.get("data", existing) if isinstance(existing, dict) else existing
            if rules_data:
                print(f"🗑️  Deleting {len(rules_data)} existing rules …")
                for rule in rules_data:
                    self._delete_rule(rule["id"])

        # 2. Plan & create new rules
        planned = self._plan_rules(companies)
        created: List[dict] = []
        self.rule_id_to_tag: Dict[str, str] = {}

        for rule_spec in planned:
            result = self._create_rule(rule_spec["value"], rule_spec["tag"])
            rule_data = result.get("data", result)
            created.append(rule_data)
            # Map rule UUID → tag for streaming
            self.rule_id_to_tag[rule_data["id"]] = rule_spec["tag"]
            print(f"   ✅ Rule created: [{rule_spec['tag']}] {rule_spec['value'][:80]}…")

        print(f"\n📡 {len(created)} rules active (max {MAX_RULES})")
        return created

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    @staticmethod
    def _match_company(text: str, companies: List[dict]) -> Optional[str]:
        """Return the first company name that appears in *text*."""
        text_lower = text.lower()
        for company in companies:
            if company["name"].lower() in text_lower:
                return company["name"]
        return None

    @staticmethod
    def _parse_sse_event(raw: str) -> Optional[dict]:
        """Parse a single SSE frame into (event_type, data_dict)."""
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

    def _extract_event(
        self, raw_event: dict, companies: List[dict],
    ) -> dict:
        """Transform a raw Firehose event into a clean event dict."""
        doc = raw_event.get("document", {})

        # Build summary from diff chunks or markdown
        summary = ""
        diff = doc.get("diff", {})
        if diff and diff.get("chunks"):
            parts = [
                chunk.get("text", "")
                for chunk in diff["chunks"]
                if chunk.get("typ") == "ins"
            ]
            summary = " ".join(parts)[:500]
        if not summary:
            summary = (doc.get("markdown") or "")[:500]

        title = doc.get("title", "")
        combined_text = f"{title} {summary}"

        source_url = doc.get("url", "")
        source_domain = urlparse(source_url).netloc if source_url else ""

        # Map query_id UUID → tag name, then strip chunk suffix (_1, _2)
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

    def stream_events(
        self,
        callback: Callable[[dict], None],
        companies: Optional[List[dict]] = None,
        duration: int = 300,
    ) -> None:
        """
        Connect to the Firehose SSE stream and call *callback* for each event.

        Streams for *duration* seconds (default 5 minutes).
        """
        companies = companies or []
        url = f"{BASE_URL}/v1/stream?timeout=60&since=30m&limit=100"
        end_time = time.time() + duration

        print(f"📡 Streaming events for {duration}s …")
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            if remaining <= 0:
                break
            try:
                with self.session.get(url, stream=True, timeout=remaining + 5) as resp:
                    resp.raise_for_status()
                    buffer = ""
                    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                        if time.time() >= end_time:
                            break
                        buffer += chunk
                        # SSE events are separated by double newlines
                        while "\n\n" in buffer:
                            frame, buffer = buffer.split("\n\n", 1)
                            raw_event = self._parse_sse_event(frame)
                            if raw_event:
                                event = self._extract_event(raw_event, companies)
                                callback(event)
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                print("⚠️  Connection lost, reconnecting …")
                time.sleep(2)

        print("✅ Stream finished")

    def collect_events(
        self,
        companies: Optional[List[dict]] = None,
        duration: int = 60,
    ) -> List[dict]:
        """Stream for *duration* seconds and return all collected events."""
        events: List[dict] = []

        def _collect(event: dict) -> None:
            events.append(event)

        self.stream_events(_collect, companies=companies, duration=duration)
        return events


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_companies(path: Path = AI_COMPANIES_FILE) -> List[dict]:
    """Load companies from the CSV."""
    companies: List[dict] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            companies.append({
                "name": row["name"].strip(),
                "website": row["website"].strip(),
                "category": row.get("category", "").strip(),
            })
    return companies


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

if __name__ == "__main__":
    companies = load_companies()
    print(f"📊 Loaded {len(companies)} AI companies from {AI_COMPANIES_FILE}")

    client = FirehoseClient()

    # Set up rules
    print("\n🔧 Setting up monitoring rules …")
    rules = client.setup_ai_company_rules(companies)

    # Stream events
    print(f"\n🎯 Streaming events for 60 seconds …\n")
    events = client.collect_events(companies=companies, duration=60)

    print(f"\n{'=' * 60}")
    print(f"📈 RESULTS: {len(events)} events captured")
    print(f"{'=' * 60}")
    for ev in events:
        company = ev.get("company_name") or "Unknown"
        signal = ev.get("signal_type", "?")
        title = ev.get("title", "")[:80]
        domain = ev.get("source_domain", "")
        print(f"   🔔 [{signal}] {company}: {title} ({domain})")
