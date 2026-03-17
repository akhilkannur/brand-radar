"""
Brand Radar — SEC EDGAR Client (EFTS Full-Text Search)
Detects funding, IPO, and regulatory filings for AI companies.
Free, no API key required.
"""

import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import requests

# SEC filing types that indicate spend-related events
FILING_SIGNAL_MAP = {
    "S-1": "funding",      # IPO registration
    "S-1/A": "funding",
    "10-K": "revenue",     # Annual report
    "10-Q": "revenue",     # Quarterly report
    "8-K": "leadership",   # Material events (exec changes, M&A, etc.)
    "SC 13D": "funding",   # Significant ownership
    "DEF 14A": "leadership",  # Proxy statement (board/exec changes)
    "D": "funding",        # Reg D (private placement / fundraise)
    "D/A": "funding",
}


class SECClient:
    """Fetch signals from SEC EDGAR full-text search — free, no auth."""

    EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
    EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, pause: float = 1.0):
        self.pause = pause
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BrandRadar research@brandradar.ai",
            "Accept": "application/json",
        })

    def _search_filings(self, query: str, limit: int = 10) -> List[dict]:
        """Search SEC EDGAR full-text search for a company."""
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": f'"{query}"',
            "dateRange": "custom",
            "startdt": (datetime.now().replace(day=1)).strftime("%Y-%m-%d"),
            "enddt": datetime.now().strftime("%Y-%m-%d"),
            "forms": ",".join(FILING_SIGNAL_MAP.keys()),
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("hits", {}).get("hits", [])[:limit]
        except (requests.RequestException, ValueError, KeyError):
            return []

    def _search_efts(self, query: str, limit: int = 10) -> List[dict]:
        """Alternative: use the EDGAR full-text search API."""
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": f'"{query}"',
            "forms": ",".join(FILING_SIGNAL_MAP.keys()),
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("hits", {}).get("hits", [])[:limit]
        except (requests.RequestException, ValueError):
            return []

    def collect_signals(self, companies: List[dict], max_per_company: int = 5) -> List[dict]:
        """Collect SEC filing signals for companies."""
        all_signals = []
        for company in companies:
            name = company["name"]
            filings = self._search_filings(name, limit=max_per_company)
            if not filings:
                filings = self._search_efts(name, limit=max_per_company)

            for filing in filings:
                source = filing.get("_source", {})
                form_type = source.get("form_type", "")
                file_date = source.get("file_date", "")
                entity_name = source.get("entity_name", "")
                file_num = source.get("file_num", "")
                display_names = source.get("display_names", [])

                signal_type = FILING_SIGNAL_MAP.get(form_type, "funding")
                filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={quote(name)}&type={form_type}&dateb=&owner=include&count=10"

                matched_at = file_date if file_date else datetime.now().isoformat()

                all_signals.append({
                    "company_name": name,
                    "signal_type": signal_type,
                    "title": f"SEC {form_type} Filing: {entity_name or name}",
                    "url": filing_url,
                    "matched_at": matched_at,
                    "summary": f"SEC {form_type} filing detected for {entity_name or name}. Form type indicates {signal_type} activity.",
                    "source_domain": "sec.gov",
                })
            time.sleep(self.pause)
        return all_signals
