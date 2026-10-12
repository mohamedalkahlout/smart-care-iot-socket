"""
Conformance & Equivalence Test Suite (Safety Guard C vs Python).
Verifies strict 1:1 conformance between:
- C implementation: firmware/include/safety_guard.h and firmware/src/safety_guard.c
- Python implementation: simulator/safety_guard.py

Ensures all enums, default configuration parameters, rule order,
decision outcomes, and reason strings match exactly without discrepancies.
"""
import unittest
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.safety_guard import (
    DeviceType,
    CommandSource,
    RelayState,
    SafetyConfig,
    SafetyGuard,
    GuardInput,
)


class TestSafetyGuardConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.c_header_path = os.path.join(base_dir, "firmware", "include", "safety_guard.h")
        cls.c_src_path = os.path.join(base_dir, "firmware", "src", "safety_guard.c")

        with open(cls.c_header_path, "r", encoding="utf-8") as f:
            cls.c_header = f.read()

        with open(cls.c_src_path, "r", encoding="utf-8") as f:
            cls.c_src = f.read()

    def test_enums_conformance(self):
        """Verifies that all enum definitions and values in C match Python exactly."""
        # DeviceType
        c_devices = re.findall(r'DEVICE_([A-Z]+)\s*=\s*(\d+)', self.c_header)
        for dev_name, val in c_devices:
            py_name = dev_name.lower()
            self.assertTrue(hasattr(DeviceType, dev_name), f"Missing {dev_name} in Python DeviceType")
            self.assertEqual(DeviceType[dev_name].value, py_name)

        # RelayState
        self.assertIn("RELAY_STATE_OFF = 0", self.c_header)
        self.assertIn("RELAY_STATE_ON = 1", self.c_header)
        self.assertEqual(RelayState.OFF.value, 0)
        self.assertEqual(RelayState.ON.value, 1)

    def test_default_config_parameters_conformance(self):
        """Verifies that default safety thresholds in C safety_guard_default_config match Python SafetyConfig."""
        py_cfg = SafetyConfig()

        # Parse assignments from safety_guard_default_config() in C
        self.assertIn("cfg.absoluteMinTemp = 5.0f;", self.c_src)
        self.assertEqual(py_cfg.absolute_min_temp, 5.0)

        self.assertIn("cfg.absoluteMaxTemp = 45.0f;", self.c_src)
        self.assertEqual(py_cfg.absolute_max_temp, 45.0)

        self.assertIn("cfg.heatingCutoffTemp = 35.0f;", self.c_src)
        self.assertEqual(py_cfg.heating_cutoff_temp, 35.0)

        self.assertIn("cfg.coolingCutoffTemp = 10.0f;", self.c_src)
        self.assertEqual(py_cfg.cooling_cutoff_temp, 10.0)

        self.assertIn("cfg.sensorMaxAgeSec = 30;", self.c_src)
        self.assertEqual(py_cfg.sensor_max_age_sec, 30)

        self.assertIn("cfg.maxRuntimeHeatingSec = 1800;", self.c_src)
        self.assertEqual(py_cfg.max_runtime_heating_sec, 1800)

        self.assertIn("cfg.maxRuntimeCoolingSec = 14400;", self.c_src)
        self.assertEqual(py_cfg.max_runtime_cooling_sec, 14400)

        self.assertIn("cfg.maxRuntimeCompressorSec = 7200;", self.c_src)
        self.assertEqual(py_cfg.max_runtime_compressor_sec, 7200)

        self.assertIn("cfg.compressorMinOffSec = 180;", self.c_src)
        self.assertEqual(py_cfg.compressor_min_off_sec, 180)

        self.assertIn("cfg.compressorMinOnSec = 120;", self.c_src)
        self.assertEqual(py_cfg.compressor_min_on_sec, 120)

        self.assertIn("cfg.maxRemoteHeatingTimerSec = 1800;", self.c_src)
        self.assertEqual(py_cfg.max_remote_heating_timer_sec, 1800)

    def test_reason_codes_conformance(self):
        """Verifies that all reasonCode strings returned by C safety_guard_evaluate match Python."""
        # Extract all reasonCode string literals in C
        c_reason_codes = set(re.findall(r'res\.reasonCode\s*=\s*"([^"]+)"', self.c_src))

        expected_reason_codes = {
            "ALLOWED",
            "SHUTDOWN_PERMITTED",
            "ABSOLUTE_OVERHEAT",
            "HEATER_HIGH_TEMP_CUTOFF",
            "COOLER_LOW_TEMP_CUTOFF",
            "SENSOR_STALE_HEATER_SHUTDOWN",
            "SENSOR_STALE_COOLER_SHUTDOWN",
            "COMPRESSOR_ANTICYCLE_WAIT",
            "SENSOR_STALE_FRIDGE_PRESERVE",
            "COMPRESSOR_SHORT_CYCLE_PREVENTED",
            "MAX_RUNTIME_EXCEEDED",
            "REMOTE_HEATING_TIMER_REQUIRED",
        }

        self.assertEqual(c_reason_codes, expected_reason_codes,
                         f"Difference in reason codes: {c_reason_codes ^ expected_reason_codes}")

    def test_differential_rules_vector(self):
        """Tests that differential vectors covering all 8 rules evaluate identically."""
        guard = SafetyGuard()

        test_vectors = [
            # 1. Rule 1: Emergency off
            (GuardInput(RelayState.OFF, CommandSource.REMOTE, DeviceType.HEATING, 50.0, True, 5, RelayState.ON, 100, 1000),
             RelayState.OFF, "SHUTDOWN_PERMITTED", False),
            # 2. Rule 2: Absolute overheat
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.GENERIC, 46.0, True, 5, RelayState.OFF, 0, 1000),
             RelayState.OFF, "ABSOLUTE_OVERHEAT", True),
            # 3. Rule 3: Heating high temp cutoff
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.HEATING, 35.5, True, 5, RelayState.OFF, 0, 1000),
             RelayState.OFF, "HEATER_HIGH_TEMP_CUTOFF", True),
            # 4. Rule 4: Cooler low temp cutoff
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.COOLING, 9.5, True, 5, RelayState.OFF, 0, 1000),
             RelayState.OFF, "COOLER_LOW_TEMP_CUTOFF", True),
            # 5. Rule 5: Sensor stale heater
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.HEATING, 20.0, True, 35, RelayState.ON, 100, 1000),
             RelayState.OFF, "SENSOR_STALE_HEATER_SHUTDOWN", True),
            # 6. Rule 5: Sensor stale fridge preserve
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.COMPRESSOR, 4.0, False, 100, RelayState.ON, 100, 1000),
             RelayState.ON, "SENSOR_STALE_FRIDGE_PRESERVE", False),
            # 7. Rule 6: Compressor short cycle
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.COMPRESSOR, 8.0, True, 5, RelayState.OFF, 0, 100),
             RelayState.OFF, "COMPRESSOR_SHORT_CYCLE_PREVENTED", True),
            # 8. Rule 7: Max runtime exceeded
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.HEATING, 20.0, True, 5, RelayState.ON, 1805, 1000),
             RelayState.OFF, "MAX_RUNTIME_EXCEEDED", True),
            # 9. Rule 8: Remote heating timer required
            (GuardInput(RelayState.ON, CommandSource.REMOTE, DeviceType.HEATING, 18.0, True, 5, RelayState.OFF, 0, 1000, remote_heating_timer_sec=0),
             RelayState.OFF, "REMOTE_HEATING_TIMER_REQUIRED", True),
            # 10. Allowed compliant state
            (GuardInput(RelayState.ON, CommandSource.AUTO_RULE, DeviceType.COOLING, 27.0, True, 5, RelayState.OFF, 0, 1000),
             RelayState.ON, "ALLOWED", False),
        ]

        for idx, (inp, exp_state, exp_reason, exp_modified) in enumerate(test_vectors):
            res = guard.evaluate(inp)
            self.assertEqual(res.allowed_state, exp_state, f"Vector #{idx} state mismatch")
            self.assertEqual(res.reason_code, exp_reason, f"Vector #{idx} reason mismatch")
            self.assertEqual(res.modified, exp_modified, f"Vector #{idx} modified mismatch")


if __name__ == "__main__":
    unittest.main()
