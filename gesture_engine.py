"""Gesture state machine with confidence-oriented temporal stabilization."""

import time
from collections import Counter, deque

from landmark_processor import (
    classify_static_shape,
    distance,
    get_diagnostics,
    palm_size,
    INDEX_TIP,
    MIDDLE_TIP,
    THUMB_TIP,
)
from motion import MotionTracker

STATIC_ACTION_GESTURES = {
    "THREE_FINGER",
    "FOUR_FINGER",
    "THUMB_UP",
    "OK_SIGN",
}


class GestureStabilizer:
    """Reject one-frame mistakes and prefer the most persistent gesture."""

    def __init__(self, history_size=6, majority=4, hold_frames=3):
        self.history = deque(maxlen=history_size)
        self.history_size = history_size
        self.majority = majority
        self.hold_frames = hold_frames
        self.candidate = "UNKNOWN"
        self.candidate_count = 0
        self.stable = "UNKNOWN"

    def reset(self):
        self.history.clear()
        self.candidate = "UNKNOWN"
        self.candidate_count = 0
        self.stable = "UNKNOWN"

    def update(self, raw_shape):
        self.history.append(raw_shape)

        if raw_shape == self.candidate:
            self.candidate_count += 1
        else:
            self.candidate = raw_shape
            self.candidate_count = 1

        counts = Counter(self.history)
        best, count = counts.most_common(1)[0]

        # UNKNOWN never displaces a good stable gesture immediately.
        if best == "UNKNOWN":
            if self.candidate_count >= self.hold_frames and self.stable != "UNKNOWN":
                return self.stable
            return "UNKNOWN"

        if count >= self.majority and self.candidate_count >= self.hold_frames:
            self.stable = best

        return self.stable


