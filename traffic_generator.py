#!/usr/bin/env python3
"""
traffic_generator.py

Replays sequences from data/generated_dataset/sequences.npy by converting
feature vectors into live network packets using Scapy. This allows for realistic
testing of the ESP32-based DDoS detection system.

Usage examples:
  # Send a SYN flood (sequence 2000) to the ESP32
  python traffic_generator.py --target 192.168.1.75 --port 80 --seq 2000

  # Send a random attack sequence with scaled intensity
  python traffic_generator.py --target 192.168.1.75 --port 80 --random --scale 1.2
"""
import argparse
import time
import socket
import numpy as np
import os
import sys
import random
from scapy.all import IP, TCP, UDP, Ether, send

def load_sequences(path):
    """Load sequence data from .npy file."""
    if not os.path.exists(path):
        print(f"❌ Sequences file not found: {path}")
        sys.exit(1)
    return np.load(path)

def generate_source_ips(num_ips):
    """Generate a list of random source IPs."""
    return [f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}" for _ in range(num_ips)]

def replay_sequence_as_packets(seq, target_ip, target_port, scale=1.0):
    """
    Replays a sequence of traffic features by generating and sending live network packets.

    Args:
        seq (np.ndarray): The sequence of traffic features, shape (timesteps, 8).
        target_ip (str): The IP address of the target (ESP32).
        target_port (int): The port on the target to send packets to.
        scale (float): A factor to scale the intensity of the traffic.
    """
    timesteps = seq.shape[0]
    print(f"🚀 Starting packet replay for {timesteps} timesteps...")

    for t in range(timesteps):
        features = seq[t, :] * scale
        
        packet_rate, byte_rate, avg_pkg_size, pkg_size_var, syn_ratio, \
        unique_src_ips, unique_dst_ports, proto_entropy = features

        # Sanitize feature values
        packet_rate = int(max(0, packet_rate))
        syn_ratio = np.clip(syn_ratio, 0, 1)
        avg_pkg_size = int(max(30, avg_pkg_size))
        unique_src_ips = int(max(1, unique_src_ips))

        print(f"\n--- Timestep {t+1}/{timesteps} ---")
        print(f"  Rate: {packet_rate:.1f} pkt/s, Size: {avg_pkg_size} B, SYN Ratio: {syn_ratio:.2%}")

        if packet_rate == 0:
            time.sleep(1.0)
            continue

        source_ips = generate_source_ips(unique_src_ips)
        packets_to_send = []
        
        start_time = time.time()

        for i in range(packet_rate):
            src_ip = random.choice(source_ips)
            
            # Determine protocol based on syn_ratio (and a bit of entropy)
            # This is a simplification. A more complex model could use proto_entropy.
            if random.random() < syn_ratio:
                protocol = "TCP_SYN"
            elif random.random() < 0.5:
                protocol = "UDP"
            else:
                protocol = "TCP_OTHER"

            # Create packet
            payload_size = int(np.random.normal(avg_pkg_size, np.sqrt(pkg_size_var) if pkg_size_var > 0 else 10))
            payload_size = max(0, payload_size - 28) # Adjust for IP/TCP/UDP header
            
            if protocol == "TCP_SYN":
                packet = IP(src=src_ip, dst=target_ip) / TCP(sport=random.randint(1024, 65535), dport=target_port, flags='S') / ("X"*payload_size)
            elif protocol == "TCP_OTHER":
                packet = IP(src=src_ip, dst=target_ip) / TCP(sport=random.randint(1024, 65535), dport=target_port, flags='A') / ("X"*payload_size)
            else: # UDP
                packet = IP(src=src_ip, dst=target_ip) / UDP(sport=random.randint(1024, 65535), dport=target_port) / ("X"*payload_size)

            packets_to_send.append(packet)

        # Send packets for this timestep
        if packets_to_send:
            print(f"  Sending {len(packets_to_send)} packets...")
            send(packets_to_send, verbose=0)
        
        # Regulate timing to match 1-second timestep
        elapsed = time.time() - start_time
        sleep_time = max(0, 1.0 - elapsed)
        time.sleep(sleep_time)

    print("\n✅ Replay finished.")

def main():
    parser = argparse.ArgumentParser(
        description="Generates live network traffic from a sequence file to test DDoS detection.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--target", required=True, help="Target IP address (e.g., your ESP32).")
    parser.add_argument("--port", type=int, default=80, help="Target port on the ESP32.")
    parser.add_argument("--seq", type=int, default=2000, 
                        help="Sequence index to replay.\n"
                             "  - 0-1999: Normal traffic\n"
                             "  - 2000+: Attack traffic (e.g., 2000 is a SYN flood)")
    parser.add_argument("--random", action="store_true", help="Pick a random sequence each run.")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale feature values to increase/decrease intensity.")
    parser.add_argument("--file", default="data/generated_dataset/sequences.npy", help="Path to sequences.npy file.")
    args = parser.parse_args()

    sequences = load_sequences(args.file)

    if sequences.ndim != 3:
        print(f"❌ Unexpected sequences.npy shape: {sequences.shape}. Expected (num_samples, timesteps, features).")
        sys.exit(1)
        
    num_samples = sequences.shape[0]

    try:
        if args.random:
            idx = np.random.randint(0, num_samples)
        else:
            idx = max(0, min(args.seq, num_samples - 1))

        seq = sequences[idx]
        
        print("="*50)
        print("      Real Traffic Generator for ESP32 DDoS Test")
        print("="*50)
        print(f"▶️  Target:      {args.target}:{args.port}")
        print(f"▶️  Sequence:    Index {idx} (Shape: {seq.shape})")
        print(f"▶️  Intensity:   {args.scale * 100:.0f}%")
        print("="*50)

        replay_sequence_as_packets(seq, args.target, args.port, scale=args.scale)
        
    except KeyboardInterrupt:
        print("\n🛑 Traffic generation stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure you are running this script with sufficient privileges (e.g., sudo on Linux).")


if __name__ == "__main__":
    main()
