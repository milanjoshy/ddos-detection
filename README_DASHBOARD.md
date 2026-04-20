# ESP32 DDoS Detection System

## Quick Start (Single Command)

```
bash
cd e:/final_project
python start_ddos_system.py
```

This will:
1. Start the Gateway Server (UDP port 5000)
2. Start the Dashboard (http://localhost:8501)

**Default Mode: ESP32** - Ready to receive data from ESP32 device

---

## Mode Options

### ESP32 Mode (Default)
```
bash
python start_ddos_system.py --mode esp32
```
- Waits for real ESP32 device data
- No traffic simulation

### Simulation Mode (Testing)
```
bash
python start_ddos_system.py --mode simulation
```
- Generates synthetic attack traffic
- For testing the system

---

## Manual Commands

If you prefer to run components separately:

### Terminal 1: Start Server
```
bash
cd e:/final_project
python integrated_esp32_server.py
```

### Terminal 2: Start Traffic (Optional)
```
bash
cd e:/final_project
python traffic_simulator.py
```

### Terminal 3: Start Dashboard
```
bash
cd e:/final_project
python -m streamlit run dashboard_v2.py
```

---

## Dashboard Features

- **Dark Theme** - Beautiful Catppuccin-inspired UI
- **4 Real-Time Graphs**:
  - Attack Probability
  - Packet Rate
  - Byte Rate
  - Confidence
- **Mode Switch** - Toggle between ESP32/Simulation in sidebar
- **Auto-Detection** - Detects ESP32 by default

---

## System Architecture

```
ESP32 Device  ──UDP (5000)──>  Server  ──>  JSON  ──>  Dashboard
                                              │
                                        latest_detection.json
```

---

## Performance

| Metric | Value |
|--------|-------|
| Accuracy | 92.44% |
| Recall | 97.67% |
| Latency | 25 ms |
| Model Size | 0.12 MB |

---

**Default**: ESP32 Mode - Connect ESP32 and view real-time detection!
