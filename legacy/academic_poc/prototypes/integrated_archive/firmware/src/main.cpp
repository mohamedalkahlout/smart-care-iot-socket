#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Preferences.h>

#include "config.h"
#include "safety_guard.h"
#include "control_logic.h"
#include "thermal_model.h"

// Hardware instances
DHT dht(DHTPIN, DHTTYPE);
Preferences prefs;

// Channel pins array
const uint8_t RELAY_PINS[CHANNEL_COUNT] = {
    RELAY_SOCKET1_PIN,
    RELAY_SOCKET2_PIN,
    RELAY_SOCKET3_PIN,
    RELAY_SOCKET4_PIN
};

// Global system state
MultiSocketSafetyConfig g_safety_config;
ChannelTelemetry g_telemetry[CHANNEL_COUNT];
ControlMode g_modes[CHANNEL_COUNT] = {MODE_AUTO, MODE_MANUAL, MODE_MANUAL, MODE_AUTO};
float g_min_temps[CHANNEL_COUNT] = {20.0f, 0.0f, 0.0f, 22.0f};
float g_max_temps[CHANNEL_COUNT] = {28.0f, 0.0f, 0.0f, 26.0f};

float g_current_temp = 25.0f;
bool g_sensor_valid = false;
unsigned long g_last_sensor_read = 0;
unsigned long g_last_cloud_poll = 0;
unsigned long g_last_heartbeat = 0;
bool g_emergency_button_latched = false;

// HTTP Helper Functions
String httpGet(const String& url) {
    if (WiFi.status() != WL_CONNECTED) return "{}";
    HTTPClient http;
    http.begin(url);
    http.setTimeout(3000);
    int code = http.GET();
    String payload = "{}";
    if (code == 200) {
        payload = http.getString();
    }
    http.end();
    return payload;
}

bool httpPut(const String& url, const String& jsonPayload) {
    if (WiFi.status() != WL_CONNECTED) return false;
    HTTPClient http;
    http.begin(url);
    http.setTimeout(3000);
    http.addHeader("Content-Type", "application/json");
    int code = http.PUT(jsonPayload);
    http.end();
    return code == 200 || code == 204;
}

void applyRelayOutput(SocketChannel ch, DeviceState state) {
    digitalWrite(RELAY_PINS[ch], state == STATE_ON ? HIGH : LOW);
    g_telemetry[ch].current_state = state;
}

void emergencyStopAll(const char* reason) {
    Serial.printf("🚨 [EMERGENCY STOP] %s -> Cutting all 4 relays immediately!\n", reason);
    g_safety_config.master_emergency_shutdown = true;
    for (int i = 0; i < CHANNEL_COUNT; i++) {
        applyRelayOutput((SocketChannel)i, STATE_OFF);
        g_telemetry[i].requested_state = STATE_OFF;
    }
    digitalWrite(LED_STATUS_PIN, HIGH); // Alert LED ON
}

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println("\n==================================================");
    Serial.println("  SmartCare Hub: Multi-Channel IoT Safety Strip");
    Serial.println("  Unified Production Firmware - mohamednael-467e0");
    Serial.println("==================================================");

    // Initialize Pins
    for (int i = 0; i < CHANNEL_COUNT; i++) {
        pinMode(RELAY_PINS[i], OUTPUT);
        digitalWrite(RELAY_PINS[i], LOW);
    }
    pinMode(BUTTON_EMERGENCY_PIN, INPUT_PULLUP);
    pinMode(LED_STATUS_PIN, OUTPUT);
    digitalWrite(LED_STATUS_PIN, LOW);

    dht.begin();
    g_safety_config = safety_guard_default_config();

    // Initialize channel telemetries
    for (int i = 0; i < CHANNEL_COUNT; i++) {
        g_telemetry[i].channel = (SocketChannel)i;
        g_telemetry[i].current_state = STATE_OFF;
        g_telemetry[i].requested_state = STATE_OFF;
        g_telemetry[i].continuous_on_seconds = 0;
        g_telemetry[i].time_since_last_off_seconds = 600;
        g_telemetry[i].time_since_last_on_seconds = 600;
        g_telemetry[i].sensor_age_seconds = 0;
    }
    g_telemetry[0].appliance_type = APPLIANCE_HEATER;
    g_telemetry[1].appliance_type = APPLIANCE_WATER_PUMP;
    g_telemetry[2].appliance_type = APPLIANCE_TV;
    g_telemetry[3].appliance_type = APPLIANCE_AC;

    // Connect WiFi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID_DEFAULT, WIFI_PASS_DEFAULT);
    Serial.print("Connecting to WiFi");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 25) {
        delay(300);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n✅ WiFi Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n⚠️ WiFi Timeout - Running in Resilient Local Offline Mode.");
    }
}

