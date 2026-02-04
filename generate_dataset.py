"""
Synthetic DDoS Traffic Generator

This module generates synthetic network traffic data for training and testing
the DDoS detection system, including various attack patterns and normal traffic.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
import random


@dataclass
class TrafficPattern:
    """Traffic pattern configuration."""
    packet_rate_mean: float
    packet_rate_std: float
    byte_rate_mean: float
    byte_rate_std: float
    avg_packet_size: float
    packet_size_variance: float
    syn_ratio: float
    unique_src_ips_mean: int
    unique_dst_ports_mean: int
    protocol_entropy: float


class TrafficGenerator:
    """Generate synthetic network traffic patterns."""
    
    # Define traffic patterns for different scenarios
    PATTERNS = {
        'normal': TrafficPattern(
            packet_rate_mean=100,
            packet_rate_std=20,
            byte_rate_mean=50000,
            byte_rate_std=10000,
            avg_packet_size=500,
            packet_size_variance=10000,
            syn_ratio=0.1,
            unique_src_ips_mean=50,
            unique_dst_ports_mean=20,
            protocol_entropy=1.5
        ),
        'syn_flood': TrafficPattern(
            packet_rate_mean=5000,
            packet_rate_std=1000,
            byte_rate_mean=250000,
            byte_rate_std=50000,
            avg_packet_size=50,
            packet_size_variance=100,
            syn_ratio=0.95,
            unique_src_ips_mean=500,
            unique_dst_ports_mean=5,
            protocol_entropy=0.3
        ),
        'udp_flood': TrafficPattern(
            packet_rate_mean=8000,
            packet_rate_std=1500,
            byte_rate_mean=8000000,
            byte_rate_std=1000000,
            avg_packet_size=1000,
            packet_size_variance=50000,
            syn_ratio=0.0,
            unique_src_ips_mean=300,
            unique_dst_ports_mean=100,
            protocol_entropy=0.5
        ),
        'http_flood': TrafficPattern(
            packet_rate_mean=3000,
            packet_rate_std=500,
            byte_rate_mean=3000000,
            byte_rate_std=500000,
            avg_packet_size=1000,
            packet_size_variance=100000,
            syn_ratio=0.15,
            unique_src_ips_mean=200,
            unique_dst_ports_mean=3,
            protocol_entropy=0.8
        ),
        'dns_amplification': TrafficPattern(
            packet_rate_mean=10000,
            packet_rate_std=2000,
            byte_rate_mean=50000000,
            byte_rate_std=10000000,
            avg_packet_size=5000,
            packet_size_variance=1000000,
            syn_ratio=0.0,
            unique_src_ips_mean=50,
            unique_dst_ports_mean=1,
            protocol_entropy=0.1
        )
    }
    
    @staticmethod
    def generate_sample(pattern: TrafficPattern, add_noise: bool = True) -> np.ndarray:
        """
        Generate a single traffic sample.
        
        Args:
            pattern: Traffic pattern configuration
            add_noise: Whether to add random noise
        
        Returns:
            Feature vector of shape (8,)
        """
        noise_factor = 0.1 if add_noise else 0.0
        
        # Generate features with optional noise
        packet_rate = max(0, np.random.normal(
            pattern.packet_rate_mean,
            pattern.packet_rate_std * (1 + noise_factor)
        ))
        
        byte_rate = max(0, np.random.normal(
            pattern.byte_rate_mean,
            pattern.byte_rate_std * (1 + noise_factor)
        ))
        
        avg_packet_size = max(0, np.random.normal(
            pattern.avg_packet_size,
            np.sqrt(pattern.packet_size_variance) * (1 + noise_factor)
        ))
        
        packet_size_variance = max(0, np.random.normal(
            pattern.packet_size_variance,
            pattern.packet_size_variance * 0.3 * (1 + noise_factor)
        ))
        
        syn_ratio = np.clip(np.random.normal(
            pattern.syn_ratio,
            0.05 * (1 + noise_factor)
        ), 0, 1)
        
        unique_src_ips = max(1, int(np.random.normal(
            pattern.unique_src_ips_mean,
            pattern.unique_src_ips_mean * 0.3 * (1 + noise_factor)
        )))
        
        unique_dst_ports = max(1, int(np.random.normal(
            pattern.unique_dst_ports_mean,
            pattern.unique_dst_ports_mean * 0.3 * (1 + noise_factor)
        )))
        
        protocol_entropy = max(0, np.random.normal(
            pattern.protocol_entropy,
            0.2 * (1 + noise_factor)
        ))
        
        return np.array([
            packet_rate,
            byte_rate,
            avg_packet_size,
            packet_size_variance,
            syn_ratio,
            unique_src_ips,
            unique_dst_ports,
            protocol_entropy
        ], dtype=np.float32)
    
    @staticmethod
    def generate_sequence(
        pattern_name: str,
        sequence_length: int,
        add_noise: bool = True
    ) -> np.ndarray:
        """
        Generate a sequence of traffic samples.
        
        Args:
            pattern_name: Name of traffic pattern
            sequence_length: Number of time steps
            add_noise: Whether to add noise
        
        Returns:
            Sequence array of shape (sequence_length, 8)
        """
        pattern = TrafficGenerator.PATTERNS[pattern_name]
        sequence = []
        
        for _ in range(sequence_length):
            sample = TrafficGenerator.generate_sample(pattern, add_noise)
            sequence.append(sample)
        
        return np.array(sequence)
    
    @staticmethod
    def generate_transition_sequence(
        start_pattern: str,
        end_pattern: str,
        sequence_length: int,
        transition_point: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a sequence with transition from normal to attack traffic.
        
        Args:
            start_pattern: Initial pattern name
            end_pattern: Final pattern name
            sequence_length: Total sequence length
            transition_point: Time step where transition occurs
        
        Returns:
            Tuple of (features, labels)
        """
        sequence = []
        labels = []
        
        # Generate starting pattern
        for t in range(transition_point):
            pattern = TrafficGenerator.PATTERNS[start_pattern]
            sample = TrafficGenerator.generate_sample(pattern, add_noise=True)
            sequence.append(sample)
            labels.append(0 if start_pattern == 'normal' else 1)
        
        # Generate transition
        for t in range(transition_point, sequence_length):
            # Gradual transition over 5 steps
            if t < transition_point + 5:
                alpha = (t - transition_point) / 5.0
                start_sample = TrafficGenerator.generate_sample(
                    TrafficGenerator.PATTERNS[start_pattern], add_noise=False
                )
                end_sample = TrafficGenerator.generate_sample(
                    TrafficGenerator.PATTERNS[end_pattern], add_noise=False
                )
                sample = (1 - alpha) * start_sample + alpha * end_sample
            else:
                pattern = TrafficGenerator.PATTERNS[end_pattern]
                sample = TrafficGenerator.generate_sample(pattern, add_noise=True)
            
            sequence.append(sample)
            labels.append(1 if end_pattern != 'normal' else 0)
        
        return np.array(sequence), np.array(labels)
    
    @staticmethod
    def generate_dataset(
        num_normal: int = 1000,
        num_attacks_per_type: int = 250,
        sequence_length: int = 60,
        include_transitions: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate complete dataset for training.
        
        Args:
            num_normal: Number of normal traffic sequences
            num_attacks_per_type: Number of sequences per attack type
            sequence_length: Length of each sequence
            include_transitions: Whether to include transition sequences
        
        Returns:
            Tuple of (sequences, labels, attack_types)
        """
        sequences = []
        labels = []
        attack_types = []
        
        # Generate normal traffic
        print(f"Generating {num_normal} normal traffic sequences...")
        for _ in range(num_normal):
            seq = TrafficGenerator.generate_sequence('normal', sequence_length)
            sequences.append(seq)
            labels.append(0)  # Normal
            attack_types.append(0)  # Normal
        
        # Generate attack traffic for each type
        attack_pattern_names = ['syn_flood', 'udp_flood', 'http_flood', 'dns_amplification']
        for attack_idx, attack_name in enumerate(attack_pattern_names):
            print(f"Generating {num_attacks_per_type} {attack_name} sequences...")
            for _ in range(num_attacks_per_type):
                seq = TrafficGenerator.generate_sequence(attack_name, sequence_length)
                sequences.append(seq)
                labels.append(1)  # Attack
                attack_types.append(attack_idx + 1)  # Attack type index
        
        # Generate transition sequences
        if include_transitions:
            print("Generating transition sequences...")
            num_transitions = num_normal // 4
            for attack_name in attack_pattern_names:
                for _ in range(num_transitions // len(attack_pattern_names)):
                    transition_point = random.randint(
                        sequence_length // 3,
                        2 * sequence_length // 3
                    )
                    seq, seq_labels = TrafficGenerator.generate_transition_sequence(
                        'normal',
                        attack_name,
                        sequence_length,
                        transition_point
                    )
                    sequences.append(seq)
                    # Use majority vote for label
                    labels.append(int(np.mean(seq_labels) > 0.5))
                    attack_types.append(attack_pattern_names.index(attack_name) + 1 if labels[-1] == 1 else 0)
        
        return (
            np.array(sequences),
            np.array(labels),
            np.array(attack_types)
        )
    
    @staticmethod
    def save_dataset(
        sequences: np.ndarray,
        labels: np.ndarray,
        attack_types: np.ndarray,
        output_dir: str
    ):
        """Save generated dataset to files."""
        from pathlib import Path
        import os
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save as numpy arrays
        np.save(output_path / 'sequences.npy', sequences)
        np.save(output_path / 'labels.npy', labels)
        np.save(output_path / 'attack_types.npy', attack_types)
        
        # Save metadata
        metadata = {
            'num_sequences': len(sequences),
            'sequence_length': sequences.shape[1],
            'num_features': sequences.shape[2],
            'num_normal': int(np.sum(labels == 0)),
            'num_attacks': int(np.sum(labels == 1)),
            'attack_type_distribution': {
                'normal': int(np.sum(attack_types == 0)),
                'syn_flood': int(np.sum(attack_types == 1)),
                'udp_flood': int(np.sum(attack_types == 2)),
                'http_flood': int(np.sum(attack_types == 3)),
                'dns_amplification': int(np.sum(attack_types == 4))
            }
        }
        
        import json
        with open(output_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\nDataset saved to {output_dir}")
        print(f"Total sequences: {metadata['num_sequences']}")
        print(f"Normal: {metadata['num_normal']}")
        print(f"Attacks: {metadata['num_attacks']}")
    
    @staticmethod
    def load_dataset(data_dir: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Load dataset from files."""
        from pathlib import Path
        
        data_path = Path(data_dir)
        
        sequences = np.load(data_path / 'sequences.npy')
        labels = np.load(data_path / 'labels.npy')
        attack_types = np.load(data_path / 'attack_types.npy')
        
        return sequences, labels, attack_types


def create_demo_pcap():
    """Create a demo PCAP file for visualization (requires scapy)."""
    try:
        from scapy.all import IP, TCP, UDP, wrpcap, Ether
    except ImportError:
        print("scapy is required for PCAP generation")
        return
    
    packets = []
    
    # Generate some normal traffic
    for i in range(100):
        pkt = Ether()/IP(src=f"192.168.1.{random.randint(1, 254)}",
                         dst="192.168.1.1")/TCP(dport=80, sport=random.randint(1024, 65535))
        packets.append(pkt)
    
    # Generate attack traffic
    for i in range(500):
        pkt = Ether()/IP(src=f"10.0.0.{random.randint(1, 254)}",
                         dst="192.168.1.1")/TCP(dport=80, sport=random.randint(1024, 65535), flags="S")
        packets.append(pkt)
    
    wrpcap("demo_traffic.pcap", packets)
    print("Demo PCAP file created: demo_traffic.pcap")


if __name__ == "__main__":
    # Generate a complete dataset
    print("Generating synthetic DDoS detection dataset...")
    sequences, labels, attack_types = TrafficGenerator.generate_dataset(
        num_normal=2000,
        num_attacks_per_type=500,
        sequence_length=60,
        include_transitions=True
    )
    
    # Save dataset
    TrafficGenerator.save_dataset(
        sequences,
        labels,
        attack_types,
        './data/generated_dataset'
    )
