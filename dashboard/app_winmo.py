"""
Brand Radar - Real Intelligence Extraction
Extracts actual insights like Winmo does
"""

import json
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"


def extract_real_intelligence(brand_name, content):
    """Extract actual intelligence from crawled content"""
    
    intelligence = {
        "leadership_changes": [],
        "agency_signals": [],
        "campaigns": [],
        "marketing_hires": [],
        "partnerships": [],
        "budget_signals": [],
        "key_facts": []
    }
    
    if not content:
        return intelligence
    
    # === LEADERSHIP CHANGES (Winmo-style) ===
    # Look for actual executive appointments
    exec_patterns = [
        r'([A-Z][a-z]+ [A-Z][a-z]+).*(?:appointed|named|joined).*(?:chief|cmo|ceo|cfo|presid|vp|director)',
        r'(?:chief|cmo|ceo|cfo).*(?:is|was|has been).*(?:appointed|named).*(?:as|to).([A-Z][a-z]+ [A-Z][a-z]+)',
        r'(?:welcome|welcome aboard|joining us).*(?:our)?(?:new)?(?:chief|cmo|ceo|marketing)',
        r'([A-Z][a-z]+ [A-Z][a-z]+).*(?:takes over|takes on|assumes role).*(?:marketing|brand|chief)',
    ]
    
    for pattern in exec_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:
            if len(match) > 3:  # Filter noise
                intelligence["leadership_changes"].append(match.strip())
    
    # === AGENCY SIGNALS ===
    # Look for agency-related hiring or reviews
    agency_patterns = [
        r'(?:seeking|looking for|hiring).*(?:advertising|media|marketing).*(?:agency|partner)',
        r'(?:agency review|rfp|request for proposal)',
        r'(?:media agency|creative agency|digital agency).*(?:search|select|appoint)',
        r'(?:parting ways|ending relationship).*(?:agency)',
    ]
    
    for pattern in agency_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            intelligence["agency_signals"].append(match.strip())
    
    # === CAMPAIGNS ===
    # Extract actual campaign names
    campaign_patterns = [
        r'(?:launch|introduce|unveil|announce).*(?:["\']([A-Z][^"\']{5,40})["\']|campaign[:\s]+([A-Z][^.\n]{5,40}))',
        r'(?:new campaign|campaign).*(?:called|titled|named).?(?:["\']?([A-Z][^"\']{5,35})["\']?)',
        r'["\']([A-Z][A-Z\s]{5,30})["\'].*(?:campaign)',
    ]
    
    for pattern in campaign_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            result = match if isinstance(match, str) else match[0] or match[1]
            if result and len(result) > 5:
                intelligence["campaigns"].append(result.strip())
    
    # === MARKETING HIRES ===
    hiring_patterns = [
        r'(?:hiring|seeking|join us).*(?:marketing|brand|growth|performance|digital).*(?:manager|director|head|vp|chief)',
        r'(?:marketing|brand).*(?:job|career|opportunity|role|position).*(?:for|in)',
    ]
    
    for pattern in hiring_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:5]:
            intelligence["marketing_hires"].append(match.strip())
    
    # === PARTNERSHIPS/SPONSORSHIPS ===
    partnership_patterns = [
        r'(?:partnership|partner|collaboration).*(?:with|and|for).([A-Z][a-z]+(?: [A-Z][a-z]+)?)',
        r'(?:sponsor|sponsorship|ambassador).*(?:for|with|of).([A-Z][a-z]+)',
        r'(?:team up|join forces|collaborate).*(?:with).([A-Z][a-z]+)',
    ]
    
    for pattern in partnership_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:
            intelligence["partnerships"].append(match.strip())
    
    # === BUDGET SIGNALS ===
    budget_patterns = [
        r'(?:increasing|expanding|growing).*(?:marketing|advertising|media).*(?:budget|spend|investment)',
        r'(?:marketing budget|ad spend).*(?:increase|grow|expand)',
        r'(?:investing|investment).*(?:marketing|brand|campaign)',
        r'(?:funding|raised).*(?:million|billion|series)',
    ]
    
    for pattern in budget_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:2]:
            intelligence["budget_signals"].append(match.strip())
    
    # === KEY FACTS (for Winmo-style summary) ===
    # Extract notable standalone facts
    if intelligence["leadership_changes"]:
        for leader in intelligence["leadership_changes"][:1]:
            intelligence["key_facts"].append(f"👔 {leader} - New decision maker (agency reviews likely in 60-90 days)")
    
    if intelligence["agency_signals"]:
        for signal in intelligence["agency_signals"][:1]:
            intelligence["key_facts"].append(f"🎯 {signal} - Direct agency opportunity")
    
    if intelligence["campaigns"]:
        for campaign in intelligence["campaigns"][:1]:
            intelligence["key_facts"].append(f"📢 Launched '{campaign}' campaign - Pitch campaign support")
    
    if len(intelligence["marketing_hires"]) >= 2:
        intelligence["key_facts"].append(f"💼 Hiring {len(intelligence['marketing_hires'])} marketing roles - Budget increasing")
    
    if intelligence["partnerships"]:
        for partner in intelligence["partnerships"][:1]:
            intelligence["key_facts"].append(f"🤝 Partnership with {partner} - Pitch co-marketing")
    
    if intelligence["budget_signals"]:
        for budget in intelligence["budget_signals"][:1]:
            intelligence["key_facts"].append(f"💰 {budget} - Active spending phase")
    
    return intelligence


