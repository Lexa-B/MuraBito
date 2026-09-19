"""A camera that eases toward a point in world pixels."""

import math


class Camera:
    def __init__(self, view_size, sharpness: float = 5.0):
        self.view_width, self.view_height = view_size
        self.sharpness = sharpness  # higher = catches up faster
        self.x = 0.0
        self.y = 0.0

    def snap(self, target) -> None:
        self.x, self.y = target

    def follow(self, target, dt: float) -> None:
        # Frame-rate independent exponential smoothing.
        blend = 1.0 - math.exp(-self.sharpness * dt)
        self.x += (target[0] - self.x) * blend
        self.y += (target[1] - self.y) * blend

    def world_to_screen(self, point):
        return (point[0] - self.x + self.view_width / 2, point[1] - self.y + self.view_height / 2)
