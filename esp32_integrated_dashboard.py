"""
ESP32-Integrated Real-Time Dashboard
Bridges ESP32 UDP data with existing dashboard.py visualizer

"""

import streamlit as st
import json
import time
from pathlib import Path
import sys

# Import your existing modules
try:
    from dashboard import DashboardVisualizer
    from realtime_detector import DetectionResult
    print("[SUCCESS] Loaded existing dashboard modules")
except ImportError as e:
    st.error(f"Cannot import dashboard modules: {e}")
    st.stop()

# ============================================================================
# LOAD LATEST DETECTION FROM FILE (written by integrated_server.py)
# ============================================================================

def load_latest_detection():
    """Load latest detection result from JSON file written by integrated_server.py"""
    detection_file = Path("logs/latest_detection.json")
    if detection_file.exists():
        try:
            with open(detection_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            return None
    return None

# ============================================================================
# STREAMLIT DASHBOARD WITH ESP32 INTEGRATION
# ============================================================================

def create_esp32_integrated_dashboard():
    """Main dashboard with ESP32 integration"""
    
    st.set_page_config(
        page_title="ESP32 DDoS Detection Dashboard",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main {background-color: #F7F9FC;}
        .stMetric {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .attack-alert {
            background-color: #ff4444;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .normal-status {
            background-color: #44ff44;
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'visualizer' not in st.session_state:
        try:
            st.session_state.visualizer = DashboardVisualizer(max_history=500)
        except Exception as e:
            st.warning(f"Could not load visualizer: {e}")
            st.session_state.visualizer = None
    
    if 'esp_data_count' not in st.session_state:
        st.session_state.esp_data_count = 0
    
    if 'last_detection' not in st.session_state:
        st.session_state.last_detection = None
    
    if 'last_json_timestamp' not in st.session_state:
        st.session_state.last_json_timestamp = None
    
    # Get references
    visualizer = st.session_state.visualizer
    
    # Header
    st.title("ESP32 Real-Time DDoS Detection Dashboard")
    st.markdown("**Live monitoring from ESP32 edge devices with S5 model predictions**")
    st.markdown("---")
    
    # Status metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    if visualizer:
        stats = visualizer.get_statistics_summary()
    else:
        stats = {'Total Detections': 0, 'Total Attacks': 0, 'Attack Rate (%)': 0, 'Average Confidence': 0}
    
    with col1:
        st.metric("ESP32 Status", "Active" if st.session_state.esp_data_count > 0 else "Waiting")
    
    with col2:
        st.metric("Data Received", st.session_state.esp_data_count)
    
    with col3:
        st.metric("Total Detections", stats['Total Detections'])
    
    with col4:
        st.metric("Total Attacks", stats['Total Attacks'])
    
    with col5:
        st.metric("Attack Rate", f"{stats['Attack Rate (%)']}%")
    
    with col6:
        st.metric("Avg Confidence", f"{stats['Average Confidence']}%")
    
    st.markdown("---")
    
    # Load latest detection from JSON file (written by integrated_server.py)
    latest_json = load_latest_detection()
    
    # Update visualizer with latest JSON data (prevent duplicates)
    if latest_json and visualizer:
        try:
            from datetime import datetime
            timestamp_str = latest_json.get('timestamp', datetime.now().isoformat())
            timestamp = datetime.fromisoformat(timestamp_str).timestamp()
            
            # Check if this is a new timestamp (prevent duplicates)
            if st.session_state.last_json_timestamp != timestamp:
                st.session_state.last_json_timestamp = timestamp
                
                class FakeResult:
                    def __init__(self, data, ts):
                        self.timestamp = ts
                        self.is_attack = data.get('is_attack', False)
                        self.attack_probability = data.get('attack_probability', 0)
                        self.confidence = data.get('confidence', 0)
                        self.attack_type = 'Normal' if not data.get('is_attack') else 'Attack'
                        self.source_ips = [f"src_{data.get('unique_src_ips', 0)}"]
                        self.packet_count = int(data.get('packet_rate', 0))
                        self.byte_rate = data.get('byte_rate', 0)
                        self.packet_rate = data.get('packet_rate', 0)
                
                fake_result = FakeResult(latest_json, timestamp)
                visualizer.update(fake_result)
                st.session_state.esp_data_count += 1
        except Exception as e:
            pass  # Ignore visualization errors
    
    # Display latest detection from JSON
    st.subheader("Latest Detection (from integrated_server.py)")
    
    if latest_json:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = "ATTACK" if latest_json.get('is_attack') else "NORMAL"
            st.metric("Status", status)
        
        with col2:
            st.metric("Probability", f"{latest_json.get('attack_probability', 0):.1%}")
        
        with col3:
            st.metric("Packet Rate", f"{latest_json.get('packet_rate', 0):.1f}/s")
        
        with col4:
            st.metric("SYN Ratio", f"{latest_json.get('syn_ratio', 0):.1%}")
        
        st.info(f"Last updated: {latest_json.get('timestamp', 'Unknown')}")
    else:
        st.info("Waiting for detection data from integrated_server.py...")
    
    st.markdown("---")
    
    # Main visualization from existing dashboard
    st.subheader("Real-Time Monitoring")
    
    if visualizer and visualizer.timestamps:
        fig = visualizer.create_realtime_plot()
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for detection data (need 60 timesteps = ~60 seconds of data)")
    
    # Source IP table
    st.markdown("---")
    st.subheader("Source IP Analysis")
    
    if visualizer:
        source_df = visualizer.create_source_ip_table(top_n=10)
        if not source_df.empty:
            st.dataframe(source_df, use_container_width=True)
        else:
            st.info("No source IPs detected yet")
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        st.metric("Server Port", "5000")
        st.metric("Sequence Length", "60 timesteps")
        st.metric("Detection Threshold", "50%")
        
        st.markdown("---")
        
        st.header("System Info")
        st.info(f"""
        Model: S5 State Space (running in integrated_esp32_server.py)
        Server Port: 5000 (UDP)
        Dashboard Port: 8501 (Streamlit)
        Status: Reading from logs/latest_detection.json
        """)
        
        st.markdown("---")
        
        st.header("Controls")
        
        refresh_rate = st.slider("Refresh Rate (sec)", 1, 10, 2)
        
        if st.button("Clear History"):
            if visualizer:
                visualizer.timestamps.clear()
                visualizer.attack_probs.clear()
                visualizer.confidences.clear()
            st.session_state.esp_data_count = 0
            st.success("History cleared!")
        
        st.markdown("---")
        
        st.header("Instructions")
        st.markdown("""
        **Before starting dashboard:**
        1. Terminal 1: Start integrated_server.py
           
```
bash
           python integrated_esp32_server.py
           
```
        
        2. Upload ESP32 firmware (Arduino IDE)
        
        3. Terminal 2: Run traffic simulator
           
```
bash
           python traffic_simulator.py --mode normal
           
```
           Or test SYN flood:
           
```
bash
           python traffic_simulator.py --mode syn_flood
           
```
        
        4. Terminal 3: This dashboard
        
        **Dashboard Reads From:**
        - `/logs/latest_detection.json` (written by server)
        - No socket binding needed!
        """)
    
    # Auto-refresh
    time.sleep(refresh_rate)
    st.rerun()


if __name__ == "__main__":
    create_esp32_integrated_dashboard()
