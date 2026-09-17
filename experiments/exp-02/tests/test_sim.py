import pytest

from ai.beliefs import BeliefStore
from body import Body
from sim import build_sim
from world import zone_of

DT = 1 / 60


def test_build_sim_wires_context_beliefs_body_and_mover():
    sim = build_sim(seed=3)
    assert sim.seed == 3
    assert sim.world.is_walkable(sim.actor.tile)
    assert sim.ctx["actor"] is sim.actor
    assert sim.ctx["beliefs"] is sim.beliefs and isinstance(sim.beliefs, BeliefStore)
    assert sim.ctx["body"] is sim.body and isinstance(sim.body, Body)
    assert "world" not in sim.ctx
    assert sim.mover.world is sim.world and sim.mover.actor is sim.actor and sim.mover.rng is sim.ctx["rng"]
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    assert sim.beliefs.beliefs == {}  # cold start
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def spy_log(sim):
    """Record every log line, even ones the bounded log deque later drops."""
    lines = []
    write = sim.tree.write_log

    def spy(text):
        lines.append(text)
        write(text)

    sim.tree.write_log = spy
    sim.ctx["log"] = spy
    return lines


def spy_claims(sim):
    """Record (name, seen this tick, result) for every Body.claim call."""
    calls = []
    claim = sim.body.claim

    def spy(name):
        seen = name in sim.beliefs.seen_now
        result = claim(name)
        calls.append((name, seen, result))
        return result

    sim.body.claim = spy
    return calls


def test_step_ticks_mover_before_tree_and_perception_first():
    sim = build_sim(seed=0)
    order = []
    sim.mover.tick = lambda dt: order.append("mover")
    sim.tree.evaluators[0].tick = lambda ctx, dt: order.append("perception")
    sim.tree.evaluators[1].tick = lambda ctx, dt: order.append("zone")
    sim.step(DT)
    assert order[:3] == ["mover", "perception", "zone"]


@pytest.mark.parametrize("seed", range(5))
def test_long_run_invariants(seed):
    sim = build_sim(seed)
    lines = spy_log(sim)
    claims = spy_claims(sim)
    subsystem = sim.world.smart_objects
    by_name = {obj.name: obj for obj in subsystem.objects}
    truth = {}  # beliefs.now -> {name: tile} after each step
    drift_on_pausing = []
    for _ in range(120 * 60):
        before = len(lines)
        claim_before = sim.ctx["Claim"]
        sim.step(DT)
        truth[sim.beliefs.now] = {obj.name: obj.tile for obj in subsystem.objects}
        if "interact: slot drifted away" in lines[before:] and claim_before is not None:
            if by_name[claim_before[0]].pauses_during_use:
                drift_on_pausing.append(claim_before)

        live = [(obj.name, slot.index) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert live == ([] if claim is None else [claim])
        assert sim.body.claimed_slot() == claim

        actor_tiles = {sim.actor.tile, sim.actor.next_tile} - {None}
        for obj in subsystem.objects:
            object_tiles = {obj.tile, obj.next_tile} - {None}
            assert all(zone_of(t) == obj.home_zone for t in object_tiles)
            assert not object_tiles & actor_tiles

        leaf = sim.tree.leaf
        in_use = [obj.name for obj in subsystem.objects if subsystem.is_in_use(obj)]
        if leaf is not None and leaf.name == "Interact" and claim is not None:
            assert in_use == [claim[0]]
        else:
            assert in_use == []

        for name, belief in sim.beliefs.beliefs.items():
            assert truth[belief.datum_time][name] == belief.datum_tile

    assert not [line for line in lines if "error" in line]
    assert drift_on_pausing == []
    assert all(seen for name, seen, result in claims if result is not None)


def run_log(seed, seconds):
    sim = build_sim(seed)
    lines = spy_log(sim)
    for _ in range(round(seconds * 60)):
        sim.step(DT)
    return lines


def test_same_seed_same_run():
    assert run_log(2, 30) == run_log(2, 30)


@pytest.mark.parametrize("seed", range(5))
def test_every_object_is_seen_within_a_minute(seed):
    sim = build_sim(seed)
    for _ in range(60 * 60):
        sim.step(DT)
        if len(sim.beliefs.beliefs) == 3:
            return
    raise AssertionError(f"seed {seed}: only saw {sorted(sim.beliefs.beliefs)} in 60 s")


def test_all_objects_get_used_within_a_minute_on_seed_0():
    sim = build_sim(seed=0)
    used = set()
    for _ in range(60 * 60):
        sim.step(DT)
        if sim.ctx["LastUsed"] is not None:
            used.add(sim.ctx["LastUsed"])
    assert used == {"A", "B", "C"}
