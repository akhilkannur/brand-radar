"""
Brand Radar - Agency Pitch Intelligence with Real Insights
Extracts actual insights from crawled content
"""

import json
import re
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from pathlib import Path
import streamlit as st

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

# Page config
st.set_page_config(
    page_title="Brand Radar - Agency Pitch Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .pitch-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 2px solid #eaeaea;
        cursor: pointer;
        transition: all 0.2s;
    }
    .pitch-card:hover {
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        border-color: #667eea;
    }
    .pitch-card.hot { border-color: #ff4757; }
    .pitch-card.warm { border-color: #ffa502; }
    
    .insight-snippet {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 12px 16px;
        margin: 12px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.95em;
    }
    
    .opp-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .opp-high { background: #ff4757; color: white; }
    .opp-med { background: #ffa502; color: white; }
    .opp-low { background: #2ed573; color: white; }
    
    .timing-badge {
        display: inline-block;
        padding: 6px 14px;
        background: #667eea;
        color: white;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    
    .detail-section {
        background: #fafbfc;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


def load_crawl_data():
    """Load crawled brand data with extracted insights"""
    brands = []
    
    if not RAW_DIR.exists():
        return pd.DataFrame()
    
    for file in RAW_DIR.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
                if data.get("success"):
                    signals = data.get("signals", {})
                    name = data.get("name", file.stem.replace("_", " ").title())
                    content = data.get("raw_content_sample", "")
                    
                    # Extract real insights from content
                    insights = extract_real_insights(name, content, signals)
                    
                    # Calculate pitch score
                    pitch_score = calculate_pitch_score(signals, insights)
                    
                    # Estimate timing
                    timing = estimate_pitch_timing(signals)
                    
                    brands.append({
                        "name": name,
                        "url": data["url"],
                        "intent_score": data.get("intent_score", 0),
                        "pitch_score": pitch_score,
                        "timing": timing,
                        "signals": signals,
                        "insights": insights,
                        "pages_crawled": data.get("pages_crawled", 1),
                    })
        except Exception as e:
            print(f"Error loading {file}: {e}")
            continue
    
    return pd.DataFrame(brands)


def extract_real_insights(brand_name, content, signals):
    """Extract actual insights from crawled content"""
    insights = {
        "leadership_changes": [],
        "hiring_roles": [],
        "campaigns": [],
        "partnerships": [],
        "products": [],
        "summary": ""
    }
    
    if not content:
        return insights
    
    # Extract leadership names (look for patterns like "John Smith as CMO")
    leadership_patterns = [
        r'([A-Z][a-z]+ [A-Z][a-z]+).*(?:chief|cmo|ceo|cfo|presid|vp|director)',
        r'(?:chief|cmo|ceo|cfo).*(?:is|was|named|appointed).([A-Z][a-z]+ [A-Z][a-z]+)',
    ]
    for pattern in leadership_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:  # Limit to 3
            insights["leadership_changes"].append(match.strip())
    
    # Extract marketing roles being hired
    hiring_patterns = [
        r'(?:hiring|seeking|join us).*(marketing|brand|growth|performance).*(?:manager|director|head|vp)',
        r'(marketing|brand|growth).*(?:job|role|position|opening)',
    ]
    for pattern in hiring_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:
            insights["hiring_roles"].append(f"{match.strip()} roles")
    
    # Extract campaign/product names (look for quoted names or capitalized phrases)
    campaign_patterns = [
        r'(?:launch|introduce|announce|unveil).*(?:the|our|new).["\']?([A-Z][^"\']{10,50})["\']?',
        r'(?:campaign|collection|product).["\']?([A-Z][^"\']{10,40})["\']?',
    ]
    for pattern in campaign_patterns:
        matches = re.findall(pattern, content)
        for match in matches[:2]:
            insights["campaigns"].append(match.strip())
    
    # Extract partnership/brand names
    partnership_patterns = [
        r'(?:partnership|collaboration|partner).*(?:with|and).([A-Z][a-z]+(?: [A-Z][a-z]+)?)',
        r'(?:sponsor|ambassador).*(?:for|with).([A-Z][a-z]+)',
    ]
    for pattern in partnership_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:2]:
            insights["partnerships"].append(match.strip())
    
    # Extract product mentions
    product_patterns = [
        r'(?:new product|product launch|introducing).[:\s]*([A-Z][^.\n]{20,60})',
    ]
    for pattern in product_patterns:
        matches = re.findall(pattern, content)
        for match in matches[:2]:
            insights["products"].append(match.strip())
    
    # Generate summary snippet
    summary_parts = []
    if insights["leadership_changes"]:
        summary_parts.append(f"👔 New leadership: {', '.join(insights['leadership_changes'][:2])}")
    if insights["hiring_roles"]:
        summary_parts.append(f"💼 Hiring: {', '.join(insights['hiring_roles'][:2])}")
    if insights["campaigns"]:
        summary_parts.append(f"📢 Campaign: {', '.join(insights['campaigns'][:1])}")
    if insights["partnerships"]:
        summary_parts.append(f"🤝 Partnership with {', '.join(insights['partnerships'][:1])}")
    if insights["products"]:
        summary_parts.append(f"🆕 Product: {', '.join(insights['products'][:1])}")
    
    if not summary_parts and signals.get("freshness", 0) > 0:
        summary_parts.append("🆕 Recent marketing activity detected")
    
    insights["summary"] = " | ".join(summary_parts) if summary_parts else "📊 Monitor for opportunities"
    
    return insights


def calculate_pitch_score(signals, insights):
    """Calculate pitch score based on signals AND real insights"""
    score = 0
    
    # Signal-based scoring
    score += signals.get("leadership", 0) * 15
    score += min(signals.get("hiring", 0) * 10, 30)
    score += min(signals.get("campaigns", 0) * 12, 25)
    score += min(signals.get("partnerships", 0) * 8, 20)
    score += signals.get("freshness", 0)
    
    # Bonus for having actual extracted insights
    if insights["leadership_changes"]:
        score += 10
    if insights["campaigns"]:
        score += 8
    if insights["partnerships"]:
        score += 5
    
    return min(score, 100)


def estimate_pitch_timing(signals):
    """Estimate best time to pitch"""
    total_signals = sum([
        signals.get("leadership", 0),
        signals.get("hiring", 0),
        signals.get("campaigns", 0),
        signals.get("partnerships", 0),
    ])
    
    if total_signals >= 8:
        return "🔥 Pitch Now", "high"
    elif total_signals >= 4:
        return "⚡ This Week", "medium"
    elif total_signals >= 2:
        return "📅 This Month", "low"
    else:
        return "👀 Watchlist", "low"


def render_pitch_card(row, idx):
    """Render a pitch opportunity card with real insights"""
    timing_label, timing_priority = row['timing']
    insights = row['insights']
    signals = row['signals']
    
    # Card style
    if row['pitch_score'] >= 60:
        card_class = "pitch-card hot"
        opp_badge = "opp-high"
        opp_label = "🔥 High Priority"
    elif row['pitch_score'] >= 30:
        card_class = "pitch-card warm"
        opp_badge = "opp-med"
        opp_label = "⚡ Warm Lead"
    else:
        card_class = "pitch-card"
        opp_badge = "opp-low"
        opp_label = "👀 Monitor"
    
    # Signal count
    total_signals = sum([
        signals.get("leadership", 0),
        signals.get("hiring", 0),
        signals.get("campaigns", 0),
        signals.get("partnerships", 0),
    ])
    
    # Card
    st.markdown(f"""
    <div class="{card_class}" id="card_{idx}">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
            <div style="flex: 1;">
                <h3 style="margin: 0 0 4px 0; font-size: 1.4em;">{row['name']}</h3>
                <p style="margin: 0 0 12px 0; color: #666; font-size: 0.9em;">{row['url']}</p>
                
                <div style="margin-bottom: 12px;">
                    <span class="opp-badge {opp_badge}">{opp_label}</span>
                    <span class="timing-badge" style="margin-left: 8px;">{timing_label}</span>
                </div>
                
                <div class="insight-snippet">
                    {insights['summary']}
                </div>
            </div>
            
            <div style="text-align: right; min-width: 120px;">
                <div style="font-size: 2em; font-weight: bold; color: #667eea;">{row['pitch_score']}</div>
                <div style="color: #666; font-size: 0.85em;">Pitch Score</div>
                <div style="margin-top: 12px; color: #999; font-size: 0.85em;">
                    {total_signals} signals detected
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Expandable details
    with st.expander("🔍 View Full Insights & Pitch Strategy", key=f"expand_{idx}"):
        # Leadership insights
        if insights["leadership_changes"]:
            st.markdown("#### 👔 Leadership Changes")
            for leader in insights["leadership_changes"]:
                st.markdown(f"- **{leader}** - New decision maker. Pitch within 90 days of appointment.")
        
        # Hiring insights
        if insights["hiring_roles"]:
            st.markdown("#### 💼 Active Hiring")
            for role in insights["hiring_roles"]:
                st.markdown(f"- **{role}** - Indicates marketing budget increase")
        
        # Campaign insights
        if insights["campaigns"]:
            st.markdown("#### 📢 Campaign Activity")
            for campaign in insights["campaigns"]:
                st.markdown(f"- **{campaign}** - Pitch campaign support or amplification")
        
        # Partnership insights
        if insights["partnerships"]:
            st.markdown("#### 🤝 Partnerships")
            for partner in insights["partnerships"]:
                st.markdown(f"- **Partnership with {partner}** - Pitch co-marketing activation")
        
        # Product insights
        if insights["products"]:
            st.markdown("#### 🆕 Product Launches")
            for product in insights["products"]:
                st.markdown(f"- **{product}** - New product needs launch campaign")
        
        # Pitch strategy
        st.markdown("#### 🎯 Recommended Pitch Strategy")
        
        if insights["leadership_changes"]:
            st.info("""
            **Angle**: Congratulate new leadership + offer transition support
            **Message**: "Saw [Name] joined as CMO. We specialize in helping new marketing leaders hit the ground running with [specific service]..."
            """)
        
        if insights["campaigns"]:
            st.info("""
            **Angle**: Campaign amplification or optimization
            **Message**: "Your recent campaign looks great. We've helped similar brands increase ROI by 40% through [specific tactic]..."
            """)
        
        if not insights["leadership_changes"] and not insights["campaigns"]:
            st.warning("""
            **Angle**: Relationship building - no hard pitch yet
            **Message**: "We've been following [Brand]'s marketing and love your approach to [specific]. Would love to share insights from similar brands..."
            """)


def main():
    # Header
    st.title("🎯 Brand Radar")
    st.markdown("**Agency Pitch Intelligence**")
    st.markdown("*Real insights from brand websites - leadership changes, campaigns, hiring & more*")
    st.divider()
    
    # Load data
    df = load_crawl_data()
    
    if df.empty:
        st.warning("""
        ### 🚨 No data yet!
        
        Run the crawler:
        ```bash
        cd /home/akhilnairmk/brand-radar
        source .venv/bin/activate
        python src/crawler_hybrid.py
        ```
        """)
        return
    
    # Sort by pitch score
    df_sorted = df.sort_values("pitch_score", ascending=False)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        high_priority = len(df[df['pitch_score'] >= 60])
        st.metric("🔥 High Priority", high_priority)
    
    with col2:
        warm_leads = len(df[(df['pitch_score'] >= 30) & (df['pitch_score'] < 60)])
        st.metric("⚡ Warm Leads", warm_leads)
    
    with col3:
        st.metric("🏢 Brands Analyzed", len(df))
    
    st.markdown("")
    st.divider()
    
    # Pitch opportunities
    st.markdown("### 📋 Pitch Opportunities")
    
    for idx, row in df_sorted.iterrows():
        render_pitch_card(row, idx)
        st.divider()
    
    # Footer
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
