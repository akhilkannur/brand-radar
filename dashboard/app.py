"""
Brand Radar — AI Intent Dashboard v4.1
"Winmo for AI companies" — monitoring 50+ AI brands for advertising/marketing intent.
UI inspired by Exploding Topics / Glimpse / Winmo Edge.
"""

import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import streamlit as st

# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
COMPANIES_CSV = DATA_DIR / "ai_companies.csv"

# Signal types from src/signals.py
SIGNAL_CONFIG = {
    "agency_review": {"icon": "🏢", "label": "Agency Review", "color": "#e53e3e"},
    "ad_spend":      {"icon": "📢", "label": "Ad Spend",      "color": "#3182ce"},
    "funding":       {"icon": "💰", "label": "Funding",       "color": "#38a169"},
    "revenue":       {"icon": "📈", "label": "Revenue",       "color": "#805ad5"},
    "leadership":    {"icon": "👔", "label": "Leadership",    "color": "#dd6b20"},
    "product":       {"icon": "🆕", "label": "Product",       "color": "#d69e2e"},
    "hiring":        {"icon": "💼", "label": "Hiring",        "color": "#319795"},
    "partnership":   {"icon": "🤝", "label": "Partnership",   "color": "#4a5568"},
    "competitive":   {"icon": "⚔️", "label": "Competitive",   "color": "#718096"},
    "events":        {"icon": "🎪", "label": "Events",        "color": "#bee3f8"},
    "regulatory":    {"icon": "⚖️", "label": "Regulatory",    "color": "#cbd5e0"},
}

st.set_page_config(page_title="Brand Radar", page_icon="🔍", layout="wide",
                   initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Session state for navigation
# ---------------------------------------------------------------------------
if "view" not in st.session_state:
    st.session_state.view = "overview"
if "selected" not in st.session_state:
    st.session_state.selected = None


def go_overview():
    st.session_state.view = "overview"
    st.session_state.selected = None


def go_brand(name):
    st.session_state.view = "detail"
    st.session_state.selected = name


# ---------------------------------------------------------------------------
# CSS — clean, modern, Exploding-Topics-inspired
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ---------- globals ---------- */
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1100px;}

