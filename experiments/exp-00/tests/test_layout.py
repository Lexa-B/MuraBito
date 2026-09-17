from ai.pathing import astar
from hexgrid import DIRECTIONS, add, in_bounds
from layout import ACTOR_START, WALLS, build_world


def objects_by_name(world):
    return {obj.name: obj for obj in world.smart_objects.objects}


def test_slots_are_walkable_and_face_their_object():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert world.is_walkable(slot.tile)
            assert add(slot.tile, DIRECTIONS[slot.facing]) == obj.tile


def test_every_slot_is_reachable_from_actor_start():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert astar(world, ACTOR_START, {slot.tile}) is not None, (obj.name, slot.index)


def test_layout_zones_match_spec():
    world = build_world()
    objects = objects_by_name(world)
    assert sorted(objects) == ["A", "B", "C"]
    assert world.zone_of(objects["A"].tile) == "West"
    assert world.zone_of(objects["B"].tile) == "East"
    assert world.zone_of(objects["C"].tile) == "East"
    assert [world.zone_of(s.tile) for s in objects["B"].slots] == ["West", "East"]
    assert world.zone_of(ACTOR_START) == "West"
    assert world.is_walkable(ACTOR_START)


def test_walls_are_in_bounds_and_within_spec_range():
    assert 30 <= len(set(WALLS)) <= 40
    assert all(in_bounds(t) for t in WALLS)


def test_objects_advertise_short_and_long_placeholder_interactions():
    world = build_world()
    for obj in world.smart_objects.objects:
        assert [(i.name, i.duration) for i in obj.interactions] == [(f"{obj.name}.Short", 1.5), (f"{obj.name}.Long", 3.0)]
        assert obj.tags == frozenset({f"Object.{obj.name}"})
        ctx = {}
        for effect in obj.interactions[0].effects:
            effect(ctx)
        assert ctx == {"LastUsed": obj.name}
