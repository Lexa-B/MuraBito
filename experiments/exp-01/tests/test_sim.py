import pytest

from layout import ACTOR_START
from sim import build_sim
from world import zone_of


def test_build_sim_wires_context_and_mover():
    sim = build_sim(seed=0)
    assert sim.actor.tile == ACTOR_START
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


@pytest.mark.parametrize("seed", range(5))
def test_long_run_invariants(seed):
    sim = build_sim(seed)
    errors = watch_errors(sim)
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
    assert errors == []
