# 🛡️ Real-Time DDoS Detection in IoT Edge Networks Using S5 Models
## Complete Project Working Guide

**Authors:** Milan Joshy, Keirolona Safana Seles  
**Institution:** Karunya Institute of Technology and Sciences  
**Project:** IoT Edge Security with State Space Models

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Hardware & Software Requirements](#requirements)
4. [Complete Setup Guide](#setup-guide)
5. [How Everything Works Together](#how-it-works)
6. [Running the Project](#running-project)
7. [Understanding the Results](#understanding-results)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

### **What This Project Does:**

This is a **distributed IoT security system** that detects DDoS attacks in real-time using:
- **ESP32 microcontroller** at the network edge (victim IoT device)
- **Your PC** as gateway server (runs AI model)
- **S5 State Space Model** for temporal pattern recognition
- **Real-time dashboard** for visualization

### **The Problem We're Solving:**

IoT devices are vulnerable to DDoS attacks but too weak to run complex AI models. Our solution:
- ✅ Lightweight feature extraction on ESP32 (520KB RAM, 240MHz)
- ✅ Heavy AI processing on powerful gateway server
- ✅ Real-time detection with 87ms latency
- ✅ Works on commodity hardware (no GPU needed)

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    COMPLETE SYSTEM DIAGRAM                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────┐        ┌─────────────┐      ┌─────────────┐ │
│  │   Your PC   │  WiFi  │   Router    │ WiFi │   ESP32     │ │
│  │ (Attacker)  │◄──────►│ 192.168.1.1 │◄────►│  (Victim)   │ │
│  │             │        └─────────────┘      │             │ │
│  └──────┬──────┘                             └──────┬──────┘ │
│         │                                           │        │
│         │ Generates Traffic                         │        │
│         │ (Normal or Attack)                        │        │
│         │                                           │        │
│         └──────────────────────►──────────────────►│        │
│                  Packets sent to ESP32              │        │
│                                                     │        │
│                                          ESP32 Receives     │
│                                          Analyzes Traffic   │
│                                          Extracts Features  │
│                                                     │        │
│                                          Sends to Gateway   │
│                                                     │        │
│  ┌─────────────────────────────────────────────────┘        │
│  │                                                           │
│  ▼                                                           │
│  ┌──────────────────────────────────────────┐               │
│  │  Gateway Server (Your PC)                │               │
│  │  ───────────────────────────              │               │
│  │  1. Receives 8D features from ESP32      │               │
│  │  2. Buffers 60 timesteps (5 minutes)     │               │
│  │  3. Runs S5 Model (87ms inference)       │               │
│  │  4. Detects: Attack or Normal            │               │
│  │  5. Updates Dashboard                    │               │
│  └──────────────────────────────────────────┘               │
│                                                                │
│  ┌──────────────────────────────────────────┐               │
│  │  Dashboard (Streamlit)                   │               │
│  │  ───────────────────                     │               │
│  │  Shows real-time:                        │               │
│  │  - Traffic statistics                    │               │
│  │  - Attack probability                    │               │
│  │  - 🟢 Normal or 🔴 Attack alert          │               │
│  │  - Graphs and visualizations             │               │
│  └──────────────────────────────────────────┘               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 💻 Hardware & Software Requirements {#requirements}

### **Hardware:**

1. **ESP32 Development Board**
   - Model: ESP32-DevKitC V4
   - RAM: 520KB SRAM
   - CPU: Dual-core 240MHz
   - WiFi: 2.4GHz 802.11 b/g/n
   - Cost: ~$8

2. **Your Computer/Laptop**
   - OS: Windows 10/11, macOS, or Linux
   - RAM: 4GB minimum (8GB recommended)
   - CPU: Intel i3 or better
   - WiFi: 2.4GHz capable

3. **WiFi Router**
   - 2.4GHz band (ESP32 requirement)
   - Both PC and ESP32 must connect to same network

### **Software:**

```bash
# Python 3.8+
python --version

# Arduino IDE 2.x
# Download from: https://www.arduino.cc/en/software

# Python Packages
pip install torch numpy pandas streamlit plotly scapy
pip install ArduinoJson  # For ESP32 (via Arduino IDE)
```

### **Project Files:**

```
your_project/
├── data/
│   ├── sequences.npy          # Your dataset
│   ├── labels.npy
│   ├── attack_types.npy
│   └── metadata.json
├── checkpoints/
│   ├── best_model.pt          # Trained S5 model
│   └── normalizer.pkl         # Feature normalizer
├── esp32_traffic_victim.ino   # ESP32 code (victim)
├── traffic_generator.py       # PC traffic generator
├── integrated_server.py       # Gateway server
├── esp32_integrated_dashboard.py  # Dashboard
├── ssm_model.py               # S5 model architecture
├── feature_extraction.py      # Feature processing
└── realtime_detector.py       # Detection engine
```

---

## 🚀 Complete Setup Guide {#setup-guide}

### **Step 1: Setup ESP32 (15 minutes)**

**1.1 Install Arduino IDE**
```bash
# Download from: https://www.arduino.cc/en/software
# Install for your OS
```

**1.2 Add ESP32 Board Support**
```
Arduino IDE → File → Preferences
Additional Board Manager URLs:
https://dl.espressif.com/dl/package_esp32_index.json

Tools → Board → Boards Manager
Search: "esp32"
Install: "esp32 by Espressif Systems"
```

**1.3 Install ArduinoJson Library**
```
Tools → Manage Libraries
Search: "ArduinoJson"
Install: ArduinoJson by Benoit Blanchon (v6.x)
```

**1.4 Configure ESP32 Code**
```cpp
// In esp32_traffic_victim.ino

// Line 21-22: Your WiFi credentials
const char* ssid = "YourWiFiName";        // ← Change this
const char* password = "YourPassword";     // ← Change this

// Line 25: Your PC's IP address
const char* gatewayIP = "192.168.1.100";  // ← Change to your PC IP
```

**How to find your PC IP:**
```bash
# Windows
ipconfig
# Look for: IPv4 Address: 192.168.1.XXX

# Mac/Linux
ifconfig
# Look for: inet 192.168.1.XXX
```

**1.5 Upload to ESP32**
```
1. Connect ESP32 via USB
2. Tools → Board → ESP32 Dev Module
3. Tools → Port → Select ESP32 port (COM3, /dev/ttyUSB0, etc.)
4. Click Upload button (→)
5. Wait for "Done uploading"
6. Open Serial Monitor (Tools → Serial Monitor)
7. Set baud rate: 115200
8. See: "ESP32 Ready! IP: 192.168.1.75"
```

---

### **Step 2: Setup Python Environment (10 minutes)**

**2.1 Create Virtual Environment (Recommended)**
```bash
# Navigate to project folder
cd your_project

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

**2.2 Install Dependencies**
```bash
pip install torch torchvision numpy pandas
pip install streamlit plotly
pip install scapy

# Verify installation
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import streamlit; print('Streamlit:', streamlit.__version__)"
```

**2.3 Verify Model Files**
```bash
# Check these files exist:
ls checkpoints/best_model.pt
ls checkpoints/normalizer.pkl
ls data/sequences.npy

# If missing, you need to train the model first
```

---

### **Step 3: Network Configuration (5 minutes)**n+
**3.1 Ensure Same WiFi Network**
```bash
# Both ESP32 and PC must be on SAME network

ESP32 IP:  192.168.1.75   (shown in Serial Monitor)
Your PC:   192.168.1.100  (from ipconfig/ifconfig)
Router:    192.168.1.1    (gateway)

# All should have 192.168.1.XXX format
```

**3.2 Allow Firewall (Important!)**

**Windows:**
```
Control Panel → Windows Firewall → Advanced Settings
Inbound Rules → New Rule → Port
Protocol: UDP, Port: 5000
Allow the connection → Name: "ESP32 Gateway"
```

**Mac:**
```bash
# Usually no firewall issues
# If problems: System Preferences → Security & Privacy → Firewall Options
```

**Linux:**
```bash
sudo ufw allow 5000/udp
```

**3.3 Test Network Connectivity**
```bash
# From your PC, ping ESP32
ping 192.168.1.75

# Should see:
# Reply from 192.168.1.75: bytes=32 time=10ms
```

---

## 🎬 How Everything Works Together {#how-it-works}

(Truncated here for brevity — full guide included in project documentation files.)
