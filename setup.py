#!/usr/bin/env python3
"""
Setup and Quick Start Script for DDoS Detection System

This script helps you get started quickly by:
1. Checking dependencies
2. Creating necessary directories
3. Generating default configuration
4. Optionally running a quick demo
"""

import sys
import subprocess
import os
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")


def check_python_version():
    """Check if Python version is adequate."""
    print("Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    print("\nChecking dependencies...")
    
    required_packages = {
        'torch': 'PyTorch',
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'sklearn': 'scikit-learn',
        'matplotlib': 'Matplotlib',
        'plotly': 'Plotly',
        'yaml': 'PyYAML'
    }
    
    missing = []
    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} (not installed)")
            missing.append(name)
    
    return missing


def install_dependencies():
    """Install dependencies from requirements.txt."""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False


def setup_directories():
    """Create necessary directories."""
    print("\nSetting up directories...")
    
    directories = [
        'data/generated_dataset',
        'checkpoints',
        'logs',
        'outputs',
        'notebooks'
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ {dir_path}")
    
    return True


def create_config():
    """Create default configuration file."""
    print("\nCreating default configuration...")
    try:
        from configs.config import create_default_config_file
        create_default_config_file('./config.yaml')
        print("✅ Configuration file created: config.yaml")
        return True
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        return False


def run_quick_demo():
    """Ask if user wants to run a quick demo."""
    print("\nWould you like to run a quick demo? (This will take about 2 minutes)")
    response = input("Run demo? [y/N]: ").strip().lower()
    
    if response in ['y', 'yes']:
        print("\nRunning quick demo...")
        try:
            # Run batch demo which is fastest
            subprocess.check_call([
                sys.executable, 'demo.py', '--mode', 'batch'
            ])
            print("\n✅ Demo completed successfully!")
            return True
        except subprocess.CalledProcessError:
            print("\n⚠️  Demo failed (this is okay if model hasn't been trained yet)")
            return False
    return True


def print_next_steps():
    """Print next steps for the user."""
    print_header("SETUP COMPLETE!")
    
    print("Next steps:")
    print("\n1. Train the model:")
    print("   python train.py")
    print("   (This will generate data and train the model - takes ~10-15 minutes)")
    
    print("\n2. Run a demo:")
    print("   python demo.py --mode console --duration 60")
    print("   python demo.py --mode dashboard --duration 300")
    print("   python demo.py --mode batch")
    
    print("\n3. Customize configuration:")
    print("   Edit config.yaml to adjust hyperparameters")
    
    print("\n4. Explore the code:")
    print("   models/ssm_model.py        - State Space Model implementation")
    print("   training/trainer.py        - Training pipeline")
    print("   inference/realtime_detector.py - Real-time detection")
    print("   visualization/dashboard.py - Dashboard visualization")
    
    print("\n5. Read the documentation:")
    print("   README.md - Comprehensive project documentation")
    
    print("\nFor help, run:")
    print("   python train.py --help")
    print("   python demo.py --help")
    
    print("\n" + "="*80)


def main():
    """Main setup function."""
    print_header("DDoS Detection System - Setup")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\nWould you like to install them now?")
        response = input("Install dependencies? [Y/n]: ").strip().lower()
        
        if response not in ['n', 'no']:
            if not install_dependencies():
                print("\nPlease install dependencies manually:")
                print("   pip install -r requirements.txt")
                sys.exit(1)
            
            # Re-check after installation
            missing = check_dependencies()
            if missing:
                print(f"\n❌ Still missing: {', '.join(missing)}")
                sys.exit(1)
        else:
            print("\nPlease install dependencies manually before proceeding:")
            print("   pip install -r requirements.txt")
            sys.exit(1)
    
    # Setup directories
    if not setup_directories():
        sys.exit(1)
    
    # Create configuration
    if not create_config():
        sys.exit(1)
    
    # Offer to run demo
    run_quick_demo()
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)
