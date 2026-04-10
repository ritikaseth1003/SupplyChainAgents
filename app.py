"""
SupplyChainAgents – Streamlit Dashboard

A live interactive dashboard that displays:
  - Agent states
  - Inventory levels
  - Predicted demand (7-day forecasts)
  - Open purchase orders
  - Real-time agent chat log
  - Key metrics (stockout rate, turnover, cost, recovery time)
  - "Trigger Disruption" button
"""

import time
import httpx
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="SupplyChainAgents Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium dark theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Agent status cards */
    .agent-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .agent-name {
        font-size: 14px;
        font-weight: 600;
        color: #e94560;
        margin-bottom: 4px;
    }
    .agent-status {
        font-size: 12px;
        color: #a8b2d1;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(83,52,131,0.3);
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #00d2ff;
    }
    .metric-label {
        font-size: 12px;
        color: #a8b2d1;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Chat log */
    .chat-msg {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        font-size: 13px;
        border-left: 3px solid;
    }
    .chat-system { 
        background: rgba(233,69,96,0.1); 
        border-left-color: #e94560; 
        color: #e94560;
    }
    .chat-forecaster { 
        background: rgba(0,210,255,0.08); 
        border-left-color: #00d2ff; 
        color: #a8b2d1;
    }
    .chat-inventory { 
        background: rgba(0,255,157,0.08); 
        border-left-color: #00ff9d; 
        color: #a8b2d1;
    }
    .chat-replenishment { 
        background: rgba(255,193,7,0.08); 
        border-left-color: #ffc107; 
        color: #a8b2d1;
    }
    .chat-logistics { 
        background: rgba(155,89,182,0.08); 
        border-left-color: #9b59b6; 
        color: #a8b2d1;
    }
    
    /* Disruption banner */
    .disruption-banner {
        background: linear-gradient(90deg, #e94560, #c0392b);
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        font-weight: 600;
        text-align: center;
        animation: pulse 2s infinite;
        margin-bottom: 16px;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Section headers */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        color: #e94560;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #0f3460;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: fetch state from the message bus
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1)
def fetch_state() -> dict:
    """Poll the message bus for current simulation state."""
    try:
        resp = httpx.get(f"{API_BASE}/state", timeout=3)
        return resp.json()
    except Exception:
        return {}


def trigger_disruption() -> dict:
    try:
        resp = httpx.post(f"{API_BASE}/disruption", timeout=5)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# 🏭 SupplyChainAgents")
    st.markdown("### Multi-Agent AI System")
    st.markdown("---")
    
    if st.button("🚨 Trigger Disruption", use_container_width=True, type="primary"):
        result = trigger_disruption()
        if "error" in result:
            st.error(f"Failed: {result['error']}")
        else:
            st.success(f"Triggered: {result.get('description', 'Unknown')}")
    
    st.markdown("---")
    
    if st.button("🔄 Reset Simulation", use_container_width=True):
        try:
            httpx.post(f"{API_BASE}/reset", timeout=3)
            st.success("Simulation reset!")
        except Exception:
            st.error("Could not reset – is the server running?")
    
    auto_refresh = st.toggle("Auto-refresh (2s)", value=True)
    
    st.markdown("---")
    st.markdown(
        "**How it works:**\n"
        "1. Start the simulator: `python -m core.simulator`\n"
        "2. Run this dashboard: `streamlit run app.py`\n"
        "3. Press **Trigger Disruption** to test recovery"
    )


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
state = fetch_state()

if not state:
    st.warning(
        "⏳ Waiting for simulator… Start it with: `python -m core.simulator`"
    )
    st.stop()

# ---- Disruption banner ----
if state.get("active_disruption"):
    dis = state["active_disruption"]
    st.markdown(
        f'<div class="disruption-banner">🚨 ACTIVE DISRUPTION: {dis["description"]}</div>',
        unsafe_allow_html=True,
    )

# ---- Title row ----
st.markdown("## 📊 Live Dashboard")
st.markdown(f"**Simulation Day:** {state.get('sim_day', 0)}")

# ---- Metrics row ----
st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)
m = state.get("metrics", {})
c1, c2, c3, c4 = st.columns(4)

total_demand = m.get("total_demand", 1)
stockouts = m.get("stockout_count", 0)
stockout_rate = round(stockouts / max(total_demand, 1) * 100, 2)

days = m.get("days_simulated", 1) or 1
inventory_vals = list(state.get("inventory", {}).values())
avg_inv = sum(inventory_vals) / max(len(inventory_vals), 1)
turnover = round(total_demand / max(avg_inv * days, 1), 2)

with c1:
    st.metric("📉 Stockout Rate", f"{stockout_rate}%", delta=f"{stockouts} events")
with c2:
    st.metric("🔄 Inventory Turnover", f"{turnover}x")
with c3:
    st.metric("💰 Total Cost", f"${m.get('total_cost', 0):,.0f}")
with c4:
    recovery = m.get("disruption_recovery_time", 0)
    st.metric("⏱️ Recovery Time", f"{recovery:.1f}s")


# ---- Agent states ----
st.markdown('<div class="section-header">Agent Status</div>', unsafe_allow_html=True)
agent_cols = st.columns(4)
agent_icons = {
    "DemandForecaster": "🔮",
    "InventoryManager": "📦",
    "ReplenishmentPlanner": "📝",
    "LogisticsCoordinator": "🚚",
}
agent_colors = {
    "DemandForecaster": "#00d2ff",
    "InventoryManager": "#00ff9d",
    "ReplenishmentPlanner": "#ffc107",
    "LogisticsCoordinator": "#9b59b6",
}

for i, (agent, status) in enumerate(state.get("agent_states", {}).items()):
    with agent_cols[i]:
        icon = agent_icons.get(agent, "🤖")
        color = agent_colors.get(agent, "#ffffff")
        st.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-name" style="color:{color}">{icon} {agent}</div>'
            f'<div class="agent-status">Status: <b>{status}</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ---- Charts row ----
col_inv, col_fc = st.columns(2)

with col_inv:
    st.markdown('<div class="section-header">Inventory Levels</div>', unsafe_allow_html=True)
    inv = state.get("inventory", {})
    safety = state.get("safety_stock", {})
    if inv:
        df_inv = pd.DataFrame({
            "Product": list(inv.keys()),
            "Stock": list(inv.values()),
            "Safety Stock": [safety.get(p, 150) for p in inv.keys()],
        })
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_inv["Product"], y=df_inv["Stock"],
            name="Current Stock",
            marker_color=["#00d2ff" if s > ss else "#e94560"
                          for s, ss in zip(df_inv["Stock"], df_inv["Safety Stock"])],
        ))
        fig.add_trace(go.Scatter(
            x=df_inv["Product"], y=df_inv["Safety Stock"],
            name="Safety Stock",
            mode="lines+markers",
            line=dict(color="#ffc107", dash="dash", width=2),
        ))
        fig.update_layout(
            template="plotly_dark",
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", y=-0.15),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

with col_fc:
    st.markdown('<div class="section-header">7-Day Demand Forecast</div>', unsafe_allow_html=True)
    forecasts = state.get("forecasts", {})
    if any(forecasts.values()):
        fig2 = go.Figure()
        colors = ["#00d2ff", "#00ff9d", "#e94560", "#ffc107", "#9b59b6"]
        for idx, (product, vals) in enumerate(forecasts.items()):
            if vals:
                fig2.add_trace(go.Scatter(
                    x=list(range(1, len(vals) + 1)),
                    y=vals,
                    name=product,
                    mode="lines+markers",
                    line=dict(color=colors[idx % len(colors)], width=2),
                ))
        fig2.update_layout(
            template="plotly_dark",
            height=350,
            xaxis_title="Day",
            yaxis_title="Units",
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", y=-0.2),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Forecasts will appear after the first agent cycle.")


# ---- Purchase Orders ----
st.markdown('<div class="section-header">Purchase Orders</div>', unsafe_allow_html=True)
pos = state.get("purchase_orders", [])
if pos:
    df_po = pd.DataFrame(pos)
    display_cols = [c for c in ["id", "product", "quantity", "supplier", "status", "estimated_cost", "created_at"] if c in df_po.columns]
    st.dataframe(
        df_po[display_cols],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No purchase orders yet.")


# ---- Supplier Info ----
with st.expander("📋 Supplier Information"):
    suppliers = state.get("suppliers", [])
    if suppliers:
        st.dataframe(pd.DataFrame(suppliers), use_container_width=True, hide_index=True)


# ---- Chat Log ----
st.markdown('<div class="section-header">Agent Chat Log</div>', unsafe_allow_html=True)
chat_log = state.get("chat_log", [])
if chat_log:
    chat_container = st.container(height=400)
    with chat_container:
        for ts, agent, msg in reversed(chat_log[-50:]):
            css_class = "chat-system"
            if "Forecaster" in agent:
                css_class = "chat-forecaster"
            elif "Inventory" in agent:
                css_class = "chat-inventory"
            elif "Replenishment" in agent:
                css_class = "chat-replenishment"
            elif "Logistics" in agent:
                css_class = "chat-logistics"
            
            # Truncate very long messages for display
            display_msg = msg[:500] + "…" if len(msg) > 500 else msg
            st.markdown(
                f'<div class="chat-msg {css_class}">'
                f'<b>[{ts}] {agent}:</b> {display_msg}'
                f'</div>',
                unsafe_allow_html=True,
            )
else:
    st.info("Chat log will appear once agents are active.")


# ---- Auto-refresh ----
if auto_refresh:
    time.sleep(2)
    st.rerun()
