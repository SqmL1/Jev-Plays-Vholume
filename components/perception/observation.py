from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    timestamp_s: float

    forward_velocity_u: int | None
    forward_velocity_confidence: float

    above_target_velocity: bool | None