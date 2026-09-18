"""The camera rail: a jog round a 4-ri circle about the world centre, with a low trailing eye."""

import math
from typing import Callable

from hexaddr import RI, WIDTH_M, Tile, shaku_at

RAIL_RADIUS_M = 4 * WIDTH_M[RI]
SPEED_M_S = 2.5
EYE_BACK_M = 8.0
EYE_UP_M = 3.0
EYE_MIN_CLEARANCE_M = 1.5
EYE_SMOOTH_S = 0.5
FOV_Y_DEG = 60.0


def focus_xz(t: float) -> tuple[float, float]:
    """Where the focus point is after t seconds (anticlockwise, starting due east)."""
    a = t * SPEED_M_S / RAIL_RADIUS_M
    return (RAIL_RADIUS_M * math.cos(a), RAIL_RADIUS_M * math.sin(a))


def heading(t: float) -> tuple[float, float]:
    """Unit direction of travel after t seconds."""
    a = t * SPEED_M_S / RAIL_RADIUS_M
    return (-math.sin(a), math.cos(a))


def lap_seconds() -> float:
    return 2 * math.pi * RAIL_RADIUS_M / SPEED_M_S


class Rail:
    """The camera's position over time. `ground(x, z)` is the full-detail terrain height."""

    def __init__(self, ground: Callable[[float, float], float], start: float = 0.0):
        self.ground = ground
        self.t = start
        self.eye_y = self._eye_target()

    def advance(self, dt: float) -> None:
        self.t += dt
        target = self._eye_target()
        self.eye_y += (target - self.eye_y) * (1 - math.exp(-dt / EYE_SMOOTH_S))
        self.eye_y = max(self.eye_y, self._eye_floor())

    @property
    def focus(self) -> tuple[float, float, float]:
        x, z = focus_xz(self.t)
        return (x, self.ground(x, z), z)

    @property
    def focus_shaku(self) -> Tile:
        return shaku_at(*focus_xz(self.t))

    @property
    def eye(self) -> tuple[float, float, float]:
        x, z = self._eye_xz()
        return (x, self.eye_y, z)

    @property
    def lap_fraction(self) -> float:
        return (self.t / lap_seconds()) % 1.0

    def _eye_xz(self) -> tuple[float, float]:
        fx, fz = focus_xz(self.t)
        hx, hz = heading(self.t)
        return (fx - EYE_BACK_M * hx, fz - EYE_BACK_M * hz)

    def _eye_floor(self) -> float:
        return self.ground(*self._eye_xz()) + EYE_MIN_CLEARANCE_M

    def _eye_target(self) -> float:
        return max(self.focus[1] + EYE_UP_M, self._eye_floor())
