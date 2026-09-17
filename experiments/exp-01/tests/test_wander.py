import random
from collections import Counter

import pytest

from hexgrid import DIRECTIONS, add, direction_index
from layout import ACTOR_START, build_world
from smartobjects import Slot, SmartObject
from wander import MOVE_RATE, STEP_SPEED, TURN_FALLOFF, ObjectMover, choose_direction, direction_weights, divergence
from world import Actor, World, zone_of

ALWAYS = 1e9  # a move_rate high enough that every idle tick starts a step


def make_world(tile=(4, 0), home_zone="NE", pauses=True):
    world = World()
    obj = SmartObject("A", tile, frozenset({"Object.A"}), [Slot(0, 3)], [], home_zone=home_zone,
                      pauses_during_use=pauses)
    world.add_object(obj)
    return world, obj


def test_placeholder_parameters():
    assert (MOVE_RATE, STEP_SPEED, TURN_FALLOFF) == (0.5, 1.5, 0.3)


@pytest.mark.parametrize(
    "heading, direction, expected",
    [(0, 0, 0), (0, 1, 1), (0, 5, 1), (0, 2, 2), (0, 4, 2), (0, 3, 3), (4, 1, 3), (5, 0, 1)],
)
def test_divergence(heading, direction, expected):
    assert divergence(heading, direction) == expected


def test_direction_weights_fall_off_with_divergence():
    assert direction_weights(0) == pytest.approx([1.0, 0.3, 0.09, 0.027, 0.09, 0.3])
    assert direction_weights(2) == pytest.approx([0.09, 0.3, 1.0, 0.3, 0.09, 0.027])


def test_choose_direction_returns_none_when_nothing_is_allowed():
    assert choose_direction(0, set(), random.Random(0)) is None


def test_choose_direction_only_returns_allowed_directions():
    rng = random.Random(1)
    assert {choose_direction(0, {2, 4}, rng) for _ in range(200)} == {2, 4}


def test_choose_direction_prefers_going_straight():
    rng = random.Random(2)
    counts = Counter(choose_direction(0, set(range(6)), rng) for _ in range(20000))
    by_divergence = [counts[0], counts[1] + counts[5], counts[2] + counts[4], counts[3]]
    assert by_divergence[0] > by_divergence[1] > by_divergence[2] > by_divergence[3]
    assert counts[0] / 20000 == pytest.approx(1.0 / 1.807, abs=0.02)


def test_choose_direction_renormalizes_over_allowed_directions():
    rng = random.Random(3)
    counts = Counter(choose_direction(0, {1, 3}, rng) for _ in range(20000))
    assert counts[1] / 20000 == pytest.approx(0.3 / 0.327, abs=0.02)


def test_step_start_frequency_matches_move_rate():
    world, obj = make_world()
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(4))
    starts = 0
    for _ in range(60000):  # 1000 idle seconds at 60 Hz
        mover.tick_object(obj, 1 / 60)
        if obj.next_tile is not None:
            starts += 1
            obj.next_tile = None  # stay idle so every tick is a fresh roll
    assert 425 <= starts <= 575  # expected 500


def test_step_completes_after_one_over_step_speed():
    world, obj = make_world()
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(5), move_rate=ALWAYS, step_speed=2.0)
    mover.tick_object(obj, 0.25)  # starts a step
    start, target = obj.tile, obj.next_tile
    assert target is not None and obj.heading == direction_index(start, target)
    mover.tick_object(obj, 0.25)
    assert obj.tile == start and obj.progress == pytest.approx(0.5)
    mover.tick_object(obj, 0.25)  # 0.5s = 1 / step_speed
    assert obj.tile == target and obj.next_tile is None and obj.progress == 0.0
    assert zone_of(obj.tile) == "NE"


def test_pausing_object_in_use_freezes_even_mid_step():
    world, obj = make_world(pauses=True)
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(6), move_rate=ALWAYS)
    mover.tick_object(obj, 0.1)
    mover.tick_object(obj, 0.1)
    frozen = (obj.tile, obj.next_tile, obj.progress)
    assert obj.next_tile is not None and obj.progress > 0
    world.smart_objects.set_in_use(obj, True)
    for _ in range(50):
        mover.tick_object(obj, 0.1)
    assert (obj.tile, obj.next_tile, obj.progress) == frozen
    world.smart_objects.set_in_use(obj, False)
    mover.tick_object(obj, 0.1)
    assert obj.progress > frozen[2] or obj.tile == frozen[1]


def test_non_pausing_object_moves_while_in_use():
    world, obj = make_world(pauses=False)
    world.smart_objects.set_in_use(obj, True)
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(7), move_rate=ALWAYS)
    mover.tick_object(obj, 0.1)
    assert obj.next_tile is not None


def test_no_step_when_every_direction_is_blocked():
    world, obj = make_world()
    for d in DIRECTIONS:
        world.add_wall(add(obj.tile, d))
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(8), move_rate=ALWAYS)
    for _ in range(100):
        mover.tick_object(obj, 0.1)
    assert obj.next_tile is None and obj.tile == (4, 0)


@pytest.mark.parametrize("seed", range(3))
def test_long_run_objects_stay_in_zone_and_never_overlap(seed):
    world = build_world()
    actor = Actor(tile=ACTOR_START)
    mover = ObjectMover(world, actor, random.Random(seed))
    objects = world.smart_objects.objects
    for _ in range(120 * 60):
        mover.tick(1 / 60)
        occupied = []
        for obj in objects:
            for tile in (obj.tile, obj.next_tile):
                if tile is None:
                    continue
                assert zone_of(tile) == obj.home_zone
                assert tile not in world.walls
                assert tile != actor.tile
                occupied.append(tile)
        assert len(occupied) == len(set(occupied))
