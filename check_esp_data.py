"""
Quick check: See if server receives data on port 5000
Run this while traffic simulator is sending data
"""
import socket
import json
import time

print("="*60)
print("Checking if data is received on port 5000...")
print("Make sure traffic_simulator.py is running!")
print("="*60)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 5000))
sock.settimeout(5)  # Wait 5 seconds for data

try:
    print("\nWaiting for data...")
    data, addr = sock.recvfrom(2048)
    print(f"\n✓ Received data from {addr}!")
    print(f"Data length: {len(data)} bytes")
    
    # Parse and show the data
    try:
        parsed = json.loads(data.decode('utf-8'))
        print("\nReceived features:")
        for key, value in parsed.items():
            print(f"  {key}: {value}")
    except:
        print(f"\nRaw data: {data[:100]}")
        
except socket.timeout:
    print("\n✗ No data received in 5 seconds")
    print("Make sure traffic_simulator.py is running!")
    print("Example: python traffic_simulator.py --mode normal --target 127.0.0.1 --port 5000 --verbose")
finally:
    sock.close()
