#!/usr/bin/env python3
"""
INTEGRATED ESP32 + Trained S5 Model Detection Server

This integrates with your existing project:
- Uses YOUR trained S5 model from checkpoints/
- Uses YOUR ssm_model.py architecture
- Uses YOUR feature normalizer
- Receives data from ESP32
- Makes real-time predictions

Author: Milan Joshy (URK22CS1182)
"""

import sys
import os
import socket
import json
import torch
import numpy as np
from datetime import datetime
from collections import deque
import threading
import time
from pathlib import Path

# Add your project directory to path
# UPDATE THIS PATH to your project location
PROJECT_DIR = Path(__file__).parent # Adjust if needed
sys.path.insert(0, str(PROJECT_DIR))


# TEMPORARY DEBUG - Remove after testing
print(f"[DEBUG] Project directory: {PROJECT_DIR}")
print(f"[DEBUG] Files found:")
for file in PROJECT_DIR.glob("*.py"):
    print(f"  - {file.name}")
print(f"[DEBUG] Checkpoints exist: {(PROJECT_DIR / 'checkpoints').exists()}")


# Import YOUR existing model architecture
try:
    from ssm_model import DDoSDetector  # Your trained model
    print("[SUCCESS] Loaded YOUR S5 model architecture")
except ImportError as e:
    print(f"[ERROR] Could not import your model: {e}")
    print("Make sure ssm_model.py is in the correct path")
    sys.exit(1)

# Import YOUR feature normalizer if available
try:
    from feature_extraction import FeatureNormalizer
    print("[SUCCESS] Loaded YOUR feature normalizer")
    HAS_NORMALIZER = True
except ImportError:
    print("[WARNING] Could not import FeatureNormalizer, using basic normalization")
    HAS_NORMALIZER = False

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5000
BUFFER_SIZE = 2048

SEQUENCE_LENGTH = 5  # Reduced for faster detection (was 60)
FEATURE_DIM = 8
DETECTION_THRESHOLD = 0.5

# Path to YOUR trained model
MODEL_PATH = PROJECT_DIR / "checkpoints" / "real_data" / "best_model.pt"
NORMALIZER_PATH = PROJECT_DIR / "checkpoints" / "normalizer.npz"

# ============================================================================
# FALLBACK NORMALIZER (if yours not available)
# ============================================================================

class SimpleNormalizer:
    """Fallback normalizer if yours not available"""
    def __init__(self, feature_dim, momentum=0.99):
        self.feature_dim = feature_dim
        self.momentum = momentum
        self.mean = np.zeros(feature_dim)
        self.var = np.ones(feature_dim)
        self.count = 0
    
    def update(self, features):
        self.count += 1
        if self.count == 1:
            self.mean = features.copy()
            self.var = np.ones_like(features)
        else:
            self.mean = self.momentum * self.mean + (1 - self.momentum) * features
            diff = features - self.mean
            self.var = self.momentum * self.var + (1 - self.momentum) * (diff ** 2)
    
    def normalize(self, features):
        std = np.sqrt(self.var + 1e-8)
        return (features - self.mean) / std

# ============================================================================
# ESP32 DATA PROCESSOR
# ============================================================================

