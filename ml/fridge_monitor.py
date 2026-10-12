"""
Refrigerator Profile & Anomaly Detection (P4.3).
Monitors:
 1. Door open detection via thermal slope (dT/dt)
 2. Compressor cycle anomaly (excessive duty ratio / cycle duration)
 3. Food safety expiration timer post-blackout
Evaluates Precision, Recall, and False Alarm Rate on injected anomaly events.
"""
import math
from typing import Dict, List, Optional, Tuple


class RefrigeratorMonitor:
    def __init__(
        self,
        normal_temp_min: float = 2.0,
        normal_temp_max: float = 5.5,
        door_open_slope_threshold: float = 0.08,  # C / minute
        max_safe_blackout_hours: float = 4.0,
    ):
        self.temp_min = normal_temp_min
        self.temp_max = normal_temp_max
        self.door_slope_threshold = door_open_slope_threshold
        self.max_blackout_hours = max_safe_blackout_hours

        self.last_temp: Optional[float] = None
        self.blackout_start_time: Optional[float] = None
        self.cycle_duty_history: List[float] = []

    def check_door_open(self, current_temp: float, dt_mins: float = 2.0) -> bool:
        if self.last_temp is None:
            self.last_temp = current_temp
            return False

        dT_dt = (current_temp - self.last_temp) / dt_mins
        self.last_temp = current_temp
        # If rising faster than normal insulation leakage -> door left open
        return dT_dt >= self.door_slope_threshold

    def check_cycle_anomaly(self, duty_ratio: float) -> Tuple[bool, str]:
        # Duty ratio = compressor_on_time / total_cycle_time
        # Normal fridge duty cycle is between 0.3 and 0.6
        if duty_ratio > 0.85:
            return True, "EXCESSIVE_DUTY_CYCLE_LEAK_OR_FAIL"
        elif duty_ratio < 0.10:
            return True, "ABNORMALLY_LOW_DUTY_STALL"
        return False, "NORMAL"

    def food_safety_status(self, current_temp: float, hours_since_blackout: float) -> Tuple[str, float]:
        # CDC / FDA guidelines: Food remains safe up to 4 hours in a closed fridge
        # If temp exceeds 8 C, danger zone timer begins
        if hours_since_blackout > self.max_blackout_hours or current_temp > 8.0:
            return "PERISHABLE_SPOILAGE_RISK", 0.0
        remaining_hours = max(0.0, self.max_blackout_hours - hours_since_blackout)
        return "SAFE", round(remaining_hours, 1)


def benchmark_fridge_anomalies() -> Dict[str, float]:
    monitor = RefrigeratorMonitor()

    # Generate synthetic fridge test stream (100 events: 20 anomalous, 80 normal)
    # NOTE: This is a purely synthetic baseline with high contrast and zero noise.
    true_anomalies = [0] * 80 + [1] * 20
    detected_anomalies = []

    for idx, is_anomaly in enumerate(true_anomalies):
        if is_anomaly:
            # Simulated open door rapid rise
            temp_prev = 4.0
            temp_curr = 4.3  # slope = 0.15 C/min
        else:
            temp_prev = 4.0
            temp_curr = 4.05  # slope = 0.025 C/min

        monitor.last_temp = temp_prev
        detected = 1 if monitor.check_door_open(temp_curr, dt_mins=2.0) else 0
        detected_anomalies.append(detected)

    tp = sum(1 for t, d in zip(true_anomalies, detected_anomalies) if t == 1 and d == 1)
    fp = sum(1 for t, d in zip(true_anomalies, detected_anomalies) if t == 0 and d == 1)
    fn = sum(1 for t, d in zip(true_anomalies, detected_anomalies) if t == 1 and d == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "false_alarm_rate_pct": round((fp / 80) * 100.0, 1),
    }


