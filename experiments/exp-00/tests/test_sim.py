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


def test_actor_cycles_through_objects_as_the_spec_predicts():
    sim = build_sim(seed=0)
    used = []
    for _ in range(180 * 60):  # 180 sim-seconds at 60 Hz
        sim.step(1 / 60)
        last = sim.ctx["LastUsed"]
        if last is not None and (not used or used[-1] != last):
            used.append(last)
    assert used[:5] == ["A", "B", "C", "B", "A"]
    assert not any("error" in text for _, text in sim.tree.log)
