#ifndef CONTROL_LOGIC_H
#define CONTROL_LOGIC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "safety_guard.h"

typedef enum {
    MODE_MANUAL = 0,
    MODE_AUTO   = 1
} ControlMode;

typedef struct {
    ControlMode mode;
    float setpoint_min_c;
    float setpoint_max_c;
    float hysteresis_c;
    DeviceState current_state;
} ChannelController;

DeviceState compute_thermal_hysteresis_state(
    float current_temp,
    float min_temp,
    float max_temp,
    float hysteresis,
    DeviceState current_state,
    bool is_cooling
);

#ifdef __cplusplus
}
#endif

#endif // CONTROL_LOGIC_H
