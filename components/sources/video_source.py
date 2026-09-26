import cv2 as cv


class VideoSource:
    def __init__(self, path: str):
        self.cap = cv.VideoCapture(path)

    def frames(self):
        while True:
            success, frame = self.cap.read()

            if not success:
                break

            timestamp_ms = self.cap.get(cv.CAP_PROP_POS_MSEC)

            yield frame, timestamp_ms / 1000.0

    def close(self):
        self.cap.release()