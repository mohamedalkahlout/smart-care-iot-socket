"""
Unit Tests for Multi-Channel Logic and Hysteresis.
"""
import unittest


def compute_thermal_hysteresis_state(
    current_temp: float,
    min_temp: float,
    max_temp: float,
    hysteresis: float,
    current_state: int,
    is_cooling: bool
) -> int:
    if is_cooling:
        if current_temp >= (max_temp + hysteresis):
            return 1  # STATE_ON
        elif current_temp <= (min_temp - hysteresis):
            return 0  # STATE_OFF
        return current_state
    else:
        if current_temp <= (min_temp - hysteresis):
            return 1  # STATE_ON
        elif current_temp >= (max_temp + hysteresis):
            return 0  # STATE_OFF
        return current_state


class TestMultiChannelControl(unittest.TestCase):
    def test_heating_hysteresis(self):
        # Min=20, Max=25, Hysteresis=0.5
        # 1. Below (20 - 0.5 = 19.5) -> Must turn ON
        self.assertEqual(compute_thermal_hysteresis_state(19.4, 20.0, 25.0, 0.5, 0, False), 1)

        # 2. Inside deadband (22.0) -> Must retain current state (ON remains ON)
        self.assertEqual(compute_thermal_hysteresis_state(22.0, 20.0, 25.0, 0.5, 1, False), 1)

        # 3. Above (25 + 0.5 = 25.5) -> Must turn OFF
        self.assertEqual(compute_thermal_hysteresis_state(25.6, 20.0, 25.0, 0.5, 1, False), 0)

    def test_cooling_hysteresis(self):
        # Min=22, Max=26, Hysteresis=0.5
        # 1. Above (26 + 0.5 = 26.5) -> Must turn ON
        self.assertEqual(compute_thermal_hysteresis_state(26.6, 22.0, 26.0, 0.5, 0, True), 1)

        # 2. Inside deadband (24.0) -> Must retain state
        self.assertEqual(compute_thermal_hysteresis_state(24.0, 22.0, 26.0, 0.5, 1, True), 1)

        # 3. Below (22 - 0.5 = 21.5) -> Must turn OFF
        self.assertEqual(compute_thermal_hysteresis_state(21.4, 22.0, 26.0, 0.5, 1, True), 0)


if __name__ == "__main__":
    unittest.main()
