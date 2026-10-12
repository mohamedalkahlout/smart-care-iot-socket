"""
Thermal Room Simulator & Synthetic 60-Day Telemetry Generator (P3.1).
Simulates room dynamics using an equivalent 1R-1C thermal network:
dT/dt = (T_out - T_in) / (R * C) + (Q_internal + Q_solar + Q_appliance) / C + noise
"""
import math
import random
import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.safety_guard import (
    CommandSource,
    DeviceType,
    RelayState,
    SafetyConfig,
    SafetyGuard,
)
from simulator.control_logic import (
    ControlMode,
    ControllerConfig,
    ControllerState,
    SmartSocketController,
)
from cloud.telemetry_logger import TelemetryLogger, TelemetryRecord


class ThermalRoomSimulator:
    def __init__(
        self,
        R_th: float = 2.5,        # Thermal resistance (K/kW)
        C_th: float = 12.0,       # Thermal capacitance (kWh/K)
        initial_temp: float = 22.0,
        seed: int = 42,
    ):
        self.R = R_th
        self.C = C_th
        self.temp_in = initial_temp
        self.random = random.Random(seed)

    def outdoor_temp(self, t_hours: float) -> float:
        # Diurnal temperature cycle: mean 24 C with 7 C amplitude, min at 4 AM, max at 4 PM
        day_progress = (t_hours % 24.0)
        diurnal = 24.0 + 7.0 * math.sin(2.0 * math.pi * (day_progress - 10.0) / 24.0)
        # Seasonal slow wave (over 60 days)
        seasonal = 2.0 * math.sin(2.0 * math.pi * t_hours / (60.0 * 24.0))
        noise = self.random.gauss(0.0, 0.4)
        return diurnal + seasonal + noise

    def step(self, dt_hours: float, t_hours: float, q_appliance_kw: float) -> float:
        t_out = self.outdoor_temp(t_hours)
        solar_gain = max(0.0, 0.8 * math.sin(math.pi * ((t_hours % 24.0) - 6.0) / 12.0))
        internal_gain = 0.3 + 0.2 * (1.0 if 18.0 <= (t_hours % 24.0) <= 23.0 else 0.0)

        # dT/dt differential
        heat_flow = (t_out - self.temp_in) / self.R + solar_gain + internal_gain + q_appliance_kw
        dT = (heat_flow / self.C) * dt_hours
        sensor_noise = self.random.gauss(0.0, 0.05)

        self.temp_in += dT
        return self.temp_in + sensor_noise


def generate_60days_telemetry(
    output_csv_path: str = "simulator/telemetry_60days.csv",
    seed: int = 42,
) -> int:
    sim = ThermalRoomSimulator(seed=seed)
    ctrl_cfg = ControllerConfig(
        device_type=DeviceType.COOLING,
        mode=ControlMode.AUTO,
        target_min_temp=21.0,
        target_max_temp=25.0,
        hysteresis=0.5,
    )
    controller = SmartSocketController(config=ctrl_cfg)
    logger = TelemetryLogger(max_buffer_size=200000)

    # 60 days in steps of 60 seconds (1 minute)
    dt_sec = 60
    dt_hours = dt_sec / 3600.0
    total_seconds = 60 * 24 * 3600
    base_ts = 1760000000  # Unix timestamp

    ctrl_state = ControllerState(
        current_relay_state=RelayState.OFF,
        has_valid_temp=True,
        last_valid_temp=22.0,
        temp_reading_age_sec=0,
    )

    appliance_power_kw = 1.2  # 1.2 kW cooler

    for step_idx in range(total_seconds // dt_sec):
        current_sec = step_idx * dt_sec
        t_hours = current_sec / 3600.0
        current_day = current_sec // 86400

        # --- Injected Faults ---
        is_sensor_stuck = (12 <= current_day < 13)       # Day 12: Sensor stuck / stale
        is_fridge_open = (24 <= current_day < 25)        # Day 24: Excess heat leak
        is_blackout = (42 <= current_day < 43)           # Day 42: Power blackout
        is_network_cut = (51 <= current_day < 52)        # Day 51: Wi-Fi offline

        # Determine cooling heat load
        q_appliance = 0.0
        if ctrl_state.current_relay_state == RelayState.ON and not is_blackout:
            q_appliance = -appliance_power_kw  # Negative heat (cooling)

        if is_fridge_open:
            q_appliance += 1.5  # Heat leakage into space

        # Step thermal physics
        room_temp = sim.step(dt_hours, t_hours, q_appliance)

        # Update controller state
        if is_sensor_stuck:
            ctrl_state.has_valid_temp = False
            ctrl_state.temp_reading_age_sec += dt_sec
        else:
            ctrl_state.has_valid_temp = True
            ctrl_state.last_valid_temp = round(room_temp, 2)
            ctrl_state.temp_reading_age_sec = 0

        ctrl_state.is_network_connected = not is_network_cut

        # Execute controller decision
        decision = controller.step(ctrl_state)

        # Update timings
        if decision.computedRelayState if hasattr(decision, 'computedRelayState') else decision.computed_relay_state == RelayState.ON:
            ctrl_state.current_relay_state = RelayState.ON
            ctrl_state.current_runtime_sec += dt_sec
        else:
            ctrl_state.current_relay_state = RelayState.OFF
            ctrl_state.current_runtime_sec = 0
            ctrl_state.time_since_last_turn_off_sec += dt_sec

        # Log sample every 10 minutes (600s) or immediately on state changes
        if (current_sec % 600 == 0) or (step_idx == 0):
            pwr = 1200.0 if ctrl_state.current_relay_state == RelayState.ON else 0.0
            if is_blackout:
                pwr = 0.0

            record = TelemetryRecord(
                ts=base_ts + current_sec,
                device_id="socket1",
                device_type="cooling",
                temp_c=ctrl_state.last_valid_temp or 0.0,
                humidity_pct=round(45.0 + 5.0 * math.sin(t_hours / 6.0), 1),
                relay_cmd="on" if decision.computed_relay_state == RelayState.ON else "off",
                relay_actual="on" if ctrl_state.current_relay_state == RelayState.ON else "off",
                mode="auto",
                source=decision.decision_source.value,
                power_w=pwr,
                rssi=-65 if ctrl_state.is_network_connected else 0,
                fw_version="1.0.0",
                guard_reason=decision.guard_result.reason_code,
            )
            logger.log(record)

    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    logger.export_csv(output_csv_path)
    return logger.count()


if __name__ == "__main__":
    count = generate_60days_telemetry()
    print(f"[SIMULATOR] Successfully generated 60 days of synthetic telemetry ({count} records).")
