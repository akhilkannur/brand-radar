"""
Brand Radar — Signal Processor for AI Companies

Processes raw Firehose events into intent scores for AI companies.
Like Winmo but for the AI sector: tracks signals that indicate an
AI company is about to spend on advertising/marketing.

Usage:
    from signals import SignalProcessor

    processor = SignalProcessor("data/ai_companies.csv")
    signal = processor.process_event(event)
    score = processor.calculate_intent_score("OpenAI", signals)
"""

import csv
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

# ---------------------------------------------------------------------------
# Source credibility tiers
# ---------------------------------------------------------------------------
HIGH_CREDIBILITY_SOURCES = {
    # Tier-1 tech/business press
    "techcrunch.com", "reuters.com", "bloomberg.com", "wsj.com",
    "nytimes.com", "ft.com", "theinformation.com", "cnbc.com",
    "venturebeat.com", "wired.com", "fortune.com", "forbes.com",
    "semafor.com", "axios.com", "theverge.com",
    # Ad industry press (critical for agency/spend signals)
    "adage.com", "adweek.com", "campaignlive.com", "digiday.com",
    "marketingweek.com", "thedrum.com", "mediapost.com",
}
MID_CREDIBILITY_SOURCES = {
    "arstechnica.com", "zdnet.com", "businessinsider.com",
    "thenextweb.com", "techradar.com", "engadget.com", "cnet.com",
    "analyticsinsight.net", "artificialintelligence-news.com",
    "ainews.com", "hbr.org", "medium.com", "substack.com",
    # Job boards (valuable for hiring signals)
    "linkedin.com", "greenhouse.io", "lever.co", "ashbyhq.com",
    "wellfound.com",
    # Regulatory / policy
    "sec.gov", "ftc.gov", "congress.gov",
}
# Everything else is low credibility

# ---------------------------------------------------------------------------
# Signal config: base weight, score cap, and "why it matters" context
# ---------------------------------------------------------------------------
SIGNAL_CONFIG = {
    # === Direct ad-spend intent (most valuable) ===
    "agency_review": {
        "base_weight": 10,
        "score_cap": 20,
        "why": "Agency review in progress — actively looking for ad partners",
    },
    "ad_spend": {
        "base_weight": 9,
        "score_cap": 15,
        "why": "Active advertising or brand campaign — confirmed spend",
    },
    # === Strong spend predictors ===
    "funding": {
        "base_weight": 8,
        "score_cap": 15,
        "why": "Fresh capital typically leads to marketing spend within 3-6 months",
    },
    "revenue": {
        "base_weight": 7,
        "score_cap": 10,
        "why": "Revenue milestone signals scale-up phase — marketing budgets follow",
    },
    "leadership": {
        "base_weight": 7,
        "score_cap": 12,
        "why": "New marketing/executive leadership often triggers agency reviews",
    },
    # === Medium predictors ===
    "product": {
        "base_weight": 6,
        "score_cap": 10,
        "why": "New product launches need marketing support and GTM spend",
    },
    "hiring": {
        "base_weight": 6,
        "score_cap": 8,
        "why": "Marketing hiring signals intent to build in-house or scale spend",
    },
    "partnership": {
        "base_weight": 5,
        "score_cap": 8,
        "why": "Partnerships drive co-marketing budgets and joint campaigns",
    },
    # === Contextual signals ===
    "competitive": {
        "base_weight": 5,
        "score_cap": 5,
        "why": "Competitive pressure forces increased marketing spend to defend position",
    },
    "events": {
        "base_weight": 4,
        "score_cap": 5,
        "why": "Event presence indicates active marketing — booth, keynote, demo spend",
    },
    "regulatory": {
        "base_weight": 3,
        "score_cap": 2,
        "why": "Regulatory attention may drive brand trust/safety campaigns",
    },
}


