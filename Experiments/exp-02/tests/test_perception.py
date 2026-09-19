from ai.beliefs import LOST, POINT, REGION, BeliefStore
from ai.perception import PerceptionEvaluator
from smartobjects import Slot, SmartObject
from world import Actor, World, zone_of


def make_object(name, tile, slot_directions=(3,), casts_shadow=False):
    return SmartObject(name, tile, frozenset({f"Object.{name}"}), [Slot(i, d) for i, d in enumerate(slot_directions)], [],
                       home_zone=zone_of(tile), casts_shadow=casts_shadow)


def setup(objects=(), walls=(), facing=0):
    world = World(walls=walls)
    for obj in objects:
        world.add_object(obj)
    log = []
    ctx = {"beliefs": BeliefStore(), "actor": Actor(tile=(0, 0), facing=facing), "log": log.append}
    return world, PerceptionEvaluator(world), ctx, log


def test_only_visible_objects_create_beliefs():
    ahead, behind = make_object("A", (4, 0)), make_object("B", (-4, 0))
    world, perception, ctx, log = setup([ahead, behind])
    perception.tick(ctx, 0.1)
    beliefs = ctx["beliefs"]
    assert set(beliefs.beliefs) == {"A"} and beliefs.seen_now == {"A"}
    assert beliefs.beliefs["A"].datum_tile == (4, 0)
    assert log == ["see A at (4,0)"]


def test_a_visible_slot_is_enough_to_see_the_object():
    # The wall at (2, 0) shadows (4, -1), but the slot at (4, -2) (direction 2 from the object) is in view.
    obj = make_object("A", (4, -1), slot_directions=(2,))
    world, perception, ctx, _ = setup([obj], walls=[(2, 0)])
    perception.tick(ctx, 0.1)
    assert (4, -1) not in ctx["beliefs"].visible_now
    assert "A" in ctx["beliefs"].seen_now


def test_an_object_stepping_into_view_is_seen():
    # A at (-2, 2) is behind the actor (facing E) and its slot (-3, 2) is too, but it is
    # stepping into (-1, 1), a neighbor of the actor.
    obj = make_object("A", (-2, 2))
    world, perception, ctx, _ = setup([obj])
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].seen_now == set()
    obj.next_tile = (-1, 1)
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].seen_now == {"A"}
    assert ctx["beliefs"].beliefs["A"].datum_next_tile == (-1, 1)
    assert not ctx["beliefs"].is_walkable((-1, 1))


def test_walls_are_learned_only_when_visible():
    world, perception, ctx, _ = setup(walls=[(2, 0), (3, 0), (-3, 0)])
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].known_walls == {(2, 0)}  # (3, 0) is in its shadow, (-3, 0) is behind


def test_only_shadow_casting_objects_hide_what_is_behind_them():
    front, back = make_object("A", (2, 0), casts_shadow=True), make_object("B", (4, 0))
    world, perception, ctx, _ = setup([front, back])
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].seen_now == {"A"}
    front.casts_shadow = False
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].seen_now == {"A", "B"}


def test_in_use_is_passed_through_so_watching_time_pauses():
    obj = make_object("A", (4, 0))
    world, perception, ctx, _ = setup([obj])
    perception.tick(ctx, 0.1)
    world.smart_objects.set_in_use(obj, True)
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].beliefs["A"].observed_seconds == 0.0
    world.smart_objects.set_in_use(obj, False)
    perception.tick(ctx, 0.1)
    assert ctx["beliefs"].beliefs["A"].observed_seconds == 0.1


def test_see_and_lose_sight_are_logged_once_per_change():
    obj = make_object("A", (4, 0))
    world, perception, ctx, log = setup([obj])
    perception.tick(ctx, 0.1)
    perception.tick(ctx, 0.1)
    ctx["actor"].facing = 3
    perception.tick(ctx, 0.1)
    perception.tick(ctx, 0.1)
    assert log == ["see A at (4,0)", "lose sight of A"]


def test_absence_outside_the_view_never_retracts_but_in_view_does():
    obj = make_object("A", (4, 0))
    world, perception, ctx, log = setup([obj])
    beliefs = ctx["beliefs"]
    perception.tick(ctx, 0.1)
    obj.tile = (0, 8)  # A moves somewhere the actor can't see
    ctx["actor"].facing = 3  # look away
    perception.tick(ctx, 0.1)
    assert beliefs.level("A") == POINT
    assert not any("retracting" in line for line in log)
    ctx["actor"].facing = 0  # look back at where A was
    perception.tick(ctx, 0.1)
    assert beliefs.level("A") == REGION
    assert log[-1] == "belief: A not at (4,0) - retracting"


def test_level_changes_from_growth_are_logged_once():
    obj = make_object("A", (4, 0))
    world, perception, ctx, log = setup([obj])
    perception.tick(ctx, 0.1)
    obj.tile = (0, 8)
    ctx["actor"].facing = 3
    for _ in range(300):  # 30 s unseen at the prior speed: REGION at about 8.3 s, LOST at about 21.7 s
        perception.tick(ctx, 0.1)
    assert ctx["beliefs"].level("A") == LOST
    assert [line for line in log if line.startswith("belief:")] == ["belief: A -> REGION", "belief: A -> LOST"]


def test_a_retraction_is_not_also_logged_as_a_level_change():
    obj = make_object("A", (4, 0))
    world, perception, ctx, log = setup([obj])
    perception.tick(ctx, 0.1)
    obj.tile = (0, 8)
    perception.tick(ctx, 0.1)  # still facing (4, 0): retracted on this tick
    perception.tick(ctx, 0.1)
    assert [line for line in log if line.startswith("belief:")] == ["belief: A not at (4,0) - retracting"]
