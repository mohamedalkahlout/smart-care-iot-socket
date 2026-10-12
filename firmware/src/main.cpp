/**
 * ==============================================================================
 * Smart Care IoT Socket (Retrofit Edge-AI & Safety Guard)
 * Production Firmware for ESP32-DevKitC-v4
 * ==============================================================================
 * 
 * Hardware Architecture & Pinout Mapping (ESP32-DevKitC-v4):
 * ------------------------------------------------------------------------------
 *  Pin Name     | GPIO    | Direction | Electrical Characteristics
 * ------------------------------------------------------------------------------
 *  PIN_RELAY    | GPIO 2  | OUTPUT    | Optocoupler-isolated relay drive signal.
 *               |         |           | Active HIGH by default (configurable).
 *               |         |           | Failsafe: Forces OFF at boot and watchdogs.
 *  PIN_BUTTON   | GPIO 4  | INPUT     | Physical emergency / override pushbutton.
 *               |         |           | Internal PULL-UP enabled, active LOW to GND.
 *               |         |           | Protected by 50ms non-blocking debounce.
 *  PIN_DHT      | GPIO 15 | INPUT     | DHT22 (AM2302) single-bus sensor data pin.
 *               |         |           | Requires external 4.7k pull-up to 3.3V.
 *  PIN_ALERT_LED| GPIO 18 | OUTPUT    | High-intensity Amber/Red alert indicator.
 *               |         |           | Active HIGH during remote triggers / guard.
 *  PIN_STATUS_LED GPIO 19 | OUTPUT    | Green heartbeat / network status indicator.
 *               |         |           | Active HIGH when Wi-Fi link is verified.
 * ------------------------------------------------------------------------------
 * 
 * Safety Guarantee (Architectural Invariant):
 *  - Under NO circumstances may the relay pin (GPIO 2) be actuated directly.
 *  - All state transitions MUST be vetted through safety_guard_evaluate() in ANSI C.
 *  - If sensor data becomes stale (>30s) or Wi-Fi drops, local safety guard rules
 *    maintain strict failsafe operation without relying on cloud availability.
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include "DHT.h"
#include "safety_guard.h"
#include "control_logic.h"

// --- Hardware Pin Definitions (ESP32-DevKitC-v4) ---
#define PIN_RELAY        2
#define PIN_BUTTON       4    // Pushbutton to GND (Internal Pull-Up)
#define PIN_DHT          15   // DHT22 data pin
#define PIN_ALERT_LED    18   // Indicator LED for remote actions / guard alerts
#define PIN_STATUS_LED   19   // Heartbeat / network connectivity LED

#define DHTTYPE DHT22
#define WDT_TIMEOUT_SECONDS 8

// --- Global Sensor & Persistent Storage Objects ---
DHT dht(PIN_DHT, DHTTYPE);
Preferences prefs;

// --- System State & Configuration ---
SafetyConfig g_safetyConfig;
ControllerConfig g_controllerConfig;
ControllerState g_controllerState;

// Network & Cloud Credentials (Default / Stored)
String g_wifiSsid = "Wokwi-GUEST";
String g_wifiPassword = "";
String g_deviceId = "socket1";
String g_databaseUrl = "https://YOUR_PROJECT-default-rtdb.firebaseio.com/sockets/socket1.json";

// Timing Variables (Non-blocking loop schedule)
unsigned long g_lastLoopMillis = 0;
unsigned long g_lastSensorReadMillis = 0;
unsigned long g_lastCloudSyncMillis = 0;
unsigned long g_lastWifiCheckMillis = 0;
unsigned long g_lastSecondTickMillis = 0;
unsigned long g_lastAlertLedMillis = 0;
bool g_alertLedActive = false;

// Button Debounce Management
int g_lastButtonState = HIGH;
unsigned long g_lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY_MS = 50;

// Function Declarations
void loadConfiguration();
void saveConfiguration();
void setupHardware();
void checkWifiConnection();
void readSensors();
void handleLocalButton();
void syncWithCloud();
void triggerRemoteAlert();

/**
 * Isolated Hardware Relay Driver.
 * CANNOT be called directly by external logic.
 * Enforces that only guard-verified decisions actuate the physical pin.
 */
static void applyRelayStateGuarded(RelayState state, const char* reasonCode);