class SignalProcessor:
    """Processes Firehose events into intent scores for AI companies."""

    def __init__(self, companies_file: str):
        self.companies = self._load_companies(companies_file)
        self._seen_hashes: set[str] = set()

    # ------------------------------------------------------------------
    # Company loading
    # ------------------------------------------------------------------
    @staticmethod
    def _load_companies(companies_file: str) -> dict:
        """Load AI companies from CSV into a lookup dict keyed by name."""
        companies = {}
        path = Path(companies_file)
        if not path.exists():
            print(f"⚠️  Companies file not found: {companies_file}")
            return companies

        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                if name:
                    companies[name] = {
                        "name": name,
                        "website": row.get("website", "").strip(),
                        "category": row.get("category", "").strip(),
                        "stage": row.get("stage", "").strip(),
                        "notable": row.get("notable", "").strip(),
                    }
        return companies

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------
    @staticmethod
    def _event_hash(event: dict) -> str:
        key = f"{event.get('company_name', '')}|{event.get('signal_type', '')}|{event.get('url', '')}"
        return hashlib.md5(key.encode()).hexdigest()

    def _is_duplicate(self, event: dict) -> bool:
        h = self._event_hash(event)
        if h in self._seen_hashes:
            return True
        self._seen_hashes.add(h)
        return False

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------
    def process_event(self, event: dict) -> Optional[dict]:
        """
        Process a raw Firehose event dict into a structured signal.

        Returns a structured signal dict, or None if duplicate/invalid.
        """
        company_name = event.get("company_name", "").strip()
        signal_type = event.get("signal_type", "").strip().lower()
        title = event.get("title", "").strip()

        if not company_name or not signal_type or not title:
            return None

        # Normalize aliases
        signal_type = self._normalize_signal_type(signal_type)

        if signal_type not in SIGNAL_CONFIG:
            signal_type = "product"

        if self._is_duplicate(event):
            return None

        source_domain = (event.get("source_domain") or "").strip().lower()
        matched_at = event.get("matched_at") or datetime.now().isoformat()

        strength = self._calculate_signal_strength(
            signal_type, source_domain, matched_at
        )

        config = SIGNAL_CONFIG[signal_type]

        return {
            "company": company_name,
            "signal_type": signal_type,
            "signal_strength": strength,
            "title": title,
            "url": event.get("url", ""),
            "source": source_domain,
            "timestamp": matched_at,
            "summary": event.get("summary", ""),
            "why_it_matters": config["why"],
        }

    @staticmethod
    def _normalize_signal_type(raw: str) -> str:
        aliases = {
            "agency_marketing": "agency_review",
            "marketing": "ad_spend",
            "product_launch": "product",
        }
        return aliases.get(raw, raw)

    def _calculate_signal_strength(
        self, signal_type: str, source_domain: str, matched_at: str
    ) -> int:
        """
        Determine signal strength (1-10) from:
        - Signal type base weight
        - Source credibility modifier
        - Recency modifier
        """
        config = SIGNAL_CONFIG.get(signal_type)
        base = config["base_weight"] if config else 4

        # Source credibility modifier (-2 to +1)
        if source_domain in HIGH_CREDIBILITY_SOURCES:
            source_mod = 1
        elif source_domain in MID_CREDIBILITY_SOURCES:
            source_mod = 0
        else:
            source_mod = -2

        # Recency modifier (-2 to +1)
        age_days = self._age_in_days(matched_at)
        if age_days <= 3:
            recency_mod = 1
        elif age_days <= 14:
            recency_mod = 0
        elif age_days <= 30:
            recency_mod = -1
        else:
            recency_mod = -2

        return max(1, min(10, base + source_mod + recency_mod))

    @staticmethod
    def _age_in_days(timestamp: str) -> int:
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return max(0, (datetime.now() - ts.replace(tzinfo=None)).days)
        except (ValueError, TypeError):
            return 30

    # ------------------------------------------------------------------
    # Intent scoring
    # ------------------------------------------------------------------
    def calculate_intent_score(
        self, company_name: str, signals: list[dict]
    ) -> dict:
        """
        Calculate 0-100 intent score for a company from its recent signals.

        Returns dict with score, trend, breakdown, top signals, insight, etc.
        """
        breakdown = {cat: 0.0 for cat in SIGNAL_CONFIG}
        now = datetime.now()

        for sig in signals:
            sig_type = sig.get("signal_type", "")
            if sig_type not in SIGNAL_CONFIG:
                continue

            strength = sig.get("signal_strength", 5)
            cap = SIGNAL_CONFIG[sig_type]["score_cap"]
            contribution = strength * 1.5
            breakdown[sig_type] = min(breakdown[sig_type] + contribution, cap)

        total = int(min(sum(breakdown.values()), 100))

        # Only include non-zero categories in output
        breakdown_clean = {k: round(v, 1) for k, v in breakdown.items() if v > 0}

        trend = self._calculate_trend(signals, now)

        sorted_signals = sorted(
            signals, key=lambda s: s.get("signal_strength", 0), reverse=True
        )
        top_signals = sorted_signals[:3]

        timestamps = [s["timestamp"] for s in signals if s.get("timestamp")]
        last_signal = max(timestamps) if timestamps else None

        insight = self._generate_insight(
            company_name, total, trend, breakdown_clean, top_signals
        )

        return {
            "company": company_name,
            "score": total,
            "trend": trend,
            "breakdown": breakdown_clean,
            "top_signals": top_signals,
            "signal_count": len(signals),
            "last_signal": last_signal,
            "insight": insight,
        }

    def _generate_insight(
        self,
        company: str,
        score: int,
        trend: str,
        breakdown: dict,
        top_signals: list[dict],
    ) -> str:
        """Generate a human-readable insight explaining why this company matters."""
        if score == 0:
            return "No recent signals detected."

        parts = []

        # Lead with the strongest signal category
        if breakdown:
            top_cat = max(breakdown, key=breakdown.get)
            config = SIGNAL_CONFIG.get(top_cat, {})
            parts.append(config.get("why", ""))

        # Momentum context
        if trend == "rising":
            parts.append("Signal volume is increasing — likely entering active spend phase.")
        elif trend == "declining":
            parts.append("Signal activity is slowing down.")

        # High-value combo signals
        cats = set(breakdown.keys())
        if {"agency_review", "leadership"} <= cats:
            parts.append("⚡ New leadership + agency review = high probability of imminent spend.")
        elif {"funding", "hiring"} <= cats:
            parts.append("💰 Fresh capital + marketing hires = building for launch.")
        elif {"ad_spend", "product"} <= cats:
            parts.append("🚀 Active campaign + new product = marketing in full swing.")
        elif {"funding", "product"} <= cats:
            parts.append("📦 Funded + launching = GTM spend incoming.")

        # Top headline for specificity
        if top_signals:
            parts.append(f'Latest: "{top_signals[0].get("title", "")}"')

        return " ".join(parts)

    @staticmethod
    def _calculate_trend(signals: list[dict], now: datetime) -> str:
        """Determine trend from signal recency distribution."""
        recent_count = 0  # last 7 days
        older_count = 0   # 8-14 days ago

        for sig in signals:
            ts_str = sig.get("timestamp", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ts_naive = ts.replace(tzinfo=None)
                age_days = (now - ts_naive).days
            except (ValueError, TypeError):
                continue

            if age_days <= 7:
                recent_count += 1
            elif age_days <= 14:
                older_count += 1

        if recent_count > older_count:
            return "rising"
        elif recent_count < older_count:
            return "declining"
        return "stable"

    # ------------------------------------------------------------------
    # Batch scoring
    # ------------------------------------------------------------------
    def get_all_scores(self, all_signals: dict[str, list[dict]]) -> list[dict]:
        """
        Score all companies. Returns sorted list (highest score first).

        Args:
            all_signals: dict of {company_name: [signal dicts]}

        Companies with zero signals are included with score 0.
        """
        scores = []

        # Score every known company
        scored_names = set()
        for name, info in self.companies.items():
            company_signals = all_signals.get(name, [])
            result = self.calculate_intent_score(name, company_signals)
            result["category"] = info.get("category", "")
            result["stage"] = info.get("stage", "")
            scores.append(result)
            scored_names.add(name)

        # Score companies that appear in signals but aren't in our CSV
        for name, company_signals in all_signals.items():
            if name not in scored_names:
                result = self.calculate_intent_score(name, company_signals)
                result["category"] = "Unknown"
                result["stage"] = "Unknown"
                scores.append(result)

        scores.sort(key=lambda s: s["score"], reverse=True)
        return scores

    # ------------------------------------------------------------------
    # Snapshot persistence
    # ------------------------------------------------------------------
    def save_snapshot(self, scores: list[dict], output_dir: str) -> Path:
        """Save current scores to a timestamped JSON file for historical tracking."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = out / f"scores_{timestamp}.json"

        snapshot = {
            "generated_at": datetime.now().isoformat(),
            "company_count": len(scores),
            "scores": scores,
        }

        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)

        print(f"💾 Snapshot saved → {filepath}")
        return filepath


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    companies_file = str(DATA_DIR / "ai_companies.csv")
    processor = SignalProcessor(companies_file)

    print("=" * 70)
    print("🔍 Brand Radar — Signal Processor")
    print("=" * 70)
    print(f"   Loaded {len(processor.companies)} AI companies")
    print(f"   Tracking {len(SIGNAL_CONFIG)} signal types:")
    for sig_type, config in SIGNAL_CONFIG.items():
        print(f"      • {sig_type:16s} (weight={config['base_weight']}, cap={config['score_cap']:2d}) — {config['why']}")
    print(f"\n   Run with Firehose data: python src/firehose_client.py")
