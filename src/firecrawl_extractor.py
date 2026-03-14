"""
Firecrawl Integration Module
Extract structured data from brand websites using Firecrawl
"""

import os
from typing import Optional, Dict, Any
from firecrawl import FirecrawlApp


class FirecrawlExtractor:
    """
    Extract structured company data using Firecrawl
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl
        
        Args:
            api_key: Firecrawl API key (optional, uses FREE tier if not provided)
        """
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.app = FirecrawlApp(api_key=self.api_key) if self.api_key else None
        
        # Define extraction schema for company data
        self.company_schema = {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Official company name"
                },
                "industry": {
                    "type": "string",
                    "description": "Company industry/sector"
                },
                "description": {
                    "type": "string",
                    "description": "Brief company description"
                },
                "headquarters": {
                    "type": "string",
                    "description": "Company headquarters location"
                },
                "employee_count": {
                    "type": "string",
                    "description": "Number of employees or range"
                },
                "revenue": {
                    "type": "string",
                    "description": "Annual revenue if mentioned"
                },
                "founded_year": {
                    "type": "string",
                    "description": "Year company was founded"
                }
            },
            "required": ["company_name"]
        }
        
        # Schema for leadership team
        self.leadership_schema = {
            "type": "object",
            "properties": {
                "executives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"},
                            "department": {"type": "string"}
                        },
                        "required": ["name", "title"]
                    }
                },
                "marketing_leadership": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "title": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        # Schema for recent news/press releases
        self.news_schema = {
            "type": "object",
            "properties": {
                "press_releases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "date": {"type": "string"},
                            "summary": {"type": "string"},
                            "category": {"type": "string"}
                        }
                    }
                },
                "recent_announcements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "type": {"type": "string"},
                            "date": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        # Schema for job postings
        self.jobs_schema = {
            "type": "object",
            "properties": {
                "marketing_jobs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "department": {"type": "string"},
                            "location": {"type": "string"},
                            "type": {"type": "string"}
                        }
                    }
                },
                "total_jobs": {
                    "type": "number"
                }
            }
        }
    
    def extract_company_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract company metadata from homepage
        
        Args:
            url: Company homepage URL
            
        Returns:
            Dictionary with company information
        """
        if not self.app:
            return self._fallback_company_extract(url)
        
        try:
            result = self.app.extract(
                url,
                {
                    "prompt": "Extract company information: name, industry, description, headquarters, employee count, revenue, founded year",
                    "schema": self.company_schema
                }
            )
            return result.get("data", {})
        except Exception as e:
            print(f"   ⚠️  Firecrawl company extract failed: {e}")
            return self._fallback_company_extract(url)
    
    def extract_leadership(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract leadership team information
        
        Args:
            url: Company about/leadership page URL
            
        Returns:
            Dictionary with executive information
        """
        if not self.app:
            return self._fallback_leadership_extract(url)
        
        try:
            result = self.app.extract(
                url,
                {
                    "prompt": "Extract executive team and leadership members with their names and titles. Focus on C-level executives and especially marketing leadership (CMO, VP Marketing, etc.)",
                    "schema": self.leadership_schema
                }
            )
            return result.get("data", {})
        except Exception as e:
            print(f"   ⚠️  Firecrawl leadership extract failed: {e}")
            return self._fallback_leadership_extract(url)
    
    def extract_news(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract recent press releases and announcements
        
        Args:
            url: Company newsroom/press page URL
            
        Returns:
            Dictionary with recent news
        """
        if not self.app:
            return self._fallback_news_extract(url)
        
        try:
            result = self.app.extract(
                url,
                {
                    "prompt": "Extract recent press releases and company announcements with titles, dates, and brief summaries. Categorize by type (product launch, partnership, leadership change, campaign, etc.)",
                    "schema": self.news_schema
                }
            )
            return result.get("data", {})
        except Exception as e:
            print(f"   ⚠️  Firecrawl news extract failed: {e}")
            return self._fallback_news_extract(url)
    
    def extract_jobs(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract job postings, especially marketing roles
        
        Args:
            url: Company careers page URL
            
        Returns:
            Dictionary with job postings
        """
        if not self.app:
            return self._fallback_jobs_extract(url)
        
        try:
            result = self.app.extract(
                url,
                {
                    "prompt": "Extract job postings, especially marketing, growth, and brand-related positions. Include title, department, location, and job type.",
                    "schema": self.jobs_schema
                }
            )
            return result.get("data", {})
        except Exception as e:
            print(f"   ⚠️  Firecrawl jobs extract failed: {e}")
            return self._fallback_jobs_extract(url)
    
    def crawl_to_markdown(self, url: str) -> Optional[str]:
        """
        Crawl a URL and return clean markdown
        
        Args:
            url: URL to crawl
            
        Returns:
            Markdown content
        """
        if not self.app:
            return None
        
        try:
            result = self.app.crawl_url(
                url,
                params={
                    "limit": 1,
                    "scrapeOptions": {
                        "formats": ["markdown"]
                    }
                }
            )
            if result.get("success") and result.get("data"):
                return result["data"][0].get("markdown", "")
        except Exception as e:
            print(f"   ⚠️  Firecrawl markdown failed: {e}")
        
        return None
    
    # Fallback methods (when no API key)
    def _fallback_company_extract(self, url: str) -> Dict[str, Any]:
        """Fallback: return basic info from URL"""
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        return {
            "company_name": domain.replace("www.", "").split(".")[0].title(),
            "source": "fallback"
        }
    
    def _fallback_leadership_extract(self, url: str) -> Dict[str, Any]:
        return {"executives": [], "marketing_leadership": [], "source": "fallback"}
    
    def _fallback_news_extract(self, url: str) -> Dict[str, Any]:
        return {"press_releases": [], "recent_announcements": [], "source": "fallback"}
    
    def _fallback_jobs_extract(self, url: str) -> Dict[str, Any]:
        return {"marketing_jobs": [], "total_jobs": 0, "source": "fallback"}