def stress_test_fridge_anomalies(seed: int = 42) -> Dict[str, any]:
    """
    Stress-test the detector under realistic adverse conditions:
      1. High sensor measurement noise (sigma = 0.08 C).
      2. Subtle door cracks / gasket leaks (slope = 0.035 to 0.065 C/min, below 0.08 threshold).
      3. Unseen anomaly types (slow thermal drift, duty cycle drift = 0.72).
    """
    import random
    rng = random.Random(seed)
    monitor = RefrigeratorMonitor()

    # 1. Subtle Door Ajar with High Noise (50 subtle leak events)
    # True label = 1, but slope is subtle (mean 0.05 C/min) with noise sigma=0.08
    subtle_detected = 0
    subtle_total = 50
    for _ in range(subtle_total):
        # Temp rise over 2 mins: 0.10 C (slope 0.05 C/min)
        noise_prev = rng.gauss(0.0, 0.08)
        noise_curr = rng.gauss(0.0, 0.08)
        t_prev = 4.0 + noise_prev
        t_curr = 4.10 + noise_curr
        monitor.last_temp = t_prev
        if monitor.check_door_open(t_curr, dt_mins=2.0):
            subtle_detected += 1

    subtle_recall = subtle_detected / subtle_total

    # 2. High Noise Normal State (100 normal events with high noise sigma = 0.08 C)
    # Normal slope = 0.015 C/min (0.03 C over 2 min), noise can trigger false alarm!
    false_alarms = 0
    normal_total = 100
    for _ in range(normal_total):
        noise_prev = rng.gauss(0.0, 0.08)
        noise_curr = rng.gauss(0.0, 0.08)
        t_prev = 4.0 + noise_prev
        t_curr = 4.03 + noise_curr
        monitor.last_temp = t_prev
        if monitor.check_door_open(t_curr, dt_mins=2.0):
            false_alarms += 1

    noise_false_alarm_rate = (false_alarms / normal_total) * 100.0

    # 3. Unseen Anomaly: Duty Cycle Drift (Compressor incipient wear / partial gas leak)
    # In real world, failing compressor duty ratio drifts from 0.45 to 0.72 (below hard 0.85 threshold)
    unseen_duty_events = [0.70, 0.72, 0.75, 0.78, 0.80]
    unseen_detected = 0
    for duty in unseen_duty_events:
        is_anom, _ = monitor.check_cycle_anomaly(duty)
        if is_anom:
            unseen_detected += 1
    unseen_recall = unseen_detected / len(unseen_duty_events)

    # 4. Unseen Anomaly: Slow Cumulative Drift (Creeping from 4.0 C to 7.0 C over 3 hours)
    # Step-by-step 2-min dT = (7.0 - 4.0) / 90 steps = 0.033 C per 2-min (slope = 0.016 C/min)
    # Check if single-step slope detector catches this persistent food safety threat:
    t_drift = 4.0
    drift_steps = 90
    caught_by_slope = False
    monitor.last_temp = None
    for _ in range(drift_steps):
        t_drift += 0.033
        if monitor.check_door_open(t_drift, dt_mins=2.0):
            caught_by_slope = True
            break

    # Check if food_safety_status catches it when blackout/drift occurs
    food_status, rem = monitor.food_safety_status(t_drift, hours_since_blackout=2.5)

    return {
        "subtle_anomaly_recall_pct": round(subtle_recall * 100.0, 1),
        "high_noise_false_alarm_rate_pct": round(noise_false_alarm_rate, 1),
        "unseen_duty_drift_recall_pct": round(unseen_recall * 100.0, 1),
        "slow_thermal_drift_caught_by_slope": caught_by_slope,
        "slow_thermal_drift_food_safety_status": food_status,
    }


if __name__ == "__main__":
    res = benchmark_fridge_anomalies()
    print("=" * 60)
    print("[EVAL] 1. Synthetic Ideal Baseline (Tuned Threshold dT/dt >= 0.08):")
    print(f"  Precision:        {res['precision'] * 100}%")
    print(f"  Recall:           {res['recall'] * 100}%")
    print(f"  F1 Score:         {res['f1_score']}")
    print(f"  False Alarm Rate: {res['false_alarm_rate_pct']}%")
    print("=" * 60)

    stress = stress_test_fridge_anomalies()
    print("[EVAL] 2. Adversarial Stress-Test (High Noise, Subtle & Unseen Anomalies):")
    print(f"  Subtle Leak Recall (slope ~0.05 C/min, noise sigma=0.08): {stress['subtle_anomaly_recall_pct']}%")
    print(f"  False Alarm Rate under High Sensor Noise (sigma=0.08 C):  {stress['high_noise_false_alarm_rate_pct']}%")
    print(f"  Unseen Duty Cycle Drift (duty 0.70-0.80 vs threshold 0.85): {stress['unseen_duty_drift_recall_pct']}%")
    print(f"  Slow Thermal Drift caught by instantaneous slope:         {stress['slow_thermal_drift_caught_by_slope']}")
    print(f"  Food Safety Catch Status after cumulative rise:           {stress['slow_thermal_drift_food_safety_status']}")
    print("=" * 60)

