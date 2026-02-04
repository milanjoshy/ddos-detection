"""
Demo Script for Real-time DDoS Detection

Demonstrates the complete system with simulated traffic and real-time visualization.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import time
import argparse
from pathlib import Path

from ssm_model import DDoSDetector
from realtime_detector import RealTimeDetector
from feature_extraction import FeatureNormalizer
from generate_dataset import TrafficGenerator
from dashboard import DashboardVisualizer, HTMLDashboard
from config import Config


class SimulatedTrafficSource:
    """Simulate network traffic for demonstration."""
    
    def __init__(self, attack_probability: float = 0.3):
        """
        Initialize traffic simulator.
        
        Args:
            attack_probability: Probability of attack traffic
        """
        self.attack_probability = attack_probability
        self.packet_counter = 0
        
    def generate_packet(self) -> dict:
        """Generate a single packet."""
        self.packet_counter += 1
        
        # Randomly select traffic pattern
        if np.random.random() < self.attack_probability:
            # Attack traffic
            attack_types = ['syn_flood', 'udp_flood', 'http_flood', 'dns_amplification']
            pattern = np.random.choice(attack_types)
        else:
            # Normal traffic
            pattern = 'normal'
        
        # Generate sample from pattern
        features = TrafficGenerator.generate_sample(
            TrafficGenerator.PATTERNS[pattern],
            add_noise=True
        )
        
        # Create packet info
        packet_info = {
            'timestamp': time.time(),
            'size': int(features[2]),  # avg_packet_size
            'src_ip': f"192.168.{np.random.randint(0, 255)}.{np.random.randint(1, 255)}",
            'dst_port': np.random.choice([80, 443, 22, 53, 8080]),
            'protocol': 'TCP' if pattern != 'udp_flood' else 'UDP',
            'is_syn': pattern == 'syn_flood' and np.random.random() > 0.5
        }
        
        return packet_info


def load_model(config: Config):
    """Load trained model and normalizer."""
    print("Loading trained model...")
    
    # Initialize model
    model = DDoSDetector(
        input_dim=config.get('model.input_dim'),
        state_dim=config.get('model.state_dim'),
        hidden_dim=config.get('model.hidden_dim'),
        num_layers=config.get('model.num_layers'),
        dropout=config.get('model.dropout'),
        use_attention=config.get('model.use_attention')
    )
    
    # Load weights
    model_path = Path(config.get('paths.checkpoint_dir')) / 'best_model.pt'
    if model_path.exists():
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f"[OK] Model loaded from {model_path}")
    else:
        print("[WARN] No trained model found. Using randomly initialized model.")
        print("   Run train.py first to train a model.")
    
    # Load normalizer
    normalizer_path = Path(config.get('paths.normalizer_save_path'))
    if normalizer_path.exists():
        normalizer = FeatureNormalizer(feature_dim=config.get('model.input_dim'))
        normalizer.load(str(normalizer_path))
        print(f"[OK] Normalizer loaded from {normalizer_path}")
    else:
        print("⚠️  No normalizer found. Creating new normalizer.")
        normalizer = FeatureNormalizer(feature_dim=config.get('model.input_dim'))
    
    return model, normalizer


def run_demo_console(config: Config, duration: int = 60):
    """Run console-based demo."""
    print("\n" + "="*80)
    print("REAL-TIME DDOS DETECTION DEMO (Console Mode)")
    print("="*80)
    
    # Load model
    model, normalizer = load_model(config)
    
    # Initialize detector with shorter sequence for demo
    detector = RealTimeDetector(
        model=model,
        normalizer=normalizer,
        sequence_length=5,  # Reduced from 60 for faster demo detection
        window_size=0.5,  # Reduced from 1.0 for faster demo
        detection_threshold=config.get('inference.detection_threshold'),
        device=config.get('edge.target_device')
    )
    
    # Initialize traffic simulator
    traffic_source = SimulatedTrafficSource(attack_probability=0.3)
    
    # Start async processing
    detector.start_async_processing()
    
    print(f"\nStarting traffic simulation for {duration} seconds...")
    print("Press Ctrl+C to stop early.\n")
    
    start_time = time.time()
    last_print_time = start_time
    packet_count = 0
    
    try:
        while time.time() - start_time < duration:
            # Generate packets
            for _ in range(10):  # Burst of packets
                packet = traffic_source.generate_packet()
                detector.process_packet(packet)
                packet_count += 1
            
            # Check for detection results
            result = detector.get_latest_result(timeout=0.1)
            if result:
                # Print result
                status = "[ATTACK]" if result.is_attack else "[OK]"
                print(f"[{time.strftime('%H:%M:%S')}] {status} | "
                      f"Prob: {result.attack_probability:.3f} | "
                      f"Conf: {result.confidence:.3f} | "
                      f"Type: {result.attack_type} | "
                      f"Rate: {result.packet_rate:.0f} pkt/s")
            
            # Print statistics every 10 seconds
            current_time = time.time()
            if current_time - last_print_time >= 10:
                stats = detector.get_statistics()
                print(f"\n--- Statistics (Uptime: {stats['uptime_seconds']:.0f}s) ---")
                print(f"  Total Detections: {stats['total_detections']}")
                print(f"  Total Attacks: {stats['total_attacks']}")
                print(f"  Attack Rate: {stats['attack_rate']:.2%}")
                print()
                last_print_time = current_time
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nStopping demo...")
    
    finally:
        detector.stop_async_processing()
    
    # Final statistics
    stats = detector.get_statistics()
    print("\n" + "="*80)
    print("DEMO COMPLETED")
    print("="*80)
    print(f"\nFinal Statistics:")
    print(f"  Total Packets Processed: {packet_count}")
    print(f"  Total Detections: {stats['total_detections']}")
    print(f"  Total Attacks Detected: {stats['total_attacks']}")
    print(f"  Attack Rate: {stats['attack_rate']:.2%}")
    print(f"  Runtime: {stats['uptime_seconds']:.1f} seconds")


def run_demo_dashboard(config: Config, duration: int = 300):
    """Run demo with HTML dashboard visualization."""
    print("\n" + "="*80)
    print("REAL-TIME DDOS DETECTION DEMO (Dashboard Mode)")
    print("="*80)
    
    # Load model
    model, normalizer = load_model(config)
    
    # Initialize detector with shorter sequence for demo
    detector = RealTimeDetector(
        model=model,
        normalizer=normalizer,
        sequence_length=5,  # Reduced from 60 for faster demo detection
        window_size=0.5,  # Reduced from 1.0 for faster demo
        detection_threshold=config.get('inference.detection_threshold'),
        device=config.get('edge.target_device')
    )
    
    # Initialize visualizer
    visualizer = DashboardVisualizer(max_history=config.get('dashboard.max_history'))
    
    # Initialize traffic simulator
    traffic_source = SimulatedTrafficSource(attack_probability=0.3)
    
    # Start async processing
    detector.start_async_processing()
    
    print(f"\nGenerating traffic and collecting data for {duration} seconds...")
    print("Dashboard will be updated every 5 seconds.\n")
    
    start_time = time.time()
    last_save_time = start_time
    save_interval = 5  # Update dashboard every 5 seconds
    
    try:
        while time.time() - start_time < duration:
            # Generate packets
            for _ in range(20):
                packet = traffic_source.generate_packet()
                detector.process_packet(packet)
            
            # Check for detection results
            result = detector.get_latest_result(timeout=0.1)
            if result:
                visualizer.update(result)
                
                # Print brief status
                status = "🚨" if result.is_attack else "✅"
                print(f"{status} {result.attack_type:20s} | "
                      f"Prob: {result.attack_probability:.3f} | "
                      f"Conf: {result.confidence:.3f}")
            
            # Save dashboard periodically
            current_time = time.time()
            if current_time - last_save_time >= save_interval:
                output_path = Path(config.get('paths.output_dir'))
                HTMLDashboard.generate_dashboard(
                    visualizer,
                    str(output_path / 'realtime_dashboard.html')
                )
                print(f"\n📊 Dashboard updated: {output_path / 'realtime_dashboard.html'}\n")
                last_save_time = current_time
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\nStopping demo...")
    
    finally:
        detector.stop_async_processing()
    
    # Save final dashboard
    output_path = Path(config.get('paths.output_dir'))
    HTMLDashboard.generate_dashboard(
        visualizer,
        str(output_path / 'realtime_dashboard.html')
    )
    
    # Print final statistics
    stats = visualizer.get_statistics_summary()
    print("\n" + "="*80)
    print("DEMO COMPLETED")
    print("="*80)
    print(f"\nFinal Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"\n📊 Dashboard saved to: {output_path / 'realtime_dashboard.html'}")
    print("   Open this file in a web browser to view the visualization.")


def run_batch_demo(config: Config):
    """Run batch detection demo on pre-generated sequences."""
    print("\n" + "="*80)
    print("BATCH DETECTION DEMO")
    print("="*80)
    
    # Load model
    model, normalizer = load_model(config)
    model.eval()
    
    # Generate test sequences
    print("\nGenerating test sequences...")
    test_sequences = []
    test_labels = []
    test_types = []
    
    patterns = ['normal', 'syn_flood', 'udp_flood', 'http_flood']
    for pattern in patterns:
        for _ in range(5):
            seq = TrafficGenerator.generate_sequence(pattern, config.get('data.sequence_length'))
            test_sequences.append(seq)
            test_labels.append(0 if pattern == 'normal' else 1)
            test_types.append(pattern)
    
    # Normalize
    test_sequences = np.array(test_sequences)
    normalized_sequences = np.array([normalizer.normalize(seq) for seq in test_sequences])
    
    # Convert to tensor
    X = torch.FloatTensor(normalized_sequences)
    
    # Predict
    print("\nPerforming batch detection...")
    with torch.no_grad():
        predictions = model.predict(X, threshold=config.get('inference.detection_threshold'))
    
    # Display results
    print("\nDetection Results:")
    print("-" * 80)
    print(f"{'Pattern':<20} {'True Label':<15} {'Predicted':<15} {'Probability':<15} {'Confidence':<15}")
    print("-" * 80)
    
    correct = 0
    for i in range(len(test_sequences)):
        true_label = "Attack" if test_labels[i] == 1 else "Normal"
        pred_label = "Attack" if predictions['is_attack'][i].item() == 1 else "Normal"
        prob = predictions['attack_probability'][i].item()
        conf = predictions['confidence'][i].item()
        
        if test_labels[i] == predictions['is_attack'][i].item():
            correct += 1
            marker = "✅"
        else:
            marker = "❌"
        
        print(f"{marker} {test_types[i]:<17} {true_label:<15} {pred_label:<15} {prob:<14.3f} {conf:<15.3f}")
    
    accuracy = correct / len(test_sequences)
    print("-" * 80)
    print(f"Accuracy: {accuracy:.2%} ({correct}/{len(test_sequences)})")


def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description='DDoS Detection Demo')
    parser.add_argument('--mode', type=str, default='console',
                       choices=['console', 'dashboard', 'batch'],
                       help='Demo mode')
    parser.add_argument('--duration', type=int, default=60,
                       help='Demo duration in seconds (for console and dashboard modes)')
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config file')
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = Config.load(args.config)
    else:
        config = Config()
    
    # Run demo based on mode
    if args.mode == 'console':
        run_demo_console(config, duration=args.duration)
    elif args.mode == 'dashboard':
        run_demo_dashboard(config, duration=args.duration)
    elif args.mode == 'batch':
        run_batch_demo(config)


if __name__ == "__main__":
    main()
