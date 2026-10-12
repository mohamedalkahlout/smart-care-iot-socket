"""
Decoupled Control Logic module for Smart IoT Socket.
Supports cooling, heating, compressor, and generic devices with hysteresis.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from simulator.safety_guard import (
    CommandSource,
    DeviceType,
    GuardInput,
    GuardResult,
    RelayState,
    SafetyConfig,
    SafetyGuard,
)


class ControlMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"


@dataclass
class ControllerConfig:
    device_type: DeviceType = DeviceType.COOLING
    mode: ControlMode = ControlMode.AUTO
    target_min_temp: float = 20.0
    target_max_temp: float = 26.0
    hysteresis: float = 0.5
    relay_active_high: bool = True
    manual_desired_state: RelayState = RelayState.OFF
    remote_heating_timer_sec: int = 0


@dataclass
class ControllerState:
    current_relay_state: RelayState = RelayState.OFF
    time_in_current_state_sec: int = 0
    current_runtime_sec: int = 0
    time_since_last_turn_off_sec: int = 3600
    last_valid_temp: Optional[float] = None
    has_valid_temp: bool = False
    temp_reading_age_sec: int = 0
    is_network_connected: bool = True
    local_button_triggered: bool = False
    local_button_desired_state: RelayState = RelayState.OFF


@dataclass
class ControllerDecision:
    computed_relay_state: RelayState
    decision_source: CommandSource
    guard_result: GuardResult


class SmartSocketController:
    def __init__(
        self,
        config: Optional[ControllerConfig] = None,
        safety_config: Optional[SafetyConfig] = None,
    ):
        self.config = config or ControllerConfig()
        self.safety_guard = SafetyGuard(safety_config)

    def step(self, state: ControllerState) -> ControllerDecision:
        cfg = self.config
        requested_state = state.current_relay_state
        source = CommandSource.AUTO_RULE

        # 1. Local physical button has overriding priority
        if state.local_button_triggered:
            requested_state = state.local_button_desired_state
            source = CommandSource.LOCAL_BUTTON
        # 2. Manual mode
        elif cfg.mode == ControlMode.MANUAL:
            requested_state = cfg.manual_desired_state
            source = CommandSource.REMOTE
        # 3. Auto mode with device-specific hysteresis
        else:
            source = CommandSource.AUTO_RULE
            if not state.has_valid_temp or state.last_valid_temp is None:
                requested_state = (
                    RelayState.ON if cfg.device_type == DeviceType.COMPRESSOR else RelayState.OFF
                )
            else:
                t = state.last_valid_temp
                h = cfg.hysteresis

                if cfg.device_type == DeviceType.COOLING:
                    # Cooling: ON if T > maxTemp, OFF if T < (maxTemp - h)
                    if t > cfg.target_max_temp:
                        requested_state = RelayState.ON
                    elif t < (cfg.target_max_temp - h):
                        requested_state = RelayState.OFF

                elif cfg.device_type == DeviceType.HEATING:
                    # Heating: ON if T < minTemp, OFF if T > (minTemp + h)
                    if t < cfg.target_min_temp:
                        requested_state = RelayState.ON
                    elif t > (cfg.target_min_temp + h):
                        requested_state = RelayState.OFF

                elif cfg.device_type == DeviceType.COMPRESSOR:
                    # Refrigerator: ON when T > target_max_temp, OFF when T < target_min_temp
                    if t > cfg.target_max_temp:
                        requested_state = RelayState.ON
                    elif t < cfg.target_min_temp:
                        requested_state = RelayState.OFF

                else:
                    if t < cfg.target_min_temp:
                        requested_state = RelayState.OFF
                    elif t > cfg.target_max_temp:
                        requested_state = RelayState.ON

        # 4. Filter strictly through Safety Guard
        guard_input = GuardInput(
            requested_state=requested_state,
            source=source,
            device_type=cfg.device_type,
            current_temp=state.last_valid_temp,
            has_temp_reading=state.has_valid_temp,
            temp_reading_age_sec=state.temp_reading_age_sec,
            current_relay_state=state.current_relay_state,
            current_runtime_sec=state.current_runtime_sec,
            time_since_last_turn_off_sec=state.time_since_last_turn_off_sec,
            remote_heating_timer_sec=cfg.remote_heating_timer_sec,
        )

        guard_res = self.safety_guard.evaluate(guard_input)
        final_state = guard_res.allowed_state
        final_source = CommandSource.GUARD if guard_res.modified else source

        return ControllerDecision(
            computed_relay_state=final_state,
            decision_source=final_source,
            guard_result=guard_res,
        )
