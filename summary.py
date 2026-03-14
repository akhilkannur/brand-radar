#!/usr/bin/env python3
"""
Brand Radar - Quick Summary Script
View crawl results in terminal
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
RAW_DIR = DATA_DIR / "raw"

def main():
    print("="*70)
    print("🔍 BRAND RADAR - Crawl Summary")
    print("="*70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    brands = []
    for f in RAW_DIR.glob("*.json"):
        try:
            data = json.load(open(f))
            if data.get("success"):
                brands.append({
                    "name": data.get("name", f.stem.replace("_", " ").title()),
                    "url": data["url"],
                    "score": data["intent_score"],
                    "pages": data.get("pages_crawled", 0),
                    "signals": data["signals"],
                    "firecrawl": data.get("firecrawl_data", {})
                })
        except Exception as e:
            continue
    
    if not brands:
        print("❌ No crawl data found!")
        print("\nRun the crawler first:")
        print("  python src/crawler_hybrid.py")
        return
    
    brands.sort(key=lambda x: x["score"], reverse=True)
    
    # Summary stats
    avg_score = sum(b["score"] for b in brands) / len(brands)
    high_intent = len([b for b in brands if b["score"] >= 50])
    
    print(f"📊 Brands crawled: {len(brands)}")
    print(f"📈 Average intent score: {avg_score:.1f}")
    print(f"🔥 High intent brands (50+): {high_intent}")
    print()
    
    # Top brands
    print("🏆 TOP BRANDS BY INTENT SCORE")
    print("-"*70)
    
    for i, brand in enumerate(brands[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        # Signal indicators
        signals = brand["signals"]
        signal_str = []
        if signals.get("leadership", 0) > 0:
            signal_str.append(f"👔 L:{signals['leadership']}")
        if signals.get("hiring", 0) > 0:
            signal_str.append(f"💼 H:{signals['hiring']}")
        if signals.get("campaigns", 0) > 0:
            signal_str.append(f"📢 C:{signals['campaigns']}")
        if signals.get("partnerships", 0) > 0:
            signal_str.append(f"🤝 P:{signals['partnerships']}")
        if signals.get("freshness", 0) > 0:
            signal_str.append(f"🆕 F:{signals['freshness']}")
        
        print(f"\n{medal} {brand['name']}: {brand['score']}")
        print(f"   URL: {brand['url']}")
        print(f"   Pages: {brand['pages']} | Signals: {' | '.join(signal_str)}")
    
    print()
    print("="*70)
    print("💡 To view the dashboard: streamlit run dashboard/app.py")
    print("="*70)

if __name__ == "__main__":
    main()
