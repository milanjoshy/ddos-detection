#!/usr/bin/env python3
"""
ESP32 DDoS Detection System - Single Command
Starts server and dashboard in ESP32 mode
"""

import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

def main():
    print("=" * 60)
    print("ESP32 DDoS Detection System")
    print("=" * 60)
    print()
    
    os.chdir(PROJECT_DIR)
    
    # Start 1: Server
    print("[1/2] Starting Gateway Server...")
    server_proc = subprocess.Popen(
        [sys.executable, "integrated_esp32_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)
    print("    ✓ Server running on port 5000")
    
    # Start 2: Dashboard
    print("[2/2] Starting Dashboard...")
    dash_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard_unified.py", "--server.port=8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)
    print("    ✓ Dashboard at http://localhost:8501")
    
    print()
    print("=" * 60)
    print("SYSTEM RUNNING")
    print("=" * 60)
    print()
    print("Dashboard: http://localhost:8501")
    print("Server: UDP port 5000")
    print()
    print("Connect ESP32 device to see detection data")
    print("Disconnect ESP32 to see 'Disconnected' status")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        server_proc.terminate()
        dash_proc.terminate()
        print("Done!")

if __name__ == "__main__":
    main()
