"""Cursor controller."""

import pyautogui

from landmark_processor import map_range


class CursorController:

    def __init__(self, config):
        self.config = config
        self.screen_width, self.screen_height = pyautogui.size()
        self.x = self.screen_width // 2
        self.y = self.screen_height // 2
        self._last_norm = None

    def move_to_normalized(self, norm_x, norm_y, frame_width, frame_height):
        cfg = self.config["cursor"]
        deadband = cfg.get("deadband", 0.0)

        if self._last_norm is not None:
            last_x, last_y = self._last_norm
            if abs(norm_x - last_x) < deadband and abs(norm_y - last_y) < deadband:
                return
        self._last_norm = (norm_x, norm_y)

        margin = cfg["frame_margin"]
        pixel_x = norm_x * frame_width
        pixel_y = norm_y * frame_height

        target_x = map_range(pixel_x, margin, frame_width - margin, 0, self.screen_width)
        target_y = map_range(pixel_y, margin, frame_height - margin, 0, self.screen_height)

        padding = cfg["screen_edge_padding"]
        target_x = max(padding, min(self.screen_width - padding, target_x))
        target_y = max(padding, min(self.screen_height - padding, target_y))

        smoothing = cfg["smoothing"]
        self.x += (target_x - self.x) * smoothing
        self.y += (target_y - self.y) * smoothing

        pyautogui.moveTo(int(self.x), int(self.y))
