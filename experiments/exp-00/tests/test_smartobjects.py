from smartobjects import Interaction, Slot, SmartObject, SmartObjectSubsystem


def make_object(name, tile, slot_tiles):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, tile=t, facing=0) for i, t in enumerate(slot_tiles)],
        interactions=[Interaction(f"{name}.Short", 1.5)],
    )


def make_subsystem():
    subsystem = SmartObjectSubsystem()
    a = make_object("A", (0, 0), [(1, 0), (-1, 0)])
    b = make_object("B", (6, 0), [(5, 0)])
    subsystem.register(a)
    subsystem.register(b)
    return subsystem, a, b


def test_find_filters_by_tag():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.B"}, near=(0, 0)) == [(b, b.slots[0])]


def test_find_requires_every_tag_in_the_query():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.A", "Something.Else"}, near=(0, 0)) == []


def test_empty_query_matches_every_object():
    subsystem, a, b = make_subsystem()
    assert len(subsystem.find(set(), near=(0, 0))) == 3


def test_find_sorts_by_hex_distance():
    subsystem, a, b = make_subsystem()
    results = subsystem.find(set(), near=(4, 0))
    assert [slot.tile for _, slot in results] == [(5, 0), (1, 0), (-1, 0)]


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
