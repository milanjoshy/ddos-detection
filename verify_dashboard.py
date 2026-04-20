#!/usr/bin/env python3
"""
Dashboard Verification & Setup Script
Checks all dependencies and environment for professional dashboard
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def check_python():
    """Check Python version"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"{Colors.GREEN}✓{Colors.RESET} Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Python 3.8+ required (found {version.major}.{version.minor})")
            return False
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.RESET} Python check failed: {e}")
        return False

def check_package(package_name, import_name=None):
    """Check if package is installed"""
    if import_name is None:
        import_name = package_name.replace('-', '_')
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def check_packages():
    """Check all required packages"""
    packages = {
        'streamlit': 'streamlit',
        'plotly': 'plotly',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'torch': 'torch',
        'sklearn': 'scikit_learn'
    }
    
    print(f"\n{Colors.CYAN}Checking Required Packages:{Colors.RESET}")
    
    missing = []
    for package, import_name in packages.items():
        if check_package(package, import_name):
            print(f"  {Colors.GREEN}✓{Colors.RESET} {package}")
        else:
            print(f"  {Colors.RED}✗{Colors.RESET} {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n{Colors.YELLOW}Install missing packages:{Colors.RESET}")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True

def check_ports():
    """Check if required ports are available"""
    print(f"\n{Colors.CYAN}Checking Ports:{Colors.RESET}")
    
    required_ports = {
        5000: "Server (UDP)",
        8501: "Dashboard (Streamlit)"
    }
    
    all_available = True
    for port, service in required_ports.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} Port {port} ({service}) - In use!")
                all_available = False
            else:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Port {port} ({service}) - Available")
            sock.close()
        except Exception as e:
            print(f"  {Colors.YELLOW}?{Colors.RESET} Port {port} - Could not check: {e}")
    
    return all_available

def check_files():
    """Check if required files exist"""
    print(f"\n{Colors.CYAN}Checking Files:{Colors.RESET}")
    
    required_files = {
        'integrated_esp32_server.py': 'Server Script',
        'dashboard_unified.py': 'Dashboard',
        'traffic_simulator.py': 'Traffic Generator',
        'requirements.txt': 'Dependencies',
        'logs': 'Logs Directory'
    }
    
    for file_path, description in required_files.items():
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size if path.is_file() else 'dir'
            if isinstance(size, int):
                size_str = f"{size:,} bytes"
            else:
                size_str = "["
            print(f"  {Colors.GREEN}✓{Colors.RESET} {description} ({file_path})")
        else:
            print(f"  {Colors.RED}✗{Colors.RESET} {description} ({file_path}) - Missing!")
    
    # Create logs directory if missing
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

def check_detection_file():
    """Check if detection JSON file exists and is recent"""
    print(f"\n{Colors.CYAN}Checking Detection File:{Colors.RESET}")
    
    detection_file = Path('logs/latest_detection.json')
    
    if detection_file.exists():
        try:
            with open(detection_file, 'r') as f:
                data = json.load(f)
            
            file_age = time.time() - detection_file.stat().st_mtime
            
            print(f"  {Colors.GREEN}✓{Colors.RESET} Detection file exists")
            
            # Check if recent
            if file_age < 10:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Data is fresh ({int(file_age)}s old)")
            else:
                print(f"  {Colors.YELLOW}⚠{Colors.RESET} Data is stale ({int(file_age)}s old)")
            
            # Show latest detection
            if 'timestamp' in data:
                print(f"  📊 Latest: {data.get('timestamp')}")
        except Exception as e:
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} Could not read file: {e}")
    else:
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} Detection file not created yet")
        print(f"     (will be created when server starts receiving data)")

def get_system_info():
    """Get system information"""
    print(f"\n{Colors.CYAN}System Information:{Colors.RESET}")
    
    try:
        import platform
        print(f"  OS: {platform.system()} {platform.release()}")
        print(f"  Architecture: {platform.machine()}")
        print(f"  Python: {platform.python_version()}")
    except:
        pass
    
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        print(f"  CUDA Available: {torch.cuda.is_available()}")
    except:
        print(f"  PyTorch: Not available")

def print_setup_instructions():
    """Print setup instructions"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}Quick Start Instructions:{Colors.RESET}")
    
    instructions = f"""
{Colors.BOLD}Terminal 1 - Start Server:{Colors.RESET}
  python integrated_esp32_server.py
  
{Colors.BOLD}Terminal 2 - Start Dashboard:{Colors.RESET}
  streamlit run dashboard_unified.py
  
{Colors.BOLD}Terminal 3 - Generate Traffic (choose one):{Colors.RESET}
  # Option 1: Mixed traffic
  python traffic_simulator.py --mode mixed
  
  # Option 2: SYN flood
  python traffic_simulator.py --mode syn_flood
  
  # Option 3: Real ESP32 device
  (Upload firmware via Arduino IDE)
    """
    print(instructions)

def verify_installation():
    """Run all checks and provide summary"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print(f"DDoS Detection System - Environment Verification")
    print(f"{'='*60}{Colors.RESET}\n")
    
    checks = {
        'Python Version': check_python,
        'Required Packages': check_packages,
        'Network Ports': check_ports,
        'Project Files': check_files,
        'Detection Data': check_detection_file
    }
    
    results = {}
    for check_name, check_func in checks.items():
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"{Colors.RED}Error in {check_name}: {e}{Colors.RESET}")
            results[check_name] = False
    
    # System info
    get_system_info()
    
    # Summary
    print(f"\n{Colors.CYAN}{Colors.BOLD}Summary:{Colors.RESET}")
    
    all_passed = all(results.values())
    
    for check_name, result in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.YELLOW}⚠ CHECK{Colors.RESET}"
        print(f"  {status} - {check_name}")
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed! Ready to run.{Colors.RESET}")
        print_setup_instructions()
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some checks need attention.{Colors.RESET}")
        print(f"  Please address any missing items above and run again.")
        return 1

def main():
    """Main entry point"""
    try:
        exit_code = verify_installation()
        
        print(f"\n{Colors.CYAN}Documentation:{Colors.RESET}")
        print(f"  📖 Full Guide: DASHBOARD_GUIDE.md")
        print(f"  🚀 Quick Start: DASHBOARD_QUICKSTART.md")
        print(f"  📋 All Commands: README_COMMANDS.md")
        
        print(f"\n{Colors.CYAN}Support:{Colors.RESET}")
        print(f"  Server logs: logs/latest_detection.json")
        print(f"  Dashboard: http://localhost:8501")
        print(f"  Server: UDP port 5000")
        
        return exit_code
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Verification cancelled.{Colors.RESET}")
        return 1
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