class GestureEngine:
    def __init__(self, config):
        self.config = config
        self.stabilizer = GestureStabilizer(
            config.get("gesture_history_size", 6),
            config.get("gesture_majority", 4),
            config.get("gesture_hold_frames", 3),
        )
        self.motion = MotionTracker(config["motion"]["window_seconds"])
        self.previous_stable_shape = "UNKNOWN"
        self.pinch_active = False
        self.locked_gesture = None
        self.last_action_times = {}
        self.last_scroll_tick = 0.0
        self.last_swipe_time = 0.0
        self.two_finger_since = None
        self.two_finger_clicked = False
        self.two_finger_scrolled = False

    def reset(self):
        self.stabilizer.reset()
        self.motion.reset()
        self.previous_stable_shape = "UNKNOWN"
        self.pinch_active = False
        self.locked_gesture = None
        self.two_finger_since = None
        self.two_finger_clicked = False
        self.two_finger_scrolled = False

    def action_ready(self, action, now):
        cooldown = self.config["click"]["cooldown"]
        return now - self.last_action_times.get(action, 0.0) >= cooldown

    def mark_action(self, action, now):
        self.last_action_times[action] = now

    def step(self, points):
        now = time.monotonic()
        cfg = self.config
        raw = classify_static_shape(points, cfg)
        stable = self.stabilizer.update(raw)
        actions = []

        # Only POINT drives the cursor. Letting every gesture move it
        # (as this used to) makes the pointer jump mid-click, mid-scroll
        # and mid-swipe, since the hand never holds perfectly still while
        # forming PINCH/TWO_FINGER/etc.
        cursor_target = points[INDEX_TIP] if stable == "POINT" else None

        if stable == "FIST":
            self.pinch_active = False
            self.locked_gesture = None
            self.motion.reset()
            self.two_finger_since = None
            self.two_finger_clicked = False
            self.two_finger_scrolled = False

        # Normalized by palm size, matching how PINCH is classified in the
        # first place - the old raw-distance check here didn't scale with
        # how close the hand is to the camera and could leave a pinch
        # "stuck" active depending on distance.
        pinch_distance = distance(points[THUMB_TIP], points[INDEX_TIP]) / palm_size(points)
        if stable == "PINCH":
            if (
                not self.pinch_active
                and self.locked_gesture is None
                and self.action_ready("LEFT_CLICK", now)
            ):
                actions.append("LEFT_CLICK")
                self.pinch_active = True
                self.locked_gesture = "PINCH"
                self.mark_action("LEFT_CLICK", now)

        if self.pinch_active and pinch_distance >= cfg["pinch"]["release_normalized"]:
            self.pinch_active = False
            if self.locked_gesture == "PINCH":
                self.locked_gesture = None

        if stable == "TWO_FINGER":
            motion_point = (
                (points[INDEX_TIP][0] + points[MIDDLE_TIP][0]) / 2,
                (points[INDEX_TIP][1] + points[MIDDLE_TIP][1]) / 2,
            )
            if self.previous_stable_shape != "TWO_FINGER":
                self.two_finger_since = now
                self.two_finger_clicked = False
                self.two_finger_scrolled = False
                self.motion.reset()
                self.motion.update(motion_point, now)
            else:
                self.motion.update(motion_point, now)
                dx, dy = self.motion.displacement()
                motion_cfg = cfg["motion"]
                if abs(dy) >= motion_cfg["scroll_step_distance"]:
                    if now - self.last_scroll_tick >= motion_cfg["scroll_tick_cooldown"]:
                        actions.append("SCROLL_UP" if dy < 0 else "SCROLL_DOWN")
                        self.last_scroll_tick = now
                        self.two_finger_scrolled = True
                        self.motion.reset()
                        self.motion.update(motion_point, now)
                elif (
                    not self.two_finger_clicked
                    and not self.two_finger_scrolled
                    and self.two_finger_since is not None
                    and now - self.two_finger_since >= motion_cfg["two_finger_intent_delay"]
                    and self.action_ready("RIGHT_CLICK", now)
                ):
                    actions.append("RIGHT_CLICK")
                    self.two_finger_clicked = True
                    self.locked_gesture = "TWO_FINGER"
                    self.mark_action("RIGHT_CLICK", now)
        else:
            self.two_finger_since = None
            self.two_finger_clicked = False
            self.two_finger_scrolled = False
            if self.locked_gesture == "TWO_FINGER":
                self.locked_gesture = None

        if stable == "OPEN_PALM":
            if self.previous_stable_shape != "OPEN_PALM":
                self.motion.reset()
                self.motion.update(points[INDEX_TIP], now)
            else:
                self.motion.update(points[INDEX_TIP], now)
                dx, dy = self.motion.displacement()
                duration = self.motion.duration()
                motion_cfg = cfg["motion"]
                swipe_ready = (
                    motion_cfg["swipe_min_duration"]
                    <= duration
                    <= motion_cfg["swipe_max_duration"]
                    and now - self.last_swipe_time >= motion_cfg["swipe_cooldown"]
                )
                if (
                    swipe_ready
                    and abs(dx) >= motion_cfg["swipe_distance"]
                    and abs(dx) > abs(dy) * 1.5
                ):
                    actions.append("BACK" if dx < 0 else "FORWARD")
                    self.last_swipe_time = now
                    self.motion.reset()

        if stable in STATIC_ACTION_GESTURES:
            changed = stable != self.previous_stable_shape
            if changed and self.locked_gesture is None:
                action = cfg["gesture_action_map"].get(stable)
                if action and self.action_ready(action, now):
                    actions.append(action)
                    self.locked_gesture = stable
                    self.mark_action(action, now)

        if stable in ("UNKNOWN", "POINT", "FIST"):
            if stable == "FIST":
                self.locked_gesture = None
            elif self.locked_gesture and self.locked_gesture not in ("PINCH", "TWO_FINGER"):
                self.locked_gesture = None

        self.previous_stable_shape = stable
        return {
            "actions": actions,
            "raw_shape": raw,
            "stable_shape": stable,
            "cursor_target": cursor_target,
            "diagnostics": get_diagnostics(points, cfg),
            "paused": False,
        }