void loop() {
    unsigned long now = millis();

    // 1. Read Physical Emergency Push Button (Active LOW)
    if (digitalRead(BUTTON_EMERGENCY_PIN) == LOW) {
        if (!g_emergency_button_latched) {
            g_emergency_button_latched = true;
            emergencyStopAll("Physical Emergency Pushbutton Pressed");
            httpPut("https://mohamednael-467e0-default-rtdb.firebaseio.com/system/emergencyShutdown.json", "true");
        }
    }

    // 2. Periodic Sensor Read (every 2000 ms)
    if (now - g_last_sensor_read >= SENSOR_READ_INTERVAL_MS) {
        g_last_sensor_read = now;
        float t = dht.readTemperature();
        if (!isnan(t)) {
            g_current_temp = t;
            g_sensor_valid = true;
            for (int i = 0; i < CHANNEL_COUNT; i++) {
                g_telemetry[i].current_temperature = g_current_temp;
                g_telemetry[i].is_temperature_valid = true;
                g_telemetry[i].sensor_age_seconds = 0;
            }
        } else {
            g_sensor_valid = false;
            for (int i = 0; i < CHANNEL_COUNT; i++) {
                g_telemetry[i].is_temperature_valid = false;
                g_telemetry[i].sensor_age_seconds += 2;
            }
            Serial.println("⚠️ DHT22 read failure!");
        }
    }

    // 3. Periodic Cloud Poll (every 1500 ms)
    if (now - g_last_cloud_poll >= POLLING_INTERVAL_MS && WiFi.status() == WL_CONNECTED) {
        g_last_cloud_poll = now;

        // Fetch sockets JSON
        String payload = httpGet(FIREBASE_SOCKETS_PATH);
        if (payload.length() > 10) {
            StaticJsonDocument<1536> doc;
            DeserializationError err = deserializeJson(doc, payload);
            if (!err) {
                // Parse Socket 1 (Thermal)
                if (doc.containsKey("socket1")) {
                    JsonObject s1 = doc["socket1"];
                    const char* st = s1["status"] | "off";
                    const char* md = s1["mode"] | "auto";
                    g_modes[0] = (strcmp(md, "auto") == 0) ? MODE_AUTO : MODE_MANUAL;
                    g_min_temps[0] = s1["minTemp"] | 20.0f;
                    g_max_temps[0] = s1["maxTemp"] | 28.0f;
                    if (g_modes[0] == MODE_MANUAL) {
                        g_telemetry[0].requested_state = (strcmp(st, "on") == 0) ? STATE_ON : STATE_OFF;
                    }
                }
                // Parse Socket 2 (Water Pump)
                if (doc.containsKey("socket2")) {
                    JsonObject s2 = doc["socket2"];
                    const char* st = s2["status"] | "off";
                    const char* md = s2["mode"] | "manual";
                    g_modes[1] = (strcmp(md, "auto") == 0) ? MODE_AUTO : MODE_MANUAL;
                    g_telemetry[1].requested_state = (strcmp(st, "on") == 0) ? STATE_ON : STATE_OFF;
                }
                // Parse Socket 3 (TV / Workstation)
                if (doc.containsKey("socket3")) {
                    JsonObject s3 = doc["socket3"];
                    const char* st = s3["status"] | "off";
                    g_telemetry[2].requested_state = (strcmp(st, "on") == 0) ? STATE_ON : STATE_OFF;
                }
                // Parse Socket 4 (AC)
                if (doc.containsKey("socket4")) {
                    JsonObject s4 = doc["socket4"];
                    const char* st = s4["status"] | "off";
                    const char* md = s4["mode"] | "auto";
                    g_modes[3] = (strcmp(md, "auto") == 0) ? MODE_AUTO : MODE_MANUAL;
                    g_min_temps[3] = s4["minTemp"] | 22.0f;
                    g_max_temps[3] = s4["maxTemp"] | 26.0f;
                    if (g_modes[3] == MODE_MANUAL) {
                        g_telemetry[3].requested_state = (strcmp(st, "on") == 0) ? STATE_ON : STATE_OFF;
                    }
                }
            }
        }

        // Check master emergency shutdown flag
        String sysPayload = httpGet(FIREBASE_SYSTEM_PATH);
        if (sysPayload.indexOf("\"emergencyShutdown\":true") >= 0) {
            if (!g_safety_config.master_emergency_shutdown) {
                emergencyStopAll("Cloud Remote Emergency Command");
            }
        }
    }

    // 4. Compute Autonomous Automation for Auto Sockets
    if (!g_safety_config.master_emergency_shutdown && g_sensor_valid) {
        // Socket 1 Automation (Heating hysteresis)
        if (g_modes[0] == MODE_AUTO) {
            g_telemetry[0].requested_state = compute_thermal_hysteresis_state(
                g_current_temp, g_min_temps[0], g_max_temps[0], 0.5f,
                g_telemetry[0].current_state, false
            );
        }
        // Socket 4 Automation (Cooling AC hysteresis)
        if (g_modes[3] == MODE_AUTO) {
            g_telemetry[3].requested_state = compute_thermal_hysteresis_state(
                g_current_temp, g_min_temps[3], g_max_temps[3], 0.5f,
                g_telemetry[3].current_state, true
            );
        }
    }

    // 5. Evaluate Safety Guard for Each Channel and Enforce
    for (int i = 0; i < CHANNEL_COUNT; i++) {
        SafetyDecision decision = safety_guard_evaluate_channel(&g_telemetry[i], &g_safety_config);
        DeviceState final_state = decision.enforced_state;

        if (final_state != g_telemetry[i].current_state) {
            applyRelayOutput((SocketChannel)i, final_state);
            Serial.printf("🔌 Channel %d -> %s (Reason: %s)\n", 
                i + 1, final_state == STATE_ON ? "ON" : "OFF", decision.reason_code);

            // Sync state change to Firebase
            if (WiFi.status() == WL_CONNECTED) {
                char path[128];
                snprintf(path, sizeof(path), "https://mohamednael-467e0-default-rtdb.firebaseio.com/sockets/socket%d/status.json", i + 1);
                httpPut(path, final_state == STATE_ON ? "\"on\"" : "\"off\"");
                snprintf(path, sizeof(path), "https://mohamednael-467e0-default-rtdb.firebaseio.com/sockets/socket%d/lastSafetyReason.json", i + 1);
                String reasonJson = "\"" + String(decision.reason_code) + "\"";
                httpPut(path, reasonJson);
            }
        }

        // Update runtime counters
        if (g_telemetry[i].current_state == STATE_ON) {
            g_telemetry[i].continuous_on_seconds += 1;
            g_telemetry[i].time_since_last_on_seconds = 0;
            g_telemetry[i].time_since_last_off_seconds += 1;
        } else {
            g_telemetry[i].continuous_on_seconds = 0;
            g_telemetry[i].time_since_last_off_seconds += 1;
            g_telemetry[i].time_since_last_on_seconds += 1;
        }
    }

    // 6. Periodic Heartbeat and Temperature Telemetry Push (every 5 seconds)
    if (now - g_last_heartbeat >= 5000 && WiFi.status() == WL_CONNECTED) {
        g_last_heartbeat = now;
        httpPut("https://mohamednael-467e0-default-rtdb.firebaseio.com/sockets/socket1/currentTemp.json", String(g_current_temp, 1));
        httpPut("https://mohamednael-467e0-default-rtdb.firebaseio.com/system/uptimeSeconds.json", String(now / 1000));
        httpPut("https://mohamednael-467e0-default-rtdb.firebaseio.com/system/wifiConnected.json", "true");
    }

    delay(200); // 200ms loop tick
}
