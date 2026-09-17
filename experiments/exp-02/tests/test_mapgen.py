import random

import pytest

from ai.vision import visible_tiles
from hexgrid import DIRECTIONS, add, all_tiles, in_bounds
from layout import OBJECTS, build_world
from mapgen import (
    MAX_WALLS,
    MIN_WALLS,
    away_from_zone_border,
    generate,
    reachable_from,
    zone_connected,
)
from smartobjects import slot_tile
from zones import ZONES, zone_of

SEEDS = range(50)


def build(seed):
    return build_world(random.Random(seed))


def test_away_from_zone_border():
    assert away_from_zone_border((-6, 0))  # deep in NW
    assert not away_from_zone_border((0, 0))  # the center touches all three zones


def test_zone_connected_detects_a_cut():
    assert zone_connected("NE", set())
    # Every tile of NE at q == 6 is a full wall line from the center diamond's edge to the map edge.
    cut = {t for t in all_tiles() if zone_of(t) == "NE" and t[0] == 6}
    assert not zone_connected("NE", cut)


def test_reachable_from_stops_at_blocked_tiles():
    ring = {add((0, 0), d) for d in DIRECTIONS}
    assert reachable_from((0, 0), ring) == {(0, 0)}


@pytest.mark.parametrize("seed", SEEDS)
def test_walls_follow_the_rules(seed):
    world, _ = build(seed)
    assert MIN_WALLS <= len(world.walls) <= MAX_WALLS
    for wall in world.walls:
        assert in_bounds(wall)
        assert away_from_zone_border(wall), wall
    for zone in ZONES:
        assert zone_connected(zone, world.walls), zone


@pytest.mark.parametrize("seed", SEEDS)
def test_objects_start_in_home_zone_with_a_walkable_slot(seed):
    world, _ = build(seed)
    objects = world.smart_objects.objects
    assert [(o.name, o.home_zone, o.pauses_during_use, o.casts_shadow) for o in objects] == [
        ("A", "NW", True, True),
        ("B", "S", True, True),
        ("C", "NE", False, False),
    ]
    tiles = [o.tile for o in objects]
    assert len(set(tiles)) == 3
    for obj in objects:
        assert zone_of(obj.tile) == obj.home_zone
        assert obj.tile not in world.walls
        assert any(world.is_walkable(slot_tile(obj, s)) for s in obj.slots), obj.name


@pytest.mark.parametrize("seed", SEEDS)
def test_actor_starts_seeing_nothing_and_can_reach_every_walkable_slot(seed):
    world, actor = build(seed)
    objects = world.smart_objects.objects
    object_tiles = {o.tile for o in objects}
    slot_tiles = {slot_tile(o, s) for o in objects for s in o.slots}
    assert world.is_walkable(actor.tile)
    assert actor.tile not in slot_tiles
    blockers = world.walls | {o.tile for o in objects if o.casts_shadow}
    assert not visible_tiles(actor.tile, actor.facing, blockers) & (object_tiles | slot_tiles)
    reachable = reachable_from(actor.tile, world.blocked)
    assert {t for t in slot_tiles if world.is_walkable(t)} <= reachable


def test_same_seed_same_map_and_different_seeds_differ():
    def snapshot(seed):
        world, actor = build(seed)
        return (sorted(world.walls), [(o.tile, o.heading) for o in world.smart_objects.objects], actor.tile, actor.facing)

    assert snapshot(7) == snapshot(7)
    assert snapshot(0) != snapshot(1)


def test_generate_draws_everything_from_the_rng_in_order():
    specs = [(zone, dirs, shadow) for _, dirs, zone, _, shadow in OBJECTS]
    a = generate(random.Random(3), specs)
    b = generate(random.Random(3), specs)
    assert a == b


def test_objects_advertise_short_and_long_placeholder_interactions():
    world, _ = build(0)
    for obj in world.smart_objects.objects:
        assert [(i.name, i.duration) for i in obj.interactions] == [(f"{obj.name}.Short", 1.5), (f"{obj.name}.Long", 3.0)]
        assert obj.tags == frozenset({f"Object.{obj.name}"})
        ctx = {}
        for effect in obj.interactions[0].effects:
            effect(ctx)
        assert ctx == {"LastUsed": obj.name}
