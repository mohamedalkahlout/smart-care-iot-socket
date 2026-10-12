"""
Safety Guard: Multi-Socket System Twin (Python Specification).
1:1 Mathematical & Rule Equivalence with firmware/src/safety_guard.c
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class SocketChannel(IntEnum):
    CHANNEL_1_THERMAL = 0
    CHANNEL_2_PUMP = 1
    CHANNEL_3_APPLIANCE = 2
    CHANNEL_4_AC = 3
    CHANNEL_COUNT = 4


class DeviceState(IntEnum):
    STATE_OFF = 0
    STATE_ON = 1


class ApplianceType(IntEnum):
    APPLIANCE_HEATER = 0
    APPLIANCE_COOLER = 1
    APPLIANCE_FRIDGE = 2
    APPLIANCE_WATER_PUMP = 3
    APPLIANCE_TV = 4
    APPLIANCE_AC = 5


class CommandSource(IntEnum):
    CMD_LOCAL_PHYSICAL = 0
    CMD_REMOTE_CLOUD = 1
    CMD_AUTOMATION = 2


@dataclass
class MultiSocketSafetyConfig:
    absolute_overheat_c: float = 45.0
    max_room_temp_c: float = 38.0
    min_freeze_temp_c: float = 2.0
    max_heater_runtime_sec: int = 7200
    compressor_anti_short_sec: int = 180
    max_pump_runtime_sec: int = 1200
    pump_cooldown_sec: int = 300
    max_tv_runtime_sec: int = 14400
    sensor_timeout_sec: int = 60
    master_emergency_shutdown: bool = False


@dataclass
class ChannelTelemetry:
    channel: SocketChannel
    current_state: DeviceState
    requested_state: DeviceState
    appliance_type: ApplianceType
    source: CommandSource
    current_temperature: float = 25.0
    is_temperature_valid: bool = True
    sensor_age_seconds: int = 0
    continuous_on_seconds: int = 0
    time_since_last_off_seconds: int = 600
    time_since_last_on_seconds: int = 600


@dataclass
class SafetyDecision:
    allowed: bool
    enforced_state: DeviceState
    reason_code: str


def safety_guard_evaluate_channel(
    telemetry: Optional[ChannelTelemetry],
    config: Optional[MultiSocketSafetyConfig]
) -> SafetyDecision:
    if telemetry is None or config is None:
        return SafetyDecision(allowed=False, enforced_state=DeviceState.STATE_OFF, reason_code="NULL_POINTER_REJECT")

    # Rule 0: Master Emergency Shutdown
    if config.master_emergency_shutdown:
        return SafetyDecision(
            allowed=(telemetry.requested_state == DeviceState.STATE_OFF),
            enforced_state=DeviceState.STATE_OFF,
            reason_code="EMERGENCY_SHUTDOWN_ACTIVE"
        )

    # Rule 1: Immediate OFF is always permitted
    if telemetry.requested_state == DeviceState.STATE_OFF:
        return SafetyDecision(
            allowed=True,
            enforced_state=DeviceState.STATE_OFF,
            reason_code="IMMEDIATE_OFF_PERMITTED"
        )

    # Rule 2: Absolute Overheat Protection
    if telemetry.is_temperature_valid and telemetry.current_temperature >= config.absolute_overheat_c:
        return SafetyDecision(
            allowed=False,
            enforced_state=DeviceState.STATE_OFF,
            reason_code="ABSOLUTE_OVERHEAT_CUTOFF"
        )

    # Rule 3: Channel 1 / Heater Continuous Runtime Ceiling
    if telemetry.appliance_type == ApplianceType.APPLIANCE_HEATER:
        if telemetry.current_state == DeviceState.STATE_ON and telemetry.continuous_on_seconds >= config.max_heater_runtime_sec:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="MAX_CONTINUOUS_RUNTIME_EXCEEDED"
            )
        if telemetry.is_temperature_valid and telemetry.current_temperature >= config.max_room_temp_c:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="HEATING_HIGH_ROOM_CUTOFF"
            )

    # Rule 4: Sensor Stale Fail-Safe for Thermal Channels
    if telemetry.appliance_type in (ApplianceType.APPLIANCE_HEATER, ApplianceType.APPLIANCE_COOLER, ApplianceType.APPLIANCE_FRIDGE, ApplianceType.APPLIANCE_AC):
        if not telemetry.is_temperature_valid or telemetry.sensor_age_seconds > config.sensor_timeout_sec:
            if telemetry.appliance_type == ApplianceType.APPLIANCE_HEATER:
                return SafetyDecision(
                    allowed=False,
                    enforced_state=DeviceState.STATE_OFF,
                    reason_code="SENSOR_STALE_HEATER_CUTOFF"
                )
            if telemetry.appliance_type == ApplianceType.APPLIANCE_FRIDGE:
                return SafetyDecision(
                    allowed=True,
                    enforced_state=DeviceState.STATE_ON,
                    reason_code="SENSOR_STALE_FRIDGE_FAILSAFE"
                )

    # Rule 5: Compressor Anti-Short-Cycle Protection (Fridge / AC)
    if telemetry.appliance_type in (ApplianceType.APPLIANCE_FRIDGE, ApplianceType.APPLIANCE_AC):
        if telemetry.current_state == DeviceState.STATE_OFF and telemetry.time_since_last_off_seconds < config.compressor_anti_short_sec:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="COMPRESSOR_ANTI_SHORT_CYCLE_WAIT"
            )

    # Rule 6 & 7: Channel 2 (Water Pump) Maximum Runtime & Cooldown
    if telemetry.appliance_type == ApplianceType.APPLIANCE_WATER_PUMP:
        if telemetry.current_state == DeviceState.STATE_ON and telemetry.continuous_on_seconds >= config.max_pump_runtime_sec:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="PUMP_MAX_RUNTIME_EXCEEDED"
            )
        if telemetry.current_state == DeviceState.STATE_OFF and telemetry.time_since_last_off_seconds < config.pump_cooldown_sec:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="PUMP_COOLDOWN_ACTIVE"
            )

    # Rule 8: Channel 3 (TV / Workstation) Auto Standby Cutoff
    if telemetry.appliance_type == ApplianceType.APPLIANCE_TV:
        if telemetry.current_state == DeviceState.STATE_ON and telemetry.continuous_on_seconds >= config.max_tv_runtime_sec:
            return SafetyDecision(
                allowed=False,
                enforced_state=DeviceState.STATE_OFF,
                reason_code="APPLIANCE_AUTO_OFF_TIMER"
            )

    return SafetyDecision(
        allowed=True,
        enforced_state=DeviceState.STATE_ON,
        reason_code="COMMAND_ALLOWED"
    )
