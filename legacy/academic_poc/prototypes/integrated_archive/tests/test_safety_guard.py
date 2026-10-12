"""
Unit Test Suite for Multi-Socket Safety Guard Rules.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "simulator")))
from safety_guard import (
    MultiSocketSafetyConfig, ChannelTelemetry, SocketChannel,
    DeviceState, ApplianceType, CommandSource, safety_guard_evaluate_channel
)


class TestMultiSocketSafetyGuard(unittest.TestCase):
    def setUp(self):
        self.config = MultiSocketSafetyConfig()

    def test_emergency_shutdown_overrides_all(self):
        self.config.master_emergency_shutdown = True
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_1_THERMAL,
            current_state=DeviceState.STATE_OFF,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_HEATER,
            source=CommandSource.CMD_LOCAL_PHYSICAL
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "EMERGENCY_SHUTDOWN_ACTIVE")

    def test_immediate_off_always_allowed(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_2_PUMP,
            current_state=DeviceState.STATE_ON,
            requested_state=DeviceState.STATE_OFF,
            appliance_type=ApplianceType.APPLIANCE_WATER_PUMP,
            source=CommandSource.CMD_REMOTE_CLOUD
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertTrue(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "IMMEDIATE_OFF_PERMITTED")

    def test_overheat_cutoff(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_1_THERMAL,
            current_state=DeviceState.STATE_OFF,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_HEATER,
            source=CommandSource.CMD_AUTOMATION,
            current_temperature=46.5,
            is_temperature_valid=True
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "ABSOLUTE_OVERHEAT_CUTOFF")

    def test_heater_max_continuous_runtime(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_1_THERMAL,
            current_state=DeviceState.STATE_ON,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_HEATER,
            source=CommandSource.CMD_AUTOMATION,
            continuous_on_seconds=7300,
            current_temperature=22.0
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "MAX_CONTINUOUS_RUNTIME_EXCEEDED")

    def test_compressor_anti_short_cycle(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_4_AC,
            current_state=DeviceState.STATE_OFF,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_AC,
            source=CommandSource.CMD_AUTOMATION,
            time_since_last_off_seconds=90  # < 180s
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "COMPRESSOR_ANTI_SHORT_CYCLE_WAIT")

    def test_pump_max_continuous_runtime(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_2_PUMP,
            current_state=DeviceState.STATE_ON,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_WATER_PUMP,
            source=CommandSource.CMD_LOCAL_PHYSICAL,
            continuous_on_seconds=1250  # > 1200s
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "PUMP_MAX_RUNTIME_EXCEEDED")

    def test_pump_cooldown_active(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_2_PUMP,
            current_state=DeviceState.STATE_OFF,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_WATER_PUMP,
            source=CommandSource.CMD_REMOTE_CLOUD,
            time_since_last_off_seconds=120  # < 300s
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "PUMP_COOLDOWN_ACTIVE")

    def test_tv_auto_off_timer(self):
        tel = ChannelTelemetry(
            channel=SocketChannel.CHANNEL_3_APPLIANCE,
            current_state=DeviceState.STATE_ON,
            requested_state=DeviceState.STATE_ON,
            appliance_type=ApplianceType.APPLIANCE_TV,
            source=CommandSource.CMD_LOCAL_PHYSICAL,
            continuous_on_seconds=15000  # > 14400s (4h)
        )
        dec = safety_guard_evaluate_channel(tel, self.config)
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.enforced_state, DeviceState.STATE_OFF)
        self.assertEqual(dec.reason_code, "APPLIANCE_AUTO_OFF_TIMER")


if __name__ == "__main__":
    unittest.main()
