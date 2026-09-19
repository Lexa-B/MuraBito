from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject, SmartObjectSubsystem, slot_facing, slot_tile


def make_object(name, tile, slot_directions):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, direction=d) for i, d in enumerate(slot_directions)],
        interactions=[Interaction(f"{name}.Short", 1.5)],
    )


def make_subsystem():
    subsystem = SmartObjectSubsystem()
    a = make_object("A", (0, 0), [0, 3])  # slots at (1, 0) and (-1, 0)
    b = make_object("B", (6, 0), [3])  # slot at (5, 0)
    subsystem.register(a)
    subsystem.register(b)
    return subsystem, a, b


def test_new_object_movement_defaults():
    obj = make_object("A", (0, 0), [0])
    assert (obj.home_zone, obj.pauses_during_use, obj.casts_shadow, obj.heading, obj.next_tile, obj.progress) == (
        "", True, False, 0, None, 0.0
    )


def test_slot_tile_and_facing_follow_the_object():
    subsystem, a, b = make_subsystem()
    slot = a.slots[0]
    assert slot_tile(a, slot) == (1, 0)
    assert slot_facing(slot) == 3
    a.tile = (2, 2)
    assert slot_tile(a, slot) == (3, 2)
    assert add(slot_tile(a, slot), DIRECTIONS[slot_facing(slot)]) == a.tile


def test_find_filters_by_tag():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.B"}, near=(0, 0)) == [(b, b.slots[0])]


def test_find_requires_every_tag_in_the_query():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.A", "Something.Else"}, near=(0, 0)) == []


def test_empty_query_matches_every_object():
    subsystem, a, b = make_subsystem()
    assert len(subsystem.find(set(), near=(0, 0))) == 3


def test_find_sorts_by_hex_distance_of_the_live_slot_tile():
    subsystem, a, b = make_subsystem()
    results = subsystem.find(set(), near=(4, 0))
    assert [slot_tile(obj, slot) for obj, slot in results] == [(5, 0), (1, 0), (-1, 0)]
    b.tile = (-6, 0)  # B's slot moves to (-7, 0)
    results = subsystem.find(set(), near=(4, 0))
    assert [slot_tile(obj, slot) for obj, slot in results] == [(1, 0), (-1, 0), (-7, 0)]


def test_find_skips_blocked_slots():
    subsystem, a, b = make_subsystem()
    found = subsystem.find({"Object.A"}, near=(0, 0), blocked_fn=lambda tile: tile == (1, 0))
    assert found == [(a, a.slots[1])]


def test_claimed_slots_are_excluded_from_find():
    subsystem, a, b = make_subsystem()
    subsystem.claim(a, a.slots[0], actor="actor")
    assert subsystem.find({"Object.A"}, near=(0, 0)) == [(a, a.slots[1])]


def test_claiming_a_claimed_slot_returns_none():
    subsystem, a, b = make_subsystem()
    handle = subsystem.claim(a, a.slots[0], actor="actor")
    assert handle is not None
    assert handle.object is a and handle.slot == a.slots[0] and handle.actor == "actor"
    assert subsystem.is_claimed(a, a.slots[0])
    assert subsystem.claim(a, a.slots[0], actor="someone else") is None


def test_release_frees_the_slot_and_is_idempotent():
    subsystem, a, b = make_subsystem()
    handle = subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(handle)
    subsystem.release(handle)
    assert not subsystem.is_claimed(a, a.slots[0])
    assert subsystem.claim(a, a.slots[0], actor="actor") is not None


def test_releasing_a_stale_handle_does_not_free_a_newer_claim():
    subsystem, a, b = make_subsystem()
    old = subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(old)
    subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(old)
    assert subsystem.is_claimed(a, a.slots[0])


def test_in_use_set_and_clear():
    subsystem, a, b = make_subsystem()
    assert not subsystem.is_in_use(a)
    subsystem.set_in_use(a, True)
    assert subsystem.is_in_use(a) and not subsystem.is_in_use(b)
    subsystem.set_in_use(a, False)
    subsystem.set_in_use(a, False)
    assert not subsystem.is_in_use(a)
