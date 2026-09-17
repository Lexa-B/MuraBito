"""The actor's private beliefs: where objects were last seen, how they seem to move, and how
sure the actor still is. Written only by perception; read by tasks, conditions and the renderer.

No world or Smart Object imports: everything here comes from observations.
"""

import math
from dataclasses import dataclass

from hexgrid import DIRECTIONS, MAP_RADIUS, Tile, add, direction_index, in_bounds
from zones import zone_of

POINT = "POINT"  # the ghost tile is a usable goal
REGION = "REGION"  # the believed area can seed a search, not a move-to-slot
LOST = "LOST"  # known to exist, whereabouts unknown

# Placeholder tuning.
PRIOR_SPEED = 0.3  # tiles/s: measured mean drift of an unused exp-01 object
PRIOR_SECONDS = 10.0  # weight of the prior in the speed blend, in seconds of watching
RADIUS_FACTOR = 2.0  # the uncertainty radius grows at speed x this
POINT_RADIUS = 5.0  # tiles: POINT while the radius is at most this
LOST_RADIUS = 13.0  # tiles: LOST once the radius is more than this
RETRACTED_RADIUS = POINT_RADIUS + 0.01  # radius floor after negative evidence: just past POINT


@dataclass(frozen=True)
class Observation:
    """What perception saw of one object this tick."""

    name: str
    tags: frozenset[str]
    tile: Tile
    next_tile: Tile | None
    slot_directions: tuple[int, ...]
    in_use: bool


@dataclass
class Belief:
    name: str
    tags: frozenset[str]
    slot_directions: tuple[int, ...]
    datum_tile: Tile  # where it was last seen
    datum_time: float  # when it was last seen
    datum_next_tile: Tile | None  # its next tile when last seen, if it was mid-step
    datum_zone: str  # the zone it was last seen in
    observed_seconds: float = 0.0  # time watched, excluding in-use time
    steps: int = 0  # steps watched, excluding in-use time
    course: int | None = None  # direction of the most recent watched step
    radius_floor: float = 0.0  # set by negative evidence until the next sighting


class BeliefStore:
    def __init__(self, map_radius: int = MAP_RADIUS):
        self.radius = map_radius  # the map radius, for A* on the believed map
        self.now = 0.0
        self.dt = 0.0
        self.beliefs: dict[str, Belief] = {}
        self.seen_now: set[str] = set()  # object names seen this tick
        self.seen_last_tick: set[str] = set()
        self.visible_now: set[Tile] = set()  # tiles seen this tick
        self.last_seen: dict[Tile, float] = {}  # tile -> last time seen; absent means never
        self.known_walls: set[Tile] = set()

    # --- written by perception, once per tick, in this order ---------------

    def begin_tick(self, dt: float) -> None:
        self.dt = dt
        self.now += dt
        self.seen_last_tick = self.seen_now
        self.seen_now = set()
        self.visible_now = set()

    def observe_tiles(self, tiles, walls) -> None:
        """`tiles` were seen this tick; `walls` are the true walls among them."""
        self.visible_now = set(tiles)
        for tile in self.visible_now:
            self.last_seen[tile] = self.now
        self.known_walls |= set(walls)

    def observe_object(self, obs: Observation) -> None:
        belief = self.beliefs.get(obs.name)
        if belief is None:
            belief = Belief(obs.name, obs.tags, obs.slot_directions, obs.tile, self.now, obs.next_tile, zone_of(obs.tile))
            self.beliefs[obs.name] = belief
        elif obs.name in self.seen_last_tick and not obs.in_use:
            belief.observed_seconds += self.dt
            if obs.tile != belief.datum_tile:
                belief.steps += 1
                belief.course = direction_index(belief.datum_tile, obs.tile)
        belief.tags = obs.tags
        belief.slot_directions = obs.slot_directions
        belief.datum_tile = obs.tile
        belief.datum_time = self.now
        belief.datum_next_tile = obs.next_tile
        belief.datum_zone = zone_of(obs.tile)
        belief.radius_floor = 0.0
        self.seen_now.add(obs.name)

    def apply_negative_evidence(self) -> list[tuple[str, Tile]]:
        """Retract POINT beliefs whose ghost tile is in view with the object not there.

        Returns (name, ghost tile) for each retraction, for logging.
        """
        retracted = []
        for name in sorted(self.beliefs):
            if name in self.seen_now or self.level(name) != POINT:
                continue
            ghost = self.ghost_tile(name)
            if ghost in self.visible_now:
                self.beliefs[name].radius_floor = RETRACTED_RADIUS
                retracted.append((name, ghost))
        return retracted

    # --- derived values ------------------------------------------------------

    def speed(self, name: str) -> float:
        """Tiles per second: the prior, blended toward the watched rate by seconds watched."""
        belief = self.beliefs[name]
        seconds = belief.observed_seconds
        watched = belief.steps / seconds if seconds > 0 else 0.0
        weight = seconds / (seconds + PRIOR_SECONDS)
        return (1 - weight) * PRIOR_SPEED + weight * watched

    def age(self, name: str) -> float:
        return self.now - self.beliefs[name].datum_time

    def uncertainty_radius(self, name: str) -> float:
        belief = self.beliefs[name]
        return max(self.speed(name) * RADIUS_FACTOR * self.age(name), belief.radius_floor)

    def level(self, name: str) -> str:
        radius = self.uncertainty_radius(name)
        if radius <= POINT_RADIUS:
            return POINT
        if radius <= LOST_RADIUS:
            return REGION
        return LOST

    def confidence(self, name: str) -> float:
        """For display only: 1 at a fresh sighting, 0 once LOST."""
        return max(0.0, 1.0 - self.uncertainty_radius(name) / LOST_RADIUS)

    def ghost_tile(self, name: str) -> Tile:
        """The dead-reckoned tile: from the datum along the last course, at the estimated speed,
        stopping before leaving the map or the zone it was seen in, or entering a known wall."""
        belief = self.beliefs[name]
        if belief.course is None:
            return belief.datum_tile
        tile = belief.datum_tile
        for _ in range(math.floor(self.speed(name) * self.age(name))):
            step = add(tile, DIRECTIONS[belief.course])
            if not in_bounds(step, self.radius) or zone_of(step) != belief.datum_zone or step in self.known_walls:
                break
            tile = step
        return tile

    def slot_tiles(self, name: str) -> list[tuple[int, Tile]]:
        """(slot index, believed tile) for each slot, riding on the ghost tile."""
        ghost = self.ghost_tile(name)
        return [(index, add(ghost, DIRECTIONS[d])) for index, d in enumerate(self.beliefs[name].slot_directions)]

    def slot_facing(self, name: str, index: int) -> int:
        """The direction a user standing on the slot faces: back toward the object."""
        return (self.beliefs[name].slot_directions[index] + 3) % 6

    def matching(self, tag_query) -> list[str]:
        """Names of believed objects carrying every tag in the query, sorted."""
        query = set(tag_query)
        return sorted(name for name, belief in self.beliefs.items() if query <= belief.tags)
