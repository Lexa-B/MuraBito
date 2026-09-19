from smartobjects import Slot, SmartObject
from world import Actor, World


def test_zone_west_is_strictly_left_of_center_column():
    world = World()
    assert world.zone_of((-1, 0)) == "West"
    assert world.zone_of((-2, 3)) == "West"
    assert world.zone_of((3, -5)) == "East"


def test_center_column_is_east():
    world = World()
    for tile in [(0, 0), (-1, 2), (1, -2), (-6, 12)]:
        assert world.zone_of(tile) == "East"


def test_walls_objects_and_out_of_bounds_are_not_walkable():
    world = World(walls=[(2, 0)])
    obj = SmartObject("A", (4, 0), frozenset({"Object.A"}), [Slot(0, (3, 0), 0)], [])
    world.add_object(obj)
    assert world.smart_objects.objects == [obj]
    assert not world.is_walkable((2, 0))
    assert not world.is_walkable((4, 0))
    assert not world.is_walkable((13, 0))
    assert world.is_walkable((3, 0))


def test_add_wall_blocks_at_runtime():
    world = World()
    assert world.is_walkable((1, 0))
    world.add_wall((1, 0))
    assert not world.is_walkable((1, 0))
    assert (1, 0) in world.walls


def test_walkable_tiles_excludes_blocked():
    assert len(World(walls=[(0, 0)]).walkable_tiles()) == 468


def test_actor_defaults():
    actor = Actor(tile=(1, 2))
    assert (actor.facing, actor.next_tile, actor.progress, actor.speed) == (0, None, 0.0, 3.0)
