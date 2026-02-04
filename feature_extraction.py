"""
Data Processing and Feature Extraction for DDoS Detection

This module handles network traffic data processing, feature extraction,
and preprocessing for the SSM model.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import time


@dataclass
class TrafficFeatures:
    """Container for extracted traffic features."""
    packet_rate: float
    byte_rate: float
    avg_packet_size: float
    packet_size_variance: float
    syn_ratio: float
    unique_src_ips: int
    unique_dst_ports: int
    protocol_entropy: float
    timestamp: float = None
    
    def to_array(self) -> np.ndarray:
        """Convert features to numpy array."""
        return np.array([
            self.packet_rate,
            self.byte_rate,
            self.avg_packet_size,
            self.packet_size_variance,
            self.syn_ratio,
            self.unique_src_ips,
            self.unique_dst_ports,
            self.protocol_entropy
        ], dtype=np.float32)
    
    @classmethod
    def get_feature_names(cls) -> List[str]:
        """Get list of feature names."""
        return [
            'packet_rate',
            'byte_rate',
            'avg_packet_size',
            'packet_size_variance',
            'syn_ratio',
            'unique_src_ips',
            'unique_dst_ports',
            'protocol_entropy'
        ]


class TrafficWindow:
    """Sliding window for traffic data collection."""
    
    def __init__(self, window_size: float = 1.0, max_packets: int = 10000):
        """
        Initialize traffic window.
        
        Args:
            window_size: Window size in seconds
            max_packets: Maximum number of packets to store
        """
        self.window_size = window_size
        self.max_packets = max_packets
        
        self.packets = deque(maxlen=max_packets)
        self.src_ips = set()
        self.dst_ports = set()
        self.protocols = []
        
        self.total_bytes = 0
        self.syn_count = 0
        self.total_count = 0
        
        self.start_time = None
        self.last_update = None
    
    def add_packet(self, packet_info: Dict):
        """
        Add a packet to the window.
        
        Args:
            packet_info: Dictionary with packet information:
                - timestamp: Packet timestamp
                - size: Packet size in bytes
                - src_ip: Source IP address
                - dst_port: Destination port
                - protocol: Protocol type
                - is_syn: Whether packet is SYN
        """
        timestamp = packet_info.get('timestamp', time.time())
        
        if self.start_time is None:
            self.start_time = timestamp
        
        # Remove old packets outside window
        self._remove_old_packets(timestamp)
        
        # Add new packet
        self.packets.append(packet_info)
        self.total_bytes += packet_info['size']
        self.total_count += 1
        
        if packet_info.get('is_syn', False):
            self.syn_count += 1
        
        self.src_ips.add(packet_info.get('src_ip', 'unknown'))
        self.dst_ports.add(packet_info.get('dst_port', 0))
        self.protocols.append(packet_info.get('protocol', 'TCP'))
        
        self.last_update = timestamp
    
    def _remove_old_packets(self, current_time: float):
        """Remove packets older than window size."""
        cutoff_time = current_time - self.window_size
        
        while self.packets and self.packets[0]['timestamp'] < cutoff_time:
            old_packet = self.packets.popleft()
            self.total_bytes -= old_packet['size']
            self.total_count -= 1
            if old_packet.get('is_syn', False):
                self.syn_count -= 1
        
        # Rebuild sets (simplified approach)
        self.src_ips = {p.get('src_ip', 'unknown') for p in self.packets}
        self.dst_ports = {p.get('dst_port', 0) for p in self.packets}
        self.protocols = [p.get('protocol', 'TCP') for p in self.packets]
    
    def extract_features(self) -> TrafficFeatures:
        """Extract traffic features from current window."""
        if not self.packets or self.last_update is None:
            return self._get_zero_features()
        
        # Time duration
        duration = max(self.window_size, self.last_update - self.start_time)
        
        # Packet and byte rates
        packet_rate = len(self.packets) / duration
        byte_rate = self.total_bytes / duration
        
        # Packet size statistics
        packet_sizes = [p['size'] for p in self.packets]
        avg_packet_size = np.mean(packet_sizes) if packet_sizes else 0
        packet_size_variance = np.var(packet_sizes) if len(packet_sizes) > 1 else 0
        
        # SYN ratio
        syn_ratio = self.syn_count / max(1, len(self.packets))
        
        # Unique IPs and ports
        unique_src_ips = len(self.src_ips)
        unique_dst_ports = len(self.dst_ports)
        
        # Protocol entropy
        protocol_entropy = self._calculate_entropy(self.protocols)
        
        return TrafficFeatures(
            packet_rate=packet_rate,
            byte_rate=byte_rate,
            avg_packet_size=avg_packet_size,
            packet_size_variance=packet_size_variance,
            syn_ratio=syn_ratio,
            unique_src_ips=unique_src_ips,
            unique_dst_ports=unique_dst_ports,
            protocol_entropy=protocol_entropy,
            timestamp=self.last_update
        )
    
    def _get_zero_features(self) -> TrafficFeatures:
        """Return zero features when no data available."""
        return TrafficFeatures(
            packet_rate=0.0,
            byte_rate=0.0,
            avg_packet_size=0.0,
            packet_size_variance=0.0,
            syn_ratio=0.0,
            unique_src_ips=0,
            unique_dst_ports=0,
            protocol_entropy=0.0,
            timestamp=time.time()
        )
    
    @staticmethod
    def _calculate_entropy(items: List) -> float:
        """Calculate Shannon entropy of items."""
        if not items:
            return 0.0
        
        # Count frequencies
        from collections import Counter
        counts = Counter(items)
        total = len(items)
        
        # Calculate entropy
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * np.log2(p)
        
        return entropy
    
    def reset(self):
        """Reset the window."""
        self.packets.clear()
        self.src_ips.clear()
        self.dst_ports.clear()
        self.protocols.clear()
        self.total_bytes = 0
        self.syn_count = 0
        self.total_count = 0
        self.start_time = None
        self.last_update = None


class FeatureNormalizer:
    """Online feature normalization using running statistics."""
    
    def __init__(self, feature_dim: int, momentum: float = 0.99):
        """
        Initialize normalizer.
        
        Args:
            feature_dim: Number of features
            momentum: Momentum for running statistics
        """
        self.feature_dim = feature_dim
        self.momentum = momentum
        
        self.running_mean = np.zeros(feature_dim, dtype=np.float32)
        self.running_var = np.ones(feature_dim, dtype=np.float32)
        self.count = 0
    
    def update(self, features: np.ndarray):
        """
        Update running statistics.
        
        Args:
            features: Feature array of shape (feature_dim,) or (batch_size, feature_dim)
        """
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        batch_mean = np.mean(features, axis=0)
        batch_var = np.var(features, axis=0)
        
        if self.count == 0:
            self.running_mean = batch_mean
            self.running_var = batch_var
        else:
            self.running_mean = self.momentum * self.running_mean + (1 - self.momentum) * batch_mean
            self.running_var = self.momentum * self.running_var + (1 - self.momentum) * batch_var
        
        self.count += features.shape[0]
    
    def normalize(self, features: np.ndarray) -> np.ndarray:
        """
        Normalize features using running statistics.
        
        Args:
            features: Feature array
        
        Returns:
            Normalized features
        """
        return (features - self.running_mean) / (np.sqrt(self.running_var) + 1e-8)
    
    def save(self, filepath: str):
        """Save normalizer statistics."""
        np.savez(
            filepath,
            running_mean=self.running_mean,
            running_var=self.running_var,
            count=self.count
        )
    
    def load(self, filepath: str):
        """Load normalizer statistics."""
        data = np.load(filepath)
        self.running_mean = data['running_mean']
        self.running_var = data['running_var']
        self.count = int(data['count'])


class TimeSeriesDataset:
    """Dataset for time series traffic data."""
    
    def __init__(
        self,
        sequence_length: int = 60,
        stride: int = 1,
        normalizer: Optional[FeatureNormalizer] = None
    ):
        """
        Initialize dataset.
        
        Args:
            sequence_length: Number of time steps in each sequence
            stride: Stride between sequences
            normalizer: Feature normalizer
        """
        self.sequence_length = sequence_length
        self.stride = stride
        self.normalizer = normalizer
        
        self.sequences = []
        self.labels = []
        self.metadata = []
    
    def add_sequence(self, features: np.ndarray, label: int, metadata: Optional[Dict] = None):
        """
        Add a sequence to the dataset.
        
        Args:
            features: Feature array of shape (seq_len, feature_dim)
            label: Label (0 for normal, 1 for attack)
            metadata: Optional metadata dictionary
        """
        if self.normalizer:
            features = self.normalizer.normalize(features)
        
        self.sequences.append(features)
        self.labels.append(label)
        self.metadata.append(metadata or {})
    
    def get_batch(self, indices: List[int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get a batch of sequences.
        
        Args:
            indices: List of sequence indices
        
        Returns:
            features: (batch_size, seq_len, feature_dim)
            labels: (batch_size,)
        """
        features = np.stack([self.sequences[i] for i in indices])
        labels = np.array([self.labels[i] for i in indices])
        return features, labels
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[np.ndarray, int]:
        return self.sequences[idx], self.labels[idx]


def load_pcap_features(pcap_file: str, window_size: float = 1.0) -> pd.DataFrame:
    """
    Load and extract features from PCAP file.
    
    Args:
        pcap_file: Path to PCAP file
        window_size: Window size in seconds
    
    Returns:
        DataFrame with extracted features
    """
    try:
        from scapy.all import rdpcap, IP, TCP, UDP
    except ImportError:
        raise ImportError("scapy is required for PCAP processing. Install with: pip install scapy")
    
    packets = rdpcap(pcap_file)
    window = TrafficWindow(window_size=window_size)
    features_list = []
    
    for pkt in packets:
        if IP in pkt:
            packet_info = {
                'timestamp': float(pkt.time),
                'size': len(pkt),
                'src_ip': pkt[IP].src,
                'dst_port': pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0),
                'protocol': 'TCP' if TCP in pkt else ('UDP' if UDP in pkt else 'OTHER'),
                'is_syn': TCP in pkt and pkt[TCP].flags & 0x02
            }
            
            window.add_packet(packet_info)
            
            # Extract features at regular intervals
            features = window.extract_features()
            features_list.append(features.to_array())
    
    # Convert to DataFrame
    df = pd.DataFrame(features_list, columns=TrafficFeatures.get_feature_names())
    return df
