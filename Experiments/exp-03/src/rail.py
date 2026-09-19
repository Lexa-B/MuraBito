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
    """The camera's position over time. `ground(x, z)` is the full-detail terrain height.

    Each `advance` needs the height under the focus point and under the trailing eye point.
    `ground` gives those one point at a time; an optional `ground_many(xs, zs)` gives both in a
    single vectorised call, which matters when `ground` is an expensive many-octave noise lookup
    (see `terrain.height`). Either way, the two heights are looked up exactly once per `advance`
    (and once at construction), then cached: `focus`, `eye` and `_eye_floor` read the cache.
    """

    def __init__(self, ground: Callable[[float, float], float], start: float = 0.0,
                 ground_many: Callable[[object, object], object] | None = None):
        self.ground = ground
        self._ground_many = ground_many
        self.t = start
        self._sample_heights()
        self.eye_y = self._eye_target()

    def advance(self, dt: float) -> None:
        self.t += dt
        self._sample_heights()
        target = self._eye_target()
        self.eye_y += (target - self.eye_y) * (1 - math.exp(-dt / EYE_SMOOTH_S))
        self.eye_y = max(self.eye_y, self._eye_floor())

    @property
    def focus(self) -> tuple[float, float, float]:
        x, z = focus_xz(self.t)
        return (x, self._focus_h, z)

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

    def _sample_heights(self) -> None:
        """Look up the focus and eye-floor heights at the current `t`, once, together."""
        fx, fz = focus_xz(self.t)
        ex, ez = self._eye_xz()
        if self._ground_many is not None:
            fh, eh = self._ground_many((fx, ex), (fz, ez))
            self._focus_h, self._eye_floor_h = float(fh), float(eh)
        else:
            self._focus_h, self._eye_floor_h = self.ground(fx, fz), self.ground(ex, ez)

    def _eye_xz(self) -> tuple[float, float]:
        fx, fz = focus_xz(self.t)
        hx, hz = heading(self.t)
        return (fx - EYE_BACK_M * hx, fz - EYE_BACK_M * hz)

    def _eye_floor(self) -> float:
        return self._eye_floor_h + EYE_MIN_CLEARANCE_M

    def _eye_target(self) -> float:
        return max(self.focus[1] + EYE_UP_M, self._eye_floor())
