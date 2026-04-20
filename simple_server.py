"""
Simple server - always shows when data received
"""
import socket
import json

print("="*50)
print("Starting simple server on port 5000...")
print("="*50)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 5000))
sock.settimeout(1)  # 1 second timeout

count = 0
print("\nWaiting for data...\n")

try:
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            count += 1
            
            print(f"✓ [{count}] RECEIVED from {addr}")
            
            # Parse and show data
            try:
                parsed = json.loads(data.decode('utf-8'))
                print(f"   device_id: {parsed.get('device_id', 'unknown')}")
                print(f"   packet_rate: {parsed.get('packet_rate', 0)}")
                print(f"   syn_ratio: {parsed.get('syn_ratio', 0)}")
            except:
                print(f"   Raw: {data[:50]}")
            print()
            
        except socket.timeout:
            print(".", end="", flush=True)
            continue
            
except KeyboardInterrupt:
    print("\n\nStopped!")
    
sock.close()