def calculate_opportunity_score(intelligence, signals):
    """Calculate opportunity score Winmo-style"""
    score = 0
    reasons = []
    
    # Leadership changes = HIGH value (new CMO reviews agencies)
    if intelligence["leadership_changes"]:
        score += 35
        reasons.append("New marketing leadership")
    
    # Agency signals = DIRECT opportunity
    if intelligence["agency_signals"]:
        score += 40
        reasons.append("Agency review/search detected")
    
    # Multiple marketing hires = budget
    if len(intelligence["marketing_hires"]) >= 3:
        score += 20
        reasons.append("Marketing team expansion")
    elif len(intelligence["marketing_hires"]) >= 1:
        score += 10
    
    # Campaigns = active spending
    if intelligence["campaigns"]:
        score += 15
        reasons.append("Active campaign development")
    
    # Partnerships = open to external help
    if intelligence["partnerships"]:
        score += 10
        reasons.append("Partnership activity")
    
    # Budget signals
    if intelligence["budget_signals"]:
        score += 15
        reasons.append("Increasing marketing budget")
    
    # Signal backup
    score += min(signals.get("freshness", 0), 10)
    
    return min(score, 100), reasons


def estimate_timing(score, intelligence):
    """Estimate when to pitch"""
    if intelligence["agency_signals"]:
        return "🔥 IMMEDIATE", "Agency review in progress"
    if intelligence["leadership_changes"]:
        return "⚡ This Week", "New CMO reviewing agencies (60-90 day window)"
    if score >= 50:
        return "📅 This Month", "High activity period"
    if score >= 30:
        return "📅 This Quarter", "Building relationship phase"
    return "👀 Watchlist", "Monitor for changes"


