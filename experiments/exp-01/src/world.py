"""The hex map (walls, objects, zones) and the actor."""

from dataclasses import dataclass

from hexgrid import MAP_RADIUS, Tile, all_tiles, in_bounds
from smartobjects import SmartObject, SmartObjectSubsystem


class World:
    def __init__(self, radius: int = MAP_RADIUS, walls=()):
        self.radius = radius
        self.walls: set[Tile] = set(walls)
        self.smart_objects = SmartObjectSubsystem()
        self.blocked: set[Tile] = set(self.walls)

    def add_wall(self, tile: Tile) -> None:
        self.walls.add(tile)
        self.blocked.add(tile)

    def add_object(self, obj: SmartObject) -> None:
        self.smart_objects.register(obj)
        self.blocked.add(obj.tile)

    def is_walkable(self, tile: Tile) -> bool:
        return in_bounds(tile, self.radius) and tile not in self.blocked

    def walkable_tiles(self) -> list[Tile]:
        return [t for t in all_tiles(self.radius) if t not in self.blocked]

    def zone_of(self, tile: Tile) -> str:
        q, r = tile
        return "West" if 2 * q + r < 0 else "East"


@dataclass
class Actor:
    tile: Tile
    facing: int = 0
    next_tile: Tile | None = None
    progress: float = 0.0  # 0..1 from tile toward next_tile
    speed: float = 3.0  # tiles per second
