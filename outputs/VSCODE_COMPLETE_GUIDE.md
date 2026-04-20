# Complete VS Code Integration Guide

## 🎯 Project Integration Overview

```
YOUR EXISTING PROJECT                NEW ESP32 INTEGRATION
────────────────────                ──────────────────────
project/                            project/
├── train_model.py         ────┐    ├── esp32_integration/
├── ssm_model.py               │    │   ├── esp32_traffic_monitor.ino
├── feature_extraction.py      │    │   └── integrated_esp32_server.py ← New!
├── generate_dataset.py        │    │
├── realtime_detector.py       │    ├── checkpoints/
├── config.py                  │    │   ├── best_model.pth ← Used here!
├── checkpoints/               ├────┘   └── normalizer.pkl  ← Used here!
│   ├── best_model.pth         │
│   └── normalizer.pkl         │    Your trained model is used
└── ...                        │    by ESP32 server!
                               │
                               └──> Real-time detection with ESP32 data
```

---

## 📥 Step 1: Install VS Code

### Windows

1. **Download:**
   - Go to https://code.visualstudio.com/
   - Click "Download for Windows"

2. **Install:**
   - Run downloaded `.exe`
   - Accept license
   - ✅ **Important:** Check "Add to PATH"
   - Complete installation

3. **Verify:**
   ```cmd
   # Open Command Prompt
   code --version
   ```

### Mac

```bash
# Using Homebrew (recommended)
brew install --cask visual-studio-code

# Or download from website
# https://code.visualstudio.com/Download
```

### Linux (Ubuntu/Debian)

```bash
# Download and install .deb package
wget -O vscode.deb 'https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64'
sudo dpkg -i vscode.deb
sudo apt-get install -f
```

---

## 🔧 Step 2: Install Python Extension

### Method 1: In VS Code

1. **Open VS Code**

2. **Open Extensions:**
   - Click Extensions icon (left sidebar)
   - Or press `Ctrl+Shift+X` (Windows/Linux)
   - Or press `Cmd+Shift+X` (Mac)

3. **Install Python:**
   - Search: `Python`
   - Find "Python" by Microsoft
   - Click **Install**

4. **Install Pylance:**
   - Search: `Pylance`
   - Find "Pylance" by Microsoft
   - Click **Install**

### Method 2: Quick Install

Press `Ctrl+P` (or `Cmd+P` on Mac), paste:
```
ext install ms-python.python
```

---

## 📂 Step 3: Organize Project Structure

### Open Your Project in VS Code

```bash
# Navigate to your project directory
cd path/to/your/ddos-detection-project

# Open in VS Code
code .
```

### Create ESP32 Integration Folder

In VS Code:

1. **Right-click** in Explorer (left panel)
2. Select **New Folder**
3. Name: `esp32_integration`

### Copy Files

Copy these files into `esp32_integration/`:

```
esp32_integration/
├── esp32_traffic_monitor.ino          ← ESP32 code (from Arduino)
├── integrated_esp32_server.py         ← Integrated server (new)
└── README_ESP32.md                    ← Documentation
```

**Final structure:**

```
your-project/
├── esp32_integration/                 ← NEW FOLDER
│   ├── integrated_esp32_server.py     ← Main server
│   └── esp32_traffic_monitor.ino      ← ESP32 code (reference)
│
├── train_model.py                     ← Your existing files
├── ssm_model.py                       ← Your S5 model class
├── feature_extraction.py              ← Your normalizer
├── config.py
├── generate_dataset.py
│
├── checkpoints/                       ← Your trained model
│   ├── best_model.pth                ← Will be loaded!
│   └── normalizer.pkl                ← Will be loaded!
│
├── outputs/
├── data/
└── requirements.txt
```

---

## 🐍 Step 4: Set Up Python Environment

### Check Python Version

```bash
# Should be Python 3.8 or higher
python --version
# or
python3 --version
```

### Create Virtual Environment (Recommended)