def load_data():
    """Load all brand intelligence"""
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
                    signals = data.get("signals", {})
                    
                    # Extract real intelligence
                    intelligence = extract_real_intelligence(name, content)
                    
                    # Calculate scores
                    score, reasons = calculate_opportunity_score(intelligence, signals)
                    timing, timing_reason = estimate_timing(score, intelligence)
                    
                    # Generate Winmo-style summary
                    if intelligence["key_facts"]:
                        summary = intelligence["key_facts"][0]
                    elif signals.get("freshness", 0) > 0:
                        summary = "📊 Recent marketing activity detected"
                    else:
                        summary = "👀 Limited signals - add to watchlist"
                    
                    brands.append({
                        "name": name,
                        "url": data["url"],
                        "opportunity_score": score,
                        "score_reasons": reasons,
                        "timing": timing,
                        "timing_reason": timing_reason,
                        "intelligence": intelligence,
                        "summary": summary,
                        "signals": signals,
                        "total_signals": sum([
                            len(intelligence["leadership_changes"]),
                            len(intelligence["agency_signals"]),
                            len(intelligence["marketing_hires"]),
                            len(intelligence["campaigns"]),
                            len(intelligence["partnerships"]),
                        ])
                    })
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    return sorted(brands, key=lambda x: x["opportunity_score"], reverse=True)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 Brand Radar - Agency Intelligence</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f8f9fa; 
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        header {
            background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
            color: white;
            padding: 40px;
            border-radius: 16px;
            margin-bottom: 30px;
        }
        header h1 { font-size: 2.5em; margin-bottom: 8px; }
        header p { opacity: 0.9; }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #2c5282; }
        .metric-label { color: #666; font-size: 0.9em; margin-top: 4px; }
        
        .brand-card {
            background: white;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border-left: 6px solid #cbd5e0;
            cursor: pointer;
            transition: all 0.3s;
        }
        .brand-card:hover {
            transform: translateX(8px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }
        .brand-card.hot { border-left-color: #e53e3e; }
        .brand-card.warm { border-left-color: #dd6b20; }
        .brand-card.cool { border-left-color: #38a169; }
        
        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .brand-info { flex: 1; min-width: 300px; }
        .brand-name { font-size: 1.6em; font-weight: bold; margin-bottom: 6px; color: #1a202c; }
        .brand-url { color: #718096; font-size: 0.9em; margin-bottom: 16px; }
        
        .summary-box {
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            margin: 16px 0;
            font-size: 0.95em;
            line-height: 1.6;
        }
        
        .badges { display: flex; gap: 10px; flex-wrap: wrap; }
        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-high { background: #fed7d7; color: #c53030; }
        .badge-med { background: #feebc8; color: #c05621; }
        .badge-low { background: #c6f6d5; color: #276749; }
        .badge-timing { background: #2c5282; color: white; }
        
        .score-section {
            text-align: right;
            min-width: 140px;
        }
        .score-value { 
            font-size: 3em; 
            font-weight: bold; 
            color: #2c5282;
            line-height: 1;
        }
        .score-label { color: #718096; font-size: 0.85em; }
        .score-reasons { 
            color: #4a5568; 
            font-size: 0.85em; 
            margin-top: 8px;
            text-align: left;
        }
        .score-reasons li { margin: 3px 0; }
        
        .details {
            margin-top: 24px;
            padding-top: 24px;
            border-top: 2px solid #e2e8f0;
            display: none;
        }
        .details.show { display: block; }
        
        .intel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .intel-card {
            background: #f7fafc;
            border-radius: 12px;
            padding: 20px;
        }
        .intel-card h4 {
            color: #2c5282;
            margin-bottom: 12px;
            font-size: 0.95em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .intel-card ul { margin-left: 20px; color: #4a5568; }
        .intel-card li { margin: 6px 0; }
        .intel-card .empty { color: #a0aec0; font-style: italic; }
        
        .pitch-box {
            background: #fffff0;
            border: 2px solid #faf089;
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }
        .pitch-box h4 { color: #975a16; margin-bottom: 12px; }
        .pitch-box .angle { font-weight: bold; margin-bottom: 8px; color: #744210; }
        .pitch-box .message { 
            background: white; 
            padding: 14px; 
            border-radius: 8px;
            font-family: monospace;
            color: #2d3748;
            line-height: 1.6;
        }
        
        footer {
            text-align: center;
            padding: 40px;
            color: #a0aec0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Brand Radar</h1>
            <p>Winmo-style Agency Intelligence — Real insights, actionable opportunities</p>
        </header>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{{ high_priority }}</div>
                <div class="metric-label">🔥 Immediate Opportunities</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ warm }}</div>
                <div class="metric-label">⚡ Warm Leads</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total }}</div>
                <div class="metric-label">🏢 Brands Tracked</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ with_leadership }}</div>
                <div class="metric-label">👔 Leadership Changes</div>
            </div>
        </div>
        
        <h2 style="margin-bottom: 20px; color: #1a202c;">📋 Pitch Opportunities</h2>
        <p style="color: #718096; margin-bottom: 24px;">Click any card to see full intelligence & pitch strategy</p>
        
        {% for brand in brands %}
        <div class="brand-card {{ 'hot' if brand.opportunity_score >= 60 else 'warm' if brand.opportunity_score >= 30 else 'cool' }}" 
             onclick="toggleDetails('details-{{ loop.index }}')">
            <div class="card-top">
                <div class="brand-info">
                    <div class="brand-name">{{ brand.name }}</div>
                    <div class="brand-url">{{ brand.url }}</div>
                    
                    <div class="summary-box">
                        {{ brand.summary }}
                    </div>
                    
                    <div class="badges">
                        <span class="badge {{ 'badge-high' if brand.opportunity_score >= 60 else 'badge-med' if brand.opportunity_score >= 30 else 'badge-low' }}">
                            {{ '🔥 High Priority' if brand.opportunity_score >= 60 else '⚡ Warm' if brand.opportunity_score >= 30 else '👀 Monitor' }}
                        </span>
                        <span class="badge badge-timing">{{ brand.timing }}</span>
                    </div>
                </div>
                
                <div class="score-section">
                    <div class="score-value">{{ brand.opportunity_score }}</div>
                    <div class="score-label">Opportunity Score</div>
                    {% if brand.score_reasons %}
                    <ul class="score-reasons">
                        {% for reason in brand.score_reasons[:3] %}
                        <li>✓ {{ reason }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                </div>
            </div>
            
            <div id="details-{{ loop.index }}" class="details">
                <h3 style="color: #2c5282; margin-bottom: 16px;">📊 Brand Intelligence</h3>
                
                <div class="intel-grid">
                    {% if brand.intelligence.leadership_changes %}
                    <div class="intel-card">
                        <h4>👔 Leadership Changes</h4>
                        <ul>
                            {% for change in brand.intelligence.leadership_changes %}
                            <li>{{ change }}</li>
                            {% endfor %}
                        </ul>
                        <p style="color: #718096; font-size: 0.85em; margin-top: 12px;">
                            💡 <strong>Winmo Insight:</strong> New CMOs typically review agency relationships within 60-90 days
                        </p>
                    </div>
                    {% endif %}
                    
                    {% if brand.intelligence.agency_signals %}
                    <div class="intel-card">
                        <h4>🎯 Agency Signals</h4>
                        <ul>
                            {% for signal in brand.intelligence.agency_signals %}
                            <li>{{ signal }}</li>
                            {% endfor %}
                        </ul>
                        <p style="color: #e53e3e; font-weight: bold; margin-top: 12px;">
                            ⚠️ DIRECT OPPORTUNITY - Agency review detected
                        </p>
                    </div>
                    {% endif %}
                    
                    {% if brand.intelligence.marketing_hires %}
                    <div class="intel-card">
                        <h4>💼 Marketing Hiring</h4>
                        <ul>
                            {% for hire in brand.intelligence.marketing_hires %}
                            <li>{{ hire }}</li>
                            {% endfor %}
                        </ul>
                        <p style="color: #718096; font-size: 0.85em; margin-top: 12px;">
                            💡 Indicates increasing marketing budget
                        </p>
                    </div>
                    {% endif %}
                    
                    {% if brand.intelligence.campaigns %}
                    <div class="intel-card">
                        <h4>📢 Campaign Activity</h4>
                        <ul>
                            {% for campaign in brand.intelligence.campaigns %}
                            <li>{{ campaign }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    {% if brand.intelligence.partnerships %}
                    <div class="intel-card">
                        <h4>🤝 Partnerships</h4>
                        <ul>
                            {% for partner in brand.intelligence.partnerships %}
                            <li>{{ partner }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    <div class="intel-card">
                        <h4>📊 Signal Summary</h4>
                        <ul>
                            <li><strong>Timing:</strong> {{ brand.timing }} ({{ brand.timing_reason }})</li>
                            <li><strong>Total Signals:</strong> {{ brand.total_signals }}</li>
                            <li><strong>Opportunity Score:</strong> {{ brand.opportunity_score }}/100</li>
                        </ul>
                    </div>
                </div>
                
                <div class="pitch-box">
                    <h4>🎯 Recommended Pitch Strategy</h4>
                    {% if brand.intelligence.agency_signals %}
                    <p class="angle">Angle: Direct agency pitch</p>
                    <p class="message">"Saw {{ brand.name }} is reviewing agency partners. We specialize in [your specialty] and have helped similar brands achieve [specific result]. Would love to share our approach..."</p>
                    {% elif brand.intelligence.leadership_changes %}
                    <p class="angle">Angle: New leadership transition</p>
                    <p class="message">"Congratulations to {{ brand.intelligence.leadership_changes[0] }} on the new role. We've helped new CMOs hit the ground running with [specific service]. Here's what worked for [similar brand]..."</p>
                    {% elif brand.intelligence.campaigns %}
                    <p class="angle">Angle: Campaign support</p>
                    <p class="message">"Your '{{ brand.intelligence.campaigns[0] }}' campaign looks great. We've helped similar brands amplify results through [specific tactic], increasing ROI by 40%..."</p>
                    {% else %}
                    <p class="angle">Angle: Relationship building</p>
                    <p class="message">"We've been following {{ brand.name }}'s marketing and admire your approach to [specific]. We work with similar brands on [service] and would love to share insights..."</p>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
        
        <footer>
            Last updated: {{ now }} | Brand Radar v2.0 — Winmo-style Intelligence
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
    warm = len([b for b in brands if 30 <= b["opportunity_score"] < 60])
    with_leadership = len([b for b in brands if b["intelligence"]["leadership_changes"]])
    
    return render_template_string(
        HTML_TEMPLATE,
        brands=brands,
        high_priority=high_priority,
        warm=warm,
        total=len(brands),
        with_leadership=with_leadership,
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


@app.route("/api/brands")
def api_brands():
    return jsonify(load_data())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8503, debug=False, threaded=True)
