"""Axial-coordinate math for a hexagon-shaped map of pointy-top hexes."""

Tile = tuple[int, int]

MAP_RADIUS = 12

# Index 0 is E, then counter-clockwise on screen (screen y grows downward, so "up" is -r).
DIRECTIONS: tuple[Tile, ...] = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def add(a: Tile, b: Tile) -> Tile:
    return (a[0] + b[0], a[1] + b[1])


def distance(a: Tile, b: Tile) -> int:
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def in_bounds(tile: Tile, radius: int = MAP_RADIUS) -> bool:
    return distance(tile, (0, 0)) <= radius


def neighbors(tile: Tile, radius: int = MAP_RADIUS) -> list[Tile]:
    return [n for d in DIRECTIONS if in_bounds(n := add(tile, d), radius)]


def all_tiles(radius: int = MAP_RADIUS) -> list[Tile]:
    return [
        (q, r)
        for q in range(-radius, radius + 1)
        for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1)
    ]


def direction_index(from_tile: Tile, to_tile: Tile) -> int:
    """Index into DIRECTIONS of the step from one tile to an adjacent one."""
    delta = (to_tile[0] - from_tile[0], to_tile[1] - from_tile[1])
    if delta not in DIRECTIONS:
        raise ValueError(f"{from_tile} and {to_tile} are not adjacent")
    return DIRECTIONS.index(delta)
