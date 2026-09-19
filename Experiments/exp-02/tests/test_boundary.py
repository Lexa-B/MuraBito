"""The truth/belief boundary: tasks, tree conditions and beliefs never read the world."""

import ast
import random
from pathlib import Path

from ai.beliefs import BeliefStore, Observation
from ai.statetree import Status
from ai.tasks import ChooseTarget, MoveTo, target_goal
from body import Body
from hexgrid import all_tiles, distance
from sim import build_sim
from smartobjects import ClaimHandle, Slot, SmartObject
from world import Actor, World
from zones import zone_of

SRC = Path(__file__).resolve().parent.parent / "src"
FORBIDDEN = {"world", "smartobjects", "wander", "body", "layout", "mapgen", "sim"}


def imported_modules(path):
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_belief_side_modules_import_nothing_from_the_truth_side():
    for relative in ["ai/tasks.py", "ai/tree_def.py", "ai/beliefs.py"]:
        assert not imported_modules(SRC / relative) & FORBIDDEN, relative


def test_ctx_has_no_world_and_no_claim_handles_even_after_claims():
    sim = build_sim(seed=0)
    assert "world" not in sim.ctx
    claimed = False
    for _ in range(60 * 60):
        sim.step(1 / 60)
        claimed = claimed or sim.ctx["Claim"] is not None
        assert not any(isinstance(value, (ClaimHandle, World, SmartObject)) for value in sim.ctx.values())
    assert claimed


def test_tasks_act_on_belief_when_belief_and_truth_disagree():
    world = World()
    b = SmartObject("B", (-10, 11), frozenset({"Object.B"}), [Slot(0, 0)], [], home_zone="S")
    world.add_object(b)  # true B, outside the believed search area around X
    beliefs = BeliefStore()
    beliefs.begin_tick(0.1)
    beliefs.observe_object(Observation("B", b.tags, (-2, 8), None, (0,), False))  # believed B at X = (-2, 8)
    beliefs.begin_tick(0.1)  # no longer in view
    actor = Actor(tile=(0, 0))
    log = []
    ctx = {"Target": None, "Claim": None, "Path": None, "actor": actor, "rng": random.Random(0),
           "log": log.append, "beliefs": beliefs}
    ctx["body"] = Body(world, actor, beliefs, log.append)

    choose = ChooseTarget({"Object.B"})
    choose.enter(ctx)
    assert choose.tick(ctx, 0.1) is Status.SUCCEEDED and ctx["Target"] == "B"
    assert target_goal(ctx) == {(-1, 8)}  # B's slot at X, not at the true (-9, 11)
    move = MoveTo(target_goal, chase=True, claim=True)
    move.enter(ctx)
    assert ctx["Path"][-1] == (-1, 8)
    beliefs.beliefs["B"].radius_floor = 6.0  # REGION: search around X
    area = beliefs.search_area("B")
    assert area[0] == (-2, 8)
    radius = beliefs.uncertainty_radius("B")
    expected = {t for t in all_tiles() if distance(t, (-2, 8)) <= radius and zone_of(t) == "S"}
    assert set(area) == expected
    assert (-10, 11) not in area  # true B is outside the believed search area
    assert ctx["Claim"] is None  # B was never in view, so nothing was claimed


def test_belief_side_modules_never_read_truth_attributes():
    """Structural guard: even `ctx["body"].world` (or `._handle`, `.smart_objects`) would be a leak."""
    forbidden_attrs = {"world", "_handle", "smart_objects"}
    for relative in ["ai/tasks.py", "ai/tree_def.py"]:
        tree = ast.parse((SRC / relative).read_text())
        hits = [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute) and node.attr in forbidden_attrs]
        assert not hits, (relative, hits)
