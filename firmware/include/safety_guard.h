#ifndef SAFETY_GUARD_H
#define SAFETY_GUARD_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    DEVICE_COOLING = 0,
    DEVICE_HEATING = 1,
    DEVICE_COMPRESSOR = 2,
    DEVICE_GENERIC = 3
} DeviceType;

typedef enum {
    CMD_LOCAL_BUTTON = 0,
    CMD_REMOTE = 1,
    CMD_AUTO_RULE = 2,
    CMD_AI = 3,
    CMD_SCHEDULE = 4,
    CMD_GUARD = 5
} CommandSource;

typedef enum {
    RELAY_STATE_OFF = 0,
    RELAY_STATE_ON = 1
} RelayState;

typedef struct {
    float absoluteMinTemp;             // e.g. 5.0 C
    float absoluteMaxTemp;             // e.g. 45.0 C
    float heatingCutoffTemp;           // e.g. 35.0 C
    float coolingCutoffTemp;           // e.g. 10.0 C
    uint32_t sensorMaxAgeSec;          // e.g. 30 sec
    uint32_t maxRuntimeHeatingSec;     // e.g. 1800 sec (30 min)
    uint32_t maxRuntimeCoolingSec;     // e.g. 14400 sec (4 hr)
    uint32_t maxRuntimeCompressorSec;  // e.g. 7200 sec (2 hr)
    uint32_t maxRuntimeGenericSec;     // e.g. 7200 sec
    uint32_t compressorMinOffSec;      // e.g. 180 sec (3 min)
    uint32_t compressorMinOnSec;       // e.g. 120 sec (2 min)
    uint32_t maxRemoteHeatingTimerSec; // e.g. 1800 sec
} SafetyConfig;

typedef struct {
    RelayState requestedState;
    CommandSource source;
    DeviceType deviceType;
    float currentTemp;
    bool hasTempReading;
    uint32_t tempReadingAgeSec;
    RelayState currentRelayState;
    uint32_t currentRuntimeSec;
    uint32_t timeSinceLastTurnOffSec;
    uint32_t remoteHeatingTimerSec;
} GuardInput;

typedef struct {
    RelayState allowedState;
    bool modified;
    const char* reasonCode;
    const char* reasonDesc;
} GuardResult;

// Returns default safety configurations
SafetyConfig safety_guard_default_config(void);

// Evaluates requested command against safety rules
GuardResult safety_guard_evaluate(const GuardInput* input, const SafetyConfig* config);

// Helper to get string name of device type
const char* device_type_to_string(DeviceType type);

// Helper to get string name of command source
const char* command_source_to_string(CommandSource source);

#ifdef __cplusplus
}
#endif

#endif // SAFETY_GUARD_H
