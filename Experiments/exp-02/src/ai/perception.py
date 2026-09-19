"""Perception: the only AI component that reads the world. Each tick it works out what the actor
can see and writes that into the belief store (Observe), then applies negative evidence (Orient)."""

from ai.beliefs import LOST, POINT, REGION, Observation
from ai.statetree import Evaluator
from ai.vision import visible_tiles
from smartobjects import slot_tile

LEVEL_RANK = {POINT: 0, REGION: 1, LOST: 2}


def fmt(tile) -> str:
    return f"({tile[0]},{tile[1]})"


class PerceptionEvaluator(Evaluator):
    def __init__(self, world):
        self.world = world
        self.levels: dict[str, str] = {}  # each belief's level after the previous tick, for logging

    def tick(self, ctx, dt):
        beliefs, actor, log = ctx["beliefs"], ctx["actor"], ctx["log"]
        world = self.world
        objects = world.smart_objects.objects
        blockers = world.walls | {obj.tile for obj in objects if obj.casts_shadow}
        seen_tiles = visible_tiles(actor.tile, actor.facing, blockers)

        beliefs.begin_tick(dt)
        beliefs.observe_tiles(seen_tiles, seen_tiles & world.walls)
        for obj in objects:
            # Seen if its tile, the tile it is stepping into, or any slot tile is in view. The next
            # tile matters: an object stepping into a tile next to the actor must be seen, or the
            # actor could step into the same tile.
            if not ({obj.tile, obj.next_tile} & seen_tiles or any(slot_tile(obj, s) in seen_tiles for s in obj.slots)):
                continue
            if obj.name not in beliefs.seen_last_tick:
                log(f"see {obj.name} at {fmt(obj.tile)}")
            beliefs.observe_object(Observation(
                obj.name, obj.tags, obj.tile, obj.next_tile,
                tuple(slot.direction for slot in obj.slots), world.smart_objects.is_in_use(obj),
            ))
        for name in sorted(beliefs.seen_last_tick - beliefs.seen_now):
            log(f"lose sight of {name}")

        retracted = beliefs.apply_negative_evidence()
        for name, tile in retracted:
            log(f"belief: {name} not at {fmt(tile)} - retracting")
        retracted_names = {name for name, _ in retracted}
        for name in sorted(beliefs.beliefs):
            level = beliefs.level(name)
            before = self.levels.get(name)
            if before is not None and LEVEL_RANK[level] > LEVEL_RANK[before] and name not in retracted_names:
                log(f"belief: {name} -> {level}")
            self.levels[name] = level
