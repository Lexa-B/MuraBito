from layout import ACTOR_START
from sim import build_sim


def test_build_sim_wires_context():
    sim = build_sim(seed=0)
    assert sim.actor.tile == ACTOR_START
    assert sim.ctx["actor"] is sim.actor and sim.ctx["world"] is sim.world
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def test_long_run_has_no_errors_and_one_claim_at_most():
    sim = build_sim(seed=0)
    subsystem = sim.world.smart_objects
    for _ in range(120 * 60):
        sim.step(1 / 60)
        claims = [(obj, slot) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert claims == ([] if claim is None else [(claim.object, claim.slot)])
    assert not any("error" in text for _, text in sim.tree.log)
    assert sim.ctx["LastUsed"] is not None
