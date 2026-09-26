import cv2 as cv

from components.sources.video_source import VideoSource
from components.perception.forward_velocity_reader import ForwardVelocityReader

from pathlib import Path

CAPTURE_DIR = Path("digit_captures")

VIDEO_PATH = "material/ozempic08.mp4"


def main():
    source = VideoSource(VIDEO_PATH)

    reader = ForwardVelocityReader()

    paused = False

    try:
        for frame_number, (frame, timestamp_s) in enumerate(
            source.frames()
        ):
            debug = reader.debug(frame)

            display_frame = debug.annotated_frame.copy()

            cv.putText(
                display_frame,
                f"Frame: {frame_number}",
                (20, 30),
                cv.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv.LINE_AA,
            )

            cv.putText(
                display_frame,
                f"Time: {timestamp_s:.3f}s",
                (20, 60),
                cv.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv.LINE_AA,
            )

            cv.imshow(
                "Velocity Debug - Frame",
                display_frame,
            )

            # Scale the tiny HUD crop up so it's easy to inspect.
            crop_large = cv.resize(
                debug.crop,
                None,
                fx=6,
                fy=6,
                interpolation=cv.INTER_NEAREST,
            )

            mask_large = cv.resize(
                debug.mask,
                None,
                fx=6,
                fy=6,
                interpolation=cv.INTER_NEAREST,
            )

            cv.imshow(
                "Velocity Debug - Crop",
                crop_large,
            )

            cv.imshow(
                "Velocity Debug - Threshold",
                mask_large,
            )

            key = cv.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord(" "):
                pause(
                    display_frame,
                    debug,
                    frame_number,
                    timestamp_s,
                )

            if key == ord("s"):
                save_digit_capture(
                    debug,
                    frame_number,
                    timestamp_s,
                )
                

    finally:
        source.close()
        cv.destroyAllWindows()

def save_digit_capture(
    debug,
    frame_number: int,
    timestamp_s: float,
):
    # Give every capture its own directory.
    capture_name = (
        f"frame_{frame_number:06d}_"
        f"time_{timestamp_s:.3f}"
    )

    capture_dir = CAPTURE_DIR / capture_name
    capture_dir.mkdir(parents=True, exist_ok=True)

    # Save the complete ROI for reference.
    cv.imwrite(
        str(capture_dir / "crop.png"),
        debug.crop,
    )

    # Save thresholded version too.
    cv.imwrite(
        str(capture_dir / "mask.png"),
        debug.mask,
    )

    # Save every detected digit individually.
    for index, (x, y, w, h) in enumerate(debug.digit_boxes):
        digit = debug.mask[
            y:y + h,
            x:x + w,
        ]

        filename = capture_dir / f"glyph_{index}.png"

        cv.imwrite(
            str(filename),
            digit,
        )

    print(
        f"Saved {len(debug.digit_boxes)} glyphs "
        f"to {capture_dir}"
    )

def pause(
    display_frame,
    debug,
    frame_number,
    timestamp_s,
):
    print(
        f"Paused at frame {frame_number}, "
        f"{timestamp_s:.3f}s"
    )

    while True:
        key = cv.waitKey(0) & 0xFF

        # Space resumes.
        if key == ord(" "):
            return

        # Q exits the pause and lets the main loop terminate
        # naturally on the next interaction.
        if key == ord("q"):
            return


if __name__ == "__main__":
    main()