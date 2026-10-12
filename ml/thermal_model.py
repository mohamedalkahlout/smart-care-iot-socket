"""
Thermal Model Training & Evaluation (P4.1).
Uses Normalized LMS (NLMS) adaptive filter for online estimation of room thermal inertia.
Provides guaranteed numerical stability, O(1) operations, and low memory footprint for microcontrollers.
"""
import csv
import math
import os
import sys
from typing import Dict, List, Tuple


class EdgeThermalModelPy:
    def __init__(self, learning_rate: float = 0.05):
        # theta: [a (retention), b (actuator cooling/heating gain), c (bias/ambient)]
        self.theta = [0.98, -0.05, 0.45]
        self.alpha = learning_rate
        self.last_temp = 22.0
        self.last_state = 0

    def update(self, current_temp: float, current_state: int):
        phi = [self.last_temp, float(self.last_state), 1.0]
        y_hat = phi[0] * self.theta[0] + phi[1] * self.theta[1] + phi[2] * self.theta[2]
        error = current_temp - y_hat

        norm_sq = phi[0] * phi[0] + phi[1] * phi[1] + phi[2] * phi[2] + 1e-4
        step = (self.alpha / norm_sq) * error

        # Gradient update with regularization
        self.theta[0] += step * phi[0]
        self.theta[1] += step * phi[1]
        self.theta[2] += step * phi[2]

        # Keep physical bounds realistic
        self.theta[0] = max(0.85, min(0.999, self.theta[0]))

        self.last_temp = current_temp
        self.last_state = current_state

    def predict(self, current_temp: float, assumed_state: int, steps: int = 1) -> float:
        val = current_temp
        for _ in range(steps):
            val = self.theta[0] * val + self.theta[1] * float(assumed_state) + self.theta[2]
        return val


def evaluate_model_on_dataset(csv_path: str) -> Dict[str, float]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset {csv_path} does not exist.")

    temps: List[float] = []
    states: List[int] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            temps.append(float(row["temp_c"]))
            states.append(1 if row["relay_actual"] == "on" else 0)

    total_samples = len(temps)
    split_idx = int(total_samples * 0.7)  # 70% Train, 30% Test

    model = EdgeThermalModelPy(learning_rate=0.08)

    # Train phase
    for i in range(split_idx):
        model.update(temps[i], states[i])

    # Test phase (horizon = 1 step)
    horizon_steps = 1
    baseline_errors: List[float] = []
    model_errors: List[float] = []

    for i in range(split_idx, total_samples - horizon_steps):
        target = temps[i + horizon_steps]
        current_t = temps[i]
        curr_state = states[i]

        baseline_pred = current_t
        baseline_errors.append(abs(target - baseline_pred))

        model_pred = model.predict(current_t, curr_state, steps=horizon_steps)
        model_errors.append(abs(target - model_pred))

        model.update(current_t, curr_state)

    mae_baseline = sum(baseline_errors) / len(baseline_errors)
    rmse_baseline = math.sqrt(sum(e * e for e in baseline_errors) / len(baseline_errors))

    mae_model = sum(model_errors) / len(model_errors)
    rmse_model = math.sqrt(sum(e * e for e in model_errors) / len(model_errors))

    improvement_pct = ((mae_baseline - mae_model) / mae_baseline) * 100.0

    return {
        "mae_baseline": round(mae_baseline, 4),
        "rmse_baseline": round(rmse_baseline, 4),
        "mae_model": round(mae_model, 4),
        "rmse_model": round(rmse_model, 4),
        "improvement_pct": round(improvement_pct, 1),
        "learned_theta": [round(t, 4) for t in model.theta]
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    csv_file = os.path.join(os.path.dirname(__file__), "..", "simulator", "telemetry_60days.csv")
    metrics = evaluate_model_on_dataset(csv_file)
    print("=" * 60)
    print("[EVAL] Thermal Model Evaluation Results:")
    print(f"  Baseline Persistence: MAE = {metrics['mae_baseline']} C | RMSE = {metrics['rmse_baseline']} C")
    print(f"  Adaptive Edge Model:  MAE = {metrics['mae_model']} C | RMSE = {metrics['rmse_model']} C")
    print(f"  Accuracy Improvement: {metrics['improvement_pct']}%")
    print(f"  Final Parameters:     {metrics['learned_theta']}")
    print("=" * 60)
