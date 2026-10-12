#ifndef CONTROL_LOGIC_H
#define CONTROL_LOGIC_H

#include "safety_guard.h"
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MODE_MANUAL = 0,
    MODE_AUTO = 1
} ControlMode;

typedef struct {
    DeviceType deviceType;
    ControlMode mode;
    float targetMinTemp;
    float targetMaxTemp;
    float hysteresis;
    bool relayActiveHigh;
    RelayState manualDesiredState;
    uint32_t remoteHeatingTimerSec;
} ControllerConfig;

typedef struct {
    RelayState currentRelayState;
    uint32_t timeInCurrentStateSec;
    uint32_t currentRuntimeSec;
    uint32_t timeSinceLastTurnOffSec;
    float lastValidTemp;
    bool hasValidTemp;
    uint32_t tempReadingAgeSec;
    bool isNetworkConnected;
    bool localButtonTriggered;
    RelayState localButtonDesiredState;
} ControllerState;

typedef struct {
    RelayState computedRelayState;
    CommandSource decisionSource;
    GuardResult guardResult;
} ControllerDecision;

// Initialize default controller configurations
ControllerConfig control_logic_default_config(DeviceType type);

// Compute state decision without blocking, calling safety guard
ControllerDecision control_logic_step(
    const ControllerConfig* cfg,
    const ControllerState* state,
    const SafetyConfig* safetyCfg
);

#ifdef __cplusplus
}
#endif

#endif // CONTROL_LOGIC_H
