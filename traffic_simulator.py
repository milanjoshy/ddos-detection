#!/usr/bin/env python3
"""
Traffic Simulator for ESP32 DDoS Detection System

Simulates network traffic with configurable parameters:
- Normal traffic or attack traffic (SYN Flood, UDP Flood, etc.)
- Configurable packet rate, SYN ratio, etc.
- Sends data to the gateway server

Usage:
    python traffic_simulator.py --mode normal --rate 100
    python traffic_simulator.py --mode syn_flood --rate 500
    python traffic_simulator.py --mode udp_flood --rate 500
"""

import argparse
import time
import socket
import json
import numpy as np
import random
from pathlib import Path

# Default configuration
DEFAULT_TARGET = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_INTERVAL = 4.0  # seconds between packets (updated for faster detection)

# Traffic modes
TRAFFIC_MODES = {
    "normal": {
        "description": "Normal legitimate traffic",
        "packet_rate": (50, 150),
        "syn_ratio": (0.1, 0.3),
        "unique_ips": (5, 20),
        "unique_ports": (3, 15),
        "avg_packet_size": (64, 512),
    },
    "syn_flood": {
        "description": "SYN Flood attack (high SYN ratio)",
        "packet_rate": (200, 800),
        "syn_ratio": (0.8, 1.0),
        "unique_ips": (50, 200),
        "unique_ports": (1, 10),
        "avg_packet_size": (40, 80),
    },
    "udp_flood": {
        "description": "UDP Flood attack",
        "packet_rate": (300, 1000),
        "syn_ratio": (0.0, 0.1),
        "unique_ips": (20, 100),
        "unique_ports": (10, 50),
        "avg_packet_size": (100, 1500),
    },
    "mixed": {
        "description": "Mixed normal and attack traffic",
        "packet_rate": (100, 400),
        "syn_ratio": (0.2, 0.6),
        "unique_ips": (20, 80),
        "unique_ports": (10, 30),
        "avg_packet_size": (60, 800),
    }
}


def generate_traffic_features(mode="normal", scale=1.0):
    """
    Generate random traffic features based on mode
    
    Returns:
        dict: Traffic features
    """
    mode_config = TRAFFIC_MODES.get(mode, TRAFFIC_MODES["normal"])
    
    # Generate random values within ranges
    packet_rate = random.randint(*mode_config["packet_rate"]) * scale
    syn_ratio = random.uniform(*mode_config["syn_ratio"])
    unique_ips = random.randint(*mode_config["unique_ips"])
    unique_ports = random.randint(*mode_config["unique_ports"])
    avg_packet_size = random.randint(*mode_config["avg_packet_size"])
    
    # Calculate derived values
    byte_rate = packet_rate * avg_packet_size / 1024  # KB/s
    packet_size_std = avg_packet_size * 0.3  # Approximate std dev
    
    # Protocol distribution
    tcp_count = int(packet_rate * 0.7)
    udp_count = int(packet_rate * 0.3)
    icmp_count = 0
    
    # Calculate protocol entropy
    total = tcp_count + udp_count + icmp_count
    if total > 0:
        probs = np.array([tcp_count, udp_count, icmp_count]) / total
        probs = probs[probs > 0]
        protocol_entropy = -np.sum(probs * np.log2(probs + 1e-10))
    else:
        protocol_entropy = 0
    
    return {
        "device_id": "Traffic_Simulator",
        "timestamp": int(time.time() * 1000),
        "packet_rate": float(packet_rate),
        "byte_rate": float(byte_rate),
        "avg_packet_size": float(avg_packet_size),
        "packet_size_std": float(packet_size_std),
        "syn_ratio": float(syn_ratio),
        "unique_src_ips": int(unique_ips),
        "unique_dst_ports": int(unique_ports),
        "protocol_entropy": float(protocol_entropy),
        "tcp_count": tcp_count,
        "udp_count": udp_count,
        "icmp_count": icmp_count,
        "mode": mode
    }


def send_traffic_data(sock, target, port, features):
    """Send traffic features as JSON to server"""
    payload = json.dumps(features).encode('utf-8')
    try:
        sock.sendto(payload, (target, port))
        return True
    except Exception as e:
        print(f"Error sending: {e}")
        return False


def run_simulator(mode, target, port, interval, duration, verbose):
    """
    Run traffic simulator
    
    Args:
        mode: Traffic mode (normal, syn_flood, udp_flood, mixed)
        target: Target server IP
        port: Target server port
        interval: Seconds between sends
        duration: Total duration in seconds (0 = infinite)
        verbose: Print verbose output
    """
    print(f"\n{'='*60}")
    print(f"[START] Traffic Simulator Starting")
    print(f"{'='*60}")
    print(f"Mode: {mode}")
    print(f"Target: {target}:{port}")
    print(f"Interval: {interval}s")
    print(f"Duration: {duration if duration > 0 else 'Infinite'}")
    print(f"{'='*60}\n")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    start_time = time.time()
    packet_count = 0
    
    try:
        while True:
            # Generate traffic
            features = generate_traffic_features(mode=mode)
            
            # Send to server
            if send_traffic_data(sock, target, port, features):
                packet_count += 1
                
                if verbose:
                    print(f"[{packet_count}] {mode.upper()}: "
                          f"pkt_rate={features['packet_rate']:.0f}/s, "
                          f"syn_ratio={features['syn_ratio']:.2%}, "
                          f"unique_ips={features['unique_src_ips']}")
            else:
                print(f"Failed to send packet {packet_count + 1}")
            
            # Wait interval
            time.sleep(interval)
            
            # Check duration
            if duration > 0 and (time.time() - start_time) >= duration:
                print(f"\n[OK] Simulation complete! Sent {packet_count} packets")
                break
                
    except KeyboardInterrupt:
        print(f"\n[STOP] Stopped by user. Sent {packet_count} packets")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(
        description="Traffic Simulator for DDoS Detection System"
    )
    
    # Traffic mode
    parser.add_argument(
        "--mode", "-m",
        choices=list(TRAFFIC_MODES.keys()),
        default="normal",
        help="Traffic mode to simulate"
    )
    
    # Target configuration
    parser.add_argument(
        "--target", "-t",
        default=DEFAULT_TARGET,
        help=f"Target server IP (default: {DEFAULT_TARGET})"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Target server port (default: {DEFAULT_PORT})"
    )
    
    # Timing configuration
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between packets (default: {DEFAULT_INTERVAL})"
    )
    
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=0,
        help="Simulation duration in seconds (0 = infinite, default: 0)"
    )
    
    # Output configuration
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print verbose output"
    )
    
    # List modes
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="List available traffic modes and exit"
    )
    
    args = parser.parse_args()
    
    # List modes
    if args.list_modes:
        print("\n[INFO] Available Traffic Modes:")
        print("="*60)
        for mode, config in TRAFFIC_MODES.items():
            print(f"\n{mode.upper()}:")
            print(f"  Description: {config['description']}")
            print(f"  Packet Rate: {config['packet_rate'][0]}-{config['packet_rate'][1]} pkt/s")
            print(f"  SYN Ratio: {config['syn_ratio'][0]*100:.0f}-{config['syn_ratio'][1]*100:.0f}%")
            print(f"  Unique IPs: {config['unique_ips'][0]}-{config['unique_ips'][1]}")
        print("\n")
        return
    
    # Run simulator
    run_simulator(
        mode=args.mode,
        target=args.target,
        port=args.port,
        interval=args.interval,
        duration=args.duration,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
