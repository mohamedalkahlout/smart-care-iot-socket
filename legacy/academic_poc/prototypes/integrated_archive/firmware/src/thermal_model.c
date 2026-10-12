#include "thermal_model.h"

void edge_nlms_init(EdgeNLMSModel* model, float learning_rate) {
    if (!model) return;
    model->weight = 1.0f;
    model->learning_rate = learning_rate > 0.0f ? learning_rate : 0.05f;
    model->regularization = 1e-4f;
}

float edge_nlms_predict(const EdgeNLMSModel* model, float current_temp) {
    if (!model) return current_temp;
    return model->weight * current_temp;
}

void edge_nlms_update(EdgeNLMSModel* model, float input_temp, float target_temp) {
    if (!model) return;
    float pred = model->weight * input_temp;
    float error = target_temp - pred;
    float norm = (input_temp * input_temp) + model->regularization;
    model->weight += (model->learning_rate * error * input_temp) / norm;
}
