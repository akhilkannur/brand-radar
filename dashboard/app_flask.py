"""
Brand Radar - Simple Flask Web Dashboard
More reliable than Streamlit for this environment
"""

from flask import Flask, render_template_string, jsonify
import json
from pathlib import Path
from datetime import datetime
import re

app = Flask(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"


def extract_insights(brand_name, content, signals):
    """Extract insights from content"""
    insights = {
        "leadership": [],
        "hiring": [],
        "campaigns": [],
        "summary": ""
    }
    
    if not content:
        return insights
    
    # Leadership
    matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+).*(?:chief|cmo|ceo|presid)', content, re.IGNORECASE)
    insights["leadership"] = list(set(matches))[:3]
    
    # Hiring
    matches = re.findall(r'(marketing|brand|growth).*(?:manager|director|head)', content, re.IGNORECASE)
    insights["hiring"] = list(set(matches))[:3]
    
    # Campaigns
    matches = re.findall(r'(?:launch|announce).*(?:new|the).([A-Z][a-z]+(?: [A-Z][a-z]+)?)', content)
    insights["campaigns"] = list(set(matches))[:2]
    
    # Summary
    parts = []
    if insights["leadership"]:
        parts.append(f"👔 {insights['leadership'][0]}")
    if insights["hiring"]:
        parts.append(f"💼 Hiring {insights['hiring'][0]}")
    if insights["campaigns"]:
        parts.append(f"📢 {insights['campaigns'][0]}")
    
    insights["summary"] = " | ".join(parts) if parts else "📊 Monitor"
    
    return insights


