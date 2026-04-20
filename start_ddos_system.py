#!/usr/bin/env python3
"""
Unified DDoS Detection System Launcher
Single command to start everything - server, simulation, and dashboard
Default: ESP32 Mode
"""

import subprocess
import sys
import os
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

class DDOSSystemLauncher:
    def __init__(self):
        self.server_process = None
        self.simulator_process = None
    
    def start_server(self):
        """Start the gateway server"""
        print("[1/2] Starting Gateway Server...")
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "integrated_esp32_server.py"],
                cwd=str(PROJECT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)
            print("    ✓ Server started on port 5000")
            return True
        except Exception as e:
            print(f"    ✗ Failed to start server: {e}")
            return False
    
    def start_simulation(self):
        """Start traffic simulation"""
        print("[2/2] Starting Traffic Simulator...")
        try:
            self.simulator_process = subprocess.Popen(
                [sys.executable, "traffic_simulator.py"],
                cwd=str(PROJECT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(1)
            print("    ✓ Simulator started")
            return True
        except Exception as e:
            print(f"    ✗ Failed to start simulator: {e}")
            return False
    
    def start_dashboard(self):
        """Start Streamlit dashboard"""
        print("[3/3] Starting Dashboard...")
        try:
            subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "dashboard_v2.py"],
                cwd=str(PROJECT_DIR)
            )
            time.sleep(2)
            print("    ✓ Dashboard started at http://localhost:8501")
            return True
        except Exception as e:
            print(f"    ✗ Failed to start dashboard: {e}")
            return False
    
    def run_esp32_mode(self):
        """Run in ESP32 mode (default)"""
        print("\n" + "="*50)
        print("ESP32 DDOS DETECTION SYSTEM")
        print("="*50 + "\n")
        
        # Start server
        if not self.start_server():
            return False
        
        # Start dashboard
        self.start_dashboard()
        
        print("\n" + "="*50)
        print("SYSTEM RUNNING - ESP32 MODE (DEFAULT)")
        print("="*50)
        print("\nWaiting for ESP32 device to send data...")
        print("Dashboard: http://localhost:8501")
        print("\nPress Ctrl+C to stop all processes\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()
    
    def run_simulation_mode(self):
        """Run in simulation mode"""
        print("\n" + "="*50)
        print("DDOS DETECTION SYSTEM - SIMULATION MODE")
        print("="*50 + "\n")
        
        # Start server
        if not self.start_server():
            return False
        
        # Start simulation
        self.start_simulation()
        
        # Start dashboard
        self.start_dashboard()
        
        print("\n" + "="*50)
        print("SYSTEM RUNNING - SIMULATION MODE")
        print("="*50)
        print("\nGenerating synthetic attack traffic...")
        print("Dashboard: http://localhost:8501")
        print("\nPress Ctrl+C to stop all processes\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()
    
    def stop_all(self):
        """Stop all processes"""
        print("\n\nStopping all processes...")
        
        if self.simulator_process:
            self.simulator_process.terminate()
            print("    ✓ Simulator stopped")
        
        if self.server_process:
            self.server_process.terminate()
            print("    ✓ Server stopped")
        
        print("\nAll processes stopped.")
        sys.exit(0)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="DDoS Detection System Launcher")
    parser.add_argument('--mode', choices=['esp32', 'simulation'], default='esp32',
                       help='Mode: esp32 (default, real device) or simulation (test traffic)')
    
    args = parser.parse_args()
    
    launcher = DDOSSystemLauncher()
    
    if args.mode == 'esp32':
        launcher.run_esp32_mode()
    else:
        launcher.run_simulation_mode()


if __name__ == "__main__":
    main()
