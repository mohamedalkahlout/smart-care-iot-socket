"""
Independent Safety Guard module for Smart IoT Socket.
Validates any requested actuator command before reaching the relay.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeviceType(str, Enum):
    COOLING = "cooling"
    HEATING = "heating"
    COMPRESSOR = "compressor"
    GENERIC = "generic"


class CommandSource(str, Enum):
    LOCAL_BUTTON = "local_button"
    REMOTE = "remote"
    AUTO_RULE = "auto_rule"
    AI = "ai"
    SCHEDULE = "schedule"
    GUARD = "guard"


class RelayState(int, Enum):
    OFF = 0
    ON = 1


@dataclass
class SafetyConfig:
    absolute_min_temp: float = 5.0
    absolute_max_temp: float = 45.0
    heating_cutoff_temp: float = 35.0
    cooling_cutoff_temp: float = 10.0
    sensor_max_age_sec: int = 30
    max_runtime_heating_sec: int = 1800     # 30 min
    max_runtime_cooling_sec: int = 14400    # 4 hours
    max_runtime_compressor_sec: int = 7200  # 2 hours
    max_runtime_generic_sec: int = 7200
    compressor_min_off_sec: int = 180       # 3 min anti-short-cycle
    compressor_min_on_sec: int = 120        # 2 min
    max_remote_heating_timer_sec: int = 1800


@dataclass
class GuardInput:
    requested_state: RelayState
    source: CommandSource
    device_type: DeviceType
    current_temp: Optional[float]
    has_temp_reading: bool
    temp_reading_age_sec: int
    current_relay_state: RelayState
    current_runtime_sec: int
    time_since_last_turn_off_sec: int
    remote_heating_timer_sec: int = 0


@dataclass
class GuardResult:
    allowed_state: RelayState
    modified: bool
    reason_code: str
    reason_desc: str


class SafetyGuard:
    def __init__(self, config: Optional[SafetyConfig] = None):
        self.config = config or SafetyConfig()

    def evaluate(self, inp: GuardInput) -> GuardResult:
        cfg = self.config

        # Rule 1: Emergency / Normal Shutdown is ALWAYS permitted
        if inp.requested_state == RelayState.OFF:
            return GuardResult(
                allowed_state=RelayState.OFF,
                modified=False,
                reason_code="SHUTDOWN_PERMITTED",
                reason_desc="Turn off request granted immediately",
            )

        # --- Requested state is RelayState.ON ---

        # Rule 2: Absolute Max Temperature Cutoff
        if inp.has_temp_reading and inp.current_temp is not None:
            if inp.current_temp >= cfg.absolute_max_temp:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="ABSOLUTE_OVERHEAT",
                    reason_desc="Temperature exceeds absolute maximum threshold (45 C)",
                )

        # Rule 3: Heating Device Safety Limit Cutoff
        if inp.device_type == DeviceType.HEATING and inp.has_temp_reading and inp.current_temp is not None:
            if inp.current_temp >= cfg.heating_cutoff_temp:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="HEATER_HIGH_TEMP_CUTOFF",
                    reason_desc="Room temperature exceeds safe heating limit (35 C)",
                )

        # Rule 4: Cooling Device Overfreeze Cutoff
        if inp.device_type == DeviceType.COOLING and inp.has_temp_reading and inp.current_temp is not None:
            if inp.current_temp <= cfg.cooling_cutoff_temp:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="COOLER_LOW_TEMP_CUTOFF",
                    reason_desc="Room temperature below safe cooling limit (10 C)",
                )

        # Rule 5: Stale or Missing Sensor Reading
        if not inp.has_temp_reading or inp.temp_reading_age_sec > cfg.sensor_max_age_sec:
            if inp.device_type == DeviceType.HEATING:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="SENSOR_STALE_HEATER_SHUTDOWN",
                    reason_desc="Sensor reading stale/missing; heater forced OFF for fire safety",
                )
            elif inp.device_type == DeviceType.COOLING:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="SENSOR_STALE_COOLER_SHUTDOWN",
                    reason_desc="Sensor reading stale/missing; cooler forced OFF",
                )
            elif inp.device_type == DeviceType.COMPRESSOR:
                if (
                    inp.current_relay_state == RelayState.OFF
                    and inp.time_since_last_turn_off_sec < cfg.compressor_min_off_sec
                ):
                    return GuardResult(
                        allowed_state=RelayState.OFF,
                        modified=True,
                        reason_code="COMPRESSOR_ANTICYCLE_WAIT",
                        reason_desc="Sensor stale but compressor must satisfy minimum OFF time",
                    )
                return GuardResult(
                    allowed_state=RelayState.ON,
                    modified=(inp.requested_state != RelayState.ON),
                    reason_code="SENSOR_STALE_FRIDGE_PRESERVE",
                    reason_desc="Sensor reading stale; refrigerator kept ON to protect perishables",
                )

        # Rule 6: Compressor Anti-Short-Cycle Protection
        if inp.device_type == DeviceType.COMPRESSOR:
            if (
                inp.current_relay_state == RelayState.OFF
                and inp.time_since_last_turn_off_sec < cfg.compressor_min_off_sec
            ):
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="COMPRESSOR_SHORT_CYCLE_PREVENTED",
                    reason_desc=f"Compressor off-duration less than {cfg.compressor_min_off_sec}s; delayed",
                )

        # Rule 7: Maximum Continuous Runtime
        if inp.current_relay_state == RelayState.ON:
            limit = cfg.max_runtime_generic_sec
            if inp.device_type == DeviceType.HEATING:
                limit = cfg.max_runtime_heating_sec
            elif inp.device_type == DeviceType.COOLING:
                limit = cfg.max_runtime_cooling_sec
            elif inp.device_type == DeviceType.COMPRESSOR:
                limit = cfg.max_runtime_compressor_sec

            if inp.current_runtime_sec >= limit:
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="MAX_RUNTIME_EXCEEDED",
                    reason_desc="Maximum continuous operational runtime exceeded; forced cooldown",
                )

        # Rule 8: Remote Heating Mandates Auto-Off Timer
        if inp.device_type == DeviceType.HEATING and inp.source == CommandSource.REMOTE:
            if (
                inp.remote_heating_timer_sec <= 0
                or inp.remote_heating_timer_sec > cfg.max_remote_heating_timer_sec
            ):
                return GuardResult(
                    allowed_state=RelayState.OFF,
                    modified=True,
                    reason_code="REMOTE_HEATING_TIMER_REQUIRED",
                    reason_desc="Remote heater activation requires positive timeout <= 30 mins",
                )

        # Allowed
        return GuardResult(
            allowed_state=RelayState.ON,
            modified=False,
            reason_code="ALLOWED",
            reason_desc="Requested state complies with all safety rules",
        )
