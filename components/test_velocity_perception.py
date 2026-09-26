import csv

from sources.video_source import VideoSource

from perception.forward_velocity_reader import (
    ForwardVelocityReader,
)
from perception.perception import Perception


VIDEO_PATH = "./material/ozempic08.mp4"

OUTPUT_PATH = "velocity_trace.csv"

TEMPLATE_DIR = "digit_captures"


def main():
    source = VideoSource(
        VIDEO_PATH
    )

    velocity_reader = ForwardVelocityReader(
        template_dir=TEMPLATE_DIR,
        threshold=180,
        minimum_match_confidence=0.50,
    )

    perception = Perception(
        velocity_reader
    )

    rows = []

    total_frames = 0
    successful_frames = 0

    try:
        for frame, timestamp_s in source.frames():
            total_frames += 1

            observation = perception.process(
                frame,
                timestamp_s,
            )

            velocity = (
                observation.forward_velocity_u
            )

            confidence = (
                observation.forward_velocity_confidence
            )

            if velocity is not None:
                successful_frames += 1

            rows.append({
                "timestamp_s": timestamp_s,
                "velocity_u": velocity,
                "confidence": confidence,
                "above_2600": (
                    observation.above_target_velocity
                ),
            })

            print(
                f"{timestamp_s:8.3f}s | "
                f"velocity={str(velocity):>5} | "
                f"confidence={confidence:.2f}"
            )

    finally:
        source.close()

    with open(
        OUTPUT_PATH,
        "w",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp_s",
                "velocity_u",
                "confidence",
                "above_2600",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    coverage = (
        successful_frames / total_frames
        if total_frames
        else 0
    )

    print()
    print("Finished")
    print(f"Frames: {total_frames}")
    print(
        f"Recognized: {successful_frames}"
    )
    print(
        f"Coverage: {coverage:.1%}"
    )
    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()