import streamlit as st
import requests
import random
from datetime import datetime, timezone
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ------------------ CONFIG ------------------
API_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 3 

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="AI API Real-Time Monitor",
    page_icon="📊",
    layout="wide",
)

# ------------------ CUSTOM STYLING (Professional Dark Mode) ------------------
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1a1c24;
        border: 1px solid #2d2e35;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #161b22; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ------------------ SESSION STATE (Persistent History) ------------------
# This stores past events so the graphs have data even when the backend window resets
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Time", "Throughput", "ErrorRate"])

# ------------------ AUTO REFRESH ------------------
st_autorefresh(interval=5000, key="data_refresh")

# ------------------ SIDEBAR: LOG SIMULATOR ------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=50)
    st.title("Settings")
    
    stream_active = st.toggle("Live Stream Simulation", value=True)
    k_threshold = st.slider("Anomaly Sensitivity (k)", 0.5, 3.0, 1.5)
    
    st.divider()
    if st.button(" Generate Burst Logs", use_container_width=True):
        for _ in range(30):
            log = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": random.choice(["alice_001", "bob_002", "charlie_003"]),
                "latency_ms": random.randint(100, 1500),
                "tokens_used": random.randint(50, 2000),
                "is_error": random.random() < 0.08,
            }
            try:
                requests.post(f"{API_URL}/ingest", json=log, timeout=1)
            except:
                pass
        st.sidebar.success("Burst sent to API!")

# ------------------ DATA FETCHING ------------------
try:
    response = requests.get(f"{API_URL}/metrics", timeout=REQUEST_TIMEOUT)
    data = response.json()
    
    # Update History Dataframe
    new_entry = {
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Throughput": data.get('requests_per_min', 0),
        "ErrorRate": data.get('error_rate', 0.0) * 100
    }
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_entry])], ignore_index=True)
    st.session_state.history = st.session_state.history.tail(20) # Keep last 20 snapshots

except Exception as e:
    st.error(" Backend unreachable. Ensure FastAPI server is running.")
    st.stop()

# ------------------ MAIN UI ------------------
st.title("AI API Real-Time Monitor")

# --- TOP ROW: KPI CARDS ---
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Throughput", f"{data.get('requests_per_min', 0)} RPM")
    with c2:
        err = data.get('error_rate', 0.0)
        st.metric("Error Rate", f"{err*100:.1f}%", delta_color="inverse")
    with c3:
        st.metric("P95 Latency", f"{data.get('p95_latency', 0):.0f} ms")
    with c4:
        st.metric("Est. Cost", f"${data.get('estimated_cost_usd', 0.0):.4f}")

st.markdown("---")

# --- MIDDLE ROW: PERFORMANCE TRENDS ---
st.subheader(" Performance Trends")
t_col1, t_col2 = st.columns(2)

with t_col1:
    st.write("*Throughput (Requests/Min)*")
    st.area_chart(st.session_state.history.set_index("Time")["Throughput"], color="#29b5e8")

with t_col2:
    st.write("*Error Rate (%)*")
    st.line_chart(st.session_state.history.set_index("Time")["ErrorRate"], color="#ff4b4b")

# --- BOTTOM ROW: DISTRIBUTION ---
st.markdown("---")
col_l, col_r = st.columns([1, 1])

with col_l:
    st.subheader(" Latency Percentiles")
    lat_data = pd.DataFrame({
        "Level": ["P50", "P95", "P99"],
        "ms": [data.get('p50_latency', 0), data.get('p95_latency', 0), data.get('p99_latency', 0)]
    }).set_index("Level")
    st.bar_chart(lat_data, color="#7f00ff")

with col_r:
    st.subheader(" User Distribution")
    user_counts = data.get("per_user_requests", {})
    if user_counts:
        user_df = pd.DataFrame.from_dict(user_counts, orient="index", columns=["Requests"])
        st.bar_chart(user_df.sort_values("Requests"), horizontal=True, color="#29b5e8")
    else:
        st.info("No active user data in window.")

# --- FOOTER: ALERTS ---
st.markdown("---")
st.subheader(" Incident Log")
alert_box = st.container(border=True)
with alert_box:
    anomalies = data.get("anomalies", [])
    if anomalies:
        for alert in anomalies:
            if "CRITICAL" in alert.upper():
                st.error(f"🔴 {alert}")
            else:
                st.warning(f"🟡 {alert}")
    else:
        st.success("✅ All systems nominal. No anomalies detected.")

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

