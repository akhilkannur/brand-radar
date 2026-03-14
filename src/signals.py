"""
Brand Radar — Signal Processor for AI Companies

Processes raw Firehose events into intent scores for AI companies.
Like Winmo but for the AI sector: tracks signals that indicate an
AI company is about to spend on advertising/marketing.
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

# ---------------------------------------------------------------------------
# Signal config
# ---------------------------------------------------------------------------
SIGNAL_CONFIG = {
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
    def __init__(self, companies_file: str):
        self.companies = self._load_companies(companies_file)
        self._seen_hashes: set[str] = set()

    @staticmethod
    def _load_companies(companies_file: str) -> dict:
        companies = {}
        path = Path(companies_file)
        if not path.exists():
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

    def process_event(self, event: dict) -> Optional[dict]:
        company_name = event.get("company_name", "").strip()
        signal_type = event.get("signal_type", "").strip().lower()
        title = event.get("title", "").strip()
        if not company_name or not signal_type or not title:
            return None
        signal_type = self._normalize_signal_type(signal_type)
        if signal_type not in SIGNAL_CONFIG:
            signal_type = "product"
        if self._is_duplicate(event):
            return None
        source_domain = (event.get("source_domain") or "").strip().lower()
        matched_at = event.get("matched_at") or datetime.now().isoformat()
        strength = self._calculate_signal_strength(signal_type, source_domain, matched_at)
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
        aliases = {"marketing": "ad_spend", "product_launch": "product"}
        return aliases.get(raw, raw)

    def _calculate_signal_strength(self, signal_type: str, source_domain: str, matched_at: str) -> int:
        config = SIGNAL_CONFIG.get(signal_type)
        base = config["base_weight"] if config else 4
        source_mod = 1 if source_domain in HIGH_CREDIBILITY_SOURCES else 0 if source_domain in MID_CREDIBILITY_SOURCES else -2
        age_days = self._age_in_days(matched_at)
        recency_mod = 1 if age_days <= 3 else 0 if age_days <= 14 else -1 if age_days <= 30 else -2
        return max(1, min(10, base + source_mod + recency_mod))

    @staticmethod
    def _age_in_days(timestamp: str) -> int:
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return max(0, (datetime.now() - ts.replace(tzinfo=None)).days)
        except (ValueError, TypeError):
            return 30

    def calculate_intent_score(self, company_name: str, signals: list[dict]) -> dict:
        breakdown = {cat: 0.0 for cat in SIGNAL_CONFIG}
        for sig in signals:
            sig_type = sig.get("signal_type", "")
            if sig_type in SIGNAL_CONFIG:
                strength = sig.get("signal_strength", 5)
                cap = SIGNAL_CONFIG[sig_type]["score_cap"]
                breakdown[sig_type] = min(breakdown[sig_type] + (strength * 1.5), cap)
        total = int(min(sum(breakdown.values()), 100))
        breakdown_clean = {k: round(v, 1) for k, v in breakdown.items() if v > 0}
        trend = self._calculate_trend(signals, datetime.now())
        top_signals = sorted(signals, key=lambda s: s.get("signal_strength", 0), reverse=True)[:3]
        last_signal = max([s["timestamp"] for s in signals if s.get("timestamp")], default=None)
        insight = self._generate_insight(company_name, total, trend, breakdown_clean, top_signals)
        return {
            "company": company_name, "score": total, "trend": trend,
            "breakdown": breakdown_clean, "top_signals": top_signals,
            "signal_count": len(signals), "last_signal": last_signal, "insight": insight,
        }

    def _generate_insight(self, company: str, score: int, trend: str, breakdown: dict, top_signals: list[dict]) -> str:
        """Generate a professional agency-style strategic brief for the company."""
        if score == 0:
            return "Stable monitoring. No immediate high-intent triggers detected in the last 14 days."
        parts = []
        cats = set(breakdown.keys())
        if "agency_review" in cats:
            parts.append("🔴 **IMMINENT OPPORTUNITY:** Active agency search or RFP activity detected. Priority outreach recommended.")
        elif "leadership" in cats and "funding" in cats:
            parts.append("🔥 **CRITICAL WINDOW:** New leadership + fresh capital indicates a total GTM overhaul is likely in the next 3 months.")
        elif "leadership" in cats:
            parts.append("👔 **LEADERSHIP TRANSITION:** New executive stakeholders often review their agency roster within 90 days of joining.")
        elif "funding" in cats:
            parts.append("💰 **GROWTH PHASE:** Post-funding companies typically scale their paid media spend by 2x-5x to hit new user growth targets.")
        elif "ad_spend" in cats:
            parts.append("📢 **ACTIVE CAMPAIGN:** Current brand activity detected. Opportunity for performance optimization or social amplification.")
        if "hiring" in cats:
            parts.append("Marketing headcount growth suggests they are building internal teams but will need specialized agency support for execution.")
        if "product" in cats:
            parts.append("Recent product/model launches indicate a shift from R&D to commercialization—demand for lead gen and sales enablement is rising.")
        if "partnership" in cats:
            parts.append("Strategic partnerships suggest a move toward ecosystem marketing; look for co-branded activation opportunities.")
        if trend == "rising":
            parts.append("Signal momentum is **accelerating**, suggesting they are entering a heavy spending cycle.")
        if top_signals:
            parts.append(f"Latest Trigger: \"{top_signals[0].get('title', '')}\"")
        return " ".join(parts)

    @staticmethod
    def _calculate_trend(signals: list[dict], now: datetime) -> str:
        recent, older = 0, 0
        for sig in signals:
            ts_str = sig.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                age = (now - ts).days
                if age <= 7: recent += 1
                elif age <= 14: older += 1
            except: continue
        return "rising" if recent > older else "declining" if recent < older else "stable"

    def get_all_scores(self, all_signals: dict) -> list[dict]:
        scores = []
        for name, info in self.companies.items():
            res = self.calculate_intent_score(name, all_signals.get(name, []))
            res.update({"category": info.get("category", ""), "stage": info.get("stage", "")})
            scores.append(res)
        scores.sort(key=lambda s: s["score"], reverse=True)
        return scores

    def save_snapshot(self, scores: list[dict], output_dir: str) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        filepath = out / f"scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, "w") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "company_count": len(scores), "scores": scores}, f, indent=2, ensure_ascii=False)
        return filepath
