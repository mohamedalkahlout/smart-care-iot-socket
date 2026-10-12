"""
Predictive Adaptive Hysteresis Controller Evaluation (P4.2).
Compares:
 1. Simple Threshold (Bang-bang without hysteresis)
 2. Fixed Hysteresis Controller
 3. Predictive Adaptive Controller (using online thermal predictions)
Runs 30 randomized simulations and reports Mean & Std Dev for:
 - Switching Cycles (Relay wear)
 - Comfort Violation Time (minutes)
 - Energy Consumption (kWh)
"""
import math
import random
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.thermal_model import EdgeThermalModelPy
from simulator.thermal_room_simulator import ThermalRoomSimulator
from simulator.safety_guard import (
    CommandSource,
    DeviceType,
    GuardInput,
    RelayState,
    SafetyGuard,
)


@dataclass
class SimulationMetrics:
    switching_cycles: int
    comfort_violation_mins: float
    energy_kwh: float


def run_single_experiment(
    controller_type: str,  # "threshold", "fixed_hysteresis", "predictive_adaptive"
    seed: int,
    duration_days: int = 7,
) -> SimulationMetrics:
    sim = ThermalRoomSimulator(seed=seed)
    guard = SafetyGuard()
    model = EdgeThermalModelPy(learning_rate=0.08)

    dt_mins = 2
    dt_hours = dt_mins / 60.0
    total_steps = int((duration_days * 24 * 60) / dt_mins)

    target_min = 21.0
    target_max = 25.0
    fixed_hysteresis = 0.5
    appliance_power_kw = 1.2

    current_state = RelayState.OFF
    switching_cycles = 0
    comfort_violations = 0
    energy_kwh = 0.0

    current_runtime_sec = 0
    time_since_off_sec = 3600

    for step_idx in range(total_steps):
        t_hours = step_idx * dt_hours
        q_power = -appliance_power_kw if current_state == RelayState.ON else 0.0

        current_temp = sim.step(dt_hours, t_hours, q_power)
        model.update(current_temp, 1 if current_state == RelayState.ON else 0)

        # Update timings
        if current_state == RelayState.ON:
            current_runtime_sec += dt_mins * 60
            energy_kwh += appliance_power_kw * dt_hours
        else:
            time_since_off_sec += dt_mins * 60

        # Check comfort boundary
        if current_temp < target_min or current_temp > target_max:
            comfort_violations += dt_mins

        # Decide requested state based on controller type
        requested_state = current_state

        if controller_type == "threshold":
            # Bang-bang
            if current_temp > target_max:
                requested_state = RelayState.ON
            else:
                requested_state = RelayState.OFF

        elif controller_type == "fixed_hysteresis":
            # Cooling: ON if T > max, OFF if T < max - h
            if current_temp > target_max:
                requested_state = RelayState.ON
            elif current_temp < (target_max - fixed_hysteresis):
                requested_state = RelayState.OFF

        elif controller_type == "predictive_adaptive":
            # Lookahead 15 mins (approx 7 steps)
            pred_temp = model.predict(current_temp, 1 if current_state == RelayState.ON else 0, steps=7)
            adaptive_h = max(0.4, min(1.2, 0.6 + 0.1 * abs(current_temp - target_max)))

            # Anticipatory turn ON if predicted temp exceeds target_max
            if pred_temp > target_max:
                requested_state = RelayState.ON
            elif current_temp < (target_max - adaptive_h):
                requested_state = RelayState.OFF

        # Pass strictly through Safety Guard
        guard_in = GuardInput(
            requested_state=requested_state,
            source=CommandSource.AI if controller_type == "predictive_adaptive" else CommandSource.AUTO_RULE,
            device_type=DeviceType.COOLING,
            current_temp=current_temp,
            has_temp_reading=True,
            temp_reading_age_sec=0,
            current_relay_state=current_state,
            current_runtime_sec=current_runtime_sec,
            time_since_last_turn_off_sec=time_since_off_sec,
        )
        guard_res = guard.evaluate(guard_in)
        next_state = guard_res.allowed_state

        if next_state != current_state:
            switching_cycles += 1
            if next_state == RelayState.ON:
                current_runtime_sec = 0
            else:
                time_since_off_sec = 0
            current_state = next_state

    return SimulationMetrics(
        switching_cycles=switching_cycles,
        comfort_violation_mins=comfort_violations,
        energy_kwh=round(energy_kwh, 2),
    )


def run_benchmark_30_trials() -> Dict[str, Dict[str, Tuple[float, float]]]:
    controllers = ["threshold", "fixed_hysteresis", "predictive_adaptive"]
    results = {c: {"cycles": [], "violations": [], "energy": []} for c in controllers}

    for seed in range(100, 130):  # 30 trials
        for c in controllers:
            m = run_single_experiment(c, seed=seed, duration_days=5)
            results[c]["cycles"].append(m.switching_cycles)
            results[c]["violations"].append(m.comfort_violation_mins)
            results[c]["energy"].append(m.energy_kwh)

    def stats(arr: List[float]) -> Tuple[float, float]:
        mean_val = sum(arr) / len(arr)
        variance = sum((x - mean_val) ** 2 for x in arr) / len(arr)
        return round(mean_val, 2), round(math.sqrt(variance), 2)

    summary = {}
    for c in controllers:
        summary[c] = {
            "cycles": stats(results[c]["cycles"]),
            "violations_mins": stats(results[c]["violations"]),
            "energy_kwh": stats(results[c]["energy"]),
        }
    return summary


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 70)
    print("[EVAL] Running 30-Trial Comparative Benchmark (RQ1 Analysis)...")
    print("=" * 70)
    res = run_benchmark_30_trials()
    print(f"{'Controller':<22} | {'Switching Cycles':<16} | {'Comfort Out (min)':<18} | {'Energy (kWh)':<14}")
    print("-" * 75)
    for c, metrics in res.items():
        cy_m, cy_s = metrics["cycles"]
        vi_m, vi_s = metrics["violations_mins"]
        en_m, en_s = metrics["energy_kwh"]
        print(f"{c:<22} | {cy_m:>6.1f} (+-{cy_s:<4.1f}) | {vi_m:>7.1f} (+-{vi_s:<5.1f}) | {en_m:>5.1f} (+-{en_s:<4.1f})")
    print("=" * 75)
