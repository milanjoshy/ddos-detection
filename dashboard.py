"""
Real-time Dashboard for DDoS Detection Monitoring

This module provides a web-based dashboard for visualizing detection results,
confidence scores, and network statistics in real-time.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import time
import torch
import threading
import random


class DashboardVisualizer:
    """Real-time visualization dashboard."""
    
    def __init__(self, max_history: int = 500):
        """
        Initialize dashboard.
        
        Args:
            max_history: Maximum number of data points to keep
        """
        self.max_history = max_history
        
        # Data buffers
        self.timestamps = deque(maxlen=max_history)
        self.attack_probs = deque(maxlen=max_history)
        self.confidences = deque(maxlen=max_history)
        self.packet_rates = deque(maxlen=max_history)
        self.byte_rates = deque(maxlen=max_history)
        self.attack_types = deque(maxlen=max_history)
        self.is_attacks = deque(maxlen=max_history)
        
        # Statistics
        self.total_detections = 0
        self.total_attacks = 0
        self.attack_sources = {}
        self.all_source_ips = {}  # Track all IPs, not just attacks
    
    def update(self, result):
        """Update dashboard with new detection result."""
        self.timestamps.append(result.timestamp)
        self.attack_probs.append(result.attack_probability)
        self.confidences.append(result.confidence)
        self.packet_rates.append(result.packet_rate)
        self.byte_rates.append(result.byte_rate)
        self.attack_types.append(result.attack_type)
        self.is_attacks.append(result.is_attack)
        
        # Track all source IPs from every detection
        for ip in result.source_ips:
            self.all_source_ips[ip] = self.all_source_ips.get(ip, 0) + 1
            if result.is_attack:
                self.attack_sources[ip] = self.attack_sources.get(ip, 0) + 1
        
        self.total_detections += 1
        if result.is_attack:
            self.total_attacks += 1
    
    def create_realtime_plot(self):
        """Create real-time monitoring plot."""
        if not self.timestamps:
            return go.Figure()
        
        # Convert timestamps to datetime
        times = [datetime.fromtimestamp(t) for t in self.timestamps]
        
        # Create subplot figure
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Attack Probability Over Time',
                'Detection Confidence',
                'Packet Rate',
                'Byte Rate',
                'Attack Type Distribution',
                'Attack vs Normal Traffic'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"type": "pie"}, {"type": "bar"}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.12
        )
        
        # Attack Probability
        attack_color = ['red' if a else 'green' for a in self.is_attacks]
        fig.add_trace(
            go.Scatter(
                x=times,
                y=list(self.attack_probs),
                mode='lines+markers',
                name='Attack Probability',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(color=attack_color, size=6),
                fill='tozeroy',
                fillcolor='rgba(255, 107, 107, 0.2)'
            ),
            row=1, col=1
        )
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray", row=1, col=1)
        
        # Confidence
        fig.add_trace(
            go.Scatter(
                x=times,
                y=list(self.confidences),
                mode='lines+markers',
                name='Confidence',
                line=dict(color='#4ECDC4', width=2),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(78, 205, 196, 0.2)'
            ),
            row=1, col=2
        )
        
        # Packet Rate
        fig.add_trace(
            go.Scatter(
                x=times,
                y=list(self.packet_rates),
                mode='lines',
                name='Packet Rate',
                line=dict(color='#95E1D3', width=2),
                fill='tozeroy'
            ),
            row=2, col=1
        )
        
        # Byte Rate
        fig.add_trace(
            go.Scatter(
                x=times,
                y=list(self.byte_rates),
                mode='lines',
                name='Byte Rate',
                line=dict(color='#F38181', width=2),
                fill='tozeroy'
            ),
            row=2, col=2
        )
        
        # Attack Type Distribution (Pie)
        attack_type_counts = pd.Series(self.attack_types).value_counts()
        fig.add_trace(
            go.Pie(
                labels=attack_type_counts.index,
                values=attack_type_counts.values,
                hole=0.4,
                marker=dict(colors=['#4ECDC4', '#FF6B6B', '#95E1D3', '#F38181', '#FFE66D'])
            ),
            row=3, col=1
        )
        
        # Attack vs Normal (Bar)
        attack_counts = pd.Series(self.is_attacks).value_counts()
        fig.add_trace(
            go.Bar(
                x=['Normal', 'Attack'],
                y=[attack_counts.get(False, 0), attack_counts.get(True, 0)],
                marker=dict(color=['#4ECDC4', '#FF6B6B']),
                text=[attack_counts.get(False, 0), attack_counts.get(True, 0)],
                textposition='auto'
            ),
            row=3, col=2
        )
        
        # Update layout
        fig.update_xaxes(title_text="Time", row=1, col=1)
        fig.update_xaxes(title_text="Time", row=1, col=2)
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_xaxes(title_text="Time", row=2, col=2)
        fig.update_xaxes(title_text="Traffic Type", row=3, col=2)
        
        fig.update_yaxes(title_text="Probability", row=1, col=1)
        fig.update_yaxes(title_text="Confidence", row=1, col=2)
        fig.update_yaxes(title_text="Packets/sec", row=2, col=1)
        fig.update_yaxes(title_text="Bytes/sec", row=2, col=2)
        fig.update_yaxes(title_text="Count", row=3, col=2)
        
        fig.update_layout(
            height=1000,
            showlegend=False,
            title_text="DDoS Detection Dashboard - Real-time Monitoring",
            title_font=dict(size=20, color='#2C3E50'),
            font=dict(size=12)
        )
        
        return fig
    
    def create_source_ip_table(self, top_n: int = 20):
        """Create table of top source IPs (all detections or just attacks)."""
        # Show all IPs if no attacks detected, otherwise show just attack sources
        sources_to_use = self.attack_sources if self.attack_sources else self.all_source_ips
        
        if not sources_to_use:
            return pd.DataFrame()
        
        sorted_sources = sorted(
            sources_to_use.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        df = pd.DataFrame(sorted_sources, columns=['Source IP', 'Detection Count'])
        total_count = self.total_attacks if self.attack_sources else self.total_detections
        df['Percentage'] = (df['Detection Count'] / max(1, total_count) * 100).round(2)
        return df
    
    def get_statistics_summary(self):
        """Get summary statistics."""
        if self.total_detections == 0:
            return {
                'Total Detections': 0,
                'Total Attacks': 0,
                'Attack Rate (%)': 0,
                'Average Confidence': 0,
                'Average Packet Rate': 0,
                'Unique Attack Sources': 0
            }

        return {
            'Total Detections': self.total_detections,
            'Total Attacks': self.total_attacks,
            'Attack Rate (%)': round(self.total_attacks / self.total_detections * 100, 2),
            'Average Confidence': round(np.mean(list(self.confidences)) * 100, 2) if self.confidences else 0,
            'Average Packet Rate': round(np.mean(list(self.packet_rates)), 2) if self.packet_rates else 0,
            'Unique Attack Sources': len(self.attack_sources)
        }


def create_streamlit_dashboard():
    """Create Streamlit-based real-time dashboard."""

    st.set_page_config(
        page_title="DDoS Detection Dashboard",
        page_icon="shield",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS
    st.markdown("""
        <style>
        .main {
            background-color: #F7F9FC;
        }
        .stMetric {
            background-color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-positive {
            color: #4ECDC4;
        }
        .metric-negative {
            color: #FF6B6B;
        }
        /* Ensure metric and content text is visible on light backgrounds */
        .stMetric, .stMetric *,
        .block-container, .streamlit-expanderHeader, .stText, .stMarkdown {
            color: #2C3E50 !important;
        }
        .stMetric svg { filter: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # Title
    st.title("Real-time DDoS Detection Dashboard")
    st.markdown("---")

    # Initialize session state
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = DashboardVisualizer()

    if 'detector' not in st.session_state:
        # Load model and normalizer
        try:
            from ssm_model import DDoSDetector
            from feature_extraction import FeatureNormalizer
            from realtime_detector import RealTimeDetector
            from generate_dataset import TrafficGenerator

            # Load model
            model = DDoSDetector(
                input_dim=8,
                state_dim=32,
                hidden_dim=64,
                num_layers=2,
                dropout=0.1,
                use_attention=True
            )
            checkpoint = torch.load('./checkpoints/best_model.pt', map_location='cpu', weights_only=False)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.eval()

            # Load normalizer
            normalizer = FeatureNormalizer(feature_dim=8)
            normalizer.load('./checkpoints/normalizer.npz')

            # Initialize detector
            detector = RealTimeDetector(
                model=model,
                normalizer=normalizer,
                sequence_length=5,  # Shorter sequence for faster dashboard demo
                window_size=0.5,    # Smaller window so detections occur sooner
                detection_threshold=0.8,  # Higher threshold to reduce false positives on real traffic
                device='cpu'
            )

            st.session_state.detector = detector
            # Start detector async processing so incoming packets are processed
            try:
                st.session_state.detector.start_async_processing()
            except Exception:
                pass
            st.session_state.traffic_generator = TrafficGenerator()
            st.session_state.live_thread = None
            st.session_state.live_running = False
            st.session_state.live_capture_running = False
            st.session_state.packet_count = 0
            st.session_state.last_detection = None

        except Exception as e:
            st.error(f"Failed to load model: {e}")
            return

    visualizer = st.session_state.visualizer
    detector = st.session_state.detector

    # Sidebar
    with st.sidebar:
        st.header("Settings")

        detection_threshold = st.slider(
            "Detection Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.05
        )

        window_size = st.slider(
            "Time Window (seconds)",
            min_value=1,
            max_value=60,
            value=10,
            step=1
        )

        refresh_rate = st.slider(
            "Refresh Rate (seconds)",
            min_value=1,
            max_value=10,
            value=2,
            step=1
        )

        st.markdown("---")

        st.header("Live Simulation")

        if st.button("Start Live Detection"):
            if not st.session_state.live_running:
                st.session_state.live_running = True
                st.session_state.live_capture_running = False
                st.session_state.start_time = time.time()
                st.success("Live detection started!")

        if st.button("Stop Live Detection"):
            st.session_state.live_running = False
            st.info("Live detection stopped.")

        st.markdown("---")

        st.header("Live Network Capture")
        st.info("Requires scapy and admin/elevated privileges. Ensure 'scapy' is installed via: pip install scapy")

        if st.button("Start Live Capture"):
            if not st.session_state.live_capture_running:
                st.session_state.live_capture_running = True
                st.session_state.live_running = False
                st.session_state.start_time = time.time()
                st.success("Live packet capture started! (Admin privileges required)")

        if st.button("Stop Live Capture"):
            st.session_state.live_capture_running = False
            st.info("Live capture stopped.")

        st.markdown("---")

        st.header("System Info")
        st.info("Model: Linear SSM")
        st.info("Device: CPU")
        mode_text = "Simulated" if st.session_state.live_running else ("Live Capture" if st.session_state.live_capture_running else "Inactive")
        st.info(f"Mode: {mode_text}")

        # Debug information to help troubleshoot live simulation
        try:
            stats = detector.get_statistics()
            st.markdown("**Debug**")
            st.write({
                'live_running': st.session_state.live_running,
                'packets_in_queue': stats.get('packets_in_queue', 'N/A'),
                'results_in_queue': stats.get('results_in_queue', 'N/A'),
                'feature_buffer_size': stats.get('buffer_size', 'N/A'),
                'total_detections': stats.get('total_detections', 'N/A')
            })
        except Exception:
            st.write("Debug: detector not available yet")

        if st.button("Reset Dashboard"):
            st.session_state.visualizer = DashboardVisualizer()
            st.session_state.live_running = False
            st.session_state.live_capture_running = False
            # Stop detector async processing if running
            try:
                if 'detector' in st.session_state:
                    st.session_state.detector.stop_async_processing()
            except Exception:
                pass
            st.rerun()

    # Update detector threshold
    detector.detection_threshold = detection_threshold

    # Run live capture if live_capture_running is True
    if st.session_state.live_capture_running:
        try:
            from realtime_detector import LiveCaptureDetector
            
            if 'live_capture_detector' not in st.session_state:
                st.session_state.live_capture_detector = LiveCaptureDetector(
                    detector=detector,
                    interface=None,  # Auto-detect default interface
                    filter_expr="ip"  # Capture all IP packets
                )
                st.session_state.live_capture_detector.start_capture(callback=None)
            
            # Check for detection results from live capture
            while True:
                result = detector.get_latest_result(timeout=0.01)
                if not result:
                    break
                visualizer.update(result)
                st.session_state.packet_count += 1
                
                # Log detection result
                try:
                    import os, json
                    os.makedirs('logs', exist_ok=True)
                    det_summary = {
                        'timestamp': result.timestamp,
                        'is_attack': result.is_attack,
                        'attack_probability': round(result.attack_probability, 3),
                        'confidence': round(result.confidence, 3),
                        'attack_type': result.attack_type,
                        'source_ips': result.source_ips,
                        'packet_count': result.packet_count,
                        'byte_rate': round(result.byte_rate, 2),
                        'packet_rate': round(result.packet_rate, 2)
                    }
                    with open(os.path.join('logs', 'detections.log'), 'a') as _dlf:
                        _dlf.write(json.dumps(det_summary) + "\n")
                except Exception:
                    pass
                
                # Save the last detection summary for UI
                try:
                    st.session_state.last_detection = {
                        'time': datetime.fromtimestamp(result.timestamp).strftime('%H:%M:%S'),
                        'type': result.attack_type,
                        'prob': round(result.attack_probability, 3),
                        'conf': round(result.confidence, 3),
                        'is_attack': result.is_attack
                    }
                except Exception:
                    st.session_state.last_detection = None
        except ImportError:
            st.error("scapy is required for live capture. Install with: pip install scapy")
            st.session_state.live_capture_running = False
        except Exception as e:
            st.error(f"Error during live capture: {e}")
            st.session_state.live_capture_running = False

    # Run simulation if live_running is True
    if st.session_state.live_running:
        # Generate a few packets per refresh
        from generate_dataset import TrafficGenerator
        import random
        
        if 'traffic_gen' not in st.session_state:
            st.session_state.traffic_gen = TrafficGenerator()
            st.session_state.attack_patterns = ['normal', 'syn_flood', 'udp_flood', 'http_flood', 'dns_amplification']
        
        traffic_gen = st.session_state.traffic_gen
        attack_patterns = st.session_state.attack_patterns
        
        # Generate packets
        for _ in range(15):
            # increase attack frequency in dashboard demo to make detections more likely
            if random.random() < 0.5:  # 50% attack traffic
                pattern = random.choice(attack_patterns[1:])
            else:
                pattern = 'normal'
            
            try:
                sample = traffic_gen.generate_sample(traffic_gen.PATTERNS[pattern])
                packet_info = {
                    'timestamp': time.time(),
                    'size': int(sample[2]),
                    'src_ip': f"192.168.1.{random.randint(1, 254)}",
                    'dst_port': random.randint(1, 65535),
                    'protocol': 'TCP' if random.random() < 0.7 else 'UDP',
                    'is_syn': random.random() < sample[4]
                }
                # Log simulated packet
                try:
                    import os, json
                    os.makedirs('logs', exist_ok=True)
                    with open(os.path.join('logs', 'packets.log'), 'a') as _lf:
                        _lf.write(json.dumps({'source': 'simulated', 'packet': packet_info, 'logged_at': time.time()}) + "\n")
                except Exception:
                    pass

                detector.process_packet(packet_info)
                # Track packet count for visible counter
                try:
                    st.session_state.packet_count += 1
                except Exception:
                    st.session_state.packet_count = 1
            except:
                pass
        
        # Drain result queue and update visualizer for all available results
        while True:
            result = detector.get_latest_result(timeout=0.01)
            if not result:
                break
            visualizer.update(result)
            
            # Log detection result
            try:
                import os, json
                os.makedirs('logs', exist_ok=True)
                det_summary = {
                    'timestamp': result.timestamp,
                    'is_attack': result.is_attack,
                    'attack_probability': round(result.attack_probability, 3),
                    'confidence': round(result.confidence, 3),
                    'attack_type': result.attack_type,
                    'source_ips': result.source_ips,
                    'packet_count': result.packet_count,
                    'byte_rate': round(result.byte_rate, 2),
                    'packet_rate': round(result.packet_rate, 2)
                }
                with open(os.path.join('logs', 'detections.log'), 'a') as _dlf:
                    _dlf.write(json.dumps(det_summary) + "\n")
            except Exception:
                pass
            
            # Save the last detection summary for UI
            try:
                st.session_state.last_detection = {
                    'time': datetime.fromtimestamp(result.timestamp).strftime('%H:%M:%S'),
                    'type': result.attack_type,
                    'prob': round(result.attack_probability, 3),
                    'conf': round(result.confidence, 3),
                    'is_attack': result.is_attack
                }
            except Exception:
                st.session_state.last_detection = None
            # Save the last detection summary for UI
            try:
                st.session_state.last_detection = {
                    'time': datetime.fromtimestamp(result.timestamp).strftime('%H:%M:%S'),
                    'type': result.attack_type,
                    'prob': round(result.attack_probability, 3),
                    'conf': round(result.confidence, 3),
                    'is_attack': result.is_attack
                }
            except Exception:
                st.session_state.last_detection = None

    # Main content
    # Statistics Row
    stats = visualizer.get_statistics_summary()

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            label="Total Detections",
            value=stats['Total Detections'],
            delta=None
        )

    with col2:
        st.metric(
            label="Total Attacks",
            value=stats['Total Attacks'],
            delta=None
        )

    with col3:
        st.metric(
            label="Attack Rate",
            value=f"{stats['Attack Rate (%)']}%",
            delta=None
        )

    with col4:
        st.metric(
            label="Avg Confidence",
            value=f"{stats['Average Confidence']}%",
            delta=None
        )

    with col5:
        st.metric(
            label="Avg Packet Rate",
            value=f"{stats['Average Packet Rate']}/s",
            delta=None
        )

    with col6:
        st.metric(
            label="Attack Sources",
            value=stats['Unique Attack Sources'] if 'Unique Attack Sources' in stats else len(visualizer.attack_sources),
            delta=None
        )

    st.markdown("---")

    # Main plot
    with st.container():
        plot_placeholder = st.empty()
        plot_placeholder.plotly_chart(
            visualizer.create_realtime_plot(),
            use_container_width=True
        )

    # Visible counters: Packets processed and last detection
    col_a, col_b = st.columns([1, 2])
    with col_a:
        pkt_count = st.session_state.get('packet_count', 0)
        st.metric(label="Packets Processed (session)", value=pkt_count)
    with col_b:
        last_det = st.session_state.get('last_detection')
        if last_det:
            st.subheader("Last Detection")
            st.write(f"Time: {last_det['time']}")
            st.write(f"Type: {last_det['type']}")
            st.write(f"Probability: {last_det['prob']}")
            st.write(f"Confidence: {last_det['conf']}")
            st.write(f"Is Attack: {last_det['is_attack']}")
        else:
            st.info("No detections yet")

    st.markdown("---")

    # Source IP Table
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Top Attack Source IPs")
        source_df = visualizer.create_source_ip_table()
        if not source_df.empty:
            st.dataframe(source_df, use_container_width=True, height=400)
        else:
            st.info("No attack sources detected yet.")

    with col2:
        st.subheader("Recent Alerts")
        if visualizer.is_attacks:
            recent_attacks = []
            for i in range(len(visualizer.timestamps)-1, max(len(visualizer.timestamps)-10, -1), -1):
                if visualizer.is_attacks[i]:
                    recent_attacks.append({
                        'Time': datetime.fromtimestamp(visualizer.timestamps[i]).strftime('%H:%M:%S'),
                        'Type': visualizer.attack_types[i],
                        'Prob': f"{visualizer.attack_probs[i]:.2%}"
                    })

            if recent_attacks:
                st.table(pd.DataFrame(recent_attacks))
            else:
                st.success("No recent attacks detected")
        else:
            st.success("No attacks detected")

    # Auto-refresh
    time.sleep(refresh_rate)
    st.rerun()


def simulate_live_traffic(detector, visualizer):
    """Simulate live traffic for demonstration."""
    try:
        from generate_dataset import TrafficGenerator
        import random

        # Initialize simulation state if not exists
        if 'traffic_gen' not in st.session_state:
            st.session_state.traffic_gen = TrafficGenerator()
            st.session_state.attack_patterns = ['normal', 'syn_flood', 'udp_flood', 'http_flood', 'dns_amplification']
            st.session_state.packet_count = 0

        traffic_gen = st.session_state.traffic_gen
        attack_patterns = st.session_state.attack_patterns
        packet_count = st.session_state.packet_count

        # Generate a few packets per run
        for _ in range(5):
            # Randomly choose traffic pattern (mostly normal, occasional attacks)
            if random.random() < 0.8:  # 80% normal traffic
                pattern = 'normal'
            else:
                pattern = random.choice(attack_patterns[1:])  # Random attack

            # Generate traffic sample
            sample = traffic_gen.generate_sample(traffic_gen.PATTERNS[pattern])

            # Create packet info
            packet_info = {
                'timestamp': time.time(),
                'size': int(sample[2]),  # avg packet size
                'src_ip': f"192.168.1.{random.randint(1, 254)}",
                'dst_port': random.randint(1, 65535),
                'protocol': 'TCP' if random.random() < 0.7 else 'UDP',
                'is_syn': random.random() < sample[4]  # syn_ratio
            }

            # Process packet
            detector.process_packet(packet_info)
            packet_count += 1

            # Check for detection result every 10 packets
            if packet_count % 10 == 0:
                result = detector.extract_and_detect()
                if result:
                    visualizer.update(result)

        st.session_state.packet_count = packet_count

    except Exception as e:
        print(f"Error in live simulation: {e}")
        import traceback
        traceback.print_exc()


class HTMLDashboard:
    """Generate HTML dashboards for offline viewing."""
    
    @staticmethod
    def generate_dashboard(visualizer, output_path: str):
        """Generate an HTML dashboard from visualizer data."""
        try:
            import plotly.io as pio
            
            # Create the plot
            fig = visualizer.create_realtime_plot()
            
            # Generate HTML
            html_content = pio.to_html(fig, include_plotlyjs='cdn')
            
            # Add statistics summary
            stats = visualizer.get_statistics_summary()
            
            stats_html = """
            <div style="margin: 20px; font-family: Arial, sans-serif;">
                <h2>Detection Statistics</h2>
                <table style="border-collapse: collapse; width: 100%;">
            """
            
            for key, value in stats.items():
                stats_html += f"""
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 10px; font-weight: bold;">{key}</td>
                        <td style="padding: 10px;">{value}</td>
                    </tr>
                """
            
            stats_html += """
                </table>
            </div>
            """
            
            # Combine HTML
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>DDoS Detection Dashboard</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f7f9fc; }}
                    .header {{ color: #2c3e50; margin-bottom: 30px; }}
                    .container {{ max-width: 1400px; margin: 0 auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="header">Real-time DDoS Detection Dashboard</h1>
                    {stats_html}
                    {html_content}
                </div>
            </body>
            </html>
            """
            
            # Save to file
            with open(output_path, 'w') as f:
                f.write(full_html)
            
            return True
        except Exception as e:
            print(f"Error generating HTML dashboard: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    create_streamlit_dashboard()
