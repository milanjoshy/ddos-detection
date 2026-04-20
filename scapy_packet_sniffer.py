#!/usr/bin/env python3
"""scapy_packet_sniffer.py

Real network packet sniffer using Scapy. Captures live traffic from network
interface, extracts 8D features, and sends to detection server.

Requirements: Scapy, Npcap (Windows) or libpcap (Linux/Mac), admin/root privileges

Usage:
  # List interfaces
  python scapy_packet_sniffer.py --list
  
  # Sniff on interface for 60 seconds, send features to server
  python scapy_packet_sniffer.py --interface "Wi-Fi" --target 127.0.0.1 --port 5000 --duration 60
  
  # Continuous sniffing
  python scapy_packet_sniffer.py --interface eth0 --target 192.168.1.100 --port 5000 --duration 0
"""
import argparse
import time
import socket
import json
import numpy as np
from collections import defaultdict, deque
from scapy.all import sniff, IP, TCP, UDP, ICMP


class TrafficAnalyzer:
    """Analyze captured packets and extract 8D features"""
    
    def __init__(self, window_size=5.0, server_ip='127.0.0.1', server_port=5000):
        """
        window_size: seconds to aggregate traffic before sending
        """
        self.window_size = window_size
        self.server_ip = server_ip
        self.server_port = server_port
        
        # Packet counters (per window)
        self.packet_count = 0
        self.byte_count = 0
        self.syn_count = 0
        self.tcp_count = 0
        self.udp_count = 0
        self.icmp_count = 0
        
        # Unique tracking
        self.unique_ips = set()
        self.unique_ports = set()
        self.packet_sizes = deque(maxlen=1000)
        
        # Timing
        self.window_start = time.time()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def process_packet(self, packet):
        """Process a single captured packet"""
        try:
            # Extract IP layer
            if not packet.haslayer(IP):
                return
            
            ip_layer = packet[IP]
            src_ip = ip_layer.src
            packet_size = len(packet)
            
            # Update counters
            self.packet_count += 1
            self.byte_count += packet_size
            self.packet_sizes.append(packet_size)
            self.unique_ips.add(src_ip)
            
            # Protocol analysis
            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                self.tcp_count += 1
                self.unique_ports.add(tcp_layer.dport)
                
                # Check for SYN flag (0x02)
                if tcp_layer.flags & 0x02:
                    self.syn_count += 1
                    
            elif packet.haslayer(UDP):
                udp_layer = packet[UDP]
                self.udp_count += 1
                self.unique_ports.add(udp_layer.dport)
                
            elif packet.haslayer(ICMP):
                self.icmp_count += 1
            
            # Check if window is complete
            elapsed = time.time() - self.window_start
            if elapsed >= self.window_size:
                self.send_features()
                self.reset_window()
                
        except Exception as e:
            print(f"[ERROR] Processing packet: {e}")
    
    def send_features(self):
        """Calculate and send 8D features as JSON"""
        # Calculate aggregated statistics
        packet_rate = self.packet_count / self.window_size if self.window_size > 0 else 0
        byte_rate = (self.byte_count / 1024.0) / self.window_size if self.window_size > 0 else 0
        
        avg_packet_size = np.mean(list(self.packet_sizes)) if self.packet_sizes else 0
        std_packet_size = np.std(list(self.packet_sizes)) if len(self.packet_sizes) > 1 else 0
        
        # SYN ratio
        syn_ratio = self.syn_count / self.tcp_count if self.tcp_count > 0 else 0
        
        # Calculate protocol entropy
        total = self.tcp_count + self.udp_count + self.icmp_count
        entropy = 0.0
        if total > 0:
            probs = np.array([
                self.tcp_count / total,
                self.udp_count / total,
                self.icmp_count / total
            ])
            probs = probs[probs > 0]
            entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        # Create ESP32-format JSON
        esp32_json = {
            "device_id": "PC_Sniffer",
            "timestamp": int(time.time() * 1000),
            "packet_rate": float(packet_rate),
            "byte_rate": float(byte_rate),
            "avg_packet_size": float(avg_packet_size),
            "packet_size_std": float(std_packet_size),
            "syn_ratio": float(syn_ratio),
            "unique_src_ips": int(len(self.unique_ips)),
            "unique_dst_ports": int(len(self.unique_ports)),
            "protocol_entropy": float(entropy),
            "tcp_count": int(self.tcp_count),
            "udp_count": int(self.udp_count),
            "icmp_count": int(self.icmp_count)
        }
        
        # Send to server
        try:
            payload = json.dumps(esp32_json).encode('utf-8')
            self.sock.sendto(payload, (self.server_ip, self.server_port))
            
            print(f"[SENT] pkt_rate={packet_rate:.1f}/s | syn_ratio={syn_ratio:.2%} | "
                  f"byte_rate={byte_rate:.1f}KB/s | ips={len(self.unique_ips)} | "
                  f"ports={len(self.unique_ports)}")
        except Exception as e:
            print(f"[ERROR] Sending to server: {e}")
    
    def reset_window(self):
        """Reset counters for next window"""
        self.packet_count = 0
        self.byte_count = 0
        self.syn_count = 0
        self.tcp_count = 0
        self.udp_count = 0
        self.icmp_count = 0
        self.unique_ips.clear()
        self.unique_ports.clear()
        self.window_start = time.time()
    
    def cleanup(self):
        """Close socket"""
        self.sock.close()


