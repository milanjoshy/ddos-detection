#!/usr/bin/env python3
"""
Real-Time DDoS Detection Dashboard
Enterprise-Grade Security Monitoring System
Provides real-time attack detection and network analysis using State Space Models

"""

import streamlit as st
import json
import time
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(
    page_title="DDoS Detection Dashboard", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional color scheme - Enterprise Design
COLORS = {
    'background': '#0F1419',
    'card_bg': '#1A2332',
    'sidebar': '#141D2B',
    'text': '#E8EAED',
    'text_secondary': '#9AA0A6',
    'primary': '#4285F4',      # Google Blue
    'success': '#34A853',      # Google Green
    'danger': '#EA4335',       # Google Red
    'warning': '#FBBC05',      # Google Yellow
    'accent': '#00BFA5',       # Teal
    'attack': '#EA4335',       # Red for attack
    'normal': '#34A853',       # Green for normal
    'connected': '#34A853',   # Green connected
    'disconnected': '#EA4335', # Red disconnected
    'chart_colors': ['#4285F4', '#00BFA5', '#EA4335', '#FBBC05', '#9C27B0', '#FF9800']
}

# Professional CSS styling
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLORS['background']}; color: {COLORS['text']}; font-family: 'Segoe UI', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: {COLORS['sidebar']}; }}
    [data-testid="stMetric"] {{ 
        background-color: {COLORS['card_bg']}; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 3px solid {COLORS['primary']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }}
    h1 {{ color: {COLORS['primary']} !important; font-weight: 700; letter-spacing: 0.5px; }}
    h2, h3 {{ color: {COLORS['accent']} !important; font-weight: 600; }}
    h4 {{ color: {COLORS['text']}; font-weight: 500; }}
    
    /* Status Boxes */
    .status-box {{ padding: 20px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 20px; }}
    .attack-box {{ 
        background-color: {COLORS['attack']}; 
        color: white; 
        padding: 15px; 
        border-radius: 8px; 
        font-weight: bold; 
        text-align: center; 
        font-size: 18px;
        box-shadow: 0 4px 12px rgba(234,67,53,0.4);
        animation: attack-pulse 1s infinite;
    }}
    .normal-box {{ 
        background-color: {COLORS['normal']}; 
        color: white; 
        padding: 15px; 
        border-radius: 8px; 
        font-weight: bold; 
        text-align: center; 
        font-size: 18px;
        box-shadow: 0 4px 12px rgba(52,168,83,0.4);
    }}
    .connected-box {{ 
        background-color: {COLORS['connected']}; 
        color: white; 
        padding: 20px; 
        border-radius: 10px; 
        font-weight: bold; 
        text-align: center; 
        font-size: 20px;
        box-shadow: 0 4px 12px rgba(52,168,83,0.4);
    }}
    .disconnected-box {{ 
        background-color: {COLORS['disconnected']}; 
        color: white; 
        padding: 20px; 
        border-radius: 10px; 
        font-weight: bold; 
        text-align: center; 
        font-size: 20px;
        box-shadow: 0 4px 12px rgba(234,67,53,0.4);
    }}
    .metric-card {{ background-color: {COLORS['card_bg']}; padding: 15px; border-radius: 8px; text-align: center; }}
    .section-header {{ 
        color: {COLORS['accent']}; 
        border-bottom: 3px solid {COLORS['primary']}; 
        padding-bottom: 10px; 
        margin-bottom: 20px;
        font-weight: 600;
        font-size: 18px;
    }}
    .info-badge {{ 
        background-color: {COLORS['primary']}; 
        color: white;
        padding: 8px 12px;
        border-radius: 5px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 5px 5px 0;
    }}
    .alert-badge {{ 
        background-color: {COLORS['warning']}; 
        color: #000;
        padding: 8px 12px;
        border-radius: 5px;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 5px 5px 0;
    }}
    @keyframes attack-pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.8; }}
    }}
    .header-container {{
        background: linear-gradient(135deg, #1A237E 0%, #6A1B9A 100%);
        padding: 30px;
        border-radius: 10px;
        margin-bottom: 30px;
        color: white;
    }}
    .stats-row {{
        background-color: {COLORS['card_bg']};
        padding: 20px;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 4px solid {COLORS['primary']};
    }}
    </style>
""", unsafe_allow_html=True)

# Session state
if 'data_history' not in st.session_state:
    st.session_state.data_history = []
if 'was_connected' not in st.session_state:
    st.session_state.was_connected = False
if 'source_type' not in st.session_state:
    st.session_state.source_type = None
if 'chart_containers' not in st.session_state:
    st.session_state.chart_containers = {}

def load_detection():
    """Load latest detection from JSON file"""
    path = Path("logs/latest_detection.json")
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def get_file_age(path):
    """Get age of file in seconds"""
    if path.exists():
        return time.time() - path.stat().st_mtime
    return float('inf')

def create_realtime_chart(data_history, key, title, y_data, color, yaxis_range=None, show_threshold=False, threshold_val=0.5):
    """Create a real-time updating chart"""
    if len(data_history) < 2:
        return None
    
    y_values = [d[y_data] for d in data_history]
    x_values = list(range(len(y_values)))
    
    fig = go.Figure()
    # Convert hex to rgba for transparency
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    rgba = f"rgba({r},{g},{b},0.2)"
    
    fig.add_trace(go.Scatter(
        y=y_values, 
        mode='lines+markers', 
        line=dict(color=color, width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor=rgba
    ))
    
    if show_threshold:
        fig.add_hline(y=threshold_val, line_dash="dash", line_color=COLORS['warning'], line_width=2)
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=COLORS['text'])),
        template="plotly_dark",
        height=220,
        margin=dict(l=40, r=20, t=40, b=30),
        paper_bgcolor='transparent',
        plot_bgcolor='transparent',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#2A3A4A',
            showticklabels=True,
            range=yaxis_range
        )
    )
    return fig

def load_training_history():
    """Load training history from checkpoint"""
    try:
        history_file = Path("checkpoints/training_history.json")
        if history_file.exists():
            with open(history_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        pass
    return None

def load_test_metrics_real_data():
    """Load real data test metrics"""
    try:
        metrics_file = Path("outputs/test_metrics_real_data.json")
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        pass
    return None

def create_training_accuracy_graph(history):
    """Create professional training vs validation accuracy graph"""
    if not history or 'train_accuracy' not in history:
        return None
    
    train_acc = history['train_accuracy']
    val_acc = history.get('val_accuracy', [])
    epochs = list(range(1, len(train_acc) + 1))
    
    fig = go.Figure()
    
    # Training accuracy
    fig.add_trace(go.Scatter(
        x=epochs, y=train_acc,
        mode='lines+markers',
        name='Training Accuracy',
        line=dict(color='#4285F4', width=3),
        marker=dict(size=5, opacity=0.8),
        fill='tozeroy',
        fillcolor='rgba(66, 133, 244, 0.15)',
        hovertemplate='<b>Training</b><br>Epoch: %{x}<br>Accuracy: %{y:.4f}<extra></extra>'
    ))
    
    # Validation accuracy
    if val_acc:
        fig.add_trace(go.Scatter(
            x=epochs[:len(val_acc)], y=val_acc,
            mode='lines+markers',
            name='Validation Accuracy',
            line=dict(color='#FBBC05', width=3),
            marker=dict(size=5, opacity=0.8),
            hovertemplate='<b>Validation</b><br>Epoch: %{x}<br>Accuracy: %{y:.4f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text='S5 Model: Training vs Validation Accuracy', font=dict(size=16, color=COLORS['text'])),
        xaxis_title='Epoch',
        yaxis_title='Accuracy',
        template='plotly_dark',
        hovermode='x unified',
        height=380,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#1A2332',
        paper_bgcolor='#0F1419',
        xaxis=dict(gridcolor='#2A3A4A', showgrid=True),
        yaxis=dict(gridcolor='#2A3A4A', showgrid=True),
        font=dict(color=COLORS['text'], family='Segoe UI'),
    )
    
    return fig

def create_training_loss_graph(history):
    """Create professional training vs validation loss graph"""
    if not history or 'train_loss' not in history:
        return None
    
    train_loss = history['train_loss']
    val_loss = history.get('val_loss', [])
    epochs = list(range(1, len(train_loss) + 1))
    
    fig = go.Figure()
    
    # Training loss
    fig.add_trace(go.Scatter(
        x=epochs, y=train_loss,
        mode='lines+markers',
        name='Training Loss',
        line=dict(color='#EA4335', width=3),
        marker=dict(size=5, opacity=0.8),
        hovertemplate='<b>Training</b><br>Epoch: %{x}<br>Loss: %{y:.6f}<extra></extra>'
    ))
    
    # Validation loss
    if val_loss:
        fig.add_trace(go.Scatter(
            x=epochs[:len(val_loss)], y=val_loss,
            mode='lines+markers',
            name='Validation Loss',
            line=dict(color='#9C27B0', width=3),
            marker=dict(size=5, opacity=0.8),
            hovertemplate='<b>Validation</b><br>Epoch: %{x}<br>Loss: %{y:.6f}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text='S5 Model: Training vs Validation Loss (Convergence Analysis)', font=dict(size=16, color=COLORS['text'])),
        xaxis_title='Epoch',
        yaxis_title='Loss (BCE)',
        template='plotly_dark',
        hovermode='x unified',
        height=380,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#1A2332',
        paper_bgcolor='#0F1419',
        xaxis=dict(gridcolor='#2A3A4A', showgrid=True),
        yaxis=dict(gridcolor='#2A3A4A', showgrid=True, type='log'),
        font=dict(color=COLORS['text'], family='Segoe UI'),
    )
    
    return fig

def create_model_metrics_comparison(history, test_metrics):
    """Create professional model performance metrics comparison"""
    if not test_metrics:
        return None
    
    # Get final training metrics
    final_train_acc = history['train_accuracy'][-1] if history and 'train_accuracy' in history else 0
    final_train_prec = history['train_precision'][-1] if history and 'train_precision' in history else 0
    final_train_rec = history['train_recall'][-1] if history and 'train_recall' in history else 0
    final_train_f1 = history['train_f1_score'][-1] if history and 'train_f1_score' in history else 0
    
    # Test metrics
    test_acc = test_metrics.get('accuracy', 0)
    test_prec = test_metrics.get('precision', 0)
    test_rec = test_metrics.get('recall', 0)
    test_f1 = test_metrics.get('f1_score', 0)
    
    metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    training = [final_train_acc, final_train_prec, final_train_rec, final_train_f1]
    testing = [test_acc, test_prec, test_rec, test_f1]
    
    fig = go.Figure(data=[
        go.Bar(x=metrics, y=training, name='Training', marker_color='#4285F4', 
               hovertemplate='<b>Training</b><br>%{x}: %{y:.4f}<extra></extra>'),
        go.Bar(x=metrics, y=testing, name='Testing', marker_color='#34A853',
               hovertemplate='<b>Testing</b><br>%{x}: %{y:.4f}<extra></extra>')
    ])
    
    fig.update_layout(
        title=dict(text='S5 Model: Final Performance Metrics (Training vs Testing)', font=dict(size=16, color=COLORS['text'])),
        xaxis_title='Metric',
        yaxis_title='Score',
        barmode='group',
        template='plotly_dark',
        height=380,
        margin=dict(l=60, r=40, t=60, b=50),
        plot_bgcolor='#1A2332',
        paper_bgcolor='#0F1419',
        xaxis=dict(gridcolor='#2A3A4A'),
        yaxis=dict(gridcolor='#2A3A4A', range=[0, 1.05]),
        font=dict(color=COLORS['text'], family='Segoe UI'),
    )
    
    return fig

def create_confusion_matrix_display(test_metrics):
    """Create professional confusion matrix display"""
    if not test_metrics:
        return None
    
    tp = test_metrics.get('true_positives', 0)
    tn = test_metrics.get('true_negatives', 0)
    fp = test_metrics.get('false_positives', 0)
    fn = test_metrics.get('false_negatives', 0)
    
    confusion_matrix = np.array([[tn, fp], [fn, tp]])
    
    fig = go.Figure(data=go.Heatmap(
        z=confusion_matrix,
        x=['Predicted Normal', 'Predicted Attack'],
        y=['Actual Normal', 'Actual Attack'],
        text=confusion_matrix,
        texttemplate='%{text}',
        textfont={"size": 18, "color": "white"},
        colorscale='Blues',
        colorbar=dict(title="Count"),
        hovertemplate='%{y}<br>%{x}<br>Count: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text='S5 Model: Test Set Confusion Matrix', font=dict(size=16, color=COLORS['text'])),
        height=380,
        margin=dict(l=100, r=100, t=60, b=50),
        plot_bgcolor='#1A2332',
        paper_bgcolor='#0F1419',
        font=dict(color=COLORS['text'], family='Segoe UI'),
    )
    
    return fig

def main():
    # Professional Header
    st.markdown("""
    <div class="header-container">
        <h1 style='margin: 0; font-size: 32px;'>🛡️ Real-Time DDoS Detection System</h1>
        <p style='margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;'>
            Enterprise-Grade Network Security Monitoring using State Space Models (S5)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Load data
    data = load_detection()
    log_path = Path("logs/latest_detection.json")
    file_age = get_file_age(log_path)
    
    # Check if data is fresh (less than 5 seconds old)
    is_fresh = file_age < 5 if log_path.exists() else False
    
    # Determine source type
    source_type = None
    if data and is_fresh:
        device_id = data.get('device_id', '').lower()
        if 'esp32' in device_id or device_id == '':
            source_type = "ESP32"
        elif 'simulator' in device_id or 'generator' in device_id:
            source_type = "Traffic Generator"
        else:
            source_type = "Unknown"
    
    is_connected = is_fresh and source_type is not None
    
    # Handle disconnection
    if st.session_state.was_connected and not is_connected:
        st.session_state.data_history = []
        st.session_state.was_connected = False
        st.session_state.source_type = None
    
    # Update connection state
    if is_connected:
        st.session_state.was_connected = True
        st.session_state.source_type = source_type
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Server Port", "5000", delta="UDP")
        with col2:
            st.metric("Protocol", "IPv4", delta="UDP")
        
        st.metric("Dashboard Port", "8501", delta="Streamlit")
        
        st.markdown("---")
        
        # Connection Status
        if is_connected:
            st.markdown(f'<div class="connected-box">✅ {source_type} CONNECTED</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="disconnected-box">❌ DISCONNECTED</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.header("🎯 Detection Settings")
        threshold = st.slider("Detection Threshold", 0.0, 1.0, 0.5, 0.05, key="threshold_slider")
        st.caption("Adjust sensitivity: lower = more sensitive, higher = stricter")
        
        refresh = st.slider("Refresh Rate (sec)", 1, 10, 2, key="refresh_slider")
        
        st.markdown("---")
        st.header("📡 Data Sources")
        
        st.markdown(f'<span class="info-badge">ESP32 Microcontroller</span>', unsafe_allow_html=True)
        st.caption("Connect real ESP32 device with network monitoring firmware")
        
        st.markdown(f'<span class="info-badge">Traffic Generator</span>', unsafe_allow_html=True)
        st.caption("Offline testing: `python traffic_simulator.py --mode mixed`")
        
        st.markdown("---")
        st.header("📊 System Metrics")
        
        if is_connected:
            st.success(f"**Receiving from:** {source_type}")
            st.metric("Last Update", f"{file_age:.1f}s ago", delta="seconds")
            st.metric("Time Connected", "Active", delta="monitoring")
        else:
            st.error("No data source connected")
            st.warning("Awaiting data source connection...")
        
        st.markdown("---")
        st.header("📖 Quick Guide")
        with st.expander("🔧 Setup Instructions"):
            st.markdown("""
            **Terminal 1: Start Server**
            ```bash
            python integrated_esp32_server.py
            ```
            
            **Terminal 2: Start Dashboard**
            ```bash
            streamlit run dashboard_unified.py
            ```
            
            **Terminal 3: Traffic (choose one)**
            - Real device: Connect ESP32
            - Simulator: `python traffic_simulator.py --mode mixed`
            """)
        
        with st.expander("ℹ️ System Information"):
            st.markdown(f"""
            **Model:** State Space Model (S5)
            **Framework:** PyTorch 2.0+
            **Inference:** CPU-Only (no GPU required)
            **Latency:** <100ms
            **Model Size:** <50MB
            **Memory:** <512MB RAM
            
            **Detection Capabilities:**
            - Binary Classification (Normal/Attack)
            - Multi-class Attack Types
            - Confidence Scoring
            - Source IP Tracking
            """)
        
        with st.expander("🔗 Project Links"):
            st.markdown("""
            - 📚 [README](README.md)
            - 📋 [Setup Guide](COMPLETE_WORKING_GUIDE.md)
            - 🚀 [Quick Start](README_COMMANDS.md)
            """)
        
        st.markdown("---")
        st.caption("© 2026 Karunya Institute | DDoS Detection System")
    
    # DISCONNECTED STATE
    if not is_connected:
        st.markdown(f'<div class="disconnected-box">❌ NO DATA SOURCE CONNECTED</div>', unsafe_allow_html=True)
        
        if st.session_state.source_type:
            st.warning(f"⚠️ **{st.session_state.source_type}** disconnected! Attempting to reconnect...")
        else:
            st.info("👁️ **Waiting for data source**... Please connect ESP32 or start traffic generator")
        
        st.markdown("---")
        st.markdown("### 📋 Quick Start Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f'<div class="stats-row" style="background-color: {COLORS["card_bg"]};">', unsafe_allow_html=True)
            st.markdown("**Option 1️⃣: Use Real ESP32 Device**")
            st.markdown("""
            1. Upload firmware to ESP32 using Arduino IDE
            2. Configure WiFi credentials in sketch
            3. Set gateway server IP
            4. Monitor via Serial (115200 baud)
            5. Dashboard auto-detects connection
            """)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stats-row" style="background-color: {COLORS["card_bg"]};">', unsafe_allow_html=True)
            st.markdown("**Option 2️⃣: Use Traffic Simulator**")
            st.markdown("""
            Run in Terminal 3:
            ```bash
            python traffic_simulator.py --mode mixed
            ```
            
            Or with SYN flood (requires admin):
            ```bash
            python traffic_simulator.py --mode syn_flood
            ```
            """)
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### ⚡ System Status")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.warning("Server Port: 5000")
        with col2:
            st.info("Data Storage: /logs/latest_detection.json")
        with col3:
            st.error("Status: Waiting for data...")
        
        time.sleep(refresh)
        st.rerun()
    
    # CONNECTED STATE - Display monitoring data
    if data and is_fresh:
        attack_prob = data.get('attack_probability', 0)
        is_attack = attack_prob >= threshold
        device_id = data.get('device_id', 'Unknown')
        
        # Add to history with timestamp
        st.session_state.data_history.append({
            'time': data.get('timestamp', ''),
            'prob': attack_prob,
            'is_attack': is_attack,
            'packet_rate': data.get('packet_rate', 0),
            'byte_rate': data.get('byte_rate', 0),
            'syn_ratio': data.get('syn_ratio', 0),
            'unique_src_ips': data.get('unique_src_ips', 0),
            'tcp_count': data.get('tcp_count', 0),
            'udp_count': data.get('udp_count', 0),
            'device_id': device_id,
            'source': source_type
        })
        
        # Keep last 100 points
        if len(st.session_state.data_history) > 100:
            st.session_state.data_history = st.session_state.data_history[-100:]
        
        # CURRENT STATUS SECTION
        st.markdown("### 🚨 Current Status")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            if is_attack:
                st.markdown(f'<div class="attack-box">🚨 ATTACK</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="normal-box">✓ NORMAL</div>', unsafe_allow_html=True)
        
        with col2:
            st.metric("Attack Probability", f"{attack_prob:.1%}")
        with col3:
            st.metric("Packets/sec", f"{data.get('packet_rate', 0):.0f}")
        with col4:
            st.metric("KB/sec", f"{data.get('byte_rate', 0):.0f}")
        with col5:
            st.metric("SYN Ratio", f"{data.get('syn_ratio', 0):.1%}")
        with col6:
            st.metric("Unique IPs", data.get('unique_src_ips', 0))
        
        # Status bar with details
        st.markdown(f"""
        <div class="stats-row">
        📡 <strong>Source:</strong> {source_type} | 
        🖥️ <strong>Device:</strong> {device_id} | 
        ⏱️ <strong>Last Update:</strong> {file_age:.1f}s ago |
        🔔 <strong>Threshold:</strong> {threshold:.0%}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # REAL-TIME CHARTS SECTION
        st.markdown("### 📊 Real-Time Network Analysis (Last 100 Data Points)")
        
        if len(st.session_state.data_history) > 1:
            # Create 2x2 subplot grid
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "🚨 Attack Probability Over Time", 
                    "📈 Packet Rate (packets/sec)",
                    "📉 Byte Rate (KB/sec)", 
                    "🔺 SYN Ratio (%)"
                ),
                vertical_spacing=0.15,
                horizontal_spacing=0.1
            )
            
            probs = [d['prob'] for d in st.session_state.data_history]
            pkt_rates = [d['packet_rate'] for d in st.session_state.data_history]
            byte_rates = [d['byte_rate'] for d in st.session_state.data_history]
            syn_ratios = [d['syn_ratio'] for d in st.session_state.data_history]
            
            # Attack Probability Chart
            fig.add_trace(go.Scatter(
                y=probs, mode='lines+markers',
                line=dict(color=COLORS['danger'], width=2),
                marker=dict(size=4),
                fill='tozeroy', fillcolor='rgba(234,67,53,0.2)',
                name='Attack Probability',
                hovertemplate='<b>Probability:</b> %{y:.1%}<extra></extra>'
            ), row=1, col=1)
            fig.add_hline(y=threshold, line_dash="dash", line_color=COLORS['warning'], line_width=2, row=1, col=1, annotation_text="Threshold")
            
            # Packet Rate Chart
            fig.add_trace(go.Scatter(
                y=pkt_rates, mode='lines+markers',
                line=dict(color=COLORS['primary'], width=2),
                marker=dict(size=4),
                fill='tozeroy', fillcolor='rgba(66,133,244,0.2)',
                name='Packet Rate',
                hovertemplate='<b>Packets/sec:</b> %{y:.0f}<extra></extra>'
            ), row=1, col=2)
            
            # Byte Rate Chart
            fig.add_trace(go.Scatter(
                y=byte_rates, mode='lines+markers',
                line=dict(color=COLORS['success'], width=2),
                marker=dict(size=4),
                fill='tozeroy', fillcolor='rgba(52,168,83,0.2)',
                name='Byte Rate',
                hovertemplate='<b>KB/sec:</b> %{y:.0f}<extra></extra>'
            ), row=2, col=1)
            
            # SYN Ratio Chart
            fig.add_trace(go.Scatter(
                y=syn_ratios, mode='lines+markers',
                line=dict(color=COLORS['accent'], width=2),
                marker=dict(size=4),
                fill='tozeroy', fillcolor='rgba(0,191,165,0.2)',
                name='SYN Ratio',
                hovertemplate='<b>SYN Ratio:</b> %{y:.1%}<extra></extra>'
            ), row=2, col=2)
            fig.add_hline(y=0.5, line_dash="dash", line_color=COLORS['warning'], line_width=2, row=2, col=2, annotation_text="Normal Threshold")
            
            # Update layout
            fig.update_layout(
                template="plotly_dark",
                height=500,
                showlegend=False,
                paper_bgcolor='#1A2332',
                plot_bgcolor='#1A2332',
                font=dict(color=COLORS['text'], family='Segoe UI'),
                margin=dict(l=60, r=30, t=80, b=30),
                hovermode='x unified'
            )
            
            # Update axes
            fig.update_xaxes(showgrid=False, showticklabels=False)
            fig.update_yaxes(showgrid=True, gridcolor='#2A3A4A')
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        st.markdown("---")
        
        # STATISTICS SECTION
        st.markdown("### 📈 Session Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        total = len(st.session_state.data_history)
        attacks = sum(1 for d in st.session_state.data_history if d['is_attack'])
        normal = total - attacks
        
        with col1:
            st.metric(
                "Total Detections",
                total,
                delta=f"{total} events",
                delta_color="off"
            )
        with col2:
            st.metric(
                "Attack Alerts",
                attacks,
                delta="Security Events",
                delta_color="inverse" if attacks > 0 else "normal"
            )
        with col3:
            st.metric(
                "Normal Traffic",
                normal,
                delta="Clean Events",
                delta_color="normal"
            )
        with col4:
            attack_rate = (attacks/max(1,total))*100
            st.metric(
                "Attack Rate",
                f"{attack_rate:.1f}%",
                delta=" ⚠️ HIGH" if attack_rate > 20 else " ✓ NORMAL",
                delta_color="inverse" if attack_rate > 20 else "normal"
            )
        
        st.markdown("---")
        
        # NETWORK DETAILS SECTION
        st.markdown("### 🌐 Network Traffic Details")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "TCP Packets",
                data.get('tcp_count', 0),
                delta="Active Connections",
                delta_color="off"
            )
        with col2:
            st.metric(
                "UDP Packets",
                data.get('udp_count', 0),
                delta="Datagram Traffic",
                delta_color="off"
            )
        with col3:
            st.metric(
                "Unique Sources",
                data.get('unique_src_ips', 0),
                delta="IP Addresses",
                delta_color="off"
            )
        with col4:
            st.metric(
                "Device ID",
                device_id[:20] + "..." if len(device_id) > 20 else device_id,
                delta="Monitoring Point",
                delta_color="off"
            )
        
        st.markdown("---")
        
        # ACTIVITY HISTORY SECTION
        st.markdown("### 📜 Recent Detection History (Last 10)")
        
        recent = st.session_state.data_history[-10:]
        table_data = []
        for idx, d in enumerate(recent, 1):
            status = "🚨 ATTACK" if d['is_attack'] else "✓ NORMAL"
            time_str = d['time'][-12:-3] if d['time'] else "N/A"
            table_data.append({
                "#": idx,
                "Time": time_str,
                "Status": status,
                "Probability": f"{d['prob']:.1%}",
                "Packets/s": f"{d['packet_rate']:.0f}",
                "Bytes/s": f"{d['byte_rate']:.0f}",
                "SYN": f"{d['syn_ratio']:.1%}",
                "IPs": d['unique_src_ips']
            })
        
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn("#", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Probability": st.column_config.TextColumn("Prob", width="small"),
            }
        )
        
        st.markdown("---")
        
        # S5 MODEL TRAINING & TESTING ANALYSIS SECTION
        st.markdown("### 🤖 S5 Model Training & Testing Analysis")
        
        training_history = load_training_history()
        test_metrics = load_test_metrics_real_data()
        
        if training_history or test_metrics:
            # Row 1: Loss comparison (Training vs Validation Loss)
            loss_fig = create_training_loss_graph(training_history)
            if loss_fig:
                st.plotly_chart(loss_fig, use_container_width=True)
            
            # Row 2: Test Results as plain text
            st.markdown("---")
            st.markdown("### 📊 Test Results (Real Data)")
            
            if test_metrics:
                st.code(json.dumps(test_metrics, indent=2), language="json")
            else:
                st.info("Test results not found in outputs/test_metrics_real_data.json")
        else:
            st.info("📁 Training and testing data not found. Run training first.")
        
        st.markdown("---")
        
        # AUTO-REFRESH
        st.markdown(f"""
        <div style='text-align: center; color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 20px;'>
        🔄 Auto-refreshing every {refresh} seconds | {len(st.session_state.data_history)} events in buffer
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh for real-time monitoring
    time.sleep(refresh)
    st.rerun()


if __name__ == "__main__":
    main()
