"""
Comfort Range Learner (P4.4).
Learns personalized user comfort setpoints from local physical overrides.
Separates Day (07:00-22:00) and Night (22:00-07:00) profiles.
Uses Exponential Moving Averages (EMA) with dampening rate and reset capability.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ComfortProfile:
    day_target_min: float = 21.0
    day_target_max: float = 25.0
    night_target_min: float = 19.5
    night_target_max: float = 23.5
    adaptation_rate: float = 0.15  # Smooth EMA update rate
    samples_count: int = 0


class ComfortLearner:
    def __init__(self, initial_profile: Optional[ComfortProfile] = None):
        self.profile = initial_profile or ComfortProfile()

    def record_manual_override(self, hour_of_day: int, room_temp: float, desired_action: str):
        """
        desired_action: "cool_more" (temp too high), "warm_more" (temp too low), or "satisfied"
        """
        is_day = 7 <= hour_of_day < 22
        alpha = self.profile.adaptation_rate

        if is_day:
            if desired_action == "cool_more" and room_temp > self.profile.day_target_max:
                # User wants it cooler during the day
                self.profile.day_target_max = (1 - alpha) * self.profile.day_target_max + alpha * room_temp
            elif desired_action == "warm_more" and room_temp < self.profile.day_target_min:
                # User feels cold during the day
                self.profile.day_target_min = (1 - alpha) * self.profile.day_target_min + alpha * room_temp
        else:
            if desired_action == "cool_more" and room_temp > self.profile.night_target_max:
                self.profile.night_target_max = (1 - alpha) * self.profile.night_target_max + alpha * room_temp
            elif desired_action == "warm_more" and room_temp < self.profile.night_target_min:
                self.profile.night_target_min = (1 - alpha) * self.profile.night_target_min + alpha * room_temp

        # Ensure min is always strictly less than max with at least 1.5 C band
        self.profile.day_target_max = max(self.profile.day_target_max, self.profile.day_target_min + 1.5)
        self.profile.night_target_max = max(self.profile.night_target_max, self.profile.night_target_min + 1.5)
        self.profile.samples_count += 1

    def get_current_setpoints(self, hour_of_day: int) -> Dict[str, float]:
        if 7 <= hour_of_day < 22:
            return {"minTemp": round(self.profile.day_target_min, 1), "maxTemp": round(self.profile.day_target_max, 1), "period": "day"}
        return {"minTemp": round(self.profile.night_target_min, 1), "maxTemp": round(self.profile.night_target_max, 1), "period": "night"}

    def reset_to_defaults(self):
        self.profile = ComfortProfile()
