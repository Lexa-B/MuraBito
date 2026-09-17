import pytest

from sim import build_sim
from world import zone_of


def test_build_sim_wires_context_and_mover():
    sim = build_sim(seed=0)
    assert sim.world.is_walkable(sim.actor.tile)
    assert sim.ctx["actor"] is sim.actor and sim.ctx["world"] is sim.world
    assert sim.mover.world is sim.world and sim.mover.actor is sim.actor and sim.mover.rng is sim.ctx["rng"]
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def watch_errors(sim):
    """Record every error log line, even ones the bounded log deque later drops."""
    errors = []
    write = sim.tree.write_log

    def spy(text):
        if "error" in text:
            errors.append(text)
        write(text)

    sim.tree.write_log = spy
    sim.ctx["log"] = spy
    return errors


def watch_drift(sim):
    """Record 'slot drifted away' lines logged while the claimed object pauses during use.

    A pausing object is frozen by the mover whenever it's in use, so its slot should
    never drift out from under the actor mid-interaction.
    """
    drifts = []
    write = sim.tree.write_log

    def spy(text):
        if text == "interact: slot drifted away":
            claim = sim.ctx["Claim"]
            if claim is not None and claim.object.pauses_during_use:
                drifts.append(text)
        write(text)

    sim.tree.write_log = spy
    sim.ctx["log"] = spy
    return drifts


def test_step_ticks_mover_before_tree():
    sim = build_sim(seed=0)
    order = []
    sim.mover.tick = lambda dt: order.append("mover")
    sim.tree.tick = lambda ctx, dt: order.append("tree")
    sim.step(1 / 60)
    assert order == ["mover", "tree"]


@pytest.mark.parametrize("seed", range(5))
def test_long_run_invariants(seed):
    sim = build_sim(seed)
    errors = watch_errors(sim)
    drifts = watch_drift(sim)
    subsystem = sim.world.smart_objects
    for _ in range(120 * 60):
        sim.step(1 / 60)
        claims = [(obj, slot) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert claims == ([] if claim is None else [(claim.object, claim.slot)])
        actor_tiles = {sim.actor.tile, sim.actor.next_tile} - {None}
        for obj in subsystem.objects:
            object_tiles = {obj.tile, obj.next_tile} - {None}
            assert all(zone_of(t) == obj.home_zone for t in object_tiles)
            assert not object_tiles & actor_tiles
        leaf = sim.tree.leaf
        in_use = [o for o in subsystem.objects if subsystem.is_in_use(o)]
        if leaf is not None and leaf.name == "Interact" and claim is not None:
            assert in_use == [claim.object]
        else:
            assert in_use == []
    assert errors == []
    assert drifts == []


def test_all_objects_get_used_within_a_minute_on_seed_0():
    sim = build_sim(seed=0)
    used = set()
    for _ in range(60 * 60):
        sim.step(1 / 60)
        if sim.ctx["LastUsed"] is not None:
            used.add(sim.ctx["LastUsed"])
    assert used == {"A", "B", "C"}
