"""
ESP32-Integrated Real-Time Dashboard v2
Dark theme with built-in mode selection and simulation control
Default mode: ESP32
"""

import streamlit as st
import json
import time
from pathlib import Path

try:
    from dashboard import DashboardVisualizer
    print("[SUCCESS] Loaded dashboard modules")
except ImportError as e:
    st.error(f"Cannot import dashboard modules: {e}")
    st.stop()

def load_latest_detection():
    detection_file = Path("logs/latest_detection.json")
    if detection_file.exists():
        try:
            with open(detection_file, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def get_current_mode():
    """Auto-detect current mode based on latest detection data"""
    latest = load_latest_detection()
    if latest:
        device_id = latest.get('device_id', '').lower()
        if 'esp32' in device_id or 'pc' in device_id:
            return 'ESP32'
        elif 'simulator' in device_id or 'generator' in device_id:
            return 'Simulation'
    return 'ESP32'  # Default mode

def main():
    st.set_page_config(page_title="DDoS Detection", page_icon="", layout="wide")
    
    st.markdown("""
        <style>
        .stApp { background-color: #1E1E2E; color: #CDD6F4; }
        [data-testid="stSidebar"] { background-color: #181825; }
        [data-testid="stMetric"] { background-color: #313244; padding: 15px; border-radius: 8px; }
        [data-testid="stMetricLabel"] { color: #A6ADC8 !important; }
        [data-testid="stMetricValue"] { color: #89B4FA !important; }
        h1, h2, h3 { color: #CBA6F7 !important; }
        .attack-box { background-color: #F38BA8; color: #181825; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; }
        .normal-box { background-color: #A6E3A1; color: #181825; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'threshold' not in st.session_state:
        st.session_state.threshold = 0.5
    if 'visualizer' not in st.session_state:
        try:
            st.session_state.visualizer = DashboardVisualizer(max_history=500)
        except:
            st.session_state.visualizer = None
    if 'data_count' not in st.session_state:
        st.session_state.data_count = 0
    if 'mode' not in st.session_state:
        st.session_state.mode = get_current_mode()
    if 'simulation_running' not in st.session_state:
        st.session_state.simulation_running = False
    
    st.title("Real-Time DDoS Detection Dashboard")
    st.markdown("---")
    
    with st.sidebar:
        st.header("Detection Mode")
        
        # Mode selection - Default is ESP32
        mode = st.radio(
            "Select Source",
            ["ESP32 (Real Device)", "Simulation (Test Traffic)"],
            index=0 if st.session_state.mode == 'ESP32' else 1
        )
        
        new_mode = 'ESP32' if 'ESP32' in mode else 'Simulation'
        
        # Handle mode change
        if new_mode != st.session_state.mode:
            st.session_state.mode = new_mode
            if new_mode == 'Simulation':
                st.session_state.simulation_running = True
            elif new_mode == 'ESP32':
                st.session_state.simulation_running = False
        
        st.markdown("---")
        
        # Simulation control (only in simulation mode)
        if st.session_state.mode == 'Simulation':
            st.header("Traffic Simulation Control")
            
            if st.button("Toggle Traffic Simulation"):
                st.session_state.simulation_running = not st.session_state.simulation_running
                st.rerun()
            
            if st.session_state.simulation_running:
                st.success("Traffic: ON")
            else:
                st.info("Traffic: OFF")
            
            st.markdown("---")
        
        # Settings
        st.header("Settings")
        threshold = st.slider("Detection Threshold", 0.0, 1.0, st.session_state.threshold, 0.05)
        st.session_state.threshold = threshold
        refresh_rate = st.slider("Refresh Rate", 1, 10, 2)
        
        st.markdown("---")
        
        # System info
        st.header("System Info")
        st.metric("Server Port", "5000")
        st.metric("Sequence Length", "60 timesteps")
        st.metric("Default Mode", "ESP32")
        
        st.markdown("---")
        
        # Instructions
        st.header("How to Use")
        st.markdown("""
        **Default: ESP32 Mode**
        - Connect ESP32 device
        - Server receives real traffic
        - View live network data
        
        **Switch to Simulation:**
        - Select "Simulation" above
        - Generates synthetic attack traffic
        - For testing the system
        """)
    
    # Status row
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    visualizer = st.session_state.visualizer
    
    if visualizer:
        stats = visualizer.get_statistics_summary()
    else:
        stats = {'Total Detections': 0, 'Total Attacks': 0, 'Attack Rate (%)': 0, 'Average Confidence': 0}
    
    # Current source status
    source_status = "Active"
    if st.session_state.mode == 'Simulation':
        source_status = "Simulation" if st.session_state.simulation_running else "Standby"
    
    with col1:
        st.metric("Mode", st.session_state.mode)
    with col2:
        st.metric("Source", source_status)
    with col3:
        st.metric("Data Received", st.session_state.data_count)
    with col4:
        st.metric("Total Detections", stats['Total Detections'])
    with col5:
        st.metric("Total Attacks", stats['Total Attacks'])
    with col6:
        st.metric("Attack Rate", f"{stats['Attack Rate (%)']}%")
    
    st.markdown("---")
    
    latest = load_latest_detection()
    
    st.subheader("Latest Detection")
    
    if latest:
        attack_prob = latest.get('attack_probability', 0)
        is_attack = attack_prob >= threshold
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if is_attack:
                st.markdown('<div class="attack-box">ATTACK DETECTED</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="normal-box">NORMAL TRAFFIC</div>', unsafe_allow_html=True)
        with col2:
            st.metric("Attack Probability", f"{attack_prob:.1%}")
        with col3:
            st.metric("Packet Rate", f"{latest.get('packet_rate', 0):.1f}/s")
        with col4:
            st.metric("SYN Ratio", f"{latest.get('syn_ratio', 0):.1%}")
        
        st.caption(f"Device: {latest.get('device_id', 'Unknown')} | Last update: {latest.get('timestamp', 'Unknown')}")
    else:
        st.info("Waiting for detection data... Make sure server is running.")
    
    st.markdown("---")
    st.subheader("Real-Time Graphs")
    
    threshold = st.session_state.threshold
    
    if visualizer and len(visualizer.timestamps) > 1:
        import plotly.graph_objects as go
        
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=visualizer.timestamps, y=visualizer.attack_probs, mode='lines', name='Attack Probability', line=dict(color='#F38BA8', width=2)))
        fig1.add_hline(y=threshold, line_dash="dash", line_color="#F9E2AF", annotation_text=f"Threshold")
        fig1.update_layout(title="Attack Probability Over Time", template="plotly_dark", height=250, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = go.Figure()
        pkts = [getattr(r, 'packet_count', 0) for r in getattr(visualizer, 'results', [])]
        fig2.add_trace(go.Scatter(x=visualizer.timestamps[:len(pkts)], y=pkts, mode='lines', name='Packet Rate', line=dict(color='#89B4FA', width=2), fill='tozeroy'))
        fig2.update_layout(title="Packet Rate Over Time", template="plotly_dark", height=250, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = go.Figure()
        bytes_r = [getattr(r, 'byte_rate', 0) for r in getattr(visualizer, 'results', [])]
        fig3.add_trace(go.Scatter(x=visualizer.timestamps[:len(bytes_r)], y=bytes_r, mode='lines', name='Byte Rate', line=dict(color='#A6E3A1', width=2), fill='tozeroy'))
        fig3.update_layout(title="Byte Rate Over Time", template="plotly_dark", height=250, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig3, use_container_width=True)
        
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=visualizer.timestamps, y=visualizer.confidences, mode='lines', name='Confidence', line=dict(color='#CBA6F7', width=2)))
        fig4.update_layout(title="Detection Confidence Over Time", template="plotly_dark", height=250, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Waiting for more data points...")
    
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()
