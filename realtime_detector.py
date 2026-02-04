"""
Real-time Inference Engine for DDoS Detection

This module provides real-time detection capabilities for edge deployment,
including packet capture, feature extraction, and model inference.
"""

import torch
import numpy as np
from typing import Dict, List, Optional, Callable
from collections import deque
import time
import threading
import queue
from dataclasses import dataclass, asdict
import json


@dataclass
class DetectionResult:
    """Container for detection results."""
    timestamp: float
    is_attack: bool
    attack_probability: float
    confidence: float
    attack_type: str
    attack_type_probabilities: Dict[str, float]
    source_ips: List[str]
    packet_count: int
    byte_rate: float
    packet_rate: float
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class RealTimeDetector:
    """Real-time DDoS detection engine."""
    
    ATTACK_TYPES = ['Normal', 'SYN Flood', 'UDP Flood', 'HTTP Flood', 'DNS Amplification']
    
    def __init__(
        self,
        model: torch.nn.Module,
        normalizer,
        sequence_length: int = 60,
        window_size: float = 1.0,
        detection_threshold: float = 0.5,
        device: str = 'cpu'
    ):
        """
        Initialize real-time detector.
        
        Args:
            model: Trained DDoS detection model
            normalizer: Feature normalizer
            sequence_length: Length of input sequence
            window_size: Time window for feature extraction (seconds)
            detection_threshold: Threshold for attack detection
            device: Device for inference
        """
        self.model = model.to(device)
        self.model.eval()
        self.normalizer = normalizer
        self.sequence_length = sequence_length
        self.window_size = window_size
        self.detection_threshold = detection_threshold
        self.device = device
        
        # Feature buffer (stores recent features)
        self.feature_buffer = deque(maxlen=sequence_length)
        
        # Traffic window for current interval
        from feature_extraction import TrafficWindow
        self.traffic_window = TrafficWindow(window_size=window_size)
        
        # Detection history
        self.detection_history = deque(maxlen=1000)
        
        # Statistics
        self.total_detections = 0
        self.total_attacks = 0
        self.start_time = time.time()
        
        # Thread-safe queue for async processing
        self.packet_queue = queue.Queue(maxsize=10000)
        self.result_queue = queue.Queue(maxsize=100)
        
        # Control flags
        self.running = False
        self.processing_thread = None
    
    def process_packet(self, packet_info: Dict):
        """
        Process a single packet.
        
        Args:
            packet_info: Dictionary with packet information
        """
        if self.running:
            try:
                self.packet_queue.put_nowait(packet_info)
            except queue.Full:
                pass  # Drop packet if queue is full
        else:
            self._process_packet_sync(packet_info)
    
    def _process_packet_sync(self, packet_info: Dict):
        """Synchronous packet processing."""
        # Add packet to window
        self.traffic_window.add_packet(packet_info)
    
    def extract_and_detect(self) -> Optional[DetectionResult]:
        """
        Extract features from current window and perform detection.
        
        Returns:
            Detection result or None if not enough data
        """
        # Extract features from current window
        features = self.traffic_window.extract_features()
        feature_array = features.to_array()
        
        # Normalize features
        normalized_features = self.normalizer.normalize(feature_array)
        
        # Add to buffer
        self.feature_buffer.append(normalized_features)
        
        # Check if we have enough data
        if len(self.feature_buffer) < self.sequence_length:
            return None
        
        # Prepare input sequence
        sequence = np.array(list(self.feature_buffer))
        sequence = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)  # (1, seq_len, feature_dim)
        
        # Perform inference
        with torch.no_grad():
            predictions = self.model.predict(sequence, threshold=self.detection_threshold)
        
        # Extract results - handle both 1D and batch tensors
        is_attack_tensor = predictions['is_attack']
        if is_attack_tensor.dim() > 0:
            is_attack = bool(is_attack_tensor[0].item())
        else:
            is_attack = bool(is_attack_tensor.item())
            
        attack_prob_tensor = predictions['attack_probability']
        if attack_prob_tensor.dim() > 0:
            attack_prob = float(attack_prob_tensor[0].item())
        else:
            attack_prob = float(attack_prob_tensor.item())
            
        confidence_tensor = predictions['confidence']
        if confidence_tensor.dim() > 0:
            confidence = float(confidence_tensor[0].item())
        else:
            confidence = float(confidence_tensor.item())
            
        attack_type_tensor = predictions['attack_type']
        if attack_type_tensor.dim() > 0:
            attack_type_idx = int(attack_type_tensor[0].item())
        else:
            attack_type_idx = int(attack_type_tensor.item())
            
        attack_type = self.ATTACK_TYPES[attack_type_idx]
        
        attack_type_probs_tensor = predictions['attack_type_probs']
        if attack_type_probs_tensor.dim() > 1:
            probs = attack_type_probs_tensor[0]
        else:
            probs = attack_type_probs_tensor
            
        attack_type_probs = {
            self.ATTACK_TYPES[i]: float(probs[i].item())
            for i in range(len(self.ATTACK_TYPES))
        }
        
        # Collect source IPs
        source_ips = list(self.traffic_window.src_ips)[:10]  # Top 10
        
        # Create result
        result = DetectionResult(
            timestamp=time.time(),
            is_attack=is_attack,
            attack_probability=attack_prob,
            confidence=confidence,
            attack_type=attack_type,
            attack_type_probabilities=attack_type_probs,
            source_ips=source_ips,
            packet_count=len(self.traffic_window.packets),
            byte_rate=features.byte_rate,
            packet_rate=features.packet_rate
        )
        
        # Update statistics
        self.total_detections += 1
        if is_attack:
            self.total_attacks += 1
        
        # Add to history
        self.detection_history.append(result)
        
        return result
    
    def start_async_processing(self):
        """Start asynchronous packet processing."""
        if self.running:
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
    
    def stop_async_processing(self):
        """Stop asynchronous packet processing."""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
    
    def _processing_loop(self):
        """Main processing loop for async mode."""
        last_detection_time = time.time()
        
        while self.running:
            try:
                # Process packets from queue
                while not self.packet_queue.empty():
                    packet_info = self.packet_queue.get_nowait()
                    self._process_packet_sync(packet_info)
                
                # Perform detection at regular intervals
                current_time = time.time()
                if current_time - last_detection_time >= self.window_size:
                    result = self.extract_and_detect()
                    if result:
                        try:
                            self.result_queue.put_nowait(result)
                        except queue.Full:
                            pass  # Drop result if queue is full
                    last_detection_time = current_time
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
            
            except Exception as e:
                print(f"Error in processing loop: {e}")
    
    def get_latest_result(self, timeout: float = 0.1) -> Optional[DetectionResult]:
        """Get latest detection result from async processing."""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_statistics(self) -> Dict:
        """Get detector statistics."""
        uptime = time.time() - self.start_time
        attack_rate = self.total_attacks / max(1, self.total_detections)
        
        return {
            'total_detections': self.total_detections,
            'total_attacks': self.total_attacks,
            'attack_rate': attack_rate,
            'uptime_seconds': uptime,
            'buffer_size': len(self.feature_buffer),
            'detection_history_size': len(self.detection_history),
            'packets_in_queue': self.packet_queue.qsize(),
            'results_in_queue': self.result_queue.qsize()
        }
    
    def reset(self):
        """Reset detector state."""
        self.feature_buffer.clear()
        self.traffic_window.reset()
        self.detection_history.clear()
        self.total_detections = 0
        self.total_attacks = 0
        self.start_time = time.time()


