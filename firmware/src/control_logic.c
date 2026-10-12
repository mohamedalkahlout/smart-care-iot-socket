#include "control_logic.h"

ControllerConfig control_logic_default_config(DeviceType type) {
    ControllerConfig cfg;
    cfg.deviceType = type;
    cfg.mode = MODE_AUTO;
    cfg.hysteresis = 0.5f;
    cfg.relayActiveHigh = true;
    cfg.manualDesiredState = RELAY_STATE_OFF;
    cfg.remoteHeatingTimerSec = 0;

    switch (type) {
        case DEVICE_COOLING:
            cfg.targetMinTemp = 20.0f;
            cfg.targetMaxTemp = 26.0f;
            break;
        case DEVICE_HEATING:
            cfg.targetMinTemp = 19.0f;
            cfg.targetMaxTemp = 23.0f;
            break;
        case DEVICE_COMPRESSOR:
            cfg.targetMinTemp = 2.0f;
            cfg.targetMaxTemp = 6.0f; // Refrigerator bounds
            cfg.hysteresis = 1.0f;
            break;
        case DEVICE_GENERIC:
        default:
            cfg.targetMinTemp = 20.0f;
            cfg.targetMaxTemp = 28.0f;
            break;
    }
    return cfg;
}

ControllerDecision control_logic_step(
    const ControllerConfig* cfg,
    const ControllerState* state,
    const SafetyConfig* safetyCfg
) {
    ControllerDecision decision;
    RelayState requestedState = state->currentRelayState;
    CommandSource source = CMD_AUTO_RULE;

    // 1. High priority: Local physical button override
    if (state->localButtonTriggered) {
        requestedState = state->localButtonDesiredState;
        source = CMD_LOCAL_BUTTON;
    }
    // 2. Manual mode: apply manual request
    else if (cfg->mode == MODE_MANUAL) {
        requestedState = cfg->manualDesiredState;
        source = CMD_REMOTE;
    }
    // 3. Auto mode: apply device-specific thermal hysteresis rules
    else {
        source = CMD_AUTO_RULE;
        if (!state->hasValidTemp) {
            // No valid temperature: request safe default for evaluation
            requestedState = (cfg->deviceType == DEVICE_COMPRESSOR) ? RELAY_STATE_ON : RELAY_STATE_OFF;
        } else {
            float t = state->lastValidTemp;
            float h = cfg->hysteresis;

            switch (cfg->deviceType) {
                case DEVICE_COOLING:
                    // Cooling: ON if T > maxTemp, OFF if T < (maxTemp - h)
                    if (t > cfg->targetMaxTemp) {
                        requestedState = RELAY_STATE_ON;
                    } else if (t < (cfg->targetMaxTemp - h)) {
                        requestedState = RELAY_STATE_OFF;
                    }
                    break;

                case DEVICE_HEATING:
                    // Heating: ON if T < minTemp, OFF if T > (minTemp + h)
                    if (t < cfg->targetMinTemp) {
                        requestedState = RELAY_STATE_ON;
                    } else if (t > (cfg->targetMinTemp + h)) {
                        requestedState = RELAY_STATE_OFF;
                    }
                    break;

                case DEVICE_COMPRESSOR:
                    // Compressor (e.g. Fridge): ON when T > targetMaxTemp, OFF when T < targetMinTemp
                    if (t > cfg->targetMaxTemp) {
                        requestedState = RELAY_STATE_ON;
                    } else if (t < cfg->targetMinTemp) {
                        requestedState = RELAY_STATE_OFF;
                    }
                    break;

                case DEVICE_GENERIC:
                default:
                    // Generic bounded zone
                    if (t < cfg->targetMinTemp) {
                        requestedState = RELAY_STATE_OFF;
                    } else if (t > cfg->targetMaxTemp) {
                        requestedState = RELAY_STATE_ON;
                    }
                    break;
            }
        }
    }

    // 4. Feed request strictly through Safety Guard
    GuardInput guardIn;
    guardIn.requestedState = requestedState;
    guardIn.source = source;
    guardIn.deviceType = cfg->deviceType;
    guardIn.currentTemp = state->lastValidTemp;
    guardIn.hasTempReading = state->hasValidTemp;
    guardIn.tempReadingAgeSec = state->tempReadingAgeSec;
    guardIn.currentRelayState = state->currentRelayState;
    guardIn.currentRuntimeSec = state->currentRuntimeSec;
    guardIn.timeSinceLastTurnOffSec = state->timeSinceLastTurnOffSec;
    guardIn.remoteHeatingTimerSec = cfg->remoteHeatingTimerSec;

    decision.guardResult = safety_guard_evaluate(&guardIn, safetyCfg);
    decision.computedRelayState = decision.guardResult.allowedState;
    decision.decisionSource = decision.guardResult.modified ? CMD_GUARD : source;

    return decision;
}
