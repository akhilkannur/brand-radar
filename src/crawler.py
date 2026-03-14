"""
Brand Radar - Crawl4AI Crawler v2
Extracts intent signals from brand websites + press pages + careers pages
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Crawl4AI imports (from findsday-airtable venv)
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
BRANDS_FILE = DATA_DIR / "brands.csv"
RESULTS_DIR = DATA_DIR / "raw"
RESULTS_DIR.mkdir(exist_ok=True)


class BrandCrawler:
    """Crawl brand websites for intent signals"""
    
    def __init__(self):
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        self.crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            word_count_threshold=10
        )
    
    def _find_subdomain_urls(self, base_url: str) -> List[str]:
        """Generate likely press/careers URLs from base URL"""
        # Extract domain
        domain = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        base = f"https://{domain}"
        
        # Prioritized URLs - most likely to have signals
        urls_to_try = [
            base_url,  # Main site (always)
            f"{base}/newsroom",  # Press (priority 1)
            f"{base}/news",      # Press (priority 2)
            f"{base}/press",     # Press (priority 3)
            f"{base}/careers",   # Careers (priority 1)
        ]
        
        return urls_to_try
    
    async def crawl_multiple_pages(self, name: str, base_url: str) -> dict:
        """
        Crawl main site + press/careers pages
        Returns aggregated signals
        """
        print(f"🕷️  Crawling: {name} ({base_url})")
        
        urls_to_try = self._find_subdomain_urls(base_url)
        crawled_urls = []
        all_content = []
        max_pages = 3  # Limit pages per brand for speed
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            for url in urls_to_try[:max_pages]:
                try:
                    result = await crawler.arun(
                        url=url,
                        config=self.crawler_config,
                        bypass_cache=True
                    )
                    
                    if result.success:
                        crawled_urls.append(url)
                        all_content.append(result.markdown)
                        print(f"   ✓ {url}")
                    
                except Exception:
                    pass  # Skip failed URLs silently
            
            if not crawled_urls:
                return {
                    "name": name,
                    "url": base_url,
                    "success": False,
                    "error": "No pages could be crawled"
                }
        
        # Combine all content
        combined_content = "\n\n".join(all_content)
        
        # Extract signals
        signals = self.extract_signals(name, base_url, combined_content)
        signals["crawled_urls"] = crawled_urls
        signals["pages_crawled"] = len(crawled_urls)
        
        return signals
    
    def extract_signals(self, name: str, url: str, content: str) -> dict:
        """
        Extract intent signals from crawled content
        v2: Improved extraction with context awareness
        """
        content_lower = content.lower()
        
        # === LEADERSHIP SIGNALS (30% weight) ===
        # Look for executive titles + action words
        leadership_patterns = [
            r"(appointed|named|joined).*(chief|cmo|ceo|cfo|presid)",
            r"(chief|cmo|ceo|cfo).*(announc|join|leav)",
            r"new (chief|cmo|ceo|cfo)",
            r"(chief marketing officer|chief executive|chief financial)",
            r"(ceo|cmo|cfo|president).*(quarter|month|year)",
        ]
        leadership_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in leadership_patterns
        )
        
        # === HIRING SIGNALS (25% weight) ===
        # Marketing role indicators
        hiring_patterns = [
            r"(hiring|joining|seeking).*(marketing|brand|growth)",
            r"(marketing|brand).*(manager|director|vp|head)",
            r"(growth|performance).*(marketing)",
            r"careers.*marketing",
            r"marketing.*careers",
            r"(we'?re hiring|join our team|join us).*(marketing)",
        ]
        hiring_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in hiring_patterns
        )
        
        # Also count generic "careers" mentions (lower weight)
        if "careers" in content_lower or "join our team" in content_lower:
            hiring_count += 2
        
        # === CAMPAIGN/PRODUCT SIGNALS (20% weight) ===
        # Launch and campaign indicators
        campaign_patterns = [
            r"(launch|unveil|introduce|announce).*(campaign|product|collection)",
            r"(new campaign|new product|new collection)",
            r"(coming soon|stay tuned|get ready)",
            r"(spring|summer|fall|winter) (2025|2026) collection",
            r"(holiday|summer|back to school).*(campaign)",
        ]
        campaign_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in campaign_patterns
        )
        
        # === TECH STACK SIGNALS (15% weight) ===
        # Marketing technology indicators
        tech_patterns = [
            r"(tiktok pixel|meta pixel|facebook pixel)",
            r"(google analytics|ga4|google tag)",
            r"(shopify|woocommerce|magento)",
            r"(salesforce|hubspot|marketo|pardot)",
            r"(optimizely|vwo|adobe target)",
            r"(segment|rudderstack|mparticle)",
        ]
        tech_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in tech_patterns
        )
        
        # === PARTNERSHIP/PRESS SIGNALS (10% weight) ===
        # Collaboration and media mentions
        partnership_patterns = [
            r"(partnership|partner|collaborat).*(brand|company)",
            r"(sponsor|sponsored|ambassador)",
            r"(press release|media kit|media contact)",
            r"(award|recognized|honored)",
            r"(collab|limited edition).*(drop|launch)",
        ]
        partnership_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in partnership_patterns
        )
        
        # === FRESHNESS SIGNAL (bonus) ===
        # Check for recent dates (2025, 2026)
        freshness_score = 0
        if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec).*(2025|2026)", content_lower):
            freshness_score = 10
        elif "2025" in content or "2026" in content:
            freshness_score = 5
        
        return {
            "name": name,
            "url": url,
            "success": True,
            "crawled_at": datetime.now().isoformat(),
            "signals": {
                "leadership": leadership_count,
                "hiring": hiring_count,
                "campaigns": campaign_count,
                "tech": tech_count,
                "partnerships": partnership_count,
                "freshness": freshness_score
            },
            "content_length": len(content),
            "raw_content_sample": content[:1000]  # First 1000 chars for debugging
        }
    
    def calculate_intent_score(self, signals: dict) -> int:
        """
        Calculate intent score (0-100) from extracted signals
        v2: Includes freshness bonus
        """
        s = signals.get("signals", {})
        
        # Weighted score with caps
        score = (
            min(s.get("leadership", 0) * 8, 30) +      # Max 30
            min(s.get("hiring", 0) * 4, 25) +          # Max 25
            min(s.get("campaigns", 0) * 5, 20) +       # Max 20
            min(s.get("tech", 0) * 5, 15) +            # Max 15
            min(s.get("partnerships", 0) * 4, 10) +    # Max 10
            min(s.get("freshness", 0), 10)             # Max 10 (bonus)
        )
        
        return int(min(score, 100))


async def main():
    """Main crawler entry point"""
    crawler = BrandCrawler()
    
    # Load brands list
    brands = []
    with open(BRANDS_FILE, "r") as f:
        next(f)  # Skip header
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",", 2)
            if len(parts) >= 2:
                name = parts[0].strip()
                url = parts[1].strip()
                if url.startswith("http"):
                    brands.append({"name": name, "url": url})
    
    print(f"📊 Starting crawl of {len(brands)} brands...")
    print(f"   Will crawl: main site + press + careers pages per brand\n")
    
    results = []
    for i, brand in enumerate(brands[:10], 1):  # Start with first 10 for testing
        print(f"\n{'='*50}")
        print(f"[{i}/10] Processing {brand['name']}...")
        print(f"{'='*50}")
        
        result = await crawler.crawl_multiple_pages(brand["name"], brand["url"])
        
        if result["success"]:
            result["intent_score"] = crawler.calculate_intent_score(result)
            print(f"\n   📊 Intent Score: {result['intent_score']}")
            print(f"   📄 Pages crawled: {result.get('pages_crawled', 0)}")
            print(f"   📈 Signals: {result['signals']}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        results.append(result)
        
        # Save after each crawl (resilience)
        output_file = RESULTS_DIR / f"{brand['name'].lower().replace(' ', '_')}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
    
    # Summary
    print("\n" + "="*60)
    print("📈 CRAWL COMPLETE")
    print("="*60)
    
    successful = [r for r in results if r.get("success")]
    print(f"Successful: {len(successful)}/{len(results)}")
    
    if successful:
        avg_score = sum(r["intent_score"] for r in successful) / len(successful)
        print(f"Average Intent Score: {avg_score:.1f}")
        
        top_brands = sorted(successful, key=lambda x: x["intent_score"], reverse=True)[:5]
        print("\n🔥 Top 5 Brands by Intent:")
        for b in top_brands:
            print(f"   • {b['name']}: {b['intent_score']} (pages: {b.get('pages_crawled', '?')})")


if __name__ == "__main__":
    asyncio.run(main())
