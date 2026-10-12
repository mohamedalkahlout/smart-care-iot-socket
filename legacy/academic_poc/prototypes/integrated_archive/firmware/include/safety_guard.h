#ifndef SAFETY_GUARD_H
#define SAFETY_GUARD_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    CHANNEL_1_THERMAL   = 0,
    CHANNEL_2_PUMP      = 1,
    CHANNEL_3_APPLIANCE = 2,
    CHANNEL_4_AC        = 3,
    CHANNEL_COUNT       = 4
} SocketChannel;

typedef enum {
    STATE_OFF = 0,
    STATE_ON  = 1
} DeviceState;

typedef enum {
    APPLIANCE_HEATER     = 0,
    APPLIANCE_COOLER     = 1,
    APPLIANCE_FRIDGE     = 2,
    APPLIANCE_WATER_PUMP = 3,
    APPLIANCE_TV         = 4,
    APPLIANCE_AC         = 5
} ApplianceType;

typedef enum {
    CMD_LOCAL_PHYSICAL = 0,
    CMD_REMOTE_CLOUD   = 1,
    CMD_AUTOMATION     = 2
} CommandSource;

typedef struct {
    float absolute_overheat_c;          // Cutoff for thermal room/heater (45.0 C)
    float max_room_temp_c;              // High cutoff (38.0 C)
    float min_freeze_temp_c;            // Freeze limit (2.0 C)
    uint32_t max_heater_runtime_sec;    // 7200s (2 hrs)
    uint32_t compressor_anti_short_sec; // 180s (3 mins)
    uint32_t max_pump_runtime_sec;      // 1200s (20 mins)
    uint32_t pump_cooldown_sec;         // 300s (5 mins)
    uint32_t max_tv_runtime_sec;        // 14400s (4 hrs)
    uint32_t sensor_timeout_sec;        // 60s
    bool master_emergency_shutdown;     // System-wide emergency stop
} MultiSocketSafetyConfig;

typedef struct {
    SocketChannel channel;
    DeviceState current_state;
    DeviceState requested_state;
    ApplianceType appliance_type;
    CommandSource source;
    float current_temperature;
    bool is_temperature_valid;
    uint32_t sensor_age_seconds;
    uint32_t continuous_on_seconds;
    uint32_t time_since_last_off_seconds;
    uint32_t time_since_last_on_seconds;
} ChannelTelemetry;

typedef struct {
    bool allowed;
    DeviceState enforced_state;
    const char* reason_code;
} SafetyDecision;

// Default configuration initialization
MultiSocketSafetyConfig safety_guard_default_config(void);

// Core safety evaluation function
SafetyDecision safety_guard_evaluate_channel(
    const ChannelTelemetry* telemetry,
    const MultiSocketSafetyConfig* config
);

#ifdef __cplusplus
}
#endif

#endif // SAFETY_GUARD_H
