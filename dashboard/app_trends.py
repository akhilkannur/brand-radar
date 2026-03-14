"""
Brand Radar - Trend Discovery Dashboard
Inspired by Exploding Topics + Glimpse + IdeaBrowser
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from pathlib import Path
import streamlit as st
import random

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"

# Page config
st.set_page_config(
    page_title="Brand Radar - Trend Discovery",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Hide default header */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Card styling */
    div[data-testid="stVerticalBlock"] > div {
        border-radius: 12px;
    }
    
    /* Score badge */
    .score-high { color: #ff4757; font-weight: bold; }
    .score-med { color: #ffa502; font-weight: bold; }
    .score-low { color: #2ed573; font-weight: bold; }
    
    /* Growth indicator */
    .growth-up { color: #2ed573; font-weight: bold; }
    .growth-down { color: #ff4757; font-weight: bold; }
    
    /* Signal badges */
    .signal-badge {
        display: inline-block;
        padding: 4px 10px;
        margin: 2px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
    }
    .signal-leadership { background: #ffebee; color: #c62828; }
    .signal-hiring { background: #e3f2fd; color: #1565c0; }
    .signal-campaigns { background: #f3e5f5; color: #7b1fa2; }
    .signal-partnerships { background: #fff3e0; color: #ef6c00; }
    .signal-freshness { background: #e8f5e9; color: #2e7d32; }
</style>
""", unsafe_allow_html=True)


def load_crawl_data():
    """Load crawled brand data"""
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
                    
                    # Generate mock historical data for trajectory
                    base_score = data.get("intent_score", 0)
                    history = generate_mock_history(base_score)
                    
                    brands.append({
                        "name": name,
                        "url": data["url"],
                        "intent_score": base_score,
                        "leadership": signals.get("leadership", 0),
                        "hiring": signals.get("hiring", 0),
                        "campaigns": signals.get("campaigns", 0),
                        "tech": signals.get("tech", 0),
                        "partnerships": signals.get("partnerships", 0),
                        "freshness": signals.get("freshness", 0),
                        "pages_crawled": data.get("pages_crawled", 1),
                        "history": history,
                        "growth_7d": history[-1] - history[0] if len(history) > 1 else 0,
                        "growth_pct": ((history[-1] - history[0]) / max(history[0], 1)) * 100 if len(history) > 1 else 0
                    })
        except Exception as e:
            continue
    
    return pd.DataFrame(brands)


def generate_mock_history(current_score):
    """Generate mock historical data for trajectory visualization"""
    points = 8
    base = max(current_score - random.randint(10, 30), 5)
    history = []
    
    for i in range(points):
        progress = i / (points - 1)
        value = base + (current_score - base) * progress
        noise = random.randint(-5, 5)
        history.append(max(0, min(100, value + noise)))
    
    history[-1] = current_score
    return history


def get_trend_status(growth_pct):
    """Determine trend status"""
    if growth_pct >= 50:
        return "🔥", "Exploding"
    elif growth_pct >= 20:
        return "📈", "Rising Fast"
    elif growth_pct >= 5:
        return "✨", "Trending"
    else:
        return "➡️", "Stable"