/* ---------- top bar ---------- */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 28px; flex-wrap: wrap; gap: 12px;
}
.topbar .logo {
    font-size: 1.6em; font-weight: 800; color: #1a202c;
    letter-spacing: -0.5px;
}
.topbar .logo span { color: #667eea; }
.topbar .sub { color: #718096; font-size: .92em; }

/* ---------- stat pills ---------- */
.stats-row {
    display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px;
}
.stat-pill {
    background: white; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 14px 22px; min-width: 140px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.stat-pill .n { font-size: 1.9em; font-weight: 800; color: #1a202c; line-height: 1.1; }
.stat-pill .l { font-size: .82em; color: #718096; margin-top: 2px; }

/* ---------- brand row (overview) ---------- */
.brand-row {
    display: flex; align-items: center; gap: 20px;
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 10px;
    transition: all .15s; cursor: pointer;
}
.brand-row:hover {
    border-color: #667eea; box-shadow: 0 4px 16px rgba(102,126,234,.12);
    transform: translateY(-1px);
}
.brand-row.no-intel { opacity: .65; }
.brand-row .rank {
    font-size: 1.1em; font-weight: 700; color: #a0aec0; min-width: 28px; text-align: center;
}
.brand-row .info { flex: 1; min-width: 0; }
.brand-row .bname { font-size: 1.1em; font-weight: 700; color: #1a202c; }
.brand-row .bsummary {
    color: #4a5568; font-size: .88em; margin-top: 4px; line-height: 1.5;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    max-width: 600px;
}
.brand-row .badges { margin-top: 6px; display: flex; gap: 6px; flex-wrap: wrap; }
.brand-row .score-col { text-align: right; min-width: 80px; }
.brand-row .score-num {
    font-size: 1.7em; font-weight: 800; line-height: 1;
    background: linear-gradient(135deg,#667eea,#764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.brand-row .score-lbl { font-size: .78em; color: #a0aec0; }

/* ---------- badges ---------- */
.b { display: inline-block; padding: 3px 10px; border-radius: 6px;
     font-size: .78em; font-weight: 700; }
.b-fire  { background: #fed7d7; color: #c53030; }
.b-warm  { background: #feebc8; color: #c05621; }
.b-watch { background: #edf2f7; color: #718096; }
.b-cat   { background: #e9d8fd; color: #553c9a; }
.b-time  { background: #ebf4ff; color: #2b6cb0; }
.b-evt   { background: #bee3f8; color: #2a4365; }

/* ---------- detail page ---------- */
.detail-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    flex-wrap: wrap; gap: 16px; margin-bottom: 8px;
}
.detail-header .score-big {
    font-size: 3.2em; font-weight: 800; line-height: 1;
    background: linear-gradient(135deg,#667eea,#764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.narrative-box {
    background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 22px 26px; line-height: 1.85; color: #2d3748; font-size: .95em;
    margin: 20px 0;
}

/* ---------- event card ---------- */
.ev {
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 12px; border-left: 4px solid #cbd5e0;
}
.ev.high   { border-left-color: #e53e3e; }
.ev.medium { border-left-color: #dd6b20; }
.ev.low    { border-left-color: #38a169; }
.ev .ev-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ev .ev-title { font-weight: 700; color: #1a202c; font-size: 1.05em; }
.ev .ev-detail { color: #4a5568; margin-bottom: 10px; font-size: .93em; }

/* ---------- pitch box ---------- */
.pitch {
    background: #fffff0; border: 2px solid #faf089; border-radius: 12px;
    padding: 20px 22px; margin-bottom: 14px;
}
.pitch h4 { color: #975a16; margin: 0 0 8px; font-size: 1em; }
.pitch .angle { font-weight: 700; color: #744210; margin-bottom: 6px; }
.pitch .msg {
    background: white; padding: 14px 16px; border-radius: 8px;
    font-family: Georgia, serif; color: #2d3748; line-height: 1.75; font-size: .93em;
}

/* ---------- sources table ---------- */
.src-table {
    width: 100%; border-collapse: collapse; background: white;
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,.04); margin: 8px 0 16px;
}
.src-table th {
    background: #f7fafc; padding: 10px 14px; text-align: left;
    color: #4a5568; font-size: .85em;
}
.src-table td { padding: 9px 14px; border-bottom: 1px solid #f0f4f8; font-size: .9em; }
.src-table a { color: #3182ce; text-decoration: none; }
.src-table a:hover { text-decoration: underline; }

/* ---------- section header ---------- */
.sh { font-size: 1.15em; font-weight: 700; color: #1a202c; margin: 28px 0 12px; }

/* ---------- meta-bar ---------- */
.meta-bar {
    background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 14px 18px; font-size: .86em; color: #718096; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_snapshots():
    """Returns list of snapshot files sorted by date descending."""
    files = sorted(SNAPSHOTS_DIR.glob("scores_*.json"), reverse=True)
    return files


@st.cache_data(ttl=60)
def load_data(snapshot_path):
    """Loads snapshot JSON and returns companies list."""
    if not snapshot_path or not Path(snapshot_path).exists():
        return None
    try:
        with open(snapshot_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error loading snapshot: {e}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_prio_lbl(score):
    if score >= 60: return "🔥 High"
    if score >= 30: return "⚡ Warm"
    return "👀 Watch"


def get_prio_cls(score):
    if score >= 60: return "b-fire"
    if score >= 30: return "b-warm"
    return "b-watch"


# ---------------------------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------------------------
def render_overview(data):
    scores = data.get("scores", [])
    gen_at = data.get("generated_at", "")

    # Header
    st.markdown("""
    <div class="topbar">
        <div>
            <div class="logo">🔍 Brand <span>Radar</span></div>
            <div class="sub">AI Intent Intelligence — monitoring news & direct signals</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    total = len(scores)
    high = sum(1 for s in scores if s["score"] >= 60)
    warm = sum(1 for s in scores if 30 <= s["score"] < 60)
    tot_sig = sum(s["signal_count"] for s in scores)
    
    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-pill"><div class="n">{high}</div><div class="l">🔥 High Priority</div></div>
        <div class="stat-pill"><div class="n">{warm}</div><div class="l">⚡ Warm Leads</div></div>
        <div class="stat-pill"><div class="n">{tot_sig}</div><div class="l">🎯 Signals Detected</div></div>
        <div class="stat-pill"><div class="n">{total}</div><div class="l">🏢 AI Companies</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar filters
    st.sidebar.subheader("Filters")
    cats = sorted(set(s["category"] for s in scores))
    sel_cat = st.sidebar.selectbox("Category", ["All"] + cats)
    
    sel_prio = st.sidebar.selectbox("Priority", ["All", "🔥 High", "⚡ Warm", "👀 Watchlist"])
    
    search = st.sidebar.text_input("Search Company", "")

    # Filter data
    filtered = scores
    if sel_cat != "All":
        filtered = [s for s in filtered if s["category"] == sel_cat]
    if sel_prio == "🔥 High":
        filtered = [s for s in filtered if s["score"] >= 60]
    elif sel_prio == "⚡ Warm":
        filtered = [s for s in filtered if 30 <= s["score"] < 60]
    elif sel_prio == "👀 Watchlist":
        filtered = [s for s in filtered if s["score"] < 30]
    if search:
        filtered = [s for s in filtered if search.lower() in s["company"].lower()]

    st.markdown(f"**{len(filtered)} companies matching criteria** — click 'View details' to see full signals")

    # Company rows
    for rank, s in enumerate(filtered, 1):
        _render_company_row(s, rank)


def _render_company_row(s, rank):
    score = s["score"]
    name = s["company"]
    prio_cls = get_prio_cls(score)
    prio_lbl = get_prio_lbl(score)
    
    cat_b = f'<span class="b b-cat">{s["category"]}</span>' if s["category"] else ""
    
    # Sig badges
    sig_badges = ""
    for stype, val in s.get("breakdown", {}).items():
        if val > 0:
            config = SIGNAL_CONFIG.get(stype, {"icon": "📌", "label": stype})
            sig_badges += f'<span class="b b-evt">{config["icon"]} {config["label"]}</span> '

    # Insight snippet (first sentence)
    insight = s.get("insight", "No specific insights yet.")
    summary = insight.split(". ")[0] + "."

    # Card HTML
    st.markdown(f"""
    <div class="brand-row">
        <div class="rank">{rank}</div>
        <div class="info">
            <div class="bname">{name} <span style="font-size:0.7em; color:#a0aec0; font-weight:normal;">({s['stage']})</span></div>
            <div class="bsummary">{summary}</div>
            <div class="badges">
                <span class="b {prio_cls}">{prio_lbl}</span>
                {cat_b} {sig_badges}
            </div>
        </div>
        <div class="score-col">
            <div class="score-num">{score}</div>
            <div class="score-lbl">intent score</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(f"View {name} details →", key=f"go_{name}", use_container_width=True, type="tertiary"):
        go_brand(name)
        st.rerun()


# ---------------------------------------------------------------------------
# DETAIL
# ---------------------------------------------------------------------------
def render_detail(company_data):
    s = company_data
    name = s["company"]

    # Back button
    if st.button("← Back to all companies", type="tertiary"):
        go_overview()
        st.rerun()

    # Header
    prio_cls = get_prio_cls(s["score"])
    prio_lbl = get_prio_lbl(s["score"]) + " Priority"
    cat_b = f'<span class="b b-cat">{s["category"]}</span>' if s["category"] else ""

    st.markdown(f"""
    <div class="detail-header">
        <div>
            <h2 style="margin:0;font-size:1.6em;">{name}</h2>
            <div style="color:#718096;margin:4px 0 10px;">
                AI-sector target company · {s['stage']} stage
            </div>
            <div><span class="b {prio_cls}">{prio_lbl}</span> {cat_b} 
                 <span class="b b-time">{s['trend'].upper()} trend</span></div>
        </div>
        <div style="text-align:right;">
            <div class="score-big">{s['score']}</div>
            <div style="color:#718096;font-size:.88em;">Intent Score</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Insight / Narrative
    st.markdown(f'<div class="narrative-box"><strong>Intelligence Summary:</strong><br>{s["insight"]}</div>', unsafe_allow_html=True)

    # Signal Breakdown Chart
    st.markdown('<div class="sh">📊 Intent Signal Breakdown</div>', unsafe_allow_html=True)
    breakdown = s.get("breakdown", {})
    if breakdown:
        sorted_br = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        names = [SIGNAL_CONFIG.get(k, {"label": k})["label"] for k, v in sorted_br]
        vals = [v for k, v in sorted_br]
        colors = [SIGNAL_CONFIG.get(k, {"color": "#667eea"})["color"] for k, v in sorted_br]
        
        fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=colors))
        fig.update_layout(height=max(200, len(names)*40), margin=dict(l=0, r=20, t=10, b=10),
                          xaxis_title="Score Contribution", yaxis=dict(autorange="reversed"),
                          plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signal breakdown available.")

    # Top Signals Feed
    st.markdown('<div class="sh">🎯 Recent Activity Feed</div>', unsafe_allow_html=True)
    top_signals = s.get("top_signals", [])
    if top_signals:
        for sig in top_signals:
            _render_signal_item(sig)
    else:
        st.caption("No recent activity records.")

    # Pitch Recommendation
    st.markdown('<div class="sh">💡 Recommended Pitch Angles</div>', unsafe_allow_html=True)
    _render_pitch_angles(s)

    # Metadata
    st.markdown(f"""
    <div class="meta-bar">
        <strong>Last signal detected:</strong> {s['last_signal'] or 'N/A'} · 
        <strong>Total signals tracked:</strong> {s['signal_count']} · 
        <strong>Trending:</strong> {s['trend']}
    </div>
    """, unsafe_allow_html=True)


def _render_signal_item(sig):
    stype = sig.get("signal_type", "product")
    config = SIGNAL_CONFIG.get(stype, {"icon": "📌", "label": stype, "color": "#cbd5e0"})
    
    st.markdown(f"""
    <div class="ev" style="border-left-color: {config['color']};">
        <div class="ev-top">
            <div class="ev-title">{config['icon']} {sig.get('title','')}</div>
            <span class="b" style="background:#f7fafc; color:#4a5568; font-size:.78em;">
                Strength: {sig.get('signal_strength',0)}/10</span>
        </div>
        <div class="ev-detail">{sig.get('summary','')}</div>
        <div style="font-size:0.8em; color:#718096; margin-top:5px;">
            Source: <a href="{sig.get('url','#')}" target="_blank" style="color:#667eea;">{sig.get('source','Link')}</a> · {sig.get('timestamp','')}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_pitch_angles(s):
    breakdown = s.get("breakdown", {})
    if not breakdown:
        st.markdown("""<div class="pitch"><div class="msg">Relationship building phase: Focus on providing value-add research about their niche's AI landscape.</div></div>""", unsafe_allow_html=True)
        return

    # Agency Review / Leadership
    if "agency_review" in breakdown or "leadership" in breakdown:
        st.markdown(f"""
        <div class="pitch"><h4>Angle: New Strategic Direction</h4>
        <div class="msg">"Saw the recent developments at <strong>{s['company']}</strong>. Transitions like this often mean it's time to reassess your agency stack. We specialize in helping AI scale-ups like yours establish a dominant brand voice during high-growth periods."</div></div>
        """, unsafe_allow_html=True)
    
    # Funding
    if "funding" in breakdown:
        st.markdown(f"""
        <div class="pitch"><h4>Angle: Capital Deployment</h4>
        <div class="msg">"Congrats on the recent funding round. As you look to deploy that capital into customer acquisition and brand awareness, our team can help you maximize ROI through AI-specific media buying and performance creative."</div></div>
        """, unsafe_allow_html=True)

    # Product / Ad Spend
    if "product" in breakdown or "ad_spend" in breakdown:
        st.markdown(f"""
        <div class="pitch"><h4>Angle: Market Domination</h4>
        <div class="msg">"Your latest product launch is making waves. We've helped AI applications scale their GTM through targeted LinkedIn and search campaigns that cut through the noise of the current AI hype cycle."</div></div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    # Sidebar snapshot selector
    st.sidebar.title("Brand Radar v4.1")
    snapshots = load_snapshots()
    if not snapshots:
        st.error("No snapshots found in `data/snapshots/`. Run `src/firehose_client.py` first.")
        return

    snap_options = {f"{f.name} ({datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})": f for f in snapshots}
    selected_snap_lbl = st.sidebar.selectbox("Select Intelligence Snapshot", list(snap_options.keys()))
    selected_snap_path = snap_options[selected_snap_lbl]

    data = load_data(selected_snap_path)
    if not data:
        st.warning("Could not load snapshot data.")
        return

    if st.session_state.view == "detail" and st.session_state.selected:
        company = next((s for s in data.get("scores", []) if s["company"] == st.session_state.selected), None)
        if company:
            render_detail(company)
        else:
            st.error(f"Company '{st.session_state.selected}' not found in this snapshot.")
            go_overview()
    else:
        render_overview(data)

    st.sidebar.divider()
    st.sidebar.caption(f"Brand Radar AI Edition\nSnapshot: {selected_snap_path.name}")


if __name__ == "__main__":
    main()
