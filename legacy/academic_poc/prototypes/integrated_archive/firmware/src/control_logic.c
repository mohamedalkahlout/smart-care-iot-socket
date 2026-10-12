#include "control_logic.h"

DeviceState compute_thermal_hysteresis_state(
    float current_temp,
    float min_temp,
    float max_temp,
    float hysteresis,
    DeviceState current_state,
    bool is_cooling
) {
    if (is_cooling) {
        // Cooling device (AC or Refrigerator):
        // Turns ON when temp rises ABOVE (max_temp + hysteresis)
        // Turns OFF when temp drops BELOW (min_temp - hysteresis)
        if (current_temp >= (max_temp + hysteresis)) {
            return STATE_ON;
        } else if (current_temp <= (min_temp - hysteresis)) {
            return STATE_OFF;
        }
        return current_state; // Retain state in deadband
    } else {
        // Heating device:
        // Turns ON when temp drops BELOW (min_temp - hysteresis)
        // Turns OFF when temp rises ABOVE (max_temp + hysteresis)
        if (current_temp <= (min_temp - hysteresis)) {
            return STATE_ON;
        } else if (current_temp >= (max_temp + hysteresis)) {
            return STATE_OFF;
        }
        return current_state; // Retain state in deadband
    }
}
