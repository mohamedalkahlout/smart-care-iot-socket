#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#include <stdbool.h>

// ==========================================
// 1. Hardware Pinout (ESP32 DevKit v4)
// ==========================================
#define RELAY_SOCKET1_PIN     2    // Socket 1: Thermal Appliance (Heater/Cooler)
#define RELAY_SOCKET2_PIN    18    // Socket 2: Water Pump Motor
#define RELAY_SOCKET3_PIN    19    // Socket 3: TV / Entertainment Workstation
#define RELAY_SOCKET4_PIN    21    // Socket 4: AC / Inductive Compressor
#define DHTPIN               15    // Temperature & Humidity Sensor
#define DHTTYPE              DHT22
#define BUTTON_EMERGENCY_PIN  4    // Master Physical Emergency All-Off Button
#define LED_STATUS_PIN       13    // System Status Indicator LED

// ==========================================
// 2. Network & Cloud Credentials (Unified)
// ==========================================
#define WIFI_SSID_DEFAULT     "Wokwi-GUEST"
#define WIFI_PASS_DEFAULT     ""
#define FIREBASE_HOST         "https://mohamednael-467e0-default-rtdb.firebaseio.com"
#define FIREBASE_SOCKETS_PATH "https://mohamednael-467e0-default-rtdb.firebaseio.com/sockets.json"
#define FIREBASE_SYSTEM_PATH  "https://mohamednael-467e0-default-rtdb.firebaseio.com/system.json"

// ==========================================
// 3. System Timings & Constants
// ==========================================
#define POLLING_INTERVAL_MS   1500
#define SENSOR_READ_INTERVAL_MS 2000
#define HEARTBEAT_INTERVAL_MS 10000

#endif // CONFIG_H
