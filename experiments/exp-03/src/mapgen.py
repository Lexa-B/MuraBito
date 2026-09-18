"""Random maps: walls first, then object starts, then an actor start with nothing in view.

Everything is drawn from one seeded rng in a fixed order, so the same seed gives the same map.
"""

from collections import deque

from ai.vision import visible_tiles
from hexgrid import DIRECTIONS, Tile, add, all_tiles, in_bounds, neighbors
from zones import zone_of

MIN_WALLS = 30
MAX_WALLS = 40
MIN_SEGMENT = 2
MAX_SEGMENT = 5
MAX_ATTEMPTS = 2000


def away_from_zone_border(tile: Tile) -> bool:
    """True if every in-bounds neighbor is in the tile's own zone."""
    zone = zone_of(tile)
    return all(zone_of(n) == zone for n in neighbors(tile))


def zone_connected(zone: str, walls) -> bool:
    """True if the zone's non-wall tiles form one connected region."""
    tiles = {t for t in all_tiles() if zone_of(t) == zone and t not in walls}
    if not tiles:
        return True
    start = min(tiles)
    seen, stack = {start}, [start]
    while stack:
        for n in neighbors(stack.pop()):
            if n in tiles and n not in seen:
                seen.add(n)
                stack.append(n)
    return seen == tiles


def reachable_from(start: Tile, blocked) -> set[Tile]:
    """Every tile reachable from `start` without entering a blocked tile."""
    seen, queue = {start}, deque([start])
    while queue:
        for n in neighbors(queue.popleft()):
            if n not in blocked and n not in seen:
                seen.add(n)
                queue.append(n)
    return seen


def generate_walls(rng) -> set[Tile]:
    """Short straight segments, 30-40 tiles in total, off zone borders, every zone kept connected."""
    target = rng.randint(MIN_WALLS, MAX_WALLS)
    tiles = all_tiles()
    walls: set[Tile] = set()
    for _ in range(MAX_ATTEMPTS):
        if len(walls) >= target:
            return walls
        start = rng.choice(tiles)
        direction = rng.randrange(6)
        length = min(rng.randint(MIN_SEGMENT, MAX_SEGMENT), MAX_WALLS - len(walls))
        segment = [start]
        while len(segment) < length:
            segment.append(add(segment[-1], DIRECTIONS[direction]))
        if any(not in_bounds(t) or t in walls or not away_from_zone_border(t) for t in segment):
            continue
        candidate = walls | set(segment)
        if all(zone_connected(zone, candidate) for zone in {zone_of(t) for t in segment}):
            walls = candidate
    if len(walls) >= target:
        return walls
    raise RuntimeError("mapgen: could not place walls")


def place_objects(rng, specs, walls) -> list[tuple[Tile, int]]:
    """(tile, heading) per object spec (home_zone, slot_directions, casts_shadow), in order.

    Each object sits in its home zone, off walls, off earlier objects and their slot tiles,
    with at least one slot tile that is in bounds, not a wall, and not an object.
    """
    placed: list[tuple[Tile, int]] = []
    taken_slots: set[Tile] = set()
    for home_zone, slot_directions, _ in specs:
        candidates = [t for t in all_tiles() if zone_of(t) == home_zone and t not in walls]
        for _ in range(MAX_ATTEMPTS):
            tile = rng.choice(candidates)
            object_tiles = {p[0] for p in placed}
            if tile in object_tiles or tile in taken_slots:
                continue
            slots = [add(tile, DIRECTIONS[d]) for d in slot_directions]
            if not any(in_bounds(s) and s not in walls and s not in object_tiles for s in slots):
                continue
            placed.append((tile, rng.randrange(6)))
            taken_slots.update(slots)
            break
        else:
            raise RuntimeError(f"mapgen: could not place an object in {home_zone}")
    return placed


def place_actor(rng, walls, specs, placed) -> tuple[Tile, int]:
    """(tile, facing) for the actor: off walls, objects and slot tiles, seeing no object or slot
    tile, and able to reach every walkable slot tile."""
    object_tiles = {tile for tile, _ in placed}
    slot_tiles = {
        add(tile, DIRECTIONS[d]) for (tile, _), (_, slot_directions, _) in zip(placed, specs) for d in slot_directions
    }
    blockers = set(walls) | {tile for (tile, _), (_, _, casts_shadow) in zip(placed, specs) if casts_shadow}
    blocked = set(walls) | object_tiles
    walkable_slots = {s for s in slot_tiles if in_bounds(s) and s not in blocked}
    candidates = [t for t in all_tiles() if t not in blocked and t not in slot_tiles]
    for _ in range(MAX_ATTEMPTS):
        tile = rng.choice(candidates)
        facing = rng.randrange(6)
        if visible_tiles(tile, facing, blockers) & (object_tiles | slot_tiles):
            continue
        if not walkable_slots <= reachable_from(tile, blocked):
            continue
        return tile, facing
    raise RuntimeError("mapgen: could not place the actor")


def generate(rng, specs):
    """Returns (walls, [(tile, heading) per spec], actor_tile, actor_facing)."""
    walls = generate_walls(rng)
    placed = place_objects(rng, specs, walls)
    actor_tile, actor_facing = place_actor(rng, walls, specs, placed)
    return walls, placed, actor_tile, actor_facing
