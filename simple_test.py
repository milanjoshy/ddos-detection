"""
Simple test - sends traffic and shows confirmation
"""
import socket
import json
import time

# Simple traffic data
test_data = {
    "device_id": "Test_Device",
    "packet_rate": 100.0,
    "byte_rate": 50.0,
    "syn_ratio": 0.5,
    "unique_src_ips": 10,
    "tcp_count": 70,
    "udp_count": 30,
    "icmp_count": 0,
    "avg_packet_size": 256,
    "packet_size_std": 50,
    "unique_dst_ports": 5,
    "protocol_entropy": 1.5
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
target = "127.0.0.1"
port = 5000

print("="*50)
print("Sending test packet to 127.0.0.1:5000...")
print("="*50)

try:
    # Send packet
    payload = json.dumps(test_data).encode()
    sock.sendto(payload, (target, port))
    print(f"SENT: packet_rate={test_data['packet_rate']}, syn_ratio={test_data['syn_ratio']}")
    print("\n✓ Packet sent successfully!")
    print("\nNow check if server received it:")
    print("  - If server is running, it should show '[RECV]' message")
    print("  - Check logs/latest_detection.json for detection result")
except Exception as e:
    print(f"ERROR: {e}")

sock.close()
