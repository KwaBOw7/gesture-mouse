"""GestureMouse entry point."""

import time

import cv2 as cv
import pyautogui

from actions import ActionController
from config import load_config
from cursor import CursorController
from gesture_engine import GestureEngine
from tracker import HandTracker


def draw_landmarks(frame, points, frame_width, frame_height):
    for x, y in points:
        cv.circle(frame, (int(x * frame_width), int(y * frame_height)), 4, (0, 255, 0), -1)


def draw_overlay(frame, result, fps):
    cv.putText(
        frame, f"FPS: {fps:.0f}", (20, 32), cv.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2
    )
    if result is None:
        cv.putText(
            frame,
            "Gesture: NO HAND",
            (20, 64),
            cv.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        return

    cv.putText(
        frame,
        f"Gesture: {result['stable_shape']}",
        (20, 64),
        cv.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    cv.putText(
        frame,
        f"Raw: {result['raw_shape']}",
        (20, 94),
        cv.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
    )

    d = result.get("diagnostics", {})
    states = d.get("fingers", (False,) * 4)
    labels = ("I", "M", "R", "P")
    finger_text = "  ".join(
        f"{label}:{'ON' if state else 'OFF'}" for label, state in zip(labels, states)
    )
    cv.putText(
        frame, finger_text, (20, 122), cv.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2
    )
    cv.putText(
        frame,
        f"T:{'ON' if d.get('thumb') else 'OFF'}  Pinch:{d.get('pinch', 0):.2f}",
        (20, 148),
        cv.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        2,
    )


def main():
    config = load_config()
    pyautogui.FAILSAFE = True

    cam = cv.VideoCapture(0)
    cam.set(cv.CAP_PROP_FRAME_WIDTH, config["camera"]["width"])
    cam.set(cv.CAP_PROP_FRAME_HEIGHT, config["camera"]["height"])
    if not cam.isOpened():
        raise RuntimeError("Could not open webcam.")

    tracker = HandTracker(config)
    engine = GestureEngine(config)
    cursor = CursorController(config)
    actions = ActionController(config)

    previous_time = time.monotonic()
    fps = 0.0
    missing_hand_frames = 0
    max_missing_hand_frames = config["tracking"]["max_missing_frames"]

    print("GestureMouse started.")
    print("Press 'q' to quit.")
    print("Move the mouse to the top-left corner for the PyAutoGUI emergency stop.")

    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                print("Could not read camera frame.")
                break

            frame = cv.flip(frame, 1)
            frame_height, frame_width = frame.shape[:2]
            points = tracker.process(frame)

            if points is not None:
                missing_hand_frames = 0
                draw_landmarks(frame, points, frame_width, frame_height)
                result = engine.step(points)

                for action in result["actions"]:
                    actions.perform(action)

                cursor_target = result["cursor_target"]
                if cursor_target is not None:
                    cursor.move_to_normalized(*cursor_target, frame_width, frame_height)

                draw_overlay(frame, result, fps)
            else:
                missing_hand_frames += 1
                if missing_hand_frames > max_missing_hand_frames:
                    engine.reset()
                draw_overlay(frame, None, fps)

            current_time = time.monotonic()
            delta = current_time - previous_time
            previous_time = current_time
            if delta > 0:
                fps = fps * 0.9 + (1.0 / delta) * 0.1

            cv.imshow("GestureMouse - Camera Active", frame)
            if cv.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cam.release()
        cv.destroyAllWindows()
        tracker.close()
        print("GestureMouse stopped.")


if __name__ == "__main__":
    main()
