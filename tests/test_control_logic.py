import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.control_logic import (
    SmartSocketController,
    ControllerConfig,
    ControllerState,
    ControlMode,
)
from simulator.safety_guard import (
    DeviceType,
    RelayState,
    CommandSource,
)


class TestControlLogic(unittest.TestCase):
    def test_cooling_hysteresis_logic(self):
        cfg = ControllerConfig(
            device_type=DeviceType.COOLING,
            mode=ControlMode.AUTO,
            target_max_temp=26.0,
            hysteresis=1.0,  # Turn ON at > 26.0, Turn OFF at < (26.0 - 1.0) = 25.0
        )
        ctrl = SmartSocketController(config=cfg)

        # 1. Temp is 25.5 (between 25.0 and 26.0), initially OFF -> remains OFF
        st = ControllerState(
            current_relay_state=RelayState.OFF,
            last_valid_temp=25.5,
            has_valid_temp=True,
        )
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.OFF)

        # 2. Temp rises to 26.5 (above 26.0) -> Turns ON
        st.last_valid_temp = 26.5
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.ON)
        self.assertEqual(dec.decision_source, CommandSource.AUTO_RULE)

        # 3. Temp drops to 25.5 while running (above 25.0 cut-off) -> remains ON (Hysteresis working!)
        st.current_relay_state = RelayState.ON
        st.last_valid_temp = 25.5
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.ON)

        # 4. Temp drops below 25.0 (e.g. 24.8) -> Turns OFF
        st.last_valid_temp = 24.8
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.OFF)

    def test_heating_hysteresis_logic(self):
        cfg = ControllerConfig(
            device_type=DeviceType.HEATING,
            mode=ControlMode.AUTO,
            target_min_temp=20.0,
            hysteresis=1.0,  # Turn ON at < 20.0, Turn OFF at > (20.0 + 1.0) = 21.0
        )
        ctrl = SmartSocketController(config=cfg)

        # Temp is 19.5 (below 20.0) -> Turns ON
        st = ControllerState(
            current_relay_state=RelayState.OFF,
            last_valid_temp=19.5,
            has_valid_temp=True,
        )
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.ON)

        # Temp rises to 20.5 (below 21.0 cut-off) -> remains ON (Hysteresis prevents chatter)
        st.current_relay_state = RelayState.ON
        st.last_valid_temp = 20.5
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.ON)

        # Temp rises to 21.2 -> Turns OFF
        st.last_valid_temp = 21.2
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.OFF)

    def test_local_physical_button_override_priority(self):
        cfg = ControllerConfig(
            device_type=DeviceType.COOLING,
            mode=ControlMode.AUTO,
            target_max_temp=24.0,
        )
        ctrl = SmartSocketController(config=cfg)

        # Auto rule wants ON (temp 28.0), but user physically pressed button for OFF
        st = ControllerState(
            current_relay_state=RelayState.ON,
            last_valid_temp=28.0,
            has_valid_temp=True,
            local_button_triggered=True,
            local_button_desired_state=RelayState.OFF,
        )
        dec = ctrl.step(st)
        self.assertEqual(dec.computed_relay_state, RelayState.OFF)
        self.assertEqual(dec.decision_source, CommandSource.LOCAL_BUTTON)

    def test_network_offline_retains_mode_and_safe_state(self):
        cfg = ControllerConfig(
            device_type=DeviceType.HEATING,
            mode=ControlMode.MANUAL,
            manual_desired_state=RelayState.OFF,
        )
        ctrl = SmartSocketController(config=cfg)

        st = ControllerState(
            current_relay_state=RelayState.OFF,
            last_valid_temp=18.0,
            has_valid_temp=True,
            is_network_connected=False,  # Offline!
        )
        dec = ctrl.step(st)
        # Does NOT randomly switch to auto or turn ON
        self.assertEqual(dec.computed_relay_state, RelayState.OFF)


if __name__ == "__main__":
    unittest.main()
