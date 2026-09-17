"""The hex map (walls, moving objects, three zones) and the actor."""

from dataclasses import dataclass

from hexgrid import MAP_RADIUS, Tile, all_tiles, in_bounds
from smartobjects import SmartObject, SmartObjectSubsystem

ZONES = ("NE", "S", "NW")


def zone_of(tile: Tile) -> str:
    """Three 120-degree sectors, by the largest cube coordinate; ties go q, then r, then s."""
    q, r = tile
    s = -q - r
    if q >= r and q >= s:
        return "NE"
    if r >= s:
        return "S"
    return "NW"


class World:
    def __init__(self, radius: int = MAP_RADIUS, walls=()):
        self.radius = radius
        self.walls: set[Tile] = set(walls)
        self.smart_objects = SmartObjectSubsystem()

    def add_wall(self, tile: Tile) -> None:
        self.walls.add(tile)

    def add_object(self, obj: SmartObject) -> None:
        self.smart_objects.register(obj)

    @property
    def blocked(self) -> set[Tile]:
        """Walls plus every object's tile and, while it steps, its next tile. Always live."""
        tiles = set(self.walls)
        for obj in self.smart_objects.objects:
            tiles.add(obj.tile)
            if obj.next_tile is not None:
                tiles.add(obj.next_tile)
        return tiles

    def is_walkable(self, tile: Tile) -> bool:
        if not in_bounds(tile, self.radius) or tile in self.walls:
            return False
        return not any(tile == obj.tile or tile == obj.next_tile for obj in self.smart_objects.objects)

    def walkable_tiles(self) -> list[Tile]:
        blocked = self.blocked
        return [t for t in all_tiles(self.radius) if t not in blocked]

    def zone_of(self, tile: Tile) -> str:
        return zone_of(tile)

    def can_object_enter(self, obj: SmartObject, tile: Tile, actor) -> bool:
        return (
            self.is_walkable(tile)
            and zone_of(tile) == obj.home_zone
            and tile != actor.tile
            and tile != actor.next_tile
        )


@dataclass
class Actor:
    tile: Tile
    facing: int = 0
    next_tile: Tile | None = None
    progress: float = 0.0  # 0..1 from tile toward next_tile
    speed: float = 3.0  # tiles per second
