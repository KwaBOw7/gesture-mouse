"""
actions.py

Executes named actions on the computer. Gesture detection
never touches pyautogui directly - it only decides *what*
should happen (an action name); this module decides *how*,
including per-platform hotkey differences.
"""

import platform

import pyautogui


class ActionController:

    def __init__(self, config):
        self.system = config.get("platform", platform.system())

    def _mod_key(self):
        return "command" if self.system == "Darwin" else "ctrl"

    def perform(self, action):
        handler = getattr(self, f"_action_{action.lower()}", None)

        if handler is None:
            print(f"[ActionController] No handler for '{action}'")
            return

        handler()
        print(action.replace("_", " "))

    # --- click / scroll -------------------------------------

    def _action_left_click(self):
        pyautogui.click()

    def _action_right_click(self):
        pyautogui.rightClick()

    def _action_scroll_up(self):
        pyautogui.scroll(3)

    def _action_scroll_down(self):
        pyautogui.scroll(-3)

    # --- clipboard --------------------------------------------

    def _action_copy(self):
        pyautogui.hotkey(self._mod_key(), "c")

    def _action_paste(self):
        pyautogui.hotkey(self._mod_key(), "v")

    # --- browser / tabs -----------------------------------------

    def _action_new_tab(self):
        pyautogui.hotkey(self._mod_key(), "t")

    def _action_close_tab(self):
        pyautogui.hotkey(self._mod_key(), "w")

    def _action_back(self):
        if self.system == "Darwin":
            pyautogui.hotkey("command", "[")
        else:
            pyautogui.hotkey("alt", "left")

    def _action_forward(self):
        if self.system == "Darwin":
            pyautogui.hotkey("command", "]")
        else:
            pyautogui.hotkey("alt", "right")

    # --- undo / redo ----------------------------------------------

    def _action_undo(self):
        pyautogui.hotkey(self._mod_key(), "z")

    def _action_redo(self):
        if self.system == "Darwin":
            pyautogui.hotkey("command", "shift", "z")
        else:
            pyautogui.hotkey("ctrl", "y")

    # --- desktop switching -------------------------------------------

    def _action_next_desktop(self):
        if self.system == "Darwin":
            pyautogui.hotkey("ctrl", "right")
        elif self.system == "Windows":
            pyautogui.hotkey("ctrl", "win", "right")
        else:
            pyautogui.hotkey("ctrl", "alt", "right")

    def _action_prev_desktop(self):
        if self.system == "Darwin":
            pyautogui.hotkey("ctrl", "left")
        elif self.system == "Windows":
            pyautogui.hotkey("ctrl", "win", "left")
        else:
            pyautogui.hotkey("ctrl", "alt", "left")