class ESP32DataProcessor:
    """Process ESP32 data and prepare for YOUR trained model"""
    
    def __init__(self, sequence_length=15, normalizer_path=None):
        self.sequence_length = sequence_length
        self.devices = {}
        self.normalizers = {}
        self.last_alert_time = {}
        
        # Try to load YOUR saved normalizer
        if normalizer_path and Path(normalizer_path).exists():
            try:
                # Load from npz file (not pickle)
                normalizer_data = np.load(normalizer_path)
                self.running_mean = normalizer_data['running_mean']
                self.running_var = normalizer_data['running_var']
                self.count = normalizer_data['count']
                print(f"[SUCCESS] Loaded YOUR normalizer from {normalizer_path}")
                print(f"  Mean: {self.running_mean}")
                print(f"  Var: {self.running_var}")
                self.use_global_normalizer = True
            except Exception as e:
                print(f"[WARNING] Could not load normalizer: {e}")
                self.use_global_normalizer = False
        else:
            self.use_global_normalizer = False
            print("[INFO] No saved normalizer found, using online normalization")
    
    def add_data(self, device_id, data):
        """Add new data point for a device"""
        if device_id not in self.devices:
            self.devices[device_id] = deque(maxlen=self.sequence_length)
            if not self.use_global_normalizer:
                self.normalizers[device_id] = SimpleNormalizer(FEATURE_DIM)
        
        # Extract features in YOUR project's format
        features = self.extract_features(data)
        
        # Update normalizer if using online
        if not self.use_global_normalizer:
            self.normalizers[device_id].update(features)
        
        # Add to buffer
        self.devices[device_id].append(features)
        
        return len(self.devices[device_id]) >= self.sequence_length
    
    def extract_features(self, data):
        """
        Extract 8 features matching YOUR training data format:
        0. Packet Rate (packets/sec)
        1. Byte Rate (KB/sec)
        2. Average Packet Size (bytes)
        3. Packet Size Std Dev (bytes)
        4. SYN Ratio (0-1)
        5. Unique Source IPs
        6. Unique Destination Ports
        7. Protocol Entropy (bits)
        """
        features = np.array([
            data.get('packet_rate', 0),
            data.get('byte_rate', 0),
            data.get('avg_packet_size', 0),
            data.get('packet_size_std', 0),  # ESP32 sends 0 for now
            data.get('syn_ratio', 0),
            data.get('unique_src_ips', 0),
            data.get('unique_dst_ports', 0),
            self.calculate_protocol_entropy(data)
        ], dtype=np.float32)
        
        return features
    
    def calculate_protocol_entropy(self, data):
        """Calculate protocol distribution entropy"""
        tcp = data.get('tcp_count', 0)
        udp = data.get('udp_count', 0)
        icmp = data.get('icmp_count', 0)
        total = tcp + udp + icmp
        
        if total == 0:
            return 0
        
        probs = np.array([tcp, udp, icmp]) / total
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        return entropy
    
    def get_sequence(self, device_id):
        """Get normalized sequence for YOUR model"""
        if device_id not in self.devices:
            return None
        
        if len(self.devices[device_id]) < self.sequence_length:
            return None
        
        # Get sequence
        sequence = np.array(list(self.devices[device_id]))
        
        # Normalize using YOUR pre-computed normalizer statistics
        if self.use_global_normalizer:
            # Use pre-computed mean and variance from training
            std = np.sqrt(self.running_var + 1e-8)
            normalized = (sequence - self.running_mean) / std
        else:
            normalizer = self.normalizers[device_id]
            normalized = np.array([normalizer.normalize(f) for f in sequence])
        
        return normalized
    
    def can_alert(self, device_id, cooldown=30):
        """Check if can send alert"""
        if device_id not in self.last_alert_time:
            return True
        return time.time() - self.last_alert_time[device_id] >= cooldown
    
    def mark_alerted(self, device_id):
        """Mark alert sent"""
        self.last_alert_time[device_id] = time.time()

# ============================================================================
# INTEGRATED DETECTION SERVER
# ============================================================================

