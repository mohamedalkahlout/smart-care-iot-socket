import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.safety_guard import (
    SafetyGuard,
    SafetyConfig,
    GuardInput,
    RelayState,
    CommandSource,
    DeviceType,
)


class TestSafetyGuard(unittest.TestCase):
    def setUp(self):
        self.guard = SafetyGuard()

    def test_immediate_off_always_allowed(self):
        inp = GuardInput(
            requested_state=RelayState.OFF,
            source=CommandSource.REMOTE,
            device_type=DeviceType.HEATING,
            current_temp=50.0,
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.ON,
            current_runtime_sec=100,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertEqual(res.reason_code, "SHUTDOWN_PERMITTED")

    def test_absolute_overheat_cutoff(self):
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.GENERIC,
            current_temp=46.0,  # exceeds 45.0
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.OFF,
            current_runtime_sec=0,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertTrue(res.modified)
        self.assertEqual(res.reason_code, "ABSOLUTE_OVERHEAT")

    def test_heating_cutoff(self):
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.HEATING,
            current_temp=36.0,  # exceeds heating cutoff 35.0
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.OFF,
            current_runtime_sec=0,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertTrue(res.modified)
        self.assertEqual(res.reason_code, "HEATER_HIGH_TEMP_CUTOFF")

    def test_sensor_stale_heater_failsafe(self):
        # Sensor reading age = 45s (exceeds 30s)
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.HEATING,
            current_temp=20.0,
            has_temp_reading=True,
            temp_reading_age_sec=45,
            current_relay_state=RelayState.ON,
            current_runtime_sec=500,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertTrue(res.modified)
        self.assertEqual(res.reason_code, "SENSOR_STALE_HEATER_SHUTDOWN")

    def test_sensor_stale_fridge_failsafe(self):
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.COMPRESSOR,
            current_temp=4.0,
            has_temp_reading=False,  # missing sensor
            temp_reading_age_sec=100,
            current_relay_state=RelayState.ON,
            current_runtime_sec=500,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.ON)
        self.assertEqual(res.reason_code, "SENSOR_STALE_FRIDGE_PRESERVE")

    def test_compressor_anti_short_cycle(self):
        # Compressor turned off only 60 seconds ago (must wait >= 180s)
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.COMPRESSOR,
            current_temp=8.0,
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.OFF,
            current_runtime_sec=0,
            time_since_last_turn_off_sec=60,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertTrue(res.modified)
        self.assertEqual(res.reason_code, "COMPRESSOR_SHORT_CYCLE_PREVENTED")

    def test_max_continuous_runtime_heater(self):
        # Heater running for 1801s (limit is 1800s)
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.AUTO_RULE,
            device_type=DeviceType.HEATING,
            current_temp=21.0,
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.ON,
            current_runtime_sec=1801,
            time_since_last_turn_off_sec=1000,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertTrue(res.modified)
        self.assertEqual(res.reason_code, "MAX_RUNTIME_EXCEEDED")

    def test_remote_heating_timer_requirement(self):
        # Remote heating without positive timer
        inp = GuardInput(
            requested_state=RelayState.ON,
            source=CommandSource.REMOTE,
            device_type=DeviceType.HEATING,
            current_temp=18.0,
            has_temp_reading=True,
            temp_reading_age_sec=5,
            current_relay_state=RelayState.OFF,
            current_runtime_sec=0,
            time_since_last_turn_off_sec=1000,
            remote_heating_timer_sec=0,
        )
        res = self.guard.evaluate(inp)
        self.assertEqual(res.allowed_state, RelayState.OFF)
        self.assertEqual(res.reason_code, "REMOTE_HEATING_TIMER_REQUIRED")

        # With valid timer (e.g. 15 min = 900s)
        inp.remote_heating_timer_sec = 900
        res_valid = self.guard.evaluate(inp)
        self.assertEqual(res_valid.allowed_state, RelayState.ON)
        self.assertEqual(res_valid.reason_code, "ALLOWED")


if __name__ == "__main__":
    unittest.main()