class LiveCaptureDetector:
    """Live network capture and detection."""
    
    def __init__(
        self,
        detector: RealTimeDetector,
        interface: str = None,
        filter_expr: str = None
    ):
        """
        Initialize live capture detector.
        
        Args:
            detector: Real-time detector instance
            interface: Network interface to capture from
            filter_expr: BPF filter expression
        """
        self.detector = detector
        self.interface = interface
        self.filter_expr = filter_expr
        
        self.capture_thread = None
        self.capturing = False
    
    def start_capture(self, callback: Optional[Callable] = None):
        """
        Start live packet capture.
        
        Args:
            callback: Optional callback function for detection results
        """
        try:
            from scapy.all import sniff, IP, TCP, UDP
        except ImportError:
            raise ImportError("scapy is required for live capture. Install with: pip install scapy")
        
        self.capturing = True
        self.detector.start_async_processing()
        
        def packet_handler(pkt):
            if not self.capturing:
                return
            
            if IP in pkt:
                packet_info = {
                    'timestamp': time.time(),
                    'size': len(pkt),
                    'src_ip': pkt[IP].src,
                    'dst_port': pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0),
                    'protocol': 'TCP' if TCP in pkt else ('UDP' if UDP in pkt else 'OTHER'),
                    'is_syn': TCP in pkt and pkt[TCP].flags & 0x02
                }
                
                # Log live captured packet
                try:
                    import os, json
                    os.makedirs('logs', exist_ok=True)
                    with open(os.path.join('logs', 'packets.log'), 'a') as _lf:
                        _lf.write(json.dumps({'source': 'live', 'packet': packet_info, 'logged_at': time.time()}) + "\n")
                except Exception:
                    pass

                self.detector.process_packet(packet_info)
                
                # Check for detection results
                if callback:
                    result = self.detector.get_latest_result(timeout=0)
                    if result:
                        callback(result)
        
        # Start capture in separate thread
        self.capture_thread = threading.Thread(
            target=lambda: sniff(
                iface=self.interface,
                filter=self.filter_expr,
                prn=packet_handler,
                store=False,
                stop_filter=lambda x: not self.capturing
            ),
            daemon=True
        )
        self.capture_thread.start()
    
    def stop_capture(self):
        """Stop live packet capture."""
        self.capturing = False
        self.detector.stop_async_processing()
        if self.capture_thread:
            self.capture_thread.join(timeout=5.0)


