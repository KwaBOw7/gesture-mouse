"""Central configuration for GestureMouse."""

import copy
import json
import platform
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "gesture_mouse_config.json"

DEFAULT_CONFIG = {
    "camera": {"width": 1280, "height": 720},
    "model_path": str(BASE_DIR / "models" / "hand_landmarker.task"),
    "tracking": {
        "detection_confidence": 0.55,
        "presence_confidence": 0.55,
        "tracking_confidence": 0.55,
        "min_smoothing": 0.30,
        "max_smoothing": 0.72,
        "max_landmark_jump": 0.20,
        "max_missing_frames": 5,
    },
    "pinch": {
        "start": 0.040,
        "release": 0.060,
        "start_normalized": 0.42,
        "release_normalized": 0.60,
    },
    "click": {"cooldown": 0.35},
    "gesture_history_size": 6,
    "gesture_majority": 4,
    "gesture_hold_frames": 3,
    "fist_pinch_ratio": 1.35,
    "finger_geometry": {
        "extended_angle": 150,
        "extended_dip_angle": 145,
        "extended_reach": 1.35,
        "max_chain_ratio": 1.32,
        "thumb_mcp_angle": 145,
        "thumb_ip_angle": 145,
        "thumb_reach": 1.25,
        "thumb_palm_clearance": 0.72,
    },
    "cursor": {
        "frame_margin": 100,
        "smoothing": 0.35,
        "screen_edge_padding": 2,
        "deadband": 0.008,
    },
    "motion": {
        "window_seconds": 0.35,
        "swipe_distance": 0.18,
        "swipe_min_duration": 0.15,
        "swipe_max_duration": 0.8,
        "swipe_cooldown": 0.6,
        "scroll_step_distance": 0.025,
        "scroll_tick_cooldown": 0.08,
        "two_finger_intent_delay": 0.18,
    },
    "gesture_action_map": {
        "PINCH": "LEFT_CLICK",
        "THREE_FINGER": "COPY",
        "FOUR_FINGER": "PASTE",
        "THUMB_UP": "NEW_TAB",
        "OK_SIGN": "CLOSE_TAB",
    },
    "platform": platform.system(),
}


def load_config():
    config = copy.deepcopy(DEFAULT_CONFIG)
    if CONFIG_PATH.is_file():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _deep_merge(config, json.load(f))
    return config


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _deep_merge(base, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
