import numpy as np

from .forward_velocity_reader import ForwardVelocityReader
from .observation import Observation


class Perception:
    def __init__(
        self,
        velocity_reader: ForwardVelocityReader,
    ):
        self.velocity_reader = velocity_reader

    def process(
        self,
        frame: np.ndarray,
        timestamp_s: float,
    ) -> Observation:

        velocity = self.velocity_reader.read(
            frame
        )

        return Observation(
            timestamp_s=timestamp_s,
            forward_velocity_u=velocity.velocity_u,
            forward_velocity_confidence=velocity.confidence,
            above_target_velocity=velocity.above_2600,
        )