class ModelOptimizer:
    """Optimize model for edge deployment."""
    
    @staticmethod
    def quantize_model(model: torch.nn.Module) -> torch.nn.Module:
        """Apply dynamic quantization to model."""
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )
        return quantized_model
    
    @staticmethod
    def export_to_onnx(
        model: torch.nn.Module,
        filepath: str,
        input_shape: tuple = (1, 60, 8)
    ):
        """
        Export model to ONNX format.
        
        Args:
            model: PyTorch model
            filepath: Output file path
            input_shape: Input tensor shape (batch, seq_len, features)
        """
        model.eval()
        dummy_input = torch.randn(*input_shape)
        
        torch.onnx.export(
            model,
            dummy_input,
            filepath,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
    
    @staticmethod
    def measure_inference_time(
        model: torch.nn.Module,
        input_shape: tuple = (1, 60, 8),
        num_runs: int = 100,
        warmup_runs: int = 10
    ) -> Dict:
        """
        Measure model inference time.
        
        Returns:
            Dictionary with timing statistics
        """
        model.eval()
        device = next(model.parameters()).device
        
        # Warmup
        dummy_input = torch.randn(*input_shape).to(device)
        with torch.no_grad():
            for _ in range(warmup_runs):
                _ = model(dummy_input)
        
        # Measure
        times = []
        with torch.no_grad():
            for _ in range(num_runs):
                start = time.time()
                _ = model(dummy_input)
                times.append(time.time() - start)
        
        return {
            'mean_ms': np.mean(times) * 1000,
            'std_ms': np.std(times) * 1000,
            'min_ms': np.min(times) * 1000,
            'max_ms': np.max(times) * 1000,
            'median_ms': np.median(times) * 1000
        }
