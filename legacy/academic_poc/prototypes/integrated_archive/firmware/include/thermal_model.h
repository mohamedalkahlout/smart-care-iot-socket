#ifndef THERMAL_MODEL_H
#define THERMAL_MODEL_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    float weight;
    float learning_rate;
    float regularization;
} EdgeNLMSModel;

void edge_nlms_init(EdgeNLMSModel* model, float learning_rate);
float edge_nlms_predict(const EdgeNLMSModel* model, float current_temp);
void edge_nlms_update(EdgeNLMSModel* model, float input_temp, float target_temp);

#ifdef __cplusplus
}
#endif

#endif // THERMAL_MODEL_H
