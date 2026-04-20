/*
 * ESP32 IoT Edge DDoS Traffic Monitor
 * 
 * Real-time traffic feature extraction for distributed DDoS detection
 * Extracts 8-dimensional features and sends to gateway server via UDP
 * 
 * Hardware: ESP32-DevKitC V4 (520KB SRAM, 240MHz, WiFi)
 * 
 * Features Extracted:
 * 1. Packet Rate (packets/sec)
 * 2. Byte Rate (KB/sec)
 * 3. Average Packet Size (bytes)
 * 4. Packet Size Std Dev (bytes)
 * 5. SYN Ratio (TCP SYN packets / Total TCP packets)
 * 6. Unique Source IPs
 * 7. Unique Destination Ports
 * 8. Protocol Entropy (TCP/UDP/ICMP distribution)
 * 
 * Authors: Milan Joshy, Keirolona Safana Seles
 * Institution: Karunya Institute of Technology and Sciences
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include "esp_wifi.h"

// ============================================================================
// CONFIGURATION - CHANGE THESE VALUES
// ============================================================================

// WiFi Credentials (2.4 GHz ONLY - ESP32 doesn't support 5GHz)
const char* ssid = "Realme";           // Your WiFi network name
const char* password = "123456789";   // Your WiFi password

// Gateway Server Configuration
const char* serverIP = "10.89.30.229";        // Your PC's IP address
const int serverPort = 5000;                   // Gateway UDP port

// Incoming traffic listener (traffic generator -> ESP32)
const int GENERATOR_PORT = 4000;               // UDP port to receive generated traffic

// Promiscuous/sniffer configuration
const bool ENABLE_PROMISCUOUS = true;           // Set true to enable WiFi promiscuous packet capture
const int PROMISCUOUS_MIN_PKT_SIZE = 40;       // minimum payload bytes to consider

// Device Identification
const char* deviceID = "ESP32_Edge_001";       // Unique ID for this device

// Monitoring Configuration
// Send every 4 seconds to match server timing (5 packets = detection)
const int SEND_INTERVAL_MS = 4000;             // Send data every 4 seconds
const int MONITOR_WINDOW_MS = 4000;            // Collect stats per 4-second window

// Hash Table Configuration
const int MAX_UNIQUE_IPS = 50;                 // Track up to 50 unique source IPs
const int MAX_UNIQUE_PORTS = 50;               // Track up to 50 unique destination ports

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

WiFiUDP udp;
unsigned long lastSendTime = 0;
unsigned long windowStartTime = 0;
bool incomingSeen = false;

// Traffic Statistics (per window)
struct TrafficStats {
  uint32_t packetCount;
  uint32_t byteCount;
  uint32_t synCount;
  uint32_t tcpCount;
  uint32_t udpCount;
  uint32_t icmpCount;
  
  // Hash tables for unique tracking (simple linear search)
  uint32_t uniqueIPs[MAX_UNIQUE_IPS];
  int uniqueIPCount;
  uint16_t uniquePorts[MAX_UNIQUE_PORTS];
  int uniquePortCount;
  
  // For average packet size calculation
  uint32_t totalPacketSize;
} stats;

// Aggregated stats (over SEND_INTERVAL_MS)
struct AggregatedStats {
  float packetRate;      // packets per second
  float byteRate;        // KB per second
  float avgPacketSize;   // average packet size in bytes
  float packetSizeStd;   // standard deviation (simplified to 0 for now)
  float synRatio;        // SYN packets / TCP packets
  int uniqueIPs;         // count of unique source IPs
  int uniquePorts;       // count of unique destination ports
  float protocolEntropy; // entropy of protocol distribution
} aggStats;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Print startup banner
  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("ESP32 IoT Edge DDoS Traffic Monitor");
  Serial.println("========================================");
  Serial.println("Device: ESP32-DevKitC V4");
  Serial.println("Features: 8D traffic characteristics");
  Serial.println("Project: Real-Time DDoS Detection");
  Serial.println("========================================\n");
  
  // Initialize stats
  resetStats();
  
  // Connect to WiFi
  connectToWiFi();
  
  // Initialize UDP listener for incoming generated traffic
  udp.begin(GENERATOR_PORT);

  // Optionally enable promiscuous sniffing (needs ESP32 Arduino core)
  if (ENABLE_PROMISCUOUS) {
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_promiscuous_rx_cb(&wifi_promiscuous_cb);
    Serial.println("[INFO] Promiscuous mode enabled: listening for raw packets");
  }
  
  // Ready
  Serial.println("\n========================================");
  Serial.println("[READY] Monitoring started...");
  Serial.printf("Sending data to: %s:%d\n", serverIP, serverPort);
  Serial.printf("Send interval: %d ms\n", SEND_INTERVAL_MS);
  Serial.println("========================================\n");
  
  windowStartTime = millis();
  lastSendTime = millis();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  unsigned long currentTime = millis();
  
  // First, handle incoming packets from traffic generator
  handleIncomingTraffic();

  // Simulate traffic monitoring only when no incoming packets seen
  if (!incomingSeen) {
    simulateTrafficCapture();
  }
  
  // Check if window completed
  if (currentTime - windowStartTime >= MONITOR_WINDOW_MS) {
    // Window complete - stats are ready
    windowStartTime = currentTime;
    
    // Check if time to send data
    if (currentTime - lastSendTime >= SEND_INTERVAL_MS) {
      // Calculate aggregated statistics
      calculateAggregatedStats();
      
      // Send to gateway
      sendDataToGateway();
      
      // Print to serial
      printStats();
      
      // Reset for next interval
      resetStats();
      lastSendTime = currentTime;
    }
  }
  
  delay(10); // Small delay to prevent watchdog timeout
}

// ============================================================================
// WIFI CONNECTION
// ============================================================================

void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[SUCCESS] WiFi Connected!");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal Strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("[FAILED] WiFi Connection Failed!");
    Serial.println("Check SSID/Password and try again");
    Serial.println("Continuing anyway for demonstration...");
  }
}

// ============================================================================
// TRAFFIC SIMULATION (Replace with actual packet capture in production)
// ============================================================================

void simulateTrafficCapture() {
  // In real implementation, this would capture actual network packets
  // For now, we simulate realistic traffic patterns
  
  // Simulate 10-100 packets per window
  int packetsThisWindow = random(10, 100);
  
  for (int i = 0; i < packetsThisWindow; i++) {
    // Simulate packet
    uint16_t packetSize = random(40, 1500);  // Typical packet sizes
    uint32_t srcIP = random(1000000, 9999999); // Simplified IP simulation
    uint16_t dstPort = random(1, 65535);
    int protocol = random(0, 3); // 0=TCP, 1=UDP, 2=ICMP
    bool isSYN = (protocol == 0 && random(0, 100) < 30); // 30% of TCP are SYN
    
    // Update stats
    stats.packetCount++;
    stats.byteCount += packetSize;
    stats.totalPacketSize += packetSize;
    
    // Protocol counts
    if (protocol == 0) {
      stats.tcpCount++;
      if (isSYN) stats.synCount++;
    } else if (protocol == 1) {
      stats.udpCount++;
    } else {
      stats.icmpCount++;
    }
    
    // Track unique IPs (simplified hash table)
    addUniqueIP(srcIP);
    
    // Track unique ports
    addUniquePort(dstPort);
  }
}

// ============================================================================
// HASH TABLES FOR UNIQUE TRACKING
// ============================================================================

void addUniqueIP(uint32_t ip) {
  // Check if IP already exists
  for (int i = 0; i < stats.uniqueIPCount; i++) {
    if (stats.uniqueIPs[i] == ip) {
      return; // Already exists
    }
  }
  
  // Add new IP if space available
  if (stats.uniqueIPCount < MAX_UNIQUE_IPS) {
    stats.uniqueIPs[stats.uniqueIPCount++] = ip;
  }
}

void addUniquePort(uint16_t port) {
  // Check if port already exists
  for (int i = 0; i < stats.uniquePortCount; i++) {
    if (stats.uniquePorts[i] == port) {
      return; // Already exists
    }
  }
  
  // Add new port if space available
  if (stats.uniquePortCount < MAX_UNIQUE_PORTS) {
    stats.uniquePorts[stats.uniquePortCount++] = port;
  }
}

// ============================================================================
// STATISTICS CALCULATION
// ============================================================================

void calculateAggregatedStats() {
  // Calculate rates (per second)
  float timeWindowSec = SEND_INTERVAL_MS / 1000.0;
  
  aggStats.packetRate = stats.packetCount / timeWindowSec;
  aggStats.byteRate = (stats.byteCount / 1024.0) / timeWindowSec; // KB/s
  
  // Average packet size
  if (stats.packetCount > 0) {
    aggStats.avgPacketSize = (float)stats.totalPacketSize / stats.packetCount;
  } else {
    aggStats.avgPacketSize = 0;
  }
  
  // Packet size std dev (simplified to 0 for now - would need to track all sizes)
  aggStats.packetSizeStd = 0;
  
  // SYN ratio
  if (stats.tcpCount > 0) {
    aggStats.synRatio = (float)stats.synCount / stats.tcpCount;
  } else {
    aggStats.synRatio = 0;
  }
  
  // Unique counts
  aggStats.uniqueIPs = stats.uniqueIPCount;
  aggStats.uniquePorts = stats.uniquePortCount;
  
  // Protocol entropy
  aggStats.protocolEntropy = calculateProtocolEntropy();
}

float calculateProtocolEntropy() {
  // Calculate Shannon entropy of protocol distribution
  uint32_t total = stats.tcpCount + stats.udpCount + stats.icmpCount;
  
  if (total == 0) return 0;
  
  float entropy = 0;
  
  if (stats.tcpCount > 0) {
    float p = (float)stats.tcpCount / total;
    entropy -= p * log(p) / log(2);
  }
  
  if (stats.udpCount > 0) {
    float p = (float)stats.udpCount / total;
    entropy -= p * log(p) / log(2);
  }
  
  if (stats.icmpCount > 0) {
    float p = (float)stats.icmpCount / total;
    entropy -= p * log(p) / log(2);
  }
  
  return entropy;
}

// ============================================================================
// HANDLE INCOMING TRAFFIC FROM GENERATOR
// ============================================================================

void handleIncomingTraffic() {
  int packetSize = udp.parsePacket();
  while (packetSize > 0) {
    // Read packet into buffer (limited size)
    const int BUF_SIZE = 512;
    static uint8_t buf[BUF_SIZE];
    int len = udp.read(buf, BUF_SIZE);
    if (len > 0) {
      // Treat each UDP packet as one packet event
      stats.packetCount++;
      stats.byteCount += len;
      stats.udpCount++;
      stats.totalPacketSize += len;

      // Try to extract source IP and dest port from UDP (if available)
      IPAddress remoteIP = udp.remoteIP();
      uint16_t remotePort = udp.remotePort();
      uint32_t ipInt = ((uint32_t)remoteIP[0] << 24) | ((uint32_t)remoteIP[1] << 16) | ((uint32_t)remoteIP[2] << 8) | (uint32_t)remoteIP[3];
      addUniqueIP(ipInt);
      addUniquePort(remotePort);

      incomingSeen = true;
    }
    packetSize = udp.parsePacket();
  }
}

// ============================================================================
// PROMISCUOUS MODE CALLBACK
// ============================================================================

extern "C" {
  void wifi_promiscuous_cb(void* buf, wifi_promiscuous_pkt_type_t type) {
    if (type != WIFI_PKT_MGMT && type != WIFI_PKT_DATA && type != WIFI_PKT_CTRL) {
      return;
    }

    const wifi_promiscuous_pkt_t *ppkt = (wifi_promiscuous_pkt_t *)buf;
    const uint8_t *payload = ppkt->payload;

    // Try to find Ethernet/IP ethertype marker (0x08 0x00) in payload
    int max_search = 128; // limit search to first bytes
    int found = -1;
    for (int i = 0; i + 1 < max_search; i++) {
      if (payload[i] == 0x08 && payload[i+1] == 0x00) { found = i; break; }
    }
    if (found < 0) return;

    const uint8_t *ip_ptr = payload + found + 2; // point to IP header

    // Basic checks: need at least IP header (20 bytes)
    uint8_t ver_ihl = ip_ptr[0];
    uint8_t ihl = (ver_ihl & 0x0F) * 4;
    if (ihl < 20) return;

    uint8_t proto = ip_ptr[9];
    const uint8_t *src_ip = ip_ptr + 12;

    // Only handle TCP
    if (proto != 6) return;

    const uint8_t *tcp_ptr = ip_ptr + ihl;

    // Read source/destination ports (network byte order)
    uint16_t dst_port = (tcp_ptr[2] << 8) | tcp_ptr[3];

    uint8_t tcp_flags = tcp_ptr[13];
    bool is_syn = (tcp_flags & 0x02) != 0;

    // Convert src_ip to uint32
    uint32_t ipInt = ((uint32_t)src_ip[0] << 24) | ((uint32_t)src_ip[1] << 16) | ((uint32_t)src_ip[2] << 8) | (uint32_t)src_ip[3];

    // Update stats
    stats.packetCount++;
    stats.tcpCount++;
    if (is_syn) stats.synCount++;
    addUniqueIP(ipInt);
    addUniquePort(dst_port);
    stats.totalPacketSize += 60; // approximate
  }
}

// ============================================================================
// SEND DATA TO GATEWAY
// ============================================================================

void sendDataToGateway() {
  // Create JSON document
  StaticJsonDocument<512> doc;
  
  doc["device_id"] = deviceID;
  doc["timestamp"] = millis();
  
  // 8-dimensional feature vector
  doc["packet_rate"] = aggStats.packetRate;
  doc["byte_rate"] = aggStats.byteRate;
  doc["avg_packet_size"] = aggStats.avgPacketSize;
  doc["packet_size_std"] = aggStats.packetSizeStd;
  doc["syn_ratio"] = aggStats.synRatio;
  doc["unique_src_ips"] = aggStats.uniqueIPs;
  doc["unique_dst_ports"] = aggStats.uniquePorts;
  doc["protocol_entropy"] = aggStats.protocolEntropy;
  
  // Additional info for debugging
  doc["tcp_count"] = stats.tcpCount;
  doc["udp_count"] = stats.udpCount;
  doc["icmp_count"] = stats.icmpCount;
  
  // Serialize to string
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send via UDP
  if (WiFi.status() == WL_CONNECTED) {
    udp.beginPacket(serverIP, serverPort);
    udp.print(jsonString);
    udp.endPacket();
  }
}

// ============================================================================
// SERIAL MONITORING OUTPUT
// ============================================================================

void printStats() {
  Serial.println("\n--- Traffic Statistics ---");
  Serial.printf("Time: %lu ms\n", millis());
  Serial.printf("Packets: %d (Rate: %.2f pkt/s)\n", 
                stats.packetCount, aggStats.packetRate);
  Serial.printf("Bytes: %d (Rate: %.2f KB/s)\n", 
                stats.byteCount, aggStats.byteRate);
  Serial.printf("Avg Size: %.2f bytes\n", aggStats.avgPacketSize);
  Serial.printf("SYN Count: %d (Ratio: %.2f%%)\n", 
                stats.synCount, aggStats.synRatio * 100);
  Serial.printf("Unique IPs: %d | Unique Ports: %d\n", 
                aggStats.uniqueIPs, aggStats.uniquePorts);
  Serial.printf("TCP: %d | UDP: %d | ICMP: %d\n", 
                stats.tcpCount, stats.udpCount, stats.icmpCount);
  Serial.printf("Protocol Entropy: %.3f bits\n", aggStats.protocolEntropy);
  Serial.printf("Data sent to server: %s:%d\n", serverIP, serverPort);
  Serial.println("==========================\n");
}

// ============================================================================
// RESET STATISTICS
// ============================================================================

void resetStats() {
  stats.packetCount = 0;
  stats.byteCount = 0;
  stats.synCount = 0;
  stats.tcpCount = 0;
  stats.udpCount = 0;
  stats.icmpCount = 0;
  stats.uniqueIPCount = 0;
  stats.uniquePortCount = 0;
  stats.totalPacketSize = 0;
  
  // Clear hash tables
  memset(stats.uniqueIPs, 0, sizeof(stats.uniqueIPs));
  memset(stats.uniquePorts, 0, sizeof(stats.uniquePorts));
}

// ============================================================================
// END OF CODE
// ============================================================================
