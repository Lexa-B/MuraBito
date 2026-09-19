"""Hierarchical hex addresses: shaku, ken, cho and ri.

Every level is a pointy-top axial hex lattice with the same orientation (packing B): a level-L
cell (a, b) is centred on the level-(L-1) cell (N*a, N*b), N = PACKING[L]. A child belongs to
exactly one parent: the nearest parent centre, ties to the lexicographically greatest (a, b).
Pure Python ints; `owner` has no numpy twin, because a level's ownership is the same for every
parent, so chunkgeom.py's templates are built from it once, not evaluated per chunk.
"""

import math
from functools import cache

from hexgrid import DIRECTIONS, Tile, distance

SHAKU, KEN, CHO, RI = 0, 1, 2, 3
LEVELS = (SHAKU, KEN, CHO, RI)
LEVEL_NAMES = ("shaku", "ken", "cho", "ri")
PACKING = (1, 6, 60, 36)          # PACKING[L]: level L-1 cells per side of a level-L cell
SCALE = (1, 6, 360, 12960)        # shaku per side of a level-L cell
SHAKU_M = 10 / 33                 # metres, flat to flat
WIDTH_M = tuple(s * SHAKU_M for s in SCALE)
WORLD_RADIUS = 12                 # ri
WINDOW_RINGS = 3
SQRT3 = math.sqrt(3)

Address = tuple[Tile, Tile, Tile, Tile]  # ri (world position), cho, ken, shaku (local offsets)


def d2(dq: int, dr: int) -> int:
    """Squared hex-plane distance of an axial offset (dq, dr), in units of a cell width squared,
    as an exact integer. For a unit neighbour step (one of hexgrid.DIRECTIONS), d2 == 1."""
    return dq * dq + dq * dr + dr * dr


def owner(cell: Tile, n: int) -> Tile:
    """The parent (on the lattice scaled by n) that owns this child cell."""
    q, r = cell
    a0, b0 = round(q / n), round(r / n)
    best = None
    best_key = None
    for a in (a0 - 1, a0, a0 + 1):
        for b in (b0 - 1, b0, b0 + 1):
            key = (d2(q - n * a, r - n * b), -a, -b)
            if best_key is None or key < best_key:
                best_key, best = key, (a, b)
    return best


def parent(cell: Tile, level: int) -> Tile:
    """The level+1 cell that owns this level cell."""
    return owner(cell, PACKING[level + 1])


def up(cell: Tile, from_level: int, to_level: int) -> Tile:
    for level in range(from_level, to_level):
        cell = parent(cell, level)
    return cell


def centre_child(cell: Tile, level: int) -> Tile:
    """The level-1 cell at the centre of this level cell."""
    n = PACKING[level]
    return (cell[0] * n, cell[1] * n)


def centre_shaku(cell: Tile, level: int) -> Tile:
    s = SCALE[level]
    return (cell[0] * s, cell[1] * s)


def local(cell: Tile, level: int) -> Tile:
    """Offset of a cell from its parent's centre, in cells of its own level."""
    p = parent(cell, level)
    n = PACKING[level + 1]
    return (cell[0] - n * p[0], cell[1] - n * p[1])


def address(shaku: Tile) -> Address:
    ken = parent(shaku, SHAKU)
    cho = parent(ken, KEN)
    ri = parent(cho, CHO)
    return (ri, local(cho, CHO), local(ken, KEN), local(shaku, SHAKU))


def from_address(addr: Address) -> Tile:
    ri, cho_off, ken_off, shaku_off = addr
    cho = (ri[0] * PACKING[RI] + cho_off[0], ri[1] * PACKING[RI] + cho_off[1])
    ken = (cho[0] * PACKING[CHO] + ken_off[0], cho[1] * PACKING[CHO] + ken_off[1])
    return (ken[0] * PACKING[KEN] + shaku_off[0], ken[1] * PACKING[KEN] + shaku_off[1])


def format_address(addr: Address) -> str:
    parts = zip(("ri", "cho", "ken", "shaku"), addr)
    return " / ".join(f"{name} ({q},{r})" for name, (q, r) in parts)


def axial_to_metres(q: float, r: float, level: int = SHAKU) -> tuple[float, float]:
    """Centre of axial (q, r) at a level, in world metres (x east, z north)."""
    w = WIDTH_M[level]
    return ((q + r / 2) * w, r * SQRT3 / 2 * w)


def metres_to_axial(x: float, z: float, level: int = SHAKU) -> tuple[float, float]:
    w = WIDTH_M[level]
    r = z / (SQRT3 / 2 * w)
    return (x / w - r / 2, r)


def hex_round(fq: float, fr: float) -> Tile:
    fs = -fq - fr
    q, r, s = round(fq), round(fr), round(fs)
    dq, dr, ds = abs(q - fq), abs(r - fr), abs(s - fs)
    if dq > dr and dq > ds:
        q = -r - s
    elif dr > ds:
        r = -q - s
    return (q, r)


def round_at(x: float, z: float, level: int) -> Tile:
    """The level cell whose ideal hexagon contains the point (nearest centre at that level)."""
    return hex_round(*metres_to_axial(x, z, level))


def shaku_at(x: float, z: float) -> Tile:
    return round_at(x, z, SHAKU)


def tier_cell(x: float, z: float, tier: int, level: int) -> Tile:
    """The level cell a point belongs to where tier `tier` is drawn: round at the tier, then own upward."""
    return up(round_at(x, z, tier), tier, level)


def in_world(ri: Tile) -> bool:
    return distance(ri, (0, 0)) <= WORLD_RADIUS


def world_ri() -> list[Tile]:
    n = WORLD_RADIUS
    return [(q, r) for q in range(-n, n + 1) for r in range(max(-n, -q - n), min(n, -q + n) + 1)]


def window(cell: Tile, rings: int = WINDOW_RINGS) -> list[Tile]:
    """The cell plus `rings` rings of neighbours at the same level."""
    q0, r0 = cell
    return [
        (q0 + q, r0 + r)
        for q in range(-rings, rings + 1)
        for r in range(max(-rings, -q - rings), min(rings, -q + rings) + 1)
    ]


@cache
def child_offsets(level: int) -> tuple[Tile, ...]:
    """Local offsets of the level-1 cells a level cell owns (the same for every cell)."""
    n = PACKING[level]
    reach = n  # owned children lie within hex distance 2n/3 of the centre
    return tuple(
        (q, r)
        for q in range(-reach, reach + 1)
        for r in range(-reach, reach + 1)
        if owner((q, r), n) == (0, 0)
    )


def children(cell: Tile, level: int) -> list[Tile]:
    cq, cr = centre_child(cell, level)
    return [(cq + q, cr + r) for q, r in child_offsets(level)]


def neighbours(cell: Tile) -> list[Tile]:
    return [(cell[0] + dq, cell[1] + dr) for dq, dr in DIRECTIONS]
