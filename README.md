# GestureMouse

Control your computer with hand gestures using only a webcam. GestureMouse tracks your hand with MediaPipe, classifies the gesture, and turns it into cursor movement, clicks, scrolling, copy/paste and browser shortcuts.

<!-- Add a demo GIF here: ![Demo](docs/demo.gif) -->

## Features

- Cursor control with your index finger
- Click, right-click, scroll, copy, paste, new/close tab, browser back/forward
- Gesture recognition based on hand geometry (joint angles, normalized hand size), not raw pixel distances
- Temporal filtering to reject one-frame misclassifications
- Live camera overlay showing FPS and the detected gesture
- Works on Windows, macOS and Linux (X11)

## Gestures

| Gesture | Action |
|---|---|
| POINT | Move cursor |
| PINCH | Left click |
| TWO_FINGER | Right click; move up/down to scroll |
| THREE_FINGER | Copy |
| FOUR_FINGER (thumb curled) | Paste |
| THUMB_UP | New tab |
| OK_SIGN | Close tab |
| OPEN_PALM + horizontal swipe | Browser back / forward |
| FIST | Neutral (no action) |

## Requirements

- Python 3.9–3.12
- A webcam
- Internet access on first run (downloads the MediaPipe hand model, ~8 MB, once)

## Installation

```bash
git clone https://github.com/<KwaBOw7>/gesture-mouse.git
cd gesture-mouse
python -m venv venv
```

Activate the environment:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

- Press **q** in the camera window to quit.
- Emergency stop: move the mouse to the **top-left corner** of the screen (PyAutoGUI failsafe).

### Platform notes

- **macOS:** grant camera and Accessibility permissions to your terminal/IDE (System Settings → Privacy & Security). Shortcuts use `Cmd` instead of `Ctrl`.
- **Linux:** PyAutoGUI needs an X11 session; Wayland is not reliably supported.

## Configuration

Defaults live in `config.py`. To override any value without editing code, create `gesture_mouse_config.json` in the project root. It is merged over the defaults, so include only the keys you want to change:

```json
{
  "camera": { "width": 640, "height": 480 },
  "cursor": { "smoothing": 0.5 },
  "gesture_action_map": { "THUMB_UP": "NEW_TAB" }
}
```

Commonly tuned settings:

| Key | Effect |
|---|---|
| `camera.width` / `camera.height` | Capture resolution (lower = faster) |
| `cursor.smoothing` | Cursor smoothness (higher = more responsive, less smooth) |
| `cursor.frame_margin` | Border of the camera frame ignored when mapping to the screen |
| `pinch.start` / `pinch.release` | Pinch click sensitivity |
| `click.cooldown` | Minimum seconds between clicks |
| `motion.swipe_distance` | How far to swipe for back/forward |

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Entry point: camera loop, overlay, wiring |
| `tracker.py` | MediaPipe hand tracking and landmark stabilization |
| `landmark_processor.py` | Hand geometry and finger-state calculations |
| `gesture_engine.py` | Gesture classification, temporal confirmation, action decisions |
| `motion.py` | Swipe and scroll motion tracking |
| `cursor.py` | Maps hand position to smoothed screen coordinates |
| `actions.py` | Executes actions via PyAutoGUI, with per-OS hotkeys |
| `config.py` | Default settings and JSON override loading |
| `models/` | MediaPipe `hand_landmarker.task` (auto-downloaded) |

## Troubleshooting

- **"Could not read camera frame":** another app is using the webcam, or the wrong camera is selected.
- **Model download fails:** check your internet connection and run again; the file is saved to `models/hand_landmarker.task`.
- **Jittery cursor or misfires:** improve lighting, keep your hand fully in frame, and raise `cursor.smoothing` or the gesture confirmation settings in the config.

## License

MIT (see `LICENSE`).