#include "safety_guard.h"

SafetyConfig safety_guard_default_config(void) {
    SafetyConfig cfg;
    cfg.absoluteMinTemp = 5.0f;
    cfg.absoluteMaxTemp = 45.0f;
    cfg.heatingCutoffTemp = 35.0f;
    cfg.coolingCutoffTemp = 10.0f;
    cfg.sensorMaxAgeSec = 30;
    cfg.maxRuntimeHeatingSec = 1800;     // 30 mins
    cfg.maxRuntimeCoolingSec = 14400;    // 4 hours
    cfg.maxRuntimeCompressorSec = 7200;  // 2 hours
    cfg.maxRuntimeGenericSec = 7200;
    cfg.compressorMinOffSec = 180;       // 3 mins anti-short-cycle
    cfg.compressorMinOnSec = 120;        // 2 mins minimum run
    cfg.maxRemoteHeatingTimerSec = 1800; // max 30 mins remote heater run
    return cfg;
}

GuardResult safety_guard_evaluate(const GuardInput* in, const SafetyConfig* cfg) {
    GuardResult res;
    res.allowedState = in->requestedState;
    res.modified = false;
    res.reasonCode = "ALLOWED";
    res.reasonDesc = "Requested state complies with all safety rules";

    // Rule 1: Turning OFF is always permitted immediately regardless of source
    if (in->requestedState == RELAY_STATE_OFF) {
        // Exception check: for compressor, if shutting down while running < minOnSec
        // we still permit it for user emergency off, but note it
        res.allowedState = RELAY_STATE_OFF;
        res.modified = false;
        res.reasonCode = "SHUTDOWN_PERMITTED";
        res.reasonDesc = "Turn off request granted";
        return res;
    }

    // --- Beyond this point, requestedState is RELAY_STATE_ON ---

    // Rule 2: Absolute Max Overheat Limit
    if (in->hasTempReading && in->currentTemp >= cfg->absoluteMaxTemp) {
        res.allowedState = RELAY_STATE_OFF;
        res.modified = true;
        res.reasonCode = "ABSOLUTE_OVERHEAT";
        res.reasonDesc = "Temperature exceeds absolute maximum threshold (45 C)";
        return res;
    }

    // Rule 3: Heating Device Safety Cutoff
    if (in->deviceType == DEVICE_HEATING && in->hasTempReading && in->currentTemp >= cfg->heatingCutoffTemp) {
        res.allowedState = RELAY_STATE_OFF;
        res.modified = true;
        res.reasonCode = "HEATER_HIGH_TEMP_CUTOFF";
        res.reasonDesc = "Room temperature exceeds safe heating limit (35 C)";
        return res;
    }

    // Rule 4: Cooling Device Overfreeze Cutoff
    if (in->deviceType == DEVICE_COOLING && in->hasTempReading && in->currentTemp <= cfg->coolingCutoffTemp) {
        res.allowedState = RELAY_STATE_OFF;
        res.modified = true;
        res.reasonCode = "COOLER_LOW_TEMP_CUTOFF";
        res.reasonDesc = "Room temperature below safe cooling limit (10 C)";
        return res;
    }

    // Rule 5: Sensor Stale / Missing Reading Check
    if (!in->hasTempReading || in->tempReadingAgeSec > cfg->sensorMaxAgeSec) {
        if (in->deviceType == DEVICE_HEATING) {
            // Heaters MUST turn OFF when sensor fails
            res.allowedState = RELAY_STATE_OFF;
            res.modified = true;
            res.reasonCode = "SENSOR_STALE_HEATER_SHUTDOWN";
            res.reasonDesc = "Sensor reading stale/missing; heater forced OFF for fire safety";
            return res;
        } else if (in->deviceType == DEVICE_COOLING) {
            res.allowedState = RELAY_STATE_OFF;
            res.modified = true;
            res.reasonCode = "SENSOR_STALE_COOLER_SHUTDOWN";
            res.reasonDesc = "Sensor reading stale/missing; cooler forced OFF";
            return res;
        } else if (in->deviceType == DEVICE_COMPRESSOR) {
            // Refrigerator default fail-safe is ON to prevent food spoilage,
            // provided anti-short-cycle allows it
            if (in->currentRelayState == RELAY_STATE_OFF && in->timeSinceLastTurnOffSec < cfg->compressorMinOffSec) {
                res.allowedState = RELAY_STATE_OFF;
                res.modified = true;
                res.reasonCode = "COMPRESSOR_ANTICYCLE_WAIT";
                res.reasonDesc = "Sensor stale but compressor must satisfy minimum OFF time";
                return res;
            }
            res.allowedState = RELAY_STATE_ON;
            res.modified = (in->requestedState != RELAY_STATE_ON);
            res.reasonCode = "SENSOR_STALE_FRIDGE_PRESERVE";
            res.reasonDesc = "Sensor reading stale; refrigerator kept ON to protect perishables";
            return res;
        }
    }

    // Rule 6: Compressor Anti-Short-Cycle Protection
    if (in->deviceType == DEVICE_COMPRESSOR) {
        if (in->currentRelayState == RELAY_STATE_OFF && in->timeSinceLastTurnOffSec < cfg->compressorMinOffSec) {
            res.allowedState = RELAY_STATE_OFF;
            res.modified = true;
            res.reasonCode = "COMPRESSOR_SHORT_CYCLE_PREVENTED";
            res.reasonDesc = "Compressor off-duration less than 180s; delayed to prevent motor stall";
            return res;
        }
    }

    // Rule 7: Maximum Continuous Runtime
    if (in->currentRelayState == RELAY_STATE_ON) {
        uint32_t limit = cfg->maxRuntimeGenericSec;
        if (in->deviceType == DEVICE_HEATING) limit = cfg->maxRuntimeHeatingSec;
        else if (in->deviceType == DEVICE_COOLING) limit = cfg->maxRuntimeCoolingSec;
        else if (in->deviceType == DEVICE_COMPRESSOR) limit = cfg->maxRuntimeCompressorSec;

        if (in->currentRuntimeSec >= limit) {
            res.allowedState = RELAY_STATE_OFF;
            res.modified = true;
            res.reasonCode = "MAX_RUNTIME_EXCEEDED";
            res.reasonDesc = "Maximum continuous operational runtime exceeded; auto forced cooldown";
            return res;
        }
    }

    // Rule 8: Remote Heating Mandates Auto-Off Timer
    if (in->deviceType == DEVICE_HEATING && in->source == CMD_REMOTE) {
        if (in->remoteHeatingTimerSec == 0 || in->remoteHeatingTimerSec > cfg->maxRemoteHeatingTimerSec) {
            res.allowedState = RELAY_STATE_OFF;
            res.modified = true;
            res.reasonCode = "REMOTE_HEATING_TIMER_REQUIRED";
            res.reasonDesc = "Remote heater activation requires positive timeout <= 30 mins";
            return res;
        }
    }

    return res;
}

const char* device_type_to_string(DeviceType type) {
    switch (type) {
        case DEVICE_COOLING: return "cooling";
        case DEVICE_HEATING: return "heating";
        case DEVICE_COMPRESSOR: return "compressor";
        case DEVICE_GENERIC: return "generic";
        default: return "unknown";
    }
}

const char* command_source_to_string(CommandSource source) {
    switch (source) {
        case CMD_LOCAL_BUTTON: return "local_button";
        case CMD_REMOTE: return "remote";
        case CMD_AUTO_RULE: return "auto_rule";
        case CMD_AI: return "ai";
        case CMD_SCHEDULE: return "schedule";
        case CMD_GUARD: return "guard";
        default: return "unknown";
    }
}
