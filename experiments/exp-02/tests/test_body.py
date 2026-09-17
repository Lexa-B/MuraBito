from ai.beliefs import BeliefStore
from body import Body
from smartobjects import Interaction, Slot, SmartObject
from world import Actor, World


def setup(slot_directions=(3, 0)):
    """Object A at (4, 0) with slots at (3, 0) and (5, 0) by default; the actor at (0, 0)."""
    world = World()
    obj = SmartObject("A", (4, 0), frozenset({"Object.A"}), [Slot(i, d) for i, d in enumerate(slot_directions)],
                      [Interaction("A.Only", 1.0)], home_zone="NE")
    world.add_object(obj)
    beliefs = BeliefStore()
    log = []
    body = Body(world, Actor(tile=(0, 0)), beliefs, log.append)
    return world, obj, beliefs, body, log


def test_claim_is_refused_for_an_object_not_in_view_and_logged_once():
    world, obj, beliefs, body, log = setup()
    assert body.claim("A") is None
    assert body.claim("A") is None
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert log == ["body: claim A refused (not in view)"]


def test_claim_takes_the_nearest_free_slot():
    world, obj, beliefs, body, log = setup()
    beliefs.seen_now = {"A"}
    assert body.claim("A") == 0  # (3, 0) is nearer the actor than (5, 0)
    assert world.smart_objects.is_claimed(obj, obj.slots[0])
    assert body.claimed_slot() == ("A", 0)
    assert log == []


def test_claim_skips_a_slot_on_a_real_wall():
    world, obj, beliefs, body, _ = setup()
    beliefs.seen_now = {"A"}
    world.add_wall((3, 0))
    assert body.claim("A") == 1


def test_claim_fails_when_no_slot_is_free_and_logs_once_until_it_succeeds():
    world, obj, beliefs, body, log = setup(slot_directions=(3,))
    beliefs.seen_now = {"A"}
    other = world.smart_objects.claim(obj, obj.slots[0], actor="someone else")
    assert body.claim("A") is None
    assert body.claim("A") is None
    assert log == ["body: claim A failed (no free slot)"]
    world.smart_objects.release(other)
    assert body.claim("A") == 0
    body.release()
    world.smart_objects.claim(obj, obj.slots[0], actor="someone else")
    assert body.claim("A") is None
    assert log == ["body: claim A failed (no free slot)", "body: claim A failed (no free slot)"]


def test_a_second_claim_while_holding_one_is_ignored():
    world, obj, beliefs, body, _ = setup()
    beliefs.seen_now = {"A"}
    assert body.claim("A") == 0
    assert body.claim("A") is None
    assert body.claimed_slot() == ("A", 0)


def test_release_is_idempotent():
    world, obj, beliefs, body, _ = setup()
    beliefs.seen_now = {"A"}
    body.claim("A")
    body.release()
    body.release()
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert body.claimed_slot() is None


def test_in_use_follows_the_claim_and_clears_the_right_object_after_release():
    world, obj, beliefs, body, _ = setup()
    subsystem = world.smart_objects
    body.set_in_use(True)  # no claim: nothing to mark
    assert not subsystem.is_in_use(obj)
    beliefs.seen_now = {"A"}
    body.claim("A")
    body.set_in_use(True)
    assert subsystem.is_in_use(obj)
    body.release()
    body.set_in_use(False)
    assert not subsystem.is_in_use(obj)


def test_interactions_come_from_the_claimed_object():
    world, obj, beliefs, body, _ = setup()
    assert body.interactions() == []
    beliefs.seen_now = {"A"}
    body.claim("A")
    assert [i.name for i in body.interactions()] == ["A.Only"]
