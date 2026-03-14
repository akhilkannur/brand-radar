"""
Brand Radar - 7-Day Fresh Intelligence
Real-time pitch opportunities for agencies
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"


def extract_date_from_content(content):
    """Try to find dates in content to determine freshness"""
    # Look for recent dates (2025-2026)
    date_patterns = [
        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(2025|2026)',
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+(2025|2026)',
        r'\d{1,2}/\d{1,2}/(2025|2026)',
        r'(2025|2026)-\d{2}-\d{2}',
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            return True
    
    # Check for relative time indicators
    recent_indicators = [
        r'(?:today|yesterday|this week|this month|recently|newly|just announced)',
        r'(?:launch|announce|appoint|join|release|unveil).*(?:today|this week|this month)',
    ]
    
    for pattern in recent_indicators:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False


def extract_real_intelligence(brand_name, content):
    """Extract actual intelligence from content - last 7 days focus"""
    
    intelligence = {
        "events": [],
        "leadership": [],
        "campaigns": [],
        "hiring": [],
        "partnerships": [],
        "products": [],
        "is_recent": False
    }
    
    if not content:
        return intelligence
    
    # Check if content is recent (last 7 days)
    intelligence["is_recent"] = extract_date_from_content(content) or "2025" in content or "2026" in content
    
    # === LEADERSHIP CHANGES ===
    # Extract actual names and titles
    patterns = [
        (r'([A-Z][a-z]+ [A-Z][a-z]+).*(?:appointed|named|joined|takes over).*(?:chief|cmo|ceo|cfo|presid|vp|director)', 'leadership'),
        (r'(?:chief|cmo|ceo|cfo).*(?:is|was|has been).*(?:appointed|named).*(?:as|to).*(?:the)?(?:new)?(?: )?([A-Z][a-z]+ [A-Z][a-z]+)', 'leadership'),
        (r'(?:welcome|welcomes|welcoming).*(?:[A-Z][a-z]+ [A-Z][a-z]+).*(?:chief|cmo|ceo|marketing)', 'leadership'),
    ]
    
    for pattern, event_type in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:2]:
            if len(match) > 3 and match.lower() not in ['the', 'and', 'for']:
                intelligence[event_type].append(match.strip())
    
    # === CAMPAIGNS ===
    campaign_patterns = [
        r'(?:launch|unveil|introduce|announce).*(?:["\']([A-Z][^"\']{10,50})["\']|campaign[:\s]+([A-Z][^.\n]{10,40}))',
        r'["\']([A-Z][A-Z\s\&]{8,40})["\'].*(?:campaign|initiative)',
        r'(?:new|latest).*(?:campaign|initiative|collection).*(?:titled|called|named).*(?:["\']?([A-Z][^"\']{8,35})["\']?)',
    ]
    
    for pattern in campaign_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            result = match if isinstance(match, str) else (match[0] or match[1])
            if result and len(result) > 8:
                intelligence["campaigns"].append(result.strip()[:50])
    
    # === PARTNERSHIPS ===
    partnership_patterns = [
        r'(?:partnership|partner|collaboration|team up).*(?:with|and|for).([A-Z][a-z]+(?: [A-Z][a-z]+)?)',
        r'(?:sponsor|sponsorship|ambassador).*(?:for|with|of).([A-Z][a-z]+)',
        r'(?:join forces|ally).*(?:with).([A-Z][a-z]+)',
    ]
    
    for pattern in partnership_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:
            if len(match) > 3:
                intelligence["partnerships"].append(match.strip())
    
    # === PRODUCTS ===
    product_patterns = [
        r'(?:new product|product launch|introducing|unveils).*(?:the)?(?: )?([A-Z][^.\n]{10,50})',
        r'(?:launch|release|introduce).*(?:new|latest).*(?:product|service|solution).*(?:["\']?([A-Z][^"\']{10,40})["\']?)',
    ]
    
    for pattern in product_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:2]:
            if match and len(match) > 10:
                intelligence["products"].append(match.strip()[:50])
    
    # === HIRING ===
    hiring_patterns = [
        r'(?:hiring|seeking|looking for|join us).*(?:marketing|brand|growth|performance|digital).*(?:manager|director|head|vp|chief)',
        r'(?:marketing|brand|growth).*(?:job|career|opportunity|role|position|opening)',
    ]
    
    for pattern in hiring_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:5]:
            intelligence["hiring"].append(match.strip()[:60])
    
    # === GENERATE EVENTS (Winmo-style) ===
    # Each event = potential pitch opportunity
    
    for leader in intelligence["leadership"][:1]:
        intelligence["events"].append({
            "type": "leadership",
            "title": f"New Marketing Leadership",
            "detail": leader,
            "pitch_angle": "New CMO typically reviews agency relationships within 60-90 days",
            "services": ["Brand strategy", "Creative services", "Media planning", "Digital transformation"],
            "urgency": "high"
        })
    
    for campaign in intelligence["campaigns"][:1]:
        intelligence["events"].append({
            "type": "campaign",
            "title": f"Campaign Launch",
            "detail": campaign,
            "pitch_angle": "Active campaign = active budget. Pitch amplification or optimization",
            "services": ["Campaign amplification", "Performance marketing", "Social media", "Influencer partnerships"],
            "urgency": "medium"
        })
    
    for partner in intelligence["partnerships"][:1]:
        intelligence["events"].append({
            "type": "partnership",
            "title": f"Partnership Announced",
            "detail": f"With {partner}",
            "pitch_angle": "Partnerships require activation - pitch co-marketing services",
            "services": ["Co-marketing campaigns", "Event activation", "Content creation", "PR"],
            "urgency": "medium"
        })
    
    for product in intelligence["products"][:1]:
        intelligence["events"].append({
            "type": "product",
            "title": f"Product Launch",
            "detail": product,
            "pitch_angle": "New products need launch campaigns and ongoing marketing",
            "services": ["Product launch campaigns", "Go-to-market strategy", "Performance creative", "Media buying"],
            "urgency": "high"
        })
    
    if len(intelligence["hiring"]) >= 2:
        intelligence["events"].append({
            "type": "hiring",
            "title": f"Marketing Team Expansion",
            "detail": f"{len(intelligence['hiring'])} marketing roles open",
            "pitch_angle": "Hiring = budget increase. They'll need agency support to scale",
            "services": ["Staff augmentation", "Specialized services", "Training", "Technology"],
            "urgency": "low"
        })
    
    return intelligence


def calculate_opportunity_score(intelligence):
    """Calculate opportunity score based on recent events"""
    score = 0
    reasons = []
    
    for event in intelligence["events"]:
        if event["urgency"] == "high":
            score += 30
        elif event["urgency"] == "medium":
            score += 20
        else:
            score += 10
        
        reasons.append(event["pitch_angle"].split(".")[0])
    
    # Bonus for recency
    if intelligence["is_recent"]:
        score += 15
    
    return min(score, 100), list(set(reasons))[:3]


def get_timing_label(score, intelligence):
    """Get timing recommendation"""
    if not intelligence["events"]:
        return "👀 Monitor", "No recent activity"
    
    if any(e["urgency"] == "high" for e in intelligence["events"]):
        return "🔥 This Week", "High-value opportunity"
    
    if score >= 40:
        return "⚡ This Month", "Active period"
    
    return "📅 Next Quarter", "Building awareness"


def load_data():
    """Load brand intelligence - last 7 days focus"""
    brands = []
    
    if not RAW_DIR.exists():
        return brands
    
    for file in RAW_DIR.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                if data.get("success"):
                    name = data.get("name", file.stem.replace("_", " ").title())
                    content = data.get("raw_content_sample", "")
                    
                    # Extract intelligence
                    intelligence = extract_real_intelligence(name, content)
                    
                    # Calculate scores
                    score, reasons = calculate_opportunity_score(intelligence)
                    timing, timing_reason = get_timing_label(score, intelligence)
                    
                    # Generate summary
                    if intelligence["events"]:
                        event = intelligence["events"][0]
                        summary = f"{event['title']}: {event['detail']} — {event['pitch_angle']}"
                    elif intelligence["is_recent"]:
                        summary = "📊 Recent activity detected - monitor for opportunities"
                    else:
                        summary = "👀 No recent signals - add to watchlist"
                    
                    brands.append({
                        "name": name,
                        "url": data["url"],
                        "opportunity_score": score,
                        "score_reasons": reasons,
                        "timing": timing,
                        "timing_reason": timing_reason,
                        "intelligence": intelligence,
                        "summary": summary,
                        "is_recent": intelligence["is_recent"],
                        "event_count": len(intelligence["events"])
                    })
        except Exception as e:
            continue
    
    # Sort: recent first, then by score
    return sorted(brands, key=lambda x: (x["is_recent"], x["opportunity_score"]), reverse=True)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 Brand Radar - 7-Day Intelligence</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8f9fa; 
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        header {
            background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
        }
        header h1 { font-size: 2.2em; margin-bottom: 8px; }
        header p { opacity: 0.9; }
        .fresh-badge { 
            display: inline-block; 
            background: #48bb78; 
            color: white; 
            padding: 4px 12px; 
            border-radius: 12px; 
            font-size: 0.85em; 
            font-weight: bold;
            margin-left: 12px;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }
        .metric {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c5282; }
        .metric-label { color: #666; font-size: 0.85em; margin-top: 4px; }
        
        .brand-card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            border-left: 6px solid #cbd5e0;
            cursor: pointer;
            transition: all 0.2s;
        }
        .brand-card:hover {
            transform: translateX(8px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }
        .brand-card.hot { border-left-color: #e53e3e; }
        .brand-card.warm { border-left-color: #dd6b20; }
        .brand-card.cool { border-left-color: #38a169; }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .brand-name { font-size: 1.5em; font-weight: bold; color: #1a202c; margin-bottom: 4px; }
        .brand-url { color: #718096; font-size: 0.9em; margin-bottom: 12px; }
        
        .summary-box {
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 14px 16px;
            border-radius: 0 8px 8px 0;
            margin: 12px 0;
            font-size: 0.95em;
            line-height: 1.5;
        }
        
        .badges { display: flex; gap: 8px; flex-wrap: wrap; }
        .badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .badge-high { background: #fed7d7; color: #c53030; }
        .badge-med { background: #feebc8; color: #c05621; }
        .badge-low { background: #c6f6d5; color: #276749; }
        .badge-timing { background: #2c5282; color: white; }
        .badge-fresh { background: #48bb78; color: white; }
        
        .score-box {
            text-align: right;
            min-width: 120px;
        }
        .score-value { font-size: 2.5em; font-weight: bold; color: #2c5282; line-height: 1; }
        .score-label { color: #718096; font-size: 0.85em; }
        
        .details {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
            display: none;
        }
        .details.show { display: block; }
        
        .events-section { margin-top: 16px; }
        .event-card {
            background: #f7fafc;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid #4299e1;
        }
        .event-card.high { border-left-color: #e53e3e; }
        .event-card.medium { border-left-color: #dd6b20; }
        
        .event-title { font-weight: bold; color: #2c5282; margin-bottom: 4px; }
        .event-detail { color: #4a5568; margin-bottom: 8px; }
        .event-angle { 
            background: white; 
            padding: 10px 14px; 
            border-radius: 8px;
            color: #2d3748;
            font-size: 0.9em;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 8px;
            margin-top: 12px;
        }
        .service-tag {
            background: #e2e8f0;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.85em;
            color: #4a5568;
            text-align: center;
        }
        
        footer {
            text-align: center;
            padding: 30px;
            color: #a0aec0;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Brand Radar</h1>
            <p>Last 7 days intelligence for agency pitch opportunities <span class="fresh-badge">Fresh Data</span></p>
        </header>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{{ high_priority }}</div>
                <div class="metric-label">🔥 High Priority</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ recent }}</div>
                <div class="metric-label">📊 Recent Activity</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total_events }}</div>
                <div class="metric-label">🎯 Total Events</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total }}</div>
                <div class="metric-label">🏢 Brands Tracked</div>
            </div>
        </div>
        
        <h2 style="margin-bottom: 16px; color: #1a202c;">📋 Pitch Opportunities (Last 7 Days)</h2>
        <p style="color: #718096; margin-bottom: 24px;">Click any brand to see events and pitch angles</p>
        
        {% for brand in brands %}
        <div class="brand-card {{ 'hot' if brand.opportunity_score >= 60 else 'warm' if brand.opportunity_score >= 30 else 'cool' }}" 
             onclick="toggleDetails('details-{{ loop.index }}')">
            <div class="card-header">
                <div style="flex: 1;">
                    <div class="brand-name">
                        {{ brand.name }}
                        {% if brand.is_recent %}<span class="badge badge-fresh">🆕 Fresh</span>{% endif %}
                    </div>
                    <div class="brand-url">{{ brand.url }}</div>
                    
                    <div class="summary-box">{{ brand.summary }}</div>
                    
                    <div class="badges">
                        <span class="badge {{ 'badge-high' if brand.opportunity_score >= 60 else 'badge-med' if brand.opportunity_score >= 30 else 'badge-low' }}">
                            {{ '🔥 High Priority' if brand.opportunity_score >= 60 else '⚡ Warm' if brand.opportunity_score >= 30 else '👀 Monitor' }}
                        </span>
                        <span class="badge badge-timing">{{ brand.timing }}</span>
                        {% if brand.event_count > 0 %}
                        <span class="badge" style="background: #edf2f7; color: #4a5568;">
                            {{ brand.event_count }} events
                        </span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="score-box">
                    <div class="score-value">{{ brand.opportunity_score }}</div>
                    <div class="score-label">Opportunity</div>
                </div>
            </div>
            
            <div id="details-{{ loop.index }}" class="details">
                <h3 style="color: #2c5282; margin-bottom: 16px;">📊 Events & Pitch Angles</h3>
                
                {% if brand.intelligence.events %}
                <div class="events-section">
                    {% for event in brand.intelligence.events %}
                    <div class="event-card {{ event.urgency }}">
                        <div class="event-title">{{ event.title }}</div>
                        <div class="event-detail">{{ event.detail }}</div>
                        <div class="event-angle">
                            <strong>💡 Pitch Angle:</strong> {{ event.pitch_angle }}
                            
                            <div class="services-grid">
                                {% for service in event.services %}
                                <div class="service-tag">{{ service }}</div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p style="color: #a0aec0; font-style: italic;">No specific events detected in last 7 days</p>
                {% endif %}
            </div>
        </div>
        {% endfor %}
        
        <footer>
            Last updated: {{ now }} | Brand Radar v3.0 — 7-Day Fresh Intelligence
        </footer>
    </div>
    
    <script>
        function toggleDetails(id) {
            const el = document.getElementById(id);
            el.classList.toggle('show');
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    brands = load_data()
    
    high_priority = len([b for b in brands if b["opportunity_score"] >= 60])
    recent = len([b for b in brands if b["is_recent"]])
    total_events = sum(b["event_count"] for b in brands)
    
    return render_template_string(
        HTML_TEMPLATE,
        brands=brands,
        high_priority=high_priority,
        recent=recent,
        total_events=total_events,
        total=len(brands),
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8503, debug=False, threaded=True)