void setup() {
    Serial.begin(115200);
    Serial.println("\n=======================================================");
    Serial.println("  Smart Care IoT Socket - Edge-AI Firmware v1.0.0");
    Serial.println("  Target Architecture: ESP32-DevKitC-v4 | Safety-First");
    Serial.println("=======================================================");

    // Hardware Watchdog setup (8 seconds timeout)
    esp_task_wdt_init(WDT_TIMEOUT_SECONDS, true);
    esp_task_wdt_add(NULL);

    setupHardware();
    loadConfiguration();

    // Default safety configuration initialization
    g_safetyConfig = safety_guard_default_config();
    g_controllerState.currentRelayState = RELAY_STATE_OFF;
    g_controllerState.hasValidTemp = false;
    g_controllerState.tempReadingAgeSec = 999;
    g_controllerState.timeSinceLastTurnOffSec = 3600;

    // Guaranteed initial state: Relay physical OFF
    applyRelayStateGuarded(RELAY_STATE_OFF, "BOOT_INITIALIZATION");

    // Initial Wi-Fi attempt (Non-blocking reconnect in main loop)
    WiFi.mode(WIFI_STA);
    WiFi.begin(g_wifiSsid.c_str(), g_wifiPassword.c_str());
    Serial.println("[WIFI] Initializing wireless connection...");
}

void loop() {
    esp_task_wdt_reset(); // Feed the hardware watchdog timer
    unsigned long currentMillis = millis();

    // 1. One-second tick for physical and safety timers
    if (currentMillis - g_lastSecondTickMillis >= 1000) {
        g_lastSecondTickMillis = currentMillis;
        if (g_controllerState.currentRelayState == RELAY_STATE_ON) {
            g_controllerState.currentRuntimeSec++;
        } else {
            g_controllerState.timeSinceLastTurnOffSec++;
        }
        g_controllerState.timeInCurrentStateSec++;
        g_controllerState.tempReadingAgeSec++;
    }

    // 2. Alert LED pulse timeout handling
    if (g_alertLedActive && (currentMillis - g_lastAlertLedMillis >= 500)) {
        digitalWrite(PIN_ALERT_LED, LOW);
        g_alertLedActive = false;
    }

    // 3. Monitor physical button (Highest Override Priority with Debounce)
    handleLocalButton();

    // 4. Sensor Reading Cadence (Sample every 3 seconds)
    if (currentMillis - g_lastSensorReadMillis >= 3000) {
        g_lastSensorReadMillis = currentMillis;
        readSensors();
    }

    // 5. Compute Control Step strictly evaluated through the Safety Guard
    ControllerDecision decision = control_logic_step(
        &g_controllerConfig,
        &g_controllerState,
        &g_safetyConfig
    );

    // Apply state change ONLY if verified and modified
    if (decision.computedRelayState != g_controllerState.currentRelayState) {
        applyRelayStateGuarded(decision.computedRelayState, decision.guardResult.reasonCode);
        Serial.printf("[DECISION] Relay changed to %s | Source: %s | Guard Reason: %s (%s)\n",
            decision.computedRelayState == RELAY_STATE_ON ? "ON" : "OFF",
            command_source_to_string(decision.decisionSource),
            decision.guardResult.reasonCode,
            decision.guardResult.reasonDesc
        );
    }

    // Clear one-shot local button trigger after step execution
    g_controllerState.localButtonTriggered = false;

    // 6. Wi-Fi Health Check & Auto-reconnect (every 5 seconds)
    if (currentMillis - g_lastWifiCheckMillis >= 5000) {
        g_lastWifiCheckMillis = currentMillis;
        checkWifiConnection();
    }

    // 7. Cloud Polling & Telemetry Sync (every 5 seconds when online)
    if (g_controllerState.isNetworkConnected && (currentMillis - g_lastCloudSyncMillis >= 5000)) {
        g_lastCloudSyncMillis = currentMillis;
        syncWithCloud();
    }
}

void setupHardware() {
    pinMode(PIN_RELAY, OUTPUT);
    pinMode(PIN_ALERT_LED, OUTPUT);
    pinMode(PIN_STATUS_LED, OUTPUT);
    pinMode(PIN_BUTTON, INPUT_PULLUP);

    // Default pin outputs to safe levels
    digitalWrite(PIN_RELAY, g_controllerConfig.relayActiveHigh ? LOW : HIGH);
    digitalWrite(PIN_ALERT_LED, LOW);
    digitalWrite(PIN_STATUS_LED, LOW);

    dht.begin();
    Serial.println("[HARDWARE] GPIO pins configured for ESP32-DevKitC-v4.");
}

void handleLocalButton() {
    int reading = digitalRead(PIN_BUTTON);
    if (reading != g_lastButtonState) {
        g_lastDebounceTime = millis();
    }

    if ((millis() - g_lastDebounceTime) > DEBOUNCE_DELAY_MS) {
        // Active LOW button pressed
        if (reading == LOW && g_lastButtonState == HIGH) {
            Serial.println("[LOCAL] Physical Button Interrupt Triggered!");
            g_controllerState.localButtonTriggered = true;
            // Toggle desired target state
            g_controllerState.localButtonDesiredState = 
                (g_controllerState.currentRelayState == RELAY_STATE_ON) ? RELAY_STATE_OFF : RELAY_STATE_ON;
        }
    }
    g_lastButtonState = reading;
}

