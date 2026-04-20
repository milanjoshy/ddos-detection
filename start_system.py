#!/usr/bin/env python3
"""
Single Command to Start Complete ESP32 DDoS Detection System

This script launches all components of the DDoS detection system:
1. Gateway Server (integrated_esp32_server.py)
2. Traffic Generator (traffic_generator.py)
3. Dashboard (esp32_integrated_dashboard.py)

Usage: 
  python start_system.py --traffic normal
  python start_system.py --traffic attack

Requirements:
- ESP32 firmware already uploaded to Arduino IDE
- All Python dependencies installed
- Firewall allows UDP port 5000
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path
import argparse

# Configuration
SERVER_PORT = 5000
TRAFFIC_TARGET = "127.0.0.1"  # Localhost for testing

class SystemLauncher:
    """Launches and manages all system components"""

    def __init__(self, sequence_index):
        self.processes = []
        self.project_dir = Path(__file__).parent
        self.sequence_index = sequence_index

    def check_requirements(self):
        """Check if all required files exist"""
        required_files = [
            "integrated_esp32_server.py",
            "traffic_generator.py",
            "esp32_integrated_dashboard.py",
            "data/generated_dataset/sequences.npy"
        ]

        missing_files = []
        for file in required_files:
            if not (self.project_dir / file).exists():
                missing_files.append(file)

        if missing_files:
            print("[ERROR] Missing required files:")
            for file in missing_files:
                print(f"   - {file}")
            print("\nPlease ensure all files are present before running.")
            return False

        print("[OK] All required files found")
        return True

    def start_server(self):
        """Start the gateway server"""
        print("\n[START] Starting Gateway Server...")
        cmd = [sys.executable, "integrated_esp32_server.py", "--port", str(SERVER_PORT)]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        self.processes.append(("Gateway Server", process))
        print(f"[OK] Gateway Server started (PID: {process.pid})")

    def start_traffic_generator(self):
        """Start the traffic simulator"""
        # Determine traffic mode based on sequence index
        # sequence_index 0-1999 = normal, 2000+ = attack
        traffic_mode = "syn_flood" if self.sequence_index >= 2000 else "normal"
        
        print(f"\n[START] Starting Traffic Simulator (Mode: {traffic_mode})...")
        cmd = [
            sys.executable, "traffic_simulator.py",
            "--mode", traffic_mode,
            "--target", TRAFFIC_TARGET,
            "--port", str(SERVER_PORT),
            "--interval", "1",
            "--verbose"
        ]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        self.processes.append(("Traffic Simulator", process))
        print(f"[OK] Traffic Simulator started (PID: {process.pid})")

    def start_dashboard(self):
        """Start the dashboard"""
        print("\n[START] Starting Dashboard...")
        cmd = [sys.executable, "-m", "streamlit", "run", "esp32_integrated_dashboard.py", "--server.port", "8501"]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        self.processes.append(("Dashboard", process))
        print(f"[OK] Dashboard started (PID: {process.pid})")

    def monitor_processes(self):
        """Monitor running processes and restart if needed"""
        while True:
            time.sleep(5)
            for name, process in self.processes:
                if process.poll() is not None:
                    print(f"[WARN] {name} has stopped (exit code: {process.returncode})")

    def wait_for_server_ready(self):
        """Wait for server to be ready"""
        print("\n[WAIT] Waiting for server to initialize...")
        time.sleep(3)

    def print_instructions(self):
        """Print usage instructions"""
        traffic_type = "ATTACK" if self.sequence_index >= 2000 else "NORMAL"
        print("\n" + "="*70)
        print("ESP32 DDoS Detection System - RUNNING")
        print("="*70)
        print(f"Dashboard: http://localhost:8501")
        print(f"Server Port: {SERVER_PORT} (UDP)")
        print(f"Traffic Target: {TRAFFIC_TARGET}:{SERVER_PORT}")
        print(f"Traffic Type: {traffic_type}")
        print("\nComponents Running:")
        for name, process in self.processes:
            status = "RUNNING" if process.poll() is None else "STOPPED"
            print(f"   {name}: {status} (PID: {process.pid})")

        print("\nTo stop the system:")
        print("   Press Ctrl+C or close this terminal")
        print("\nInstructions:")
        print("   1. Dashboard will show live detection results.")
        print("   2. Traffic generator is sending a pre-defined sequence.")
        print("   3. Server processes data from the ESP32 and updates the dashboard.")
        print("   4. Detection delay: ~15 seconds (15 timesteps * 1s interval)")
        print("\n" + "="*70)

    def cleanup(self):
        """Clean up all processes"""
        print("\n[SHUTDOWN] Shutting down system...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"[OK] {name} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"[WARN] {name} force killed")
        print("[DONE] System shutdown complete")

    def run(self):
        """Main execution"""
        print("ESP32 DDoS Detection System Launcher")
        print("="*50)

        if not self.check_requirements():
            return

        def signal_handler(signum, frame):
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.start_server()
            self.wait_for_server_ready()
            self.start_traffic_generator()
            self.start_dashboard()
            self.print_instructions()
            self.monitor_processes()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Start the DDoS Detection System.")
    parser.add_argument(
        "--traffic", 
        type=str, 
        choices=['normal', 'attack'], 
        default='normal',
        help="Type of traffic to generate. 'normal' or 'attack'."
    )
    args = parser.parse_args()

    if args.traffic == 'attack':
        sequence_index = 2000
        print("[TRAFFIC] Starting with ATTACK traffic simulation.")
    else:
        sequence_index = 0
        print("[TRAFFIC] Starting with NORMAL traffic simulation.")

    launcher = SystemLauncher(sequence_index=sequence_index)
    launcher.run()


if __name__ == "__main__":
    main()