def load_data():
    """Load all brand data"""
    brands = []
    
    if not RAW_DIR.exists():
        return brands
    
    for file in RAW_DIR.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                if data.get("success"):
                    signals = data.get("signals", {})
                    name = data.get("name", file.stem.replace("_", " ").title())
                    content = data.get("raw_content_sample", "")
                    
                    insights = extract_insights(name, content, signals)
                    
                    # Calculate pitch score
                    score = (
                        signals.get("leadership", 0) * 15 +
                        min(signals.get("hiring", 0) * 10, 30) +
                        min(signals.get("campaigns", 0) * 12, 25) +
                        signals.get("freshness", 0)
                    )
                    score = min(score + (10 if insights["leadership"] else 0), 100)
                    
                    # Timing
                    total = sum([signals.get("leadership", 0), signals.get("hiring", 0), 
                                signals.get("campaigns", 0), signals.get("partnerships", 0)])
                    if total >= 8:
                        timing = ("🔥 Pitch Now", "high")
                    elif total >= 4:
                        timing = ("⚡ This Week", "medium")
                    elif total >= 2:
                        timing = ("📅 This Month", "low")
                    else:
                        timing = ("👀 Watchlist", "low")
                    
                    brands.append({
                        "name": name,
                        "url": data["url"],
                        "pitch_score": score,
                        "timing": timing[0],
                        "timing_priority": timing[1],
                        "signals": signals,
                        "insights": insights,
                        "total_signals": total
                    })
        except Exception as e:
            continue
    
    return sorted(brands, key=lambda x: x["pitch_score"], reverse=True)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 Brand Radar</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f6fa; 
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
        }
        header h1 { font-size: 2.5em; margin-bottom: 8px; }
        header p { opacity: 0.9; font-size: 1.1em; }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #667eea; }
        .metric-label { color: #666; font-size: 0.9em; }
        
        .brand-card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border-left: 4px solid #ddd;
            cursor: pointer;
            transition: all 0.3s;
        }
        .brand-card:hover {
            transform: translateX(8px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }
        .brand-card.hot { border-left-color: #ff4757; }
        .brand-card.warm { border-left-color: #ffa502; }
        .brand-card.cool { border-left-color: #2ed573; }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 16px;
        }
        .brand-name { font-size: 1.5em; font-weight: bold; margin-bottom: 4px; }
        .brand-url { color: #666; font-size: 0.9em; }
        
        .badges { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .badge-high { background: #ff4757; color: white; }
        .badge-medium { background: #ffa502; color: white; }
        .badge-low { background: #2ed573; color: white; }
        .badge-timing { background: #667eea; color: white; }
        
        .insight-snippet {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .score-box {
            text-align: right;
            min-width: 100px;
        }
        .score-value { font-size: 2.5em; font-weight: bold; color: #667eea; line-height: 1; }
        .score-label { color: #666; font-size: 0.85em; }
        
        .details {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            display: none;
        }
        .details.show { display: block; }
        
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 16px;
        }
        .detail-item {
            background: #fafbfc;
            padding: 16px;
            border-radius: 8px;
        }
        .detail-item h4 { color: #667eea; margin-bottom: 8px; font-size: 0.95em; }
        .detail-item ul { margin-left: 20px; color: #555; }
        .detail-item li { margin: 4px 0; }
        
        .pitch-strategy {
            background: #fff9e6;
            border: 1px solid #ffeaa7;
            padding: 16px;
            border-radius: 8px;
            margin-top: 16px;
        }
        .pitch-strategy h4 { color: #d68910; margin-bottom: 8px; }
        
        footer {
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Brand Radar</h1>
            <p>Agency Pitch Intelligence — Real insights from brand websites</p>
        </header>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{{ high_priority }}</div>
                <div class="metric-label">🔥 High Priority</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ warm_leads }}</div>
                <div class="metric-label">⚡ Warm Leads</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ total }}</div>
                <div class="metric-label">🏢 Brands Analyzed</div>
            </div>
        </div>
        
        <h2 style="margin-bottom: 20px;">📋 Pitch Opportunities</h2>
        
        {% for brand in brands %}
        <div class="brand-card {{ 'hot' if brand.pitch_score >= 60 else 'warm' if brand.pitch_score >= 30 else 'cool' }}" 
             onclick="toggleDetails('details-{{ loop.index }}')">
            <div class="card-header">
                <div>
                    <div class="brand-name">{{ brand.name }}</div>
                    <div class="brand-url">{{ brand.url }}</div>
                    
                    <div class="badges">
                        <span class="badge {{ 'badge-high' if brand.timing_priority == 'high' else 'badge-medium' if brand.timing_priority == 'medium' else 'badge-low' }}">
                            {{ '🔥 High Priority' if brand.pitch_score >= 60 else '⚡ Warm Lead' if brand.pitch_score >= 30 else '👀 Monitor' }}
                        </span>
                        <span class="badge badge-timing">{{ brand.timing }}</span>
                    </div>
                    
                    <div class="insight-snippet">{{ brand.insights.summary }}</div>
                </div>
                
                <div class="score-box">
                    <div class="score-value">{{ brand.pitch_score }}</div>
                    <div class="score-label">Pitch Score</div>
                    <div style="color: #999; font-size: 0.85em; margin-top: 8px;">
                        {{ brand.total_signals }} signals
                    </div>
                </div>
            </div>
            
            <div id="details-{{ loop.index }}" class="details">
                <div class="detail-grid">
                    {% if brand.insights.leadership %}
                    <div class="detail-item">
                        <h4>👔 Leadership Changes</h4>
                        <ul>
                            {% for leader in brand.insights.leadership %}
                            <li>{{ leader }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    {% if brand.insights.hiring %}
                    <div class="detail-item">
                        <h4>💼 Active Hiring</h4>
                        <ul>
                            {% for role in brand.insights.hiring %}
                            <li>{{ role }} roles</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    {% if brand.insights.campaigns %}
                    <div class="detail-item">
                        <h4>📢 Campaign Activity</h4>
                        <ul>
                            {% for campaign in brand.insights.campaigns %}
                            <li>{{ campaign }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                    
                    <div class="detail-item">
                        <h4>📊 Signal Breakdown</h4>
                        <ul>
                            <li>👔 Leadership: {{ brand.signals.leadership | default(0) }}</li>
                            <li>💼 Hiring: {{ brand.signals.hiring | default(0) }}</li>
                            <li>📢 Campaigns: {{ brand.signals.campaigns | default(0) }}</li>
                            <li>🤝 Partnerships: {{ brand.signals.partnerships | default(0) }}</li>
                        </ul>
                    </div>
                </div>
                
                <div class="pitch-strategy">
                    <h4>🎯 Pitch Strategy</h4>
                    {% if brand.insights.leadership %}
                    <p><strong>Angle:</strong> New leadership transition</p>
                    <p><strong>Message:</strong> "Congratulations to {{ brand.insights.leadership[0] }} on the new role. We specialize in helping new marketing leaders..."</p>
                    {% elif brand.insights.campaigns %}
                    <p><strong>Angle:</strong> Campaign support</p>
                    <p><strong>Message:</strong> "Your recent campaign looks great. We've helped similar brands increase ROI by 40% through..."</p>
                    {% else %}
                    <p><strong>Angle:</strong> Relationship building</p>
                    <p><strong>Message:</strong> "We've been following {{ brand.name }}'s marketing and love your approach. Would love to share insights..."</p>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
        
        <footer>
            Last updated: {{ now }} | Brand Radar v1.0
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
    
    high_priority = len([b for b in brands if b["pitch_score"] >= 60])
    warm_leads = len([b for b in brands if 30 <= b["pitch_score"] < 60])
    
    return render_template_string(
        HTML_TEMPLATE,
        brands=brands,
        high_priority=high_priority,
        warm_leads=warm_leads,
        total=len(brands),
        now=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


@app.route("/api/brands")
def api_brands():
    return jsonify(load_data())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8503, debug=False)