class IntegratedDDoSServer:
    """Server using YOUR trained S5 model with ESP32 data"""
    
    def __init__(self):
        self.server_socket = None
        self.running = False
        self.processor = ESP32DataProcessor(
            sequence_length=SEQUENCE_LENGTH,
            normalizer_path=NORMALIZER_PATH
        )
        
        # Load YOUR trained model
        print("\n" + "="*70)
        print("Loading YOUR Trained S5 DDoS Detection Model")
        print("="*70)
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        
        # Initialize YOUR model architecture
        try:
            self.model = DDoSDetector(
                input_dim=8,
                state_dim=32,
                hidden_dim=64,
                num_layers=2,
                dropout=0.2,
                use_attention=True
            )
            print("[SUCCESS] Initialized YOUR model architecture")
        except Exception as e:
            print(f"[ERROR] Could not initialize model: {e}")
            print("Check ssm_model.py DDoSDetector class")
            sys.exit(1)
        
        # Load YOUR trained weights
        if MODEL_PATH.exists():
            try:
                # Add weights_only=False for compatibility
                checkpoint = torch.load(MODEL_PATH, map_location=self.device, weights_only=False)   
                
                # Handle different checkpoint formats
                if 'model_state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                    print(f"[SUCCESS] Loaded trained weights from checkpoint")
                    if 'epoch' in checkpoint:
                        print(f"  Epoch: {checkpoint['epoch']}")
                    if 'val_accuracy' in checkpoint:
                        print(f"  Validation Accuracy: {checkpoint['val_accuracy']:.4f}")
                elif 'state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['state_dict'])
                    print(f"[SUCCESS] Loaded trained weights")
                else:
                    self.model.load_state_dict(checkpoint)
                    print(f"[SUCCESS] Loaded trained weights")
                
                print(f"Model loaded from: {MODEL_PATH}")
            except Exception as e:
                print(f"[ERROR] Could not load trained weights: {e}")
                print("[WARNING] Using randomly initialized weights!")
                print("To use trained model, ensure checkpoints/best_model.pth exists")
        else:
            print(f"[WARNING] No trained model found at {MODEL_PATH}")
            print("[WARNING] Using randomly initialized weights!")
            print("Train your model first using train_model.py")
        
        self.model.to(self.device)
        self.model.eval()
        
        # Statistics
        self.total_received = 0
        self.total_detections = 0
        self.total_attacks = 0
        
        print("="*70 + "\n")
    
    def start(self):
        """Start the server"""
        print("="*70)
        print("ESP32 + Trained S5 Model - Integrated Detection Server")
        print("="*70)
        print(f"Server: {SERVER_IP}:{SERVER_PORT}")
        print(f"Model: YOUR trained S5 model")
        print(f"Sequence Length: {SEQUENCE_LENGTH}")
        print(f"Detection Threshold: {DETECTION_THRESHOLD}")
        print(f"Device: {self.device}")
        print("="*70 + "\n")
        
        # Create UDP socket (allow reuse to avoid TIME_WAIT conflicts)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass  # not all platforms support this
        self.server_socket.bind((SERVER_IP, SERVER_PORT))
        self.server_socket.settimeout(1.0)
        
        self.running = True
        
        # Statistics thread
        stats_thread = threading.Thread(target=self.print_statistics, daemon=True)
        stats_thread.start()
        
        print("[READY] Waiting for ESP32 data...\n")
        
        try:
            while self.running:
                try:
                    data, addr = self.server_socket.recvfrom(BUFFER_SIZE)
                    self.handle_data(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ERROR] {e}")
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down...")
        finally:
            self.stop()
    
    def handle_data(self, data, addr):
        """Handle ESP32 data"""
        try:
            json_data = json.loads(data.decode('utf-8'))
            device_id = json_data.get('device_id', f'ESP32_{addr[0]}')
            
            self.total_received += 1
            
            print(f"\n[RECV] {device_id} ({addr[0]})")
            print(f"  Packets: {json_data.get('packet_rate', 0):.2f} pkt/s")
            print(f"  Bytes: {json_data.get('byte_rate', 0):.2f} KB/s")
            print(f"  SYN: {json_data.get('syn_ratio', 0):.2%}")
            
            # Add to processor
            ready = self.processor.add_data(device_id, json_data)

            # Write latest received data to JSON so dashboard can show live updates
            try:
                self.write_latest_detection(device_id, 0.0, json_data)
            except Exception as e:
                print(f"[WARNING] Could not write live detection JSON: {e}")
            
            # Run YOUR model when ready
            if ready:
                self.run_detection(device_id, json_data)
        
        except Exception as e:
            print(f"[ERROR] {e}")
    
    def run_detection(self, device_id, latest_data):
        """Run YOUR trained S5 model"""
        self.total_detections += 1
        
        # Get normalized sequence
        sequence = self.processor.get_sequence(device_id)
        if sequence is None:
            return
        
        attack_prob = 0.0
        confidence = 0.0
        
        try:
            # Prepare input for YOUR model
            x = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)  # (1, 60, 8)
            
            # Run YOUR trained model
            with torch.no_grad():
                output = self.model(x)

            # DEBUG: Print raw output
            print(f"[DEBUG] Model output type: {type(output)}")
            if isinstance(output, dict):
                print(f"[DEBUG] Dict keys: {output.keys()}")
                for k, v in output.items():
                    if isinstance(v, torch.Tensor):
                        print(f"[DEBUG]   {k}: shape={v.shape}, values={v}")
                    else:
                        print(f"[DEBUG]   {k}: {v}")

            # Extract prediction from output
            if isinstance(output, dict):
                if 'final_prediction' in output:
                    # Direct prediction from model
                    attack_prob = float(output['final_prediction'].item())
                    confidence = float(output.get('confidence', output['final_prediction']).item())
                    print(f"[DEBUG] Using final_prediction: {attack_prob}")
                elif 'logits' in output:
                    logits = output['logits']
                    probs = torch.softmax(logits, dim=-1)
                    attack_prob = probs[0, -1].item()  # Last class = attack
                    confidence = probs.max().item()
                    print(f"[DEBUG] Using logits: {attack_prob}")
                else:
                    # Try to find any tensor in the dict
                    for key, value in output.items():
                        if isinstance(value, torch.Tensor) and value.numel() > 0:
                            if value.dim() == 2:
                                probs = torch.softmax(value, dim=-1)
                                attack_prob = probs[0, -1].item()
                            else:
                                attack_prob = float(value[0].item()) if value.numel() > 1 else float(value.item())
                            confidence = abs(attack_prob)
                            print(f"[DEBUG] Using {key}: {attack_prob}")
                            break
            elif isinstance(output, torch.Tensor):
                # Raw tensor output
                if output.dim() == 2:  # (batch, classes)
                    probs = torch.softmax(output, dim=-1)
                    attack_prob = probs[0, 1].item() if probs.shape[-1] > 1 else probs[0, 0].item()
                    confidence = probs.max().item()
                else:
                    attack_prob = float(output[0].item()) if output.numel() > 1 else float(output.item())
                    confidence = abs(attack_prob)
                print(f"[DEBUG] Raw tensor attack_prob: {attack_prob}")

            is_attack = attack_prob >= DETECTION_THRESHOLD
            print(f"[DEBUG] Final attack_prob: {attack_prob}, is_attack: {is_attack}")
        
        except Exception as e:
            print(f"[ERROR] Detection failed: {e}")
            import traceback
            traceback.print_exc()
            attack_prob = 0.0
            confidence = 0.0
            is_attack = False
        
        # Display results
        print(f"\n{'='*70}")
        print(f"[DETECTION] {device_id}")
        print(f"{'='*70}")
        print(f"Attack Probability: {attack_prob:.4f} ({attack_prob*100:.2f}%)")
        print(f"Confidence: {confidence:.4f}")
        print(f"Classification: {'🚨 DDoS ATTACK DETECTED' if is_attack else '✓ Normal Traffic'}")
        
        if is_attack:
            self.total_attacks += 1
            if self.processor.can_alert(device_id):
                self.send_alert(device_id, attack_prob, latest_data)
                self.processor.mark_alerted(device_id)
        
        # Always write latest detection JSON for the dashboard (attack or normal)
        try:
            self.write_latest_detection(device_id, attack_prob, latest_data)
        except Exception as e:
            print(f"[WARNING] Failed to write latest detection JSON: {e}")

        print(f"{'='*70}\n")
    
    def send_alert(self, device_id, attack_prob, data):
        """Send DDoS alert"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{'🔴'*35}")
        print(f"     ⚠️  DDoS ATTACK DETECTED  ⚠️")
        print(f"{'🔴'*35}")
        print(f"Time: {timestamp}")
        print(f"Device: {device_id}")
        print(f"Attack Probability: {attack_prob:.2%}")
        print(f"Packet Rate: {data.get('packet_rate', 0):.2f} pkt/s")
        print(f"Byte Rate: {data.get('byte_rate', 0):.2f} KB/s")
        print(f"SYN Ratio: {data.get('syn_ratio', 0):.2%}")
        print(f"Unique IPs: {data.get('unique_src_ips', 0)}")
        print(f"{'🔴'*35}\n")
        
        # Log to file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "ddos_alerts.log"
        
        with open(log_file, 'a') as f:
            f.write(f"{timestamp} | {device_id} | Prob: {attack_prob:.4f} | ")
            f.write(f"Rate: {data.get('packet_rate', 0):.2f} pkt/s | ")
            f.write(f"SYN: {data.get('syn_ratio', 0):.4f}\n")
        
        # Write latest detection to JSON for dashboard
        self.write_latest_detection(device_id, attack_prob, data)
    
    def write_latest_detection(self, device_id, attack_prob, data):
        """Write latest detection result to JSON for dashboard"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        detection_file = log_dir / "latest_detection.json"
        
        detection_json = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "is_attack": attack_prob >= DETECTION_THRESHOLD,
            "attack_probability": float(attack_prob),
            "confidence": float(attack_prob),
            "packet_rate": float(data.get('packet_rate', 0)),
            "byte_rate": float(data.get('byte_rate', 0)),
            "syn_ratio": float(data.get('syn_ratio', 0)),
            "unique_src_ips": int(data.get('unique_src_ips', 0)),
            "tcp_count": int(data.get('tcp_count', 0)),
            "udp_count": int(data.get('udp_count', 0))
        }
        
        try:
            with open(detection_file, 'w') as f:
                json.dump(detection_json, f)
        except Exception as e:
            print(f"[WARNING] Could not write detection JSON: {e}")
    
    def print_statistics(self):
        """Print periodic statistics"""
        while self.running:
            time.sleep(30)
            print(f"\n{'─'*70}")
            print(f"[STATS] Received: {self.total_received} | "
                  f"Detections: {self.total_detections} | "
                  f"Attacks: {self.total_attacks}")
            print(f"{'─'*70}\n")
    
    def stop(self):
        """Stop server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[INFO] Server stopped")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integrated ESP32 + Trained S5 Model Detection Server"
    )
    parser.add_argument('--model', type=str, 
                       default=str(MODEL_PATH),
                       help='Path to YOUR trained model')
    parser.add_argument('--normalizer', type=str,
                       default=str(NORMALIZER_PATH),
                       help='Path to YOUR saved normalizer')
    parser.add_argument('--port', type=int, default=5000,
                       help='Server port')
    
    args = parser.parse_args()
    
    # Update paths
    MODEL_PATH = Path(args.model)
    NORMALIZER_PATH = Path(args.normalizer)
    SERVER_PORT = args.port
    
    # Start integrated server
    server = IntegratedDDoSServer()
    server.start()
