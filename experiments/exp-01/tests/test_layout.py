from ai.pathing import astar
from hexgrid import DIRECTIONS, add, all_tiles, in_bounds, neighbors
from layout import ACTOR_START, WALLS, build_world
from smartobjects import slot_facing, slot_tile
from world import zone_of


def objects_by_name(world):
    return {obj.name: obj for obj in world.smart_objects.objects}


def test_slots_are_walkable_and_face_their_object():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert world.is_walkable(slot_tile(obj, slot))
            assert add(slot_tile(obj, slot), DIRECTIONS[slot_facing(slot)]) == obj.tile


def test_every_slot_is_reachable_from_actor_start():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert astar(world, ACTOR_START, {slot_tile(obj, slot)}) is not None, (obj.name, slot.index)


def test_objects_match_spec():
    objects = objects_by_name(build_world())
    assert sorted(objects) == ["A", "B", "C"]
    assert [(o.home_zone, o.pauses_during_use, len(o.slots)) for o in (objects["A"], objects["B"], objects["C"])] == [
        ("NW", True, 2),
        ("S", True, 2),
        ("NE", False, 2),
    ]
    for obj in objects.values():
        assert zone_of(obj.tile) == obj.home_zone


def test_actor_starts_walkable_in_nw_and_not_on_a_slot():
    world = build_world()
    assert zone_of(ACTOR_START) == "NW"
    assert world.is_walkable(ACTOR_START)
    slot_tiles = {slot_tile(o, s) for o in world.smart_objects.objects for s in o.slots}
    assert ACTOR_START not in slot_tiles


def test_walls_are_in_range_in_bounds_and_away_from_zone_borders():
    assert 30 <= len(set(WALLS)) <= 40
    for wall in WALLS:
        assert in_bounds(wall)
        assert all(zone_of(n) == zone_of(wall) for n in neighbors(wall)), wall


def test_each_zone_stays_connected_around_walls():
    walls = set(WALLS)
    for zone in ("NE", "S", "NW"):
        tiles = {t for t in all_tiles() if zone_of(t) == zone and t not in walls}
        start = next(iter(tiles))
        seen, stack = {start}, [start]
        while stack:
            for n in neighbors(stack.pop()):
                if n in tiles and n not in seen:
                    seen.add(n)
                    stack.append(n)
        assert seen == tiles, zone


def test_objects_advertise_short_and_long_placeholder_interactions():
    world = build_world()
    for obj in world.smart_objects.objects:
        assert [(i.name, i.duration) for i in obj.interactions] == [(f"{obj.name}.Short", 1.5), (f"{obj.name}.Long", 3.0)]
        assert obj.tags == frozenset({f"Object.{obj.name}"})
        ctx = {}
        for effect in obj.interactions[0].effects:
            effect(ctx)
        assert ctx == {"LastUsed": obj.name}
