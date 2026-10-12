"""
Multi-Socket Hub Physical Environment Simulator.
Simulates 4 concurrently operated home appliances:
 - S1: Thermal Room Heater (1R-1C thermal model)
 - S2: Rooftop Water Pump & Reservoir Tank
 - S3: TV & Workstation with Standby Vampire Drain
 - S4: AC Compressor with Outdoor Heat Load
"""
import math
import random
from typing import Dict, List
from safety_guard import (
    MultiSocketSafetyConfig, ChannelTelemetry, SocketChannel,
    DeviceState, ApplianceType, CommandSource, safety_guard_evaluate_channel
)


class MultiSocketSimulator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.config = MultiSocketSafetyConfig()

        # Channel 1: Thermal Room
        self.room_temp = 18.0
        self.ambient_temp = 10.0
        self.thermal_r = 2.5   # K/kW
        self.thermal_c = 15.0  # kWh/K
        self.heater_power_kw = 1.5

        # Channel 2: Water Tank
        self.tank_level_liters = 150.0 # 0 to 500L
        self.tank_capacity = 500.0
        self.pump_flow_rate_lpm = 25.0  # 25 L/min
        self.drain_rate_lpm = 2.0      # domestic usage

        # Channel 3: TV Standby
        self.tv_state = DeviceState.STATE_OFF

        # Channel 4: AC Room
        self.ac_room_temp = 28.0
        self.outdoor_summer_temp = 36.0
        self.ac_cooling_power_kw = 2.5

        # Telemetry history
        self.history: List[Dict] = []

    def step(self, dt_minutes: float = 1.0, actions: Dict[int, DeviceState] = None):
        if actions is None:
            actions = {0: DeviceState.STATE_OFF, 1: DeviceState.STATE_OFF, 2: DeviceState.STATE_OFF, 3: DeviceState.STATE_OFF}

        dt_hours = dt_minutes / 60.0

        # S1: Update Thermal Room
        s1_state = actions.get(0, DeviceState.STATE_OFF)
        q_heater = self.heater_power_kw if s1_state == DeviceState.STATE_ON else 0.0
        dT_dt = ((self.ambient_temp - self.room_temp) / (self.thermal_r * self.thermal_c)) + (q_heater / self.thermal_c)
        self.room_temp += dT_dt * dt_hours + random.gauss(0, 0.02)

        # S2: Update Water Tank
        s2_state = actions.get(1, DeviceState.STATE_OFF)
        pump_in = (self.pump_flow_rate_lpm * dt_minutes) if s2_state == DeviceState.STATE_ON else 0.0
        water_out = self.drain_rate_lpm * dt_minutes
        self.tank_level_liters = max(0.0, min(self.tank_capacity, self.tank_level_liters + pump_in - water_out))

        # S3: TV Standby
        s3_state = actions.get(2, DeviceState.STATE_OFF)

        # S4: AC Cooling
        s4_state = actions.get(3, DeviceState.STATE_OFF)
        q_ac = -self.ac_cooling_power_kw if s4_state == DeviceState.STATE_ON else 0.0
        ac_dT = ((self.outdoor_summer_temp - self.ac_room_temp) / (1.8 * 12.0)) + (q_ac / 12.0)
        self.ac_room_temp += ac_dT * dt_hours + random.gauss(0, 0.02)

        record = {
            "room_temp": round(self.room_temp, 2),
            "tank_liters": round(self.tank_level_liters, 1),
            "ac_room_temp": round(self.ac_room_temp, 2),
            "s1_state": s1_state.value,
            "s2_state": s2_state.value,
            "s3_state": s3_state.value,
            "s4_state": s4_state.value,
        }
        self.history.append(record)
        return record


def run_demo_simulation(steps: int = 120):
    sim = MultiSocketSimulator()
    print("=" * 60)
    print(f"[SIM] Running SmartCare Hub Simulation ({steps} minutes)...")
    print("=" * 60)

    for m in range(steps):
        # Auto control policy
        s1 = DeviceState.STATE_ON if sim.room_temp < 20.0 else DeviceState.STATE_OFF
        s2 = DeviceState.STATE_ON if sim.tank_level_liters < 200.0 else DeviceState.STATE_OFF
        s3 = DeviceState.STATE_ON if 30 <= m <= 90 else DeviceState.STATE_OFF
        s4 = DeviceState.STATE_ON if sim.ac_room_temp > 25.0 else DeviceState.STATE_OFF

        rec = sim.step(1.0, {0: s1, 1: s2, 2: s3, 3: s4})
        if m % 30 == 0 or m == steps - 1:
            print(f"Min {m:03d} | Heater: {rec['room_temp']} C | Tank: {rec['tank_liters']} L | TV: {rec['s3_state']} | AC: {rec['ac_room_temp']} C")

    print(f"[DONE] Simulation complete. Generated {len(sim.history)} steps.")


if __name__ == "__main__":
    run_demo_simulation(120)
