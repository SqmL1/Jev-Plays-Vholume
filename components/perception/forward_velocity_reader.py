from dataclasses import dataclass
from pathlib import Path

import cv2 as cv
import numpy as np


@dataclass(frozen=True)
class VelocityReading:
    velocity_u: int | None
    confidence: float

    digits: str
    digit_confidences: tuple[float, ...]

    above_2600: bool | None


@dataclass
class VelocityDebugResult:
    annotated_frame: np.ndarray
    crop: np.ndarray
    mask: np.ndarray
    digit_boxes: list[tuple[int, int, int, int]]


class ForwardVelocityReader:
    TEMPLATE_WIDTH = 32
    TEMPLATE_HEIGHT = 48

    def __init__(
        self,
        template_dir: str,
        threshold: int = 180,
        minimum_match_confidence: float = 0.50,
    ):
        self.roi = (0.894, 0.125, 0.9625, 0.165)
        self.threshold = threshold
        self.minimum_match_confidence = minimum_match_confidence

        self.templates = self._load_templates(
            template_dir
        )

    def read(
        self,
        frame: np.ndarray,
    ) -> VelocityReading:

        crop = self._crop(frame)

        if crop.size == 0:
            return self._empty_reading()

        mask = self._preprocess(crop)

        boxes = self._find_glyph_boxes(mask)

        if not boxes:
            return self._empty_reading()

        recognized_digits = []
        confidences = []

        for x, y, w, h in boxes:
            glyph = mask[
                y:y + h,
                x:x + w,
            ]

            digit, confidence = self._recognize_digit(
                glyph
            )

            # Don't blindly build a velocity from a glyph
            # we're very unsure about.
            if confidence < self.minimum_match_confidence:
                continue

            recognized_digits.append(str(digit))
            confidences.append(confidence)

        if not recognized_digits:
            return self._empty_reading()

        digits = "".join(recognized_digits)

        try:
            velocity = int(digits)
        except ValueError:
            return self._empty_reading()

        confidence = min(confidences)

        above_2600 = velocity >= 2600

        return VelocityReading(
            velocity_u=velocity,
            confidence=confidence,
            digits=digits,
            digit_confidences=tuple(confidences),
            above_2600=above_2600,
        )

    def debug(
        self,
        frame: np.ndarray,
    ) -> VelocityDebugResult:

        crop = self._crop(frame)
        mask = self._preprocess(crop)

        boxes = self._find_glyph_boxes(mask)

        annotated_frame = frame.copy()
        annotated_crop = crop.copy()

        self._draw_normalized_grid(
            annotated_frame
        )

        x1, y1, x2, y2 = self._roi_pixels(frame)

        cv.rectangle(
            annotated_frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        left, top, right, bottom = self.roi

        cv.putText(
            annotated_frame,
            (
                f"ROI: ({left:.3f}, {top:.3f}) -> "
                f"({right:.3f}, {bottom:.3f})"
            ),
            (20, 45),
            cv.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv.LINE_AA,
        )

        for index, (x, y, w, h) in enumerate(boxes):
            glyph = mask[
                y:y + h,
                x:x + w,
            ]

            digit, confidence = self._recognize_digit(
                glyph
            )

            cv.rectangle(
                annotated_crop,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2,
            )

            cv.putText(
                annotated_crop,
                f"{digit} {confidence:.2f}",
                (x, max(12, y - 4)),
                cv.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 255, 0),
                1,
                cv.LINE_AA,
            )

        return VelocityDebugResult(
            annotated_frame=annotated_frame,
            crop=annotated_crop,
            mask=mask,
            digit_boxes=boxes,
        )

    # ---------------------------------------------------------
    # ROI
    # ---------------------------------------------------------

    def _roi_pixels(
        self,
        frame: np.ndarray,
    ) -> tuple[int, int, int, int]:

        height, width = frame.shape[:2]

        left, top, right, bottom = self.roi

        return (
            int(left * width),
            int(top * height),
            int(right * width),
            int(bottom * height),
        )

    def _crop(
        self,
        frame: np.ndarray,
    ) -> np.ndarray:

        x1, y1, x2, y2 = self._roi_pixels(frame)

        return frame[
            y1:y2,
            x1:x2,
        ]

    # ---------------------------------------------------------
    # Image processing
    # ---------------------------------------------------------

    def _preprocess(
        self,
        image: np.ndarray,
    ) -> np.ndarray:

        if image.ndim == 3:
            gray = cv.cvtColor(
                image,
                cv.COLOR_BGR2GRAY,
            )
        else:
            gray = image

        _, mask = cv.threshold(
            gray,
            self.threshold,
            255,
            cv.THRESH_BINARY,
        )

        return mask

    def _find_glyph_boxes(
        self,
        mask: np.ndarray,
    ) -> list[tuple[int, int, int, int]]:

        contours, _ = cv.findContours(
            mask,
            cv.RETR_EXTERNAL,
            cv.CHAIN_APPROX_SIMPLE,
        )

        image_height, _ = mask.shape

        boxes = []

        for contour in contours:
            x, y, w, h = cv.boundingRect(contour)

            # Ignore small compression/noise contours.
            if h < image_height * 0.35:
                continue

            if w < 2:
                continue

            boxes.append(
                (x, y, w, h)
            )

        # Velocity is read left -> right.
        boxes.sort(
            key=lambda box: box[0]
        )

        return boxes

    # ---------------------------------------------------------
    # Recognition
    # ---------------------------------------------------------

    def _recognize_digit(
        self,
        glyph: np.ndarray,
    ) -> tuple[int, float]:

        normalized = self._normalize_glyph(
            glyph
        )

        best_digit = -1
        best_score = -1.0

        for digit, template in self.templates.items():
            result = cv.matchTemplate(
                normalized,
                template,
                cv.TM_CCOEFF_NORMED,
            )

            score = float(result[0, 0])

            if score > best_score:
                best_digit = digit
                best_score = score

        # CCOEFF may theoretically return negatives.
        confidence = max(
            0.0,
            min(1.0, best_score),
        )

        return best_digit, confidence

    def _normalize_glyph(
        self,
        glyph: np.ndarray,
    ) -> np.ndarray:

        # Ensure glyph itself is binary.
        glyph = self._preprocess(glyph)

        contours, _ = cv.findContours(
            glyph,
            cv.RETR_EXTERNAL,
            cv.CHAIN_APPROX_SIMPLE,
        )

        if contours:
            points = np.vstack(contours)

            x, y, w, h = cv.boundingRect(points)

            glyph = glyph[
                y:y + h,
                x:x + w,
            ]

        source_h, source_w = glyph.shape

        inner_width = self.TEMPLATE_WIDTH - 4
        inner_height = self.TEMPLATE_HEIGHT - 4

        scale = min(
            inner_width / max(source_w, 1),
            inner_height / max(source_h, 1),
        )

        new_width = max(
            1,
            int(source_w * scale),
        )

        new_height = max(
            1,
            int(source_h * scale),
        )

        resized = cv.resize(
            glyph,
            (new_width, new_height),
            interpolation=cv.INTER_NEAREST,
        )

        canvas = np.zeros(
            (
                self.TEMPLATE_HEIGHT,
                self.TEMPLATE_WIDTH,
            ),
            dtype=np.uint8,
        )

        x_offset = (
            self.TEMPLATE_WIDTH - new_width
        ) // 2

        y_offset = (
            self.TEMPLATE_HEIGHT - new_height
        ) // 2

        canvas[
            y_offset:y_offset + new_height,
            x_offset:x_offset + new_width,
        ] = resized

        return canvas

    def _load_templates(
        self,
        directory: str,
    ) -> dict[int, np.ndarray]:

        directory = Path(directory)

        templates = {}

        for digit in range(10):
            path = (
                directory
                / f"glyph_{digit}.png"
            )

            image = cv.imread(
                str(path),
                cv.IMREAD_GRAYSCALE,
            )

            if image is None:
                raise FileNotFoundError(
                    f"Missing digit template: {path}"
                )

            templates[digit] = (
                self._normalize_glyph(image)
            )

        return templates

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def _empty_reading(
        self,
    ) -> VelocityReading:

        return VelocityReading(
            velocity_u=None,
            confidence=0.0,
            digits="",
            digit_confidences=(),
            above_2600=None,
        )

    def _draw_normalized_grid(
        self,
        frame: np.ndarray,
        step: float = 0.1,
    ) -> None:

        height, width = frame.shape[:2]

        divisions = round(1.0 / step)

        for i in range(divisions + 1):
            value = i * step

            x = min(
                int(value * width),
                width - 1,
            )

            y = min(
                int(value * height),
                height - 1,
            )

            cv.line(
                frame,
                (x, 0),
                (x, height - 1),
                (100, 100, 100),
                1,
            )

            cv.line(
                frame,
                (0, y),
                (width - 1, y),
                (100, 100, 100),
                1,
            )

            label = f"{value:.1f}"

            cv.putText(
                frame,
                label,
                (
                    min(x + 3, width - 40),
                    18,
                ),
                cv.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv.LINE_AA,
            )

            cv.putText(
                frame,
                label,
                (
                    5,
                    max(15, y - 4),
                ),
                cv.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv.LINE_AA,
            )