def create_sparkline(history, color="#667eea"):
    """Create sparkline chart"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=history,
        mode='lines',
        line=dict(color=color, width=3),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)',
        hoverinfo='skip'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=60,
        width=150
    )
    return fig


def create_trajectory_chart(df):
    """Create trajectory chart for top brands"""
    fig = go.Figure()
    colors = ['#ff4757', '#ffa502', '#2ed573', '#3742fa', '#9b59b6']
    
    for idx, (_, row) in enumerate(df.iterrows()):
        fig.add_trace(go.Scatter(
            y=row['history'],
            mode='lines+markers',
            name=row['name'],
            line=dict(color=colors[idx % len(colors)], width=3),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        height=400,
        margin=dict(l=60, r=20, t=20, b=60),
        xaxis=dict(title="Time (weeks)", showgrid=False),
        yaxis=dict(title="Intent Score", showgrid=True, gridcolor='#f0f0f0'),
        hovermode='x unified',
        legend=dict(orientation='h', y=1.1, x=0)
    )
    
    return fig


def render_brand_card(row, idx):
    """Render a single brand card"""
    status_icon, status_label = get_trend_status(row['growth_pct'])
    
    # Score class
    if row['intent_score'] >= 50:
        score_class = "score-high"
        score_emoji = "🟢"
    elif row['intent_score'] >= 30:
        score_class = "score-med"
        score_emoji = "🟡"
    else:
        score_class = "score-low"
        score_emoji = "🔴"
    
    # Growth
    growth_class = "growth-up" if row['growth_7d'] >= 0 else "growth-down"
    growth_sign = "+" if row['growth_7d'] >= 0 else ""
    
    # Signal badges
    badges = []
    if row['leadership'] > 0:
        badges.append(f'<span class="signal-badge signal-leadership">👔 {row["leadership"]}</span>')
    if row['hiring'] > 0:
        badges.append(f'<span class="signal-badge signal-hiring">💼 {row["hiring"]}</span>')
    if row['campaigns'] > 0:
        badges.append(f'<span class="signal-badge signal-campaigns">📢 {row["campaigns"]}</span>')
    if row['partnerships'] > 0:
        badges.append(f'<span class="signal-badge signal-partnerships">🤝 {row["partnerships"]}</span>')
    if row['freshness'] > 0:
        badges.append(f'<span class="signal-badge signal-freshness">🆕 Recent</span>')
    
    # Create sparkline
    sparkline = create_sparkline(row['history'])
    
    # Card layout
    col1, col2, col3 = st.columns([3, 2, 1])
    
    with col1:
        st.markdown(f"#### {status_icon} {row['name']}")
        st.caption(row['url'])
        st.markdown("")
        
        # Signal badges
        if badges:
            st.markdown(' '.join(badges), unsafe_allow_html=True)
        
        st.markdown("")
        st.markdown(
            f'<span class="{score_class}" style="font-size:1.2em;">{score_emoji} Score: {row["intent_score"]}</span>  '
            f'<span class="{growth_class}" style="font-size:1.1em;">{growth_sign}{row["growth_7d"]:.0f} ({growth_sign}{row["growth_pct"]:.0f}%)</span>',
            unsafe_allow_html=True
        )
    
    with col2:
        st.plotly_chart(sparkline, use_container_width=False, key=f"spark_{idx}")
    
    with col3:
        st.metric("Status", status_label)


def main():
    # Header
    st.title("🔥 Brand Radar")
    st.markdown("**Discover brands about to spend on advertising** — before they issue RFPs")
    st.markdown("*Inspired by Exploding Topics + Glimpse*")
    st.divider()
    
    # Load data
    df = load_crawl_data()
    
    if df.empty:
        st.warning("""
        ### 🚨 No data yet!
        
        Run the crawler first:
        ```bash
        cd /home/akhilnairmk/brand-radar
        source .venv/bin/activate
        python src/crawler_hybrid.py
        ```
        """)
        return
    
    # Sort by growth for trending
    df_sorted = df.sort_values("growth_pct", ascending=False)
    
    # === TRENDING SECTION ===
    st.markdown("### 🔥 Trending Brands This Week")
    st.markdown("*Brands with the biggest intent score increases*")
    st.markdown("")
    
    # Display each brand as a card
    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        render_brand_card(row, idx)
        st.divider()
    
    st.markdown("")
    
    # === TRAJECTORY CHARTS ===
    st.markdown("### 📈 Intent Trajectories")
    st.markdown("*How brand intent scores have evolved over time*")
    
    top_5 = df.sort_values("intent_score", ascending=False).head(5)
    trajectory_fig = create_trajectory_chart(top_5)
    st.plotly_chart(trajectory_fig, use_container_width=True)
    
    st.markdown("")
    st.divider()
    
    # === SIGNAL BREAKDOWN ===
    st.markdown("### 🎯 What's Driving Intent")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Top Signals by Category")
        
        signal_leaders = {}
        if df['leadership'].max() > 0:
            signal_leaders["👔 Leadership"] = df.loc[df['leadership'].idxmax(), 'name']
        if df['hiring'].max() > 0:
            signal_leaders["💼 Hiring"] = df.loc[df['hiring'].idxmax(), 'name']
        if df['campaigns'].max() > 0:
            signal_leaders["📢 Campaigns"] = df.loc[df['campaigns'].idxmax(), 'name']
        if df['partnerships'].max() > 0:
            signal_leaders["🤝 Partnerships"] = df.loc[df['partnerships'].idxmax(), 'name']
        
        for signal, brand in signal_leaders.items():
            st.markdown(f"- **{signal}**: {brand}")
    
    with col2:
        st.markdown("#### Signal Distribution")
        
        signal_totals = {
            "Leadership": df['leadership'].sum(),
            "Hiring": df['hiring'].sum(),
            "Campaigns": df['campaigns'].sum(),
            "Partnerships": df['partnerships'].sum(),
        }
        
        fig = px.pie(
            values=list(signal_totals.values()),
            names=list(signal_totals.keys()),
            color_discrete_sequence=['#ff4757', '#3498db', '#9b59b6', '#f39c12']
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("")
    st.divider()
    
    # === ALL BRANDS TABLE ===
    with st.expander("📋 View All Brands Data"):
        display_df = df[['name', 'intent_score', 'growth_7d', 'growth_pct', 
                         'leadership', 'hiring', 'campaigns', 'partnerships', 'pages_crawled']].copy()
        display_df.columns = ['Brand', 'Score', '7d Δ', 'Growth %', '👔', '💼', '📢', '🤝', 'Pages']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data from {len(df)} brands")


if __name__ == "__main__":
    main()
