"""
Brand Radar - Hybrid Crawler (Crawl4AI + Firecrawl)
Combines Crawl4AI for signal detection + Firecrawl for structured data
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

# Crawl4AI imports
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Firecrawl extractor
from firecrawl_extractor import FirecrawlExtractor

# Data paths
DATA_DIR = Path(__file__).parent.parent / "data"
BRANDS_FILE = DATA_DIR / "brands.csv"
RESULTS_DIR = DATA_DIR / "raw"
RESULTS_DIR.mkdir(exist_ok=True)


class HybridBrandCrawler:
    """
    Hybrid crawler combining Crawl4AI + Firecrawl
    - Crawl4AI: Fast signal detection, keyword matching
    - Firecrawl: Structured data extraction (leadership, news, jobs)
    """
    
    def __init__(self, use_firecrawl: bool = False):
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        self.crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            word_count_threshold=10
        )
        
        # Initialize Firecrawl (optional)
        self.use_firecrawl = use_firecrawl
        self.firecrawl = FirecrawlExtractor() if use_firecrawl else None
    
    def _find_urls_to_crawl(self, base_url: str) -> List[str]:
        """Generate prioritized URLs to crawl - focus on NEWS and PRESS pages"""
        domain = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        base = f"https://{domain}"
        
        # PRIORITIZE newsroom/press pages where actual intelligence lives
        return [
            f"{base}/newsroom",      # Press releases (highest value)
            f"{base}/news",          # Company news
            f"{base}/press",         # Press center
            f"{base}/press-releases",# Official releases
            f"{base}/media",         # Media center
            f"{base}/media-center",
            f"{base}/about/leadership",  # Leadership team
            f"{base}/about",         # About page
            f"{base}/careers",       # Job postings
            base_url,                # Homepage (lowest priority)
        ]
    
    async def crawl_brand(self, name: str, base_url: str) -> dict:
        """
        Crawl brand using both Crawl4AI and Firecrawl
        
        Returns enriched data structure
        """
        print(f"🕷️  Crawling: {name} ({base_url})")
        
        # === CRAWL4AI: Fast signal detection ===
        crawl4ai_result = await self._crawl_with_crawl4ai(base_url)
        
        if not crawl4ai_result["success"]:
            return crawl4ai_result
        
        # === FIRECRAWL: Structured data extraction ===
        firecrawl_data = {}
        if self.use_firecrawl and self.firecrawl:
            print(f"   🔥 Firecrawl extracting structured data...")
            firecrawl_data = await self._extract_with_firecrawl(name, base_url)
        
        # === Combine results ===
        result = crawl4ai_result
        result["firecrawl_data"] = firecrawl_data
        
        # Calculate enhanced intent score
        result["intent_score"] = self._calculate_enhanced_score(result)
        
        return result
    
    async def _crawl_with_crawl4ai(self, base_url: str) -> dict:
        """Use Crawl4AI for fast signal detection"""
        urls_to_crawl = self._find_urls_to_crawl(base_url)
        crawled_urls = []
        all_content = []
        max_pages = 3
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            for url in urls_to_crawl[:max_pages]:
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
                    pass
        
        if not crawled_urls:
            return {
                "name": base_url.split("//")[1].split("/")[0],
                "url": base_url,
                "success": False,
                "error": "No pages could be crawled"
            }
        
        combined_content = "\n\n".join(all_content)
        signals = self._extract_signals(combined_content)
        
        return {
            "url": base_url,
            "success": True,
            "crawled_at": datetime.now().isoformat(),
            "crawled_urls": crawled_urls,
            "pages_crawled": len(crawled_urls),
            "signals": signals,
            "content_length": len(combined_content),
            "raw_content_sample": combined_content[:1000]
        }
    
    async def _extract_with_firecrawl(self, name: str, base_url: str) -> dict:
        """Use Firecrawl for structured data extraction"""
        domain = base_url.replace("https://", "").replace("http://", "").split("/")[0]
        base = f"https://{domain}"
        
        data = {
            "company_info": None,
            "leadership": None,
            "news": None,
            "jobs": None
        }
        
        # Extract company info from homepage
        data["company_info"] = self.firecrawl.extract_company_info(base_url)
        
        # Extract leadership from about page
        data["leadership"] = self.firecrawl.extract_leadership(f"{base}/about")
        
        # Extract news from newsroom
        data["news"] = self.firecrawl.extract_news(f"{base}/newsroom")
        
        # Extract jobs from careers page
        data["jobs"] = self.firecrawl.extract_jobs(f"{base}/careers")
        
        return data
    
    def _extract_signals(self, content: str) -> dict:
        """Extract intent signals using regex patterns"""
        content_lower = content.lower()
        
        # Leadership signals
        leadership_patterns = [
            r"(appointed|named|joined).*(chief|cmo|ceo|cfo|presid)",
            r"(chief|cmo|ceo|cfo).*(announc|join|leav)",
            r"new (chief|cmo|ceo|cfo)",
            r"(chief marketing officer|chief executive|chief financial)",
        ]
        leadership_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in leadership_patterns
        )
        
        # Hiring signals
        hiring_patterns = [
            r"(hiring|joining|seeking).*(marketing|brand|growth)",
            r"(marketing|brand).*(manager|director|vp|head)",
            r"careers.*marketing",
        ]
        hiring_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in hiring_patterns
        )
        
        if "careers" in content_lower or "join our team" in content_lower:
            hiring_count += 2
        
        # Campaign signals
        campaign_patterns = [
            r"(launch|unveil|introduce|announce).*(campaign|product|collection)",
            r"(new campaign|new product|new collection)",
            r"(coming soon|stay tuned)",
        ]
        campaign_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in campaign_patterns
        )
        
        # Tech stack signals
        tech_patterns = [
            r"(tiktok pixel|meta pixel|facebook pixel)",
            r"(google analytics|ga4|google tag)",
            r"(shopify|woocommerce|magento)",
        ]
        tech_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in tech_patterns
        )
        
        # Partnership signals
        partnership_patterns = [
            r"(partnership|partner|collaborat).*(brand|company)",
            r"(sponsor|sponsored|ambassador)",
            r"(press release|media kit)",
        ]
        partnership_count = sum(
            len(re.findall(pattern, content_lower)) 
            for pattern in partnership_patterns
        )
        
        # Freshness bonus
        freshness_score = 0
        if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec).*(2025|2026)", content_lower):
            freshness_score = 10
        elif "2025" in content or "2026" in content:
            freshness_score = 5
        
        return {
            "leadership": leadership_count,
            "hiring": hiring_count,
            "campaigns": campaign_count,
            "tech": tech_count,
            "partnerships": partnership_count,
            "freshness": freshness_score
        }
    
    def _calculate_enhanced_score(self, result: dict) -> int:
        """Calculate enhanced intent score with Firecrawl data"""
        s = result.get("signals", {})
        fc_data = result.get("firecrawl_data", {})
        
        # Base score from Crawl4AI signals
        score = (
            min(s.get("leadership", 0) * 8, 30) +
            min(s.get("hiring", 0) * 4, 25) +
            min(s.get("campaigns", 0) * 5, 20) +
            min(s.get("tech", 0) * 5, 15) +
            min(s.get("partnerships", 0) * 4, 10) +
            min(s.get("freshness", 0), 10)
        )
        
        # Bonus from Firecrawl structured data
        if fc_data:
            # Leadership bonus
            leadership = fc_data.get("leadership", {})
            if leadership and leadership.get("marketing_leadership"):
                score += min(len(leadership["marketing_leadership"]) * 5, 15)
            
            # News bonus (recent announcements)
            news = fc_data.get("news", {})
            if news and news.get("recent_announcements"):
                score += min(len(news["recent_announcements"]) * 3, 10)
            
            # Jobs bonus (marketing hiring)
            jobs = fc_data.get("jobs", {})
            if jobs and jobs.get("marketing_jobs"):
                score += min(len(jobs["marketing_jobs"]) * 4, 15)
        
        return int(min(score, 100))


async def main():
    """Main crawler entry point"""
    # Set use_firecrawl=False if no API key (will use fallback mode)
    use_firecrawl = False  # Change to True if you have FIRECRAWL_API_KEY
    
    crawler = HybridBrandCrawler(use_firecrawl=use_firecrawl)
    
    # Load brands
    brands = []
    with open(BRANDS_FILE, "r") as f:
        next(f)
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
    
    print(f"📊 Starting hybrid crawl of {len(brands)} brands...")
    print(f"   Mode: {'Crawl4AI + Firecrawl' if use_firecrawl else 'Crawl4AI only (Firecrawl in fallback mode)'}\n")
    
    results = []
    # Crawl first 20 brands for better data
    for i, brand in enumerate(brands[:20], 1):
        print(f"\n{'='*60}")
        print(f"[{i}/10] Processing {brand['name']}...")
        print(f"{'='*60}")
        
        result = await crawler.crawl_brand(brand["name"], brand["url"])
        
        if result["success"]:
            print(f"\n   📊 Intent Score: {result['intent_score']}")
            print(f"   📄 Pages crawled: {result.get('pages_crawled', 0)}")
            print(f"   📈 Signals: {result['signals']}")
            
            if result.get("firecrawl_data"):
                fc = result["firecrawl_data"]
                if fc.get("company_info"):
                    print(f"   🏢 Company: {fc['company_info'].get('company_name', 'N/A')}")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        results.append(result)
        
        # Save results
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
            print(f"   • {b.get('name', 'Unknown')}: {b['intent_score']}")


if __name__ == "__main__":
    asyncio.run(main())
