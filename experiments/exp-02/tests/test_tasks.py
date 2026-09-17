import random

import pytest

from ai.statetree import ROOT, Condition, State, StateTree, Status, Transition, Trigger
from ai.tasks import (
    FindAndClaim,
    Interact,
    MoveTo,
    Wait,
    ZoneEvaluator,
    claimed_slot_goal,
    random_tile_goal,
    release_claim,
)
from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject, slot_tile
from world import Actor, World, zone_of


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def make_ctx(object_tile=(6, 0), slot_direction=3, duration=0.5, pauses=True):
    """One object A; with the defaults its only slot is at (5, 0) and the actor starts at (0, 0)."""
    world = World()
    obj = SmartObject(
        "A", object_tile, frozenset({"Object.A"}), [Slot(0, slot_direction)],
        [Interaction("A.Only", duration, (set_last_used("A"),))],
        home_zone=zone_of(object_tile), pauses_during_use=pauses,
    )
    world.add_object(obj)
    log = []
    ctx = {
        "Zone": None, "LastUsed": None, "Target": None, "Claim": None,
        "Interaction": None, "InteractionElapsed": 0.0, "Path": None,
        "actor": Actor(tile=(0, 0)), "world": world, "rng": random.Random(0), "log": log.append,
    }
    return ctx, obj, log


def run(task, ctx, dt=0.1, max_ticks=1000):
    for _ in range(max_ticks):
        status = task.tick(ctx, dt)
        if status is not Status.RUNNING:
            return status
    raise AssertionError("task never finished")


def claim_a(ctx):
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.SUCCEEDED


def test_zone_evaluator_sets_zone_from_actor_tile():
    ctx, _, _ = make_ctx()
    ctx["actor"].tile = (-3, 0)
    ZoneEvaluator().tick(ctx, 0.1)
    assert ctx["Zone"] == "NW"


def test_find_and_claim_success():
    ctx, obj, log = make_ctx()
    claim_a(ctx)
    assert ctx["Target"] == "A"
    assert slot_tile(ctx["Claim"].object, ctx["Claim"].slot) == (5, 0)
    assert ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert log == ["claim A / slot 0"]


def test_find_and_claim_fails_when_no_object_matches():
    ctx, _, _ = make_ctx()
    task = FindAndClaim({"Object.Z"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert ctx["Claim"] is None


def test_find_and_claim_fails_when_every_slot_is_claimed():
    ctx, obj, _ = make_ctx()
    ctx["world"].smart_objects.claim(obj, obj.slots[0], actor="someone else")
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_find_and_claim_skips_a_blocked_slot():
    ctx, _, _ = make_ctx()
    ctx["world"].add_wall((5, 0))
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_move_to_walks_to_claimed_slot_and_faces_object():
    # Object is SE of the slot, so the last step (heading E) must not decide the final facing.
    ctx, obj, _ = make_ctx(object_tile=(5, 1), slot_direction=2)
    claim_a(ctx)
    move = MoveTo(claimed_slot_goal, chase=True)
    move.enter(ctx)
    assert ctx["Path"][0] == (0, 0) and ctx["Path"][-1] == (5, 0)
    assert run(move, ctx) is Status.SUCCEEDED
    actor = ctx["actor"]
    assert actor.tile == (5, 0) and actor.next_tile is None
    assert actor.facing == 5
    assert ctx["Path"] == [(5, 0)]


def test_move_to_speed_is_tiles_per_second():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    assert move.tick(ctx, 1.0) is Status.RUNNING  # speed 3 -> exactly 3 tiles in 1s
    assert ctx["actor"].tile == (3, 0)
    assert ctx["Path"] == [(3, 0), (4, 0), (5, 0)]  # a straight axis line has one shortest path


def test_move_to_fails_without_a_path():
    ctx, _, _ = make_ctx()
    goal = (0, 8)
    for d in DIRECTIONS:
        ctx["world"].add_wall(add(goal, d))
    move = MoveTo(lambda ctx: {goal})
    move.enter(ctx)
    assert ctx["Path"] is None
    assert move.tick(ctx, 0.1) is Status.FAILED


def test_move_to_replans_around_a_new_wall():
    ctx, _, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    wall = ctx["Path"][3]
    ctx["world"].add_wall(wall)
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0)
    assert "replan: path blocked" in log


def test_move_to_replans_around_an_object_stepping_into_the_path():
    ctx, obj, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    obj.next_tile = ctx["Path"][2]  # the object starts stepping onto the path
    assert run(move, ctx) is Status.SUCCEEDED
    assert "replan: path blocked" in log


def test_move_to_fails_when_the_goal_gets_walled_in():
    ctx, _, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    for tile in [(6, -1), (5, -1), (4, 0), (4, 1), (5, 1)]:  # (6, 0) is the object
        ctx["world"].add_wall(tile)
    assert run(move, ctx) is Status.FAILED
    assert "replan: path blocked" in log


def test_move_to_chases_a_moving_slot():
    ctx, obj, log = make_ctx()
    claim_a(ctx)
    move = MoveTo(claimed_slot_goal, chase=True)
    move.enter(ctx)
    move.tick(ctx, 0.5)
    obj.tile = (6, 2)  # the slot moves from (5, 0) to (5, 2)
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 2)
    assert "replan: slot moved" in log


