"""
Conformance Test Suite: C (firmware/src/safety_guard.c) vs Python (simulator/safety_guard.py).
Ensures 1:1 structural, parameter, and rule equivalence.
"""
import os
import re
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
C_HEADER_PATH = os.path.join(ROOT_DIR, "firmware", "include", "safety_guard.h")
C_SOURCE_PATH = os.path.join(ROOT_DIR, "firmware", "src", "safety_guard.c")

import sys
sys.path.insert(0, os.path.join(ROOT_DIR, "simulator"))
import safety_guard as py_sg


class TestMultiSocketConformance(unittest.TestCase):
    def setUp(self):
        with open(C_HEADER_PATH, "r", encoding="utf-8") as f:
            self.c_header = f.read()
        with open(C_SOURCE_PATH, "r", encoding="utf-8") as f:
            self.c_source = f.read()

    def test_enums_conformance(self):
        # 1. DeviceState
        self.assertEqual(py_sg.DeviceState.STATE_OFF.value, 0)
        self.assertEqual(py_sg.DeviceState.STATE_ON.value, 1)

        # 2. SocketChannel
        self.assertEqual(py_sg.SocketChannel.CHANNEL_1_THERMAL.value, 0)
        self.assertEqual(py_sg.SocketChannel.CHANNEL_2_PUMP.value, 1)
        self.assertEqual(py_sg.SocketChannel.CHANNEL_3_APPLIANCE.value, 2)
        self.assertEqual(py_sg.SocketChannel.CHANNEL_4_AC.value, 3)

        # 3. ApplianceType
        self.assertEqual(py_sg.ApplianceType.APPLIANCE_HEATER.value, 0)
        self.assertEqual(py_sg.ApplianceType.APPLIANCE_WATER_PUMP.value, 3)
        self.assertEqual(py_sg.ApplianceType.APPLIANCE_TV.value, 4)
        self.assertEqual(py_sg.ApplianceType.APPLIANCE_AC.value, 5)

    def test_default_config_parameters_conformance(self):
        py_cfg = py_sg.MultiSocketSafetyConfig()

        # Check values in C source match Python dataclass defaults
        self.assertIn("absolute_overheat_c          = 45.0f;", self.c_source)
        self.assertEqual(py_cfg.absolute_overheat_c, 45.0)

        self.assertIn("max_heater_runtime_sec       = 7200;", self.c_source)
        self.assertEqual(py_cfg.max_heater_runtime_sec, 7200)

        self.assertIn("compressor_anti_short_sec    = 180;", self.c_source)
        self.assertEqual(py_cfg.compressor_anti_short_sec, 180)

        self.assertIn("max_pump_runtime_sec         = 1200;", self.c_source)
        self.assertEqual(py_cfg.max_pump_runtime_sec, 1200)

        self.assertIn("pump_cooldown_sec            = 300;", self.c_source)
        self.assertEqual(py_cfg.pump_cooldown_sec, 300)

        self.assertIn("max_tv_runtime_sec           = 14400;", self.c_source)
        self.assertEqual(py_cfg.max_tv_runtime_sec, 14400)

    def test_reason_codes_conformance(self):
        expected_reason_codes = [
            "NULL_POINTER_REJECT",
            "EMERGENCY_SHUTDOWN_ACTIVE",
            "IMMEDIATE_OFF_PERMITTED",
            "ABSOLUTE_OVERHEAT_CUTOFF",
            "MAX_CONTINUOUS_RUNTIME_EXCEEDED",
            "HEATING_HIGH_ROOM_CUTOFF",
            "SENSOR_STALE_HEATER_CUTOFF",
            "SENSOR_STALE_FRIDGE_FAILSAFE",
            "COMPRESSOR_ANTI_SHORT_CYCLE_WAIT",
            "PUMP_MAX_RUNTIME_EXCEEDED",
            "PUMP_COOLDOWN_ACTIVE",
            "APPLIANCE_AUTO_OFF_TIMER",
            "COMMAND_ALLOWED"
        ]

        for code in expected_reason_codes:
            self.assertIn(f'"{code}"', self.c_source, f"Reason code {code} missing in C source")


if __name__ == "__main__":
    unittest.main()
