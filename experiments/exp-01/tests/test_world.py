from collections import Counter

import pytest

from hexgrid import all_tiles
from smartobjects import Slot, SmartObject
from world import ZONES, Actor, World, zone_of


def make_object(tile, home_zone="NE"):
    return SmartObject("A", tile, frozenset({"Object.A"}), [Slot(0, 3)], [], home_zone=home_zone)


@pytest.mark.parametrize(
    "tile, zone",
    [
        ((6, -3), "NE"), ((12, 0), "NE"), ((12, -12), "NE"),  # q largest
        ((-3, 6), "S"), ((0, 12), "S"), ((-12, 12), "S"),  # r largest
        ((-3, -3), "NW"), ((-12, 0), "NW"), ((0, -12), "NW"),  # s largest
    ],
)
def test_zone_sectors(tile, zone):
    assert zone_of(tile) == zone
    assert World().zone_of(tile) == zone


@pytest.mark.parametrize(
    "tile, zone",
    [
        ((0, 0), "NE"),  # q == r == s
        ((2, 2), "NE"),  # q == r > s
        ((1, -2), "NE"),  # q == s > r
        ((-2, 1), "S"),  # r == s > q
    ],
)
def test_zone_ties_break_q_then_r_then_s(tile, zone):
    assert zone_of(tile) == zone


def test_every_tile_is_in_one_of_three_zones():
    counts = Counter(zone_of(t) for t in all_tiles())
    assert set(counts) == set(ZONES)
    assert counts == {"NE": 163, "S": 156, "NW": 150}


def test_walls_objects_and_out_of_bounds_are_not_walkable():
    world = World(walls=[(2, 0)])
    obj = make_object((4, 0))
    world.add_object(obj)
    assert world.smart_objects.objects == [obj]
    assert not world.is_walkable((2, 0))
    assert not world.is_walkable((4, 0))
    assert not world.is_walkable((13, 0))
    assert world.is_walkable((3, 0))


def test_object_next_tile_is_blocked_while_stepping():
    world = World()
    obj = make_object((4, 0))
    world.add_object(obj)
    obj.next_tile = (5, 0)
    assert not world.is_walkable((5, 0))
    assert world.blocked == {(4, 0), (5, 0)}
    obj.next_tile = None
    assert world.is_walkable((5, 0))


def test_blocking_follows_object_moves():
    world = World()
    obj = make_object((4, 0))
    world.add_object(obj)
    obj.tile = (1, 1)
    assert world.is_walkable((4, 0))
    assert not world.is_walkable((1, 1))
    assert world.blocked == {(1, 1)}


def test_add_wall_blocks_at_runtime():
    world = World()
    assert world.is_walkable((1, 0))
    world.add_wall((1, 0))
    assert not world.is_walkable((1, 0))
    assert (1, 0) in world.walls


def test_walkable_tiles_excludes_walls_and_objects():
    world = World(walls=[(0, 0)])
    assert len(world.walkable_tiles()) == 468
    world.add_object(make_object((3, 0)))
    assert len(world.walkable_tiles()) == 467


def test_can_object_enter():
    world = World(walls=[(5, -1)])
    obj = make_object((3, 0), home_zone="NE")
    world.add_object(obj)
    actor = Actor(tile=(8, 0), next_tile=(9, 0))
    assert world.can_object_enter(obj, (4, 0), actor)
    assert not world.can_object_enter(obj, (0, 5), actor)  # S zone
    assert not world.can_object_enter(obj, (5, -1), actor)  # wall
    assert not world.can_object_enter(obj, (8, 0), actor)  # actor tile
    assert not world.can_object_enter(obj, (9, 0), actor)  # actor next tile


def test_actor_defaults():
    actor = Actor(tile=(1, 2))
    assert (actor.facing, actor.next_tile, actor.progress, actor.speed) == (0, None, 0.0, 3.0)