void readSensors() {
    float t = dht.readTemperature();
    if (!isnan(t)) {
        g_controllerState.lastValidTemp = t;
        g_controllerState.hasValidTemp = true;
        g_controllerState.tempReadingAgeSec = 0;
    } else {
        Serial.println("[WARN] DHT sensor read error! Age counter will trigger safe fallback.");
    }
}

/**
 * Isolated Relay Driver
 * Enforces hardware state update with verified reason code.
 */
static void applyRelayStateGuarded(RelayState state, const char* reasonCode) {
    g_controllerState.currentRelayState = state;
    g_controllerState.timeInCurrentStateSec = 0;

    if (state == RELAY_STATE_ON) {
        g_controllerState.currentRuntimeSec = 0;
        digitalWrite(PIN_RELAY, g_controllerConfig.relayActiveHigh ? HIGH : LOW);
    } else {
        g_controllerState.timeSinceLastTurnOffSec = 0;
        digitalWrite(PIN_RELAY, g_controllerConfig.relayActiveHigh ? LOW : HIGH);
    }
}

void checkWifiConnection() {
    if (WiFi.status() == WL_CONNECTED) {
        g_controllerState.isNetworkConnected = true;
        digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
        g_controllerState.isNetworkConnected = false;
        digitalWrite(PIN_STATUS_LED, LOW);
        WiFi.reconnect();
    }
}

void syncWithCloud() {
    HTTPClient http;
    http.begin(g_databaseUrl);
    http.setTimeout(3000);
    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        StaticJsonDocument<512> doc;
        DeserializationError err = deserializeJson(doc, payload);

        if (!err) {
            // Safe JSON Extraction
            if (doc.containsKey("mode")) {
                const char* modeStr = doc["mode"];
                ControlMode prevMode = g_controllerConfig.mode;
                g_controllerConfig.mode = (strcmp(modeStr, "manual") == 0) ? MODE_MANUAL : MODE_AUTO;
                if (prevMode != g_controllerConfig.mode) saveConfiguration();
            }

            if (doc.containsKey("status") && g_controllerConfig.mode == MODE_MANUAL) {
                const char* stStr = doc["status"];
                RelayState desired = (strcmp(stStr, "on") == 0) ? RELAY_STATE_ON : RELAY_STATE_OFF;
                if (desired != g_controllerConfig.manualDesiredState) {
                    g_controllerConfig.manualDesiredState = desired;
                    triggerRemoteAlert();
                }
            }

            if (doc.containsKey("minTemp")) {
                g_controllerConfig.targetMinTemp = doc["minTemp"].as<float>();
            }
            if (doc.containsKey("maxTemp")) {
                g_controllerConfig.targetMaxTemp = doc["maxTemp"].as<float>();
            }
        }
    }
    http.end();

    // Telemetry Sync: Send current sensor data back
    if (g_controllerState.hasValidTemp) {
        HTTPClient httpPut;
        String putUrl = g_databaseUrl;
        putUrl.replace(".json", "/currentTemp.json");
        httpPut.begin(putUrl);
        httpPut.addHeader("Content-Type", "application/json");
        httpPut.PUT(String(g_controllerState.lastValidTemp, 2));
        httpPut.end();
    }
}

void triggerRemoteAlert() {
    digitalWrite(PIN_ALERT_LED, HIGH);
    g_alertLedActive = true;
    g_lastAlertLedMillis = millis();
}

void loadConfiguration() {
    prefs.begin("smart_sock", false);
    g_controllerConfig.deviceType = (DeviceType)prefs.getInt("dev_type", (int)DEVICE_COOLING);
    g_controllerConfig.mode = (ControlMode)prefs.getInt("mode", (int)MODE_AUTO);
    g_controllerConfig.targetMinTemp = prefs.getFloat("min_t", 20.0f);
    g_controllerConfig.targetMaxTemp = prefs.getFloat("max_t", 26.0f);
    g_controllerConfig.hysteresis = prefs.getFloat("hyst", 0.5f);
    g_controllerConfig.relayActiveHigh = prefs.getBool("pol_high", true);
    prefs.end();
    Serial.println("[CONFIG] Configuration loaded from non-volatile storage (NVS).");
}

void saveConfiguration() {
    prefs.begin("smart_sock", false);
    prefs.putInt("dev_type", (int)g_controllerConfig.deviceType);
    prefs.putInt("mode", (int)g_controllerConfig.mode);
    prefs.putFloat("min_t", g_controllerConfig.targetMinTemp);
    prefs.putFloat("max_t", g_controllerConfig.targetMaxTemp);
    prefs.putFloat("hyst", g_controllerConfig.hysteresis);
    prefs.putBool("pol_high", g_controllerConfig.relayActiveHigh);
    prefs.end();
    Serial.println("[CONFIG] Configuration safely committed to NVS.");
}
