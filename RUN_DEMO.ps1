#!/usr/bin/env powershell
# RUN_DEMO.ps1 - Start all components for end-to-end DDoS detection demo

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "ESP32 DDoS Detection - Complete Demo"   -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Colors for output
$InfoColor = "Yellow"
$SuccessColor = "Green"
$ErrorColor = "Red"

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor $InfoColor
python --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found!" -ForegroundColor $ErrorColor
    exit 1
}

# Check required files
Write-Host "Checking required files..." -ForegroundColor $InfoColor
$files = @(
    "integrated_esp32_server.py",
    "esp32_integrated_dashboard.py",
    "traffic_generator.py",
    "scapy_syn_flood.py",
    "data/generated_dataset/sequences.npy"
)

foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        Write-Host "ERROR: Missing file: $file" -ForegroundColor $ErrorColor
        exit 1
    }
}

Write-Host "✅ All files found" -ForegroundColor $SuccessColor
Write-Host ""

# Instructions
Write-Host "SETUP INSTRUCTIONS:" -ForegroundColor $InfoColor
Write-Host "==================" -ForegroundColor $InfoColor
Write-Host ""
Write-Host "1. CONNECT ESP32:"
Write-Host "   - Upload the modified esp32_traffic_monitor.ino sketch to your ESP32"
Write-Host "   - Set your WiFi SSID and password in the sketch"
Write-Host "   - Set your PC's IP as the gateway server IP"
Write-Host "   - Open Serial Monitor (115200 baud) to verify connection"
Write-Host ""

Write-Host "2. NETWORK SETUP:"
Write-Host "   - Both ESP32 and PC must be on the same 2.4GHz WiFi network"
Write-Host "   - Configure firewall to allow UDP port 5000 (Server port)"
Write-Host "   - Find your PC IP with: ipconfig"
Write-Host ""

Write-Host "3. START DEMO (3 Terminals):"
Write-Host ""

Write-Host "   Terminal 1 - START SERVER (Port 5000):" -ForegroundColor $SuccessColor
Write-Host "   python integrated_esp32_server.py --port 5000"
Write-Host ""

Write-Host "   Terminal 2 - GENERATE TRAFFIC:" -ForegroundColor $SuccessColor
Write-Host "   Option A (Replay dataset):"
Write-Host "     python traffic_generator.py --target 192.168.1.75 --port 4000 --seq 0"
Write-Host ""
Write-Host "   Option B (SYN Flood - requires admin):"
Write-Host "     python scapy_syn_flood.py --target 192.168.1.75 --port 80 --rate 500 --duration 10"
Write-Host ""

Write-Host "   Terminal 3 - START DASHBOARD:" -ForegroundColor $SuccessColor
Write-Host "   streamlit run esp32_integrated_dashboard.py"
Write-Host ""

Write-Host "4. WATCH FOR DETECTION:" -ForegroundColor $SuccessColor
Write-Host "   - Dashboard loads http://localhost:8501"
Write-Host "   - Server terminal shows [DETECTION] logs"
Write-Host "   - 🟢 NORMAL or 🔴 ATTACK displayed in dashboard"
Write-Host ""

Write-Host "TROUBLESHOOTING:" -ForegroundColor $InfoColor
Write-Host "===============" -ForegroundColor $InfoColor
Write-Host ""
Write-Host "If port 5000 is in use:"
Write-Host "  - Kill existing process: netstat -ano | findstr :5000"
Write-Host "  - Or specify different port: python integrated_esp32_server.py --port 5001"
Write-Host ""

Write-Host "If ESP32 not connecting:"
Write-Host "  - Check Serial Monitor (Tools → Serial Monitor in Arduino IDE)"
Write-Host "  - Verify WiFi SSID/password match"
Write-Host "  - Check that both are on 2.4GHz band (not 5GHz)"
Write-Host ""

Write-Host "If no detections:"
Write-Host "  - Ensure server is running and listening"
Write-Host "  - Check logs/latest_detection.json is being created"
Write-Host "  - Verify traffic generator is connected to correct ESP32 IP"
Write-Host ""

Write-Host "Ready to go! Open 3 terminals and follow the setup above." -ForegroundColor $SuccessColor
Write-Host ""
