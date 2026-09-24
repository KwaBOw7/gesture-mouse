"""Motion tracking for GestureMouse."""

from collections import deque


class MotionTracker:

    def __init__(self, window_seconds=0.35, max_samples=90):
        self.window_seconds = window_seconds
        self.samples = deque(maxlen=max_samples)

    def reset(self):
        self.samples.clear()

    def update(self, position, timestamp):
        self.samples.append((timestamp, position[0], position[1]))

        cutoff = timestamp - self.window_seconds
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()

    def displacement(self):
        if len(self.samples) < 2:
            return 0.0, 0.0

        _, x0, y0 = self.samples[0]
        _, x1, y1 = self.samples[-1]
        return (x1 - x0, y1 - y0)

    def duration(self):
        if len(self.samples) < 2:
            return 0.0
        return self.samples[-1][0] - self.samples[0][0]

    def velocity(self):
        duration = self.duration()
        if duration <= 0:
            return 0.0, 0.0

        dx, dy = self.displacement()
        return (dx / duration, dy / duration)