def test_move_to_without_chase_keeps_its_first_goal():
    ctx, _, log = make_ctx()
    ctx["goal"] = {(5, 0)}
    move = MoveTo(lambda ctx: ctx["goal"])
    move.enter(ctx)
    ctx["goal"] = {(0, 5)}
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0)
    assert not any(text.startswith("replan") for text in log)


def test_move_to_exit_clears_mid_step_movement():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    move.tick(ctx, 0.1)
    assert ctx["actor"].next_tile is not None
    move.exit(ctx)
    assert ctx["actor"].next_tile is None and ctx["actor"].progress == 0.0
    assert ctx["Path"] is None


def test_random_tile_goal_picks_a_walkable_tile():
    ctx, _, _ = make_ctx()
    (tile,) = random_tile_goal(ctx)
    assert ctx["world"].is_walkable(tile)


def test_interact_applies_effects_after_duration_and_marks_in_use():
    ctx, obj, _ = make_ctx(duration=0.5)
    claim_a(ctx)
    ctx["actor"].tile = (5, 0)
    task = Interact()
    task.enter(ctx)
    subsystem = ctx["world"].smart_objects
    assert ctx["Interaction"].name == "A.Only"
    assert subsystem.is_in_use(obj)
    assert task.tick(ctx, 0.3) is Status.RUNNING
    assert ctx["LastUsed"] is None
    assert ctx["InteractionElapsed"] == pytest.approx(0.3)
    assert task.tick(ctx, 0.3) is Status.SUCCEEDED
    assert ctx["LastUsed"] == "A"
    assert ctx["Interaction"] is None
    task.exit(ctx)
    assert not subsystem.is_in_use(obj)


def test_interact_fails_when_the_slot_drifts_away():
    ctx, obj, log = make_ctx(duration=5.0, pauses=False)
    claim_a(ctx)
    ctx["actor"].tile = (5, 0)
    task = Interact()
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.RUNNING
    obj.tile = (7, 0)  # slot moves to (6, 0)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert ctx["LastUsed"] is None
    assert "interact: slot drifted away" in log
    task.exit(ctx)
    assert not ctx["world"].smart_objects.is_in_use(obj)


def test_interact_fails_without_a_claim():
    ctx, _, _ = make_ctx()
    task = Interact()
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_wait():
    task = Wait(1.0)
    task.enter({})
    assert task.tick({}, 0.6) is Status.RUNNING
    assert task.tick({}, 0.6) is Status.SUCCEEDED


def test_release_claim_clears_and_logs_and_is_a_noop_without_claim():
    ctx, obj, log = make_ctx()
    release_claim(ctx)
    assert log == []
    claim = FindAndClaim({"Object.A"})
    claim.enter(ctx)
    release_claim(ctx)
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert log == ["claim A / slot 0", "release A / slot 0"]


def go_use_tree():
    return StateTree(State("Root", children=[
        State("GoUse(A)", conditions=[Condition("LastUsed==None", lambda ctx: ctx["LastUsed"] is None)],
              on_exit=release_claim, children=[
            State("FindAndClaim", task=FindAndClaim({"Object.A"}), transitions=[
                Transition(Trigger.ON_COMPLETED, "GoUse(A)/MoveTo"),
                Transition(Trigger.ON_FAILED, "Idle"),
            ]),
            State("MoveTo", task=MoveTo(claimed_slot_goal, chase=True), transitions=[
                Transition(Trigger.ON_COMPLETED, "GoUse(A)/Interact"),
                Transition(Trigger.ON_FAILED, "Idle"),
            ]),
            State("Interact", task=Interact(), transitions=[
                Transition(Trigger.ON_COMPLETED, ROOT),
                Transition(Trigger.ON_FAILED, ROOT),
            ]),
        ]),
        State("Idle", task=Wait(100.0)),
    ]), evaluators=[ZoneEvaluator()])


def run_until(tree, ctx, leaf_path, max_ticks=1000):
    for _ in range(max_ticks):
        tree.tick(ctx, 0.1)
        if tree.leaf is not None and tree.leaf.path == leaf_path:
            return
    raise AssertionError(f"tree never reached {leaf_path}")


def test_claim_released_when_go_use_completes():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    run_until(tree, ctx, "Idle")
    assert ctx["LastUsed"] == "A"
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert not ctx["world"].smart_objects.is_in_use(obj)
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert "release A / slot 0" in log


def test_claim_released_when_move_fails_partway():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    tree.tick(ctx, 0.1)  # claims, then moves on to MoveTo, which plans its path
    assert tree.leaf.path == "GoUse(A)/MoveTo"
    for tile in [(6, -1), (5, -1), (4, 0), (4, 1), (5, 1)]:  # wall the slot in
        ctx["world"].add_wall(tile)
    run_until(tree, ctx, "Idle")
    assert ctx["LastUsed"] is None
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None
    assert ctx["actor"].tile != (5, 0)


def test_in_use_and_claim_cleared_when_tree_resets_mid_interaction():
    ctx, obj, _ = make_ctx(duration=5.0)
    tree = go_use_tree()
    run_until(tree, ctx, "GoUse(A)/Interact")
    subsystem = ctx["world"].smart_objects
    assert subsystem.is_in_use(obj)
    tree.reset(ctx)
    assert not subsystem.is_in_use(obj)
    assert not subsystem.is_claimed(obj, obj.slots[0])
