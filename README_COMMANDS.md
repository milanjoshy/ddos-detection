# ESP32 DDoS Detection System

## Running in 3 Terminals (Manual)

### Terminal 1 - Server
```
bash
cd e:/final_project
python integrated_esp32_server.py
```

### Terminal 2 - Dashboard
```
bash
cd e:/final_project
python -m streamlit run dashboard_unified.py
```

### Terminal 3 - ESP32 (Real Device)
Connect ESP32 device via USB and upload the firmware using Arduino IDE

---

## OR: Using Traffic Generator (Testing Without ESP32)

If you don't have ESP32 connected, use traffic generator instead:

### Terminal 1 - Server
```
bash
cd e:/final_project
python integrated_esp32_server.py
```

### Terminal 2 - Dashboard
```
bash
cd e:/final_project
python -m streamlit run dashboard_unified.py
```

### Terminal 3 - Traffic Generator
```
bash
cd e:/final_project
python traffic_simulator.py --mode mixed --interval 1
```

---

## Dashboard Behavior

| Scenario | Result |
|----------|--------|
| ESP32/Traffic connected | Shows real-time data + 4 graphs |
| Disconnected | Shows "❌ ESP32 DISCONNECTED" |

---

## Dashboard Features

- **4 Graphs (2x2)**: Attack Probability, Packet Rate, Byte Rate, SYN Ratio
- **Network Details**: TCP/UDP packets, Source IPs, Device ID
- **IP Details**: Device info, Network summary
- **Statistics**: Total, Attacks, Normal, Rate
- **Recent Activity**: Table with timestamps

---

## Access

- **Dashboard**: http://localhost:8501
- **Server**: UDP port 5000
