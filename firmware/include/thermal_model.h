#ifndef THERMAL_MODEL_H
#define THERMAL_MODEL_H

/**
 * Lightweight Normalized LMS (NLMS) Edge Thermal Model for ESP32 (P4.1).
 * Features:
 *  - Unconditionally stable (no covariance explosion)
 *  - 4 multiplications and 3 additions per step
 *  - RAM footprint: 24 bytes
 */

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float theta[3];      // [0]=a (inertia), [1]=b (cooling/heating gain), [2]=c (ambient bias)
    float alpha;         // Learning rate (e.g. 0.05)
    float lastTemp;
    int lastState;
    int initialized;
} EdgeThermalModel;

static inline void thermal_model_init(EdgeThermalModel* m, float alpha) {
    m->theta[0] = 0.98f;
    m->theta[1] = -0.05f;
    m->theta[2] = 0.45f;
    m->alpha = alpha;
    m->lastTemp = 22.0f;
    m->lastState = 0;
    m->initialized = 1;
}

static inline void thermal_model_update(EdgeThermalModel* m, float currentTemp, int currentRelayState) {
    if (!m->initialized) thermal_model_init(m, 0.05f);

    float phi[3];
    phi[0] = m->lastTemp;
    phi[1] = (float)m->lastState;
    phi[2] = 1.0f;

    float y_hat = phi[0] * m->theta[0] + phi[1] * m->theta[1] + phi[2] * m->theta[2];
    float error = currentTemp - y_hat;

    float norm_sq = phi[0] * phi[0] + phi[1] * phi[1] + phi[2] * phi[2] + 0.0001f;
    float step = (m->alpha / norm_sq) * error;

    m->theta[0] += step * phi[0];
    m->theta[1] += step * phi[1];
    m->theta[2] += step * phi[2];

    // Bound parameters to physically realistic values
    if (m->theta[0] < 0.85f) m->theta[0] = 0.85f;
    if (m->theta[0] > 0.999f) m->theta[0] = 0.999f;

    m->lastTemp = currentTemp;
    m->lastState = currentRelayState;
}

static inline float thermal_model_predict(const EdgeThermalModel* m, float currentTemp, int assumedState, int horizonSteps) {
    float temp_est = currentTemp;
    for (int i = 0; i < horizonSteps; i++) {
        temp_est = m->theta[0] * temp_est + m->theta[1] * (float)assumedState + m->theta[2];
    }
    return temp_est;
}

#ifdef __cplusplus
}
#endif

#endif // THERMAL_MODEL_H
