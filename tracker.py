"""MediaPipe hand tracking + landmark stabilization."""

import time
import urllib.request
from pathlib import Path

import cv2 as cv
import mediapipe as mp

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)


def ensure_model(model_path):
    path = Path(model_path)
    if path.is_file() and path.stat().st_size > 100_000:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print("MediaPipe hand model not found. Downloading it once...")
    try:
        urllib.request.urlretrieve(MODEL_URL, path)
    except Exception as exc:
        raise RuntimeError(
            "Could not download hand_landmarker.task. "
            "Check your internet connection and run the program again."
        ) from exc
    if not path.is_file() or path.stat().st_size <= 100_000:
        raise RuntimeError("The MediaPipe hand model download was incomplete.")


class HandTracker:
    def __init__(self, config):
        self.config = config
        tracking_cfg = config["tracking"]
        ensure_model(config["model_path"])

        base_options = mp.tasks.BaseOptions(model_asset_path=config["model_path"])
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=tracking_cfg["detection_confidence"],
            min_hand_presence_confidence=tracking_cfg["presence_confidence"],
            min_tracking_confidence=tracking_cfg["tracking_confidence"],
        )
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1
        self._previous_points = None
        self.min_smoothing = tracking_cfg["min_smoothing"]
        self.max_smoothing = tracking_cfg["max_smoothing"]
        self.max_jump = tracking_cfg["max_landmark_jump"]
        self.max_missing_frames = tracking_cfg["max_missing_frames"]
        self.missing_frames = 0

    def close(self):
        self.landmarker.close()

    def reset_smoothing(self):
        self._previous_points = None

    def process(self, frame_bgr):
        rgb_frame = cv.cvtColor(frame_bgr, cv.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(time.time() * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.hand_landmarks:
            self.missing_frames += 1
            if self.missing_frames > self.max_missing_frames:
                self.reset_smoothing()
            return None

        self.missing_frames = 0
        raw_points = [(lm.x, lm.y) for lm in result.hand_landmarks[0]]
        return self._stabilize(raw_points)

    def _stabilize(self, current_points):
        if self._previous_points is None:
            self._previous_points = current_points
            return current_points

        stabilized = []
        for current, previous in zip(current_points, self._previous_points):
            cx, cy = current
            px, py = previous
            dx, dy = cx - px, cy - py
            movement = (dx * dx + dy * dy) ** 0.5
            if movement > self.max_jump:
                stabilized.append(previous)
                continue
            movement_ratio = min(movement / self.max_jump, 1.0)
            # Heavier smoothing (low alpha) when nearly still kills jitter;
            # lighter smoothing (high alpha) when moving fast keeps the
            # cursor from lagging behind the hand. The formula here was
            # inverted - it was doing the opposite of both.
            smoothing = (
                self.min_smoothing + (self.max_smoothing - self.min_smoothing) * movement_ratio
            )
            stabilized.append((px + dx * smoothing, py + dy * smoothing))

        self._previous_points = stabilized
        return stabilized