**In VS Code Terminal** (`Ctrl+` ` or View → Terminal):

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

**You should see `(venv)` in terminal prompt**

### Install Dependencies

```bash
# Install required packages
pip install torch numpy

# Or if you have requirements.txt:
pip install -r requirements.txt
```

**Verify installation:**
```bash
python -c "import torch; import numpy; print('OK')"
```

---

## 📝 Step 5: Update Integrated Server Path

### Open `integrated_esp32_server.py`

In VS Code, open: `esp32_integration/integrated_esp32_server.py`

### Find Path Configuration (Line ~20)

```python
# Line 20-22: UPDATE THIS PATH
PROJECT_DIR = Path(__file__).parent.parent  # Goes up one level
sys.path.insert(0, str(PROJECT_DIR))
```

**This should point to YOUR project root.**

### Verify Path is Correct

Add temporary debug print (around line 25):

```python
# Add after PROJECT_DIR definition
print(f"[DEBUG] Project directory: {PROJECT_DIR}")
print(f"[DEBUG] Files in project: {list(PROJECT_DIR.glob('*.py'))}")
```

Run to test:
```bash
python esp32_integration/integrated_esp32_server.py
```

Should print:
```
[DEBUG] Project directory: /path/to/your/project
[DEBUG] Files in project: [train_model.py, ssm_model.py, ...]
```

### If Path is Wrong

**Option 1: Adjust parent levels**
```python
# If server is in esp32_integration folder:
PROJECT_DIR = Path(__file__).parent.parent  # Up 1 level

# If server is in subfolder of esp32_integration:
PROJECT_DIR = Path(__file__).parent.parent.parent  # Up 2 levels
```

**Option 2: Hardcode path**
```python
# Replace with your actual path
PROJECT_DIR = Path("/home/milan/ddos-detection-project")
```

---

## 🔍 Step 6: Verify Model Files Exist

### Check Model File

In VS Code terminal:

```bash
# Check trained model exists
ls -lh checkpoints/best_model.pth
# or Windows:
dir checkpoints\best_model.pth
```

Should show file size (~500KB to 5MB).

### Check Normalizer File

```bash
ls -lh checkpoints/normalizer.pkl
# or Windows:
dir checkpoints\normalizer.pkl
```

### If Files Don't Exist

**You need to train the model first:**

```bash
# Train the S5 model on your dataset
python train_model.py

# This will create:
# - checkpoints/best_model.pth (trained weights)
# - checkpoints/normalizer.pkl (feature normalizer)
```

**Or for testing, the server will run with random weights** (but won't detect accurately).

---

## ⚙️ Step 7: Configure Firewall

### Windows Firewall

**Method 1: GUI**

1. Open: Windows Security → Firewall & network protection
2. Click: "Allow an app through firewall"
3. Click: "Change settings" (requires admin)
4. Click: "Allow another app..."
5. Browse to: `python.exe` in your venv
6. Select both Private and Public
7. Click OK

**Method 2: Command Line (Run as Administrator)**

```cmd
# Open Command Prompt as Admin
# Allow UDP port 5000
netsh advfirewall firewall add rule name="ESP32 DDoS Server" protocol=UDP dir=in localport=5000 action=allow

# Allow Python
netsh advfirewall firewall add rule name="Python ESP32" dir=in action=allow program="C:\path\to\python.exe" enable=yes
```

### Mac Firewall

```bash
# Mac usually allows by default
# If needed, System Preferences → Security & Privacy → Firewall
# Click "Firewall Options" → Add Python → Allow
```

### Linux (Ubuntu/Debian)

```bash
# Allow UDP port 5000
sudo ufw allow 5000/udp

# Or disable firewall for testing
sudo ufw disable
```

---

## 🚀 Step 8: Run Integrated Server

### Open Terminal in VS Code

1. **View → Terminal** or `` Ctrl+` ``
2. Make sure virtual environment is activated `(venv)`

### Navigate to ESP32 Integration Folder

```bash
cd esp32_integration
```

### Run Server

```bash
python integrated_esp32_server.py
```

### Expected Output

```
======================================================================
Loading YOUR Trained S5 DDoS Detection Model
======================================================================
Using device: cpu
[SUCCESS] Initialized YOUR model architecture
[SUCCESS] Loaded trained weights from checkpoint
  Epoch: 50
  Validation Accuracy: 0.9452
Model loaded from: /path/to/checkpoints/best_model.pth
[SUCCESS] Loaded YOUR normalizer from /path/to/checkpoints/normalizer.pkl
======================================================================

======================================================================
ESP32 + Trained S5 Model - Integrated Detection Server
======================================================================
Server: 0.0.0.0:5000
Model: YOUR trained S5 model
Sequence Length: 60
Detection Threshold: 0.8
Device: cpu
======================================================================

[READY] Waiting for ESP32 data...
```

### If You See Warnings

**Warning: "No trained model found"**
```
[WARNING] No trained model found at checkpoints/best_model.pth
[WARNING] Using randomly initialized weights!
```
→ Train your model first with `python train_model.py`

**Warning: "Could not import your model"**
```
[ERROR] Could not import your model: No module named 'ssm_model'
```
→ Check PROJECT_DIR path is correct (Step 5)

---

## 📡 Step 9: Test ESP32 Connection

### With ESP32 Running (from Arduino IDE)

You should see in VS Code terminal:

```
[RECV] ESP32_IoT_Gateway_001 (192.168.1.75)
  Packets: 45.23 pkt/s
  Bytes: 67.89 KB/s
  SYN: 32.00%

======================================================================
[DETECTION] ESP32_IoT_Gateway_001
======================================================================
Attack Probability: 0.1234 (12.34%)
Confidence: 0.8766
Classification: ✓ Normal Traffic
======================================================================
```

### If No Data Received

**Check:**
1. ✅ ESP32 Serial Monitor shows "Data sent to server"
2. ✅ ESP32 and PC on same WiFi
3. ✅ Server IP in ESP32 code matches PC IP
4. ✅ Firewall allows UDP port 5000

**Debug:**
```bash
# On Windows, check if port is listening
netstat -an | findstr 5000

# On Mac/Linux
netstat -an | grep 5000
# or
sudo lsof -i :5000
```

---

## 🧪 Step 10: Test with Simulated Attack

### In ESP32 Code (Arduino IDE)

The code automatically simulates attacks (5% chance).

When attack occurs, ESP32 Serial Monitor shows:
```
[WARNING] Simulating attack traffic!
Packets: 3450 (Rate: 690.00 pkt/s)
```

### In VS Code Terminal

After 60 seconds of attack traffic, you'll see:

```
======================================================================
[DETECTION] ESP32_IoT_Gateway_001
======================================================================
Attack Probability: 0.9456 (94.56%)
Confidence: 0.9456
Classification: 🚨 DDoS ATTACK DETECTED
======================================================================

🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
     ⚠️  DDoS ATTACK DETECTED  ⚠️
🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
Time: 2026-02-18 14:35:22
Device: ESP32_IoT_Gateway_001
Attack Probability: 94.56%
Packet Rate: 690.00 pkt/s
Byte Rate: 1034.50 KB/s
SYN Ratio: 78.90%
Unique IPs: 45
🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
```

---

## 🐛 Debugging in VS Code

### Enable Debug Mode

Add to `integrated_esp32_server.py` (around line 300):

```python
# Add verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Use VS Code Debugger

1. **Open `integrated_esp32_server.py`**

2. **Set Breakpoint:**
   - Click left margin next to line numbers
   - Red dot appears

3. **Start Debugging:**
   - Press `F5`
   - Select "Python File"

4. **Debug Controls:**
   - `F10`: Step over
   - `F11`: Step into
   - `F5`: Continue
   - Variables panel shows current values

### Print Debugging

Add debug prints:

```python
# In run_detection() method
print(f"[DEBUG] Sequence shape: {x.shape}")
print(f"[DEBUG] Model output: {output}")
print(f"[DEBUG] Attack prob: {attack_prob}")
```

---

## 📊 Step 11: View Logs

### Alert Logs

Alerts are saved to `logs/ddos_alerts.log`:

```bash
# View in VS Code
code logs/ddos_alerts.log

# Or in terminal
cat logs/ddos_alerts.log
# Windows:
type logs\ddos_alerts.log
```

**Format:**
```
2026-02-18 14:35:22 | ESP32_IoT_Gateway_001 | Prob: 0.9456 | Rate: 690.00 pkt/s | SYN: 0.7890
```

### Real-time Log Monitoring

**In new VS Code terminal:**

```bash
# Linux/Mac
tail -f logs/ddos_alerts.log

# Windows (PowerShell)
Get-Content logs\ddos_alerts.log -Wait
```

---

## ⚡ Step 12: Running Multiple Components

### Terminal 1: Integrated Server

```bash
cd esp32_integration
python integrated_esp32_server.py
```

### Terminal 2: Monitor Logs

```bash
tail -f logs/ddos_alerts.log
```

### Terminal 3: Additional ESP32 Device (if multiple)

Each ESP32 will send data to same server.

**VS Code has split terminal:**
- Click `+` dropdown → Split Terminal
- Or press `Ctrl+Shift+5`

---

## 🔄 Step 13: Making Changes

### Modify Detection Threshold

In `integrated_esp32_server.py`:

```python
# Line ~33
DETECTION_THRESHOLD = 0.8  # Default

# Change to be more sensitive:
DETECTION_THRESHOLD = 0.5  # Detects more attacks (more false positives)

# Change to be more strict:
DETECTION_THRESHOLD = 0.9  # Only very certain attacks (fewer false positives)
```

### Restart Server

1. Stop server: `Ctrl+C` in terminal
2. Save changes: `Ctrl+S`
3. Restart: `python integrated_esp32_server.py`

### Hot Reload (Advanced)

For development, use:

```bash
# Install watchdog
pip install watchdog

# Run with auto-restart (create run_dev.sh)
while true; do
    python integrated_esp32_server.py
    sleep 2
done
```

---

## 📦 Step 14: Package for Deployment

### Create Requirements File

```bash
# Auto-generate from current environment
pip freeze > requirements_esp32.txt
```

### Create Startup Script

**Windows: `start_server.bat`**
```batch
@echo off
cd esp32_integration
call ..\venv\Scripts\activate
python integrated_esp32_server.py
pause
```

**Linux/Mac: `start_server.sh`**
```bash
#!/bin/bash
cd esp32_integration
source ../venv/bin/activate
python integrated_esp32_server.py
```

Make executable:
```bash
chmod +x start_server.sh
```

---

## 🎯 Step 15: VS Code Tips & Tricks

### Keyboard Shortcuts

```
Toggle Terminal:        Ctrl+`
New Terminal:          Ctrl+Shift+`
Split Terminal:        Ctrl+Shift+5
Find:                  Ctrl+F
Find in Files:         Ctrl+Shift+F
Go to Line:            Ctrl+G
Command Palette:       Ctrl+Shift+P
Format Document:       Shift+Alt+F
Comment Line:          Ctrl+/
```

### Extensions for Python

Install these for better experience:

1. **Python** (Microsoft) - already installed
2. **Pylance** (Microsoft) - already installed
3. **Python Test Explorer** - for testing
4. **autoDocstring** - auto-generate docstrings
5. **Better Comments** - colorful comments

### Workspace Settings

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true,
    "files.autoSave": "afterDelay"
}
```

---

## ✅ Verification Checklist

**Before running integrated system:**

- [ ] VS Code installed and Python extension added
- [ ] Project folder opened in VS Code
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`torch`, `numpy`)
- [ ] `integrated_esp32_server.py` in project
- [ ] PROJECT_DIR path verified
- [ ] Trained model exists in `checkpoints/best_model.pth`
- [ ] Normalizer exists in `checkpoints/normalizer.pkl`
- [ ] Firewall configured for UDP port 5000
- [ ] ESP32 uploaded and running (Arduino IDE)
- [ ] ESP32 connected to same WiFi as PC
- [ ] Server started and listening

