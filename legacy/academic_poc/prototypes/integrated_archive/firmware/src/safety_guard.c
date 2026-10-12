#include "safety_guard.h"

MultiSocketSafetyConfig safety_guard_default_config(void) {
    MultiSocketSafetyConfig config;
    config.absolute_overheat_c          = 45.0f;
    config.max_room_temp_c              = 38.0f;
    config.min_freeze_temp_c            = 2.0f;
    config.max_heater_runtime_sec       = 7200;  // 2 hours
    config.compressor_anti_short_sec    = 180;   // 3 minutes
    config.max_pump_runtime_sec         = 1200;  // 20 minutes
    config.pump_cooldown_sec            = 300;   // 5 minutes
    config.max_tv_runtime_sec           = 14400; // 4 hours
    config.sensor_timeout_sec           = 60;    // 60 seconds
    config.master_emergency_shutdown    = false;
    return config;
}

SafetyDecision safety_guard_evaluate_channel(
    const ChannelTelemetry* telemetry,
    const MultiSocketSafetyConfig* config
) {
    SafetyDecision decision;
    decision.allowed = true;
    decision.enforced_state = telemetry->requested_state;
    decision.reason_code = "COMMAND_ALLOWED";

    if (!telemetry || !config) {
        decision.allowed = false;
        decision.enforced_state = STATE_OFF;
        decision.reason_code = "NULL_POINTER_REJECT";
        return decision;
    }

    // Rule 0: Master Emergency Shutdown
    if (config->master_emergency_shutdown) {
        decision.allowed = (telemetry->requested_state == STATE_OFF);
        decision.enforced_state = STATE_OFF;
        decision.reason_code = "EMERGENCY_SHUTDOWN_ACTIVE";
        return decision;
    }

    // Rule 1: Immediate OFF is always permitted without constraint
    if (telemetry->requested_state == STATE_OFF) {
        decision.allowed = true;
        decision.enforced_state = STATE_OFF;
        decision.reason_code = "IMMEDIATE_OFF_PERMITTED";
        return decision;
    }

    // --- The following rules apply when requested_state == STATE_ON ---

    // Rule 2: Absolute Overheat Protection
    if (telemetry->is_temperature_valid && telemetry->current_temperature >= config->absolute_overheat_c) {
        decision.allowed = false;
        decision.enforced_state = STATE_OFF;
        decision.reason_code = "ABSOLUTE_OVERHEAT_CUTOFF";
        return decision;
    }

    // Rule 3: Channel 1 / Heater Continuous Runtime Ceiling
    if (telemetry->appliance_type == APPLIANCE_HEATER) {
        if (telemetry->current_state == STATE_ON && telemetry->continuous_on_seconds >= config->max_heater_runtime_sec) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "MAX_CONTINUOUS_RUNTIME_EXCEEDED";
            return decision;
        }
        if (telemetry->is_temperature_valid && telemetry->current_temperature >= config->max_room_temp_c) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "HEATING_HIGH_ROOM_CUTOFF";
            return decision;
        }
    }

    // Rule 4: Sensor Stale Fail-Safe for Thermal Channels
    if (telemetry->appliance_type == APPLIANCE_HEATER || 
        telemetry->appliance_type == APPLIANCE_COOLER || 
        telemetry->appliance_type == APPLIANCE_FRIDGE || 
        telemetry->appliance_type == APPLIANCE_AC) {
        
        if (!telemetry->is_temperature_valid || telemetry->sensor_age_seconds > config->sensor_timeout_sec) {
            if (telemetry->appliance_type == APPLIANCE_HEATER) {
                decision.allowed = false;
                decision.enforced_state = STATE_OFF;
                decision.reason_code = "SENSOR_STALE_HEATER_CUTOFF";
                return decision;
            }
            if (telemetry->appliance_type == APPLIANCE_FRIDGE) {
                decision.allowed = true;
                decision.enforced_state = STATE_ON;
                decision.reason_code = "SENSOR_STALE_FRIDGE_FAILSAFE";
                return decision;
            }
        }
    }

    // Rule 5: Compressor Anti-Short-Cycle Protection (Fridge / AC)
    if (telemetry->appliance_type == APPLIANCE_FRIDGE || telemetry->appliance_type == APPLIANCE_AC) {
        if (telemetry->current_state == STATE_OFF && 
            telemetry->time_since_last_off_seconds < config->compressor_anti_short_sec) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "COMPRESSOR_ANTI_SHORT_CYCLE_WAIT";
            return decision;
        }
    }

    // Rule 6: Channel 2 (Water Pump) Maximum Runtime Limit
    if (telemetry->appliance_type == APPLIANCE_WATER_PUMP) {
        if (telemetry->current_state == STATE_ON && telemetry->continuous_on_seconds >= config->max_pump_runtime_sec) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "PUMP_MAX_RUNTIME_EXCEEDED";
            return decision;
        }
        // Rule 7: Water Pump Cooldown Window
        if (telemetry->current_state == STATE_OFF && telemetry->time_since_last_off_seconds < config->pump_cooldown_sec) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "PUMP_COOLDOWN_ACTIVE";
            return decision;
        }
    }

    // Rule 8: Channel 3 (TV / Workstation) Auto Standby Cutoff
    if (telemetry->appliance_type == APPLIANCE_TV) {
        if (telemetry->current_state == STATE_ON && telemetry->continuous_on_seconds >= config->max_tv_runtime_sec) {
            decision.allowed = false;
            decision.enforced_state = STATE_OFF;
            decision.reason_code = "APPLIANCE_AUTO_OFF_TIMER";
            return decision;
        }
    }

    return decision;
}