def list_interfaces():
    """List all available network interfaces"""
    try:
        from scapy.arch import get_if_list
        interfaces = get_if_list()
        print("\n=== Available Network Interfaces ===")
        for i, iface in enumerate(interfaces, 1):
            print(f"{i}. {iface}")
        print("\nUse --interface <name> to sniff on that interface")
    except Exception as e:
        print(f"Error listing interfaces: {e}")


def main():
    parser = argparse.ArgumentParser(description="Real packet sniffer with feature extraction")
    parser.add_argument('--list', action='store_true', help='List network interfaces and exit')
    parser.add_argument('--interface', default='Wi-Fi', help='Network interface to sniff on (default: Wi-Fi)')
    parser.add_argument('--target', default='127.0.0.1', help='Server IP address')
    parser.add_argument('--port', type=int, default=5000, help='Server UDP port')
    parser.add_argument('--duration', type=int, default=60, help='Sniffing duration in seconds (0=infinite)')
    parser.add_argument('--window', type=float, default=5.0, help='Feature aggregation window size (seconds)')
    args = parser.parse_args()
    
    # List interfaces if requested
    if args.list:
        list_interfaces()
        return
    
    # Create analyzer
    analyzer = TrafficAnalyzer(
        window_size=args.window,
        server_ip=args.target,
        server_port=args.port
    )
    
    try:
        print(f"\n{'='*70}")
        print(f"Real Packet Sniffer - Feature Extraction & Server Upload")
        print(f"{'='*70}")
        print(f"Interface: {args.interface}")
        print(f"Server: {args.target}:{args.port}")
        print(f"Window: {args.window}s")
        if args.duration > 0:
            print(f"Duration: {args.duration}s")
        else:
            print(f"Duration: Infinite (Ctrl+C to stop)")
        print(f"{'='*70}\n")
        
        # Sniff packets
        sniff(
            iface=args.interface,
            prn=analyzer.process_packet,
            timeout=args.duration if args.duration > 0 else None,
            store=False
        )
        
    except KeyboardInterrupt:
        print("\n[INFO] Sniffing stopped by user")
    except Exception as e:
        print(f"[ERROR] Sniffing error: {e}")
        print("\nTroubleshooting:")
        print("- Windows: Ensure Npcap is installed (https://npcap.com/)")
        print("- Linux/Mac: Run with sudo")
        print("- Use --list to see available interfaces")
    finally:
        analyzer.cleanup()


if __name__ == '__main__':
    main()