**When all checked:**
✅ System ready for real-time DDoS detection!

---

## 🚨 Common Issues

### Issue: Import Error "No module named 'ssm_model'"

**Solution:**
```python
# Check PROJECT_DIR in integrated_esp32_server.py
print(PROJECT_DIR)  # Should show your project root
print(list(PROJECT_DIR.glob('*.py')))  # Should list ssm_model.py

# If not, adjust:
PROJECT_DIR = Path("/full/path/to/your/project")
```

### Issue: "Could not load normalizer"

**Solution:**
Train model first to generate normalizer:
```bash
python train_model.py
```

### Issue: Server starts but no data received

**Solution:**
```bash
# Check ESP32 is sending (Arduino Serial Monitor)
# Check IP address matches
# Check firewall
# Try: sudo ufw disable  (Linux, for testing)
```

### Issue: Virtual environment not activating

**Windows:**
```cmd
# May need to enable scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
venv\Scripts\activate
```

**Linux/Mac:**
```bash
# Make sure script has execute permission
chmod +x venv/bin/activate
source venv/bin/activate
```

---

## 🎓 Next Steps

✅ VS Code setup complete
✅ Integrated server running
✅ Using YOUR trained model
✅ Receiving ESP32 data

**Now you have:**
- Real IoT hardware (ESP32) at edge
- Your trained S5 model running on PC
- Real-time DDoS detection
- Complete integrated system!

---

## 📖 Additional Resources

**VS Code Python:**
- Official Docs: https://code.visualstudio.com/docs/python/python-tutorial
- Debugging: https://code.visualstudio.com/docs/python/debugging

**PyTorch:**
- Docs: https://pytorch.org/docs/
- Tutorials: https://pytorch.org/tutorials/

**Your Project:**
- Check existing README files
- Review training scripts
- Understand model architecture

---

**VS Code integration complete! Your project is now fully integrated with ESP32 hardware.**
