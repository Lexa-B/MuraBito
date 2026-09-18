"""Line of sight: a cone in the facing direction plus the neighboring tiles, with blockers
casting shadows (hex shadowcasting, ring by ring). Pure geometry, no pygame."""

import math
from functools import lru_cache

from hexgrid import DIRECTIONS, MAP_RADIUS, Tile, distance, in_bounds

SENSE_RANGE = 6  # tiles; placeholder, tune by watching the sim
SENSE_HALF_ANGLE = 60.0  # degrees either side of the facing direction (a 120-degree cone)

EPSILON = 1e-9  # angle tolerance in degrees, so exact cone and shadow edges compare reliably


def center(tile: Tile) -> tuple[float, float]:
    """Unsquashed pointy-top hex center for a hex of size 1 (screen y grows downward)."""
    q, r = tile
    return (math.sqrt(3) * (q + r / 2), 1.5 * r)


def angle_of(point) -> float:
    return math.degrees(math.atan2(point[1], point[0]))


def normalize(angle: float) -> float:
    """Wrap an angle in degrees to (-180, 180]."""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped <= -180.0 else wrapped


def facing_angle(facing: int) -> float:
    return angle_of(center(DIRECTIONS[facing]))


@lru_cache(maxsize=None)
def _offsets(radius: int):
    """Every offset within `radius` (excluding 0), nearest ring first, with its center angle and
    the angular span of its six corners relative to that center angle."""
    result = []
    for dq in range(-radius, radius + 1):
        for dr in range(-radius, radius + 1):
            ring = distance((dq, dr), (0, 0))
            if ring == 0 or ring > radius:
                continue
            cx, cy = center((dq, dr))
            middle = angle_of((cx, cy))
            deltas = [
                normalize(angle_of((cx + math.cos(math.radians(30 + 60 * i)), cy + math.sin(math.radians(30 + 60 * i)))) - middle)
                for i in range(6)
            ]
            result.append((ring, (dq, dr), middle, min(deltas), max(deltas)))
    result.sort()
    return tuple(result)


def _split(lo: float, hi: float) -> list[tuple[float, float]]:
    """Split an interval that crosses +/-180 degrees into two that don't."""
    if lo < -180.0:
        return [(lo + 360.0, 180.0), (-180.0, hi)]
    if hi > 180.0:
        return [(lo, 180.0), (-180.0, hi - 360.0)]
    return [(lo, hi)]


def _merge(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge touching or overlapping intervals, so there is no zero-width gap between two shadows."""
    merged: list[tuple[float, float]] = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1] + EPSILON:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def visible_tiles(origin: Tile, facing: int, blockers, radius: int = SENSE_RANGE, half_angle: float = SENSE_HALF_ANGLE,
                  map_radius: int = MAP_RADIUS) -> set[Tile]:
    """Tiles the viewer at `origin` sees.

    The origin and its neighbors are always seen. Farther tiles, out to `radius`, are seen if
    their center is within `half_angle` of the facing direction (edges included) and not
    strictly inside a shadow cast by lit blockers in closer rings (touching shadows merge, so
    there's no gap between them). A lit blocker is itself seen if it is in the cone, and casts a
    shadow whether or not it is in the cone.
    """
    facing_deg = facing_angle(facing)
    seen = {origin} if in_bounds(origin, map_radius) else set()
    shadows: list[tuple[float, float]] = []
    pending: list[tuple[float, float]] = []
    current_ring = 1
    for ring, (dq, dr), middle, lo_delta, hi_delta in _offsets(radius):
        if ring != current_ring:
            shadows = _merge(shadows + pending)  # shadows only affect rings farther out
            pending = []
            current_ring = ring
        tile = (origin[0] + dq, origin[1] + dr)
        if not in_bounds(tile, map_radius):
            continue
        relative = normalize(middle - facing_deg)
        if any(lo + EPSILON < relative < hi - EPSILON for lo, hi in shadows):
            continue
        if ring == 1 or abs(relative) <= half_angle + EPSILON:
            seen.add(tile)
        if tile in blockers:
            pending.extend(_split(relative + lo_delta, relative + hi_delta))
    return seen
