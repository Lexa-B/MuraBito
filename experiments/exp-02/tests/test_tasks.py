import random

import pytest

from ai.beliefs import LOST_RADIUS, BeliefStore, Observation
from ai.perception import PerceptionEvaluator
from ai.statetree import State, StateTree, Status
from ai.tasks import (
    ChooseTarget,
    Explore,
    Interact,
    MoveTo,
    Search,
    Wait,
    ZoneEvaluator,
    random_tile_goal,
    release_claim,
    target_goal,
)
from ai.tree_def import go_use_state
from ai.statetree import Condition, Mode
from body import Body
from hexgrid import DIRECTIONS, add, all_tiles, distance
from smartobjects import Interaction, Slot, SmartObject
from world import Actor, World, zone_of


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def make_object(name="A", tile=(6, 0), slot_directions=(3,), duration=0.5, pauses=True):
    return SmartObject(
        name, tile, frozenset({f"Object.{name}"}), [Slot(i, d) for i, d in enumerate(slot_directions)],
        [Interaction(f"{name}.Only", duration, (set_last_used(name),))],
        home_zone=zone_of(tile), pauses_during_use=pauses,
    )


def make_ctx(*objects):
    """A world holding `objects` (default: A at (6, 0) with one slot at (5, 0)); the actor at (0, 0)."""
    world = World()
    for obj in objects or (make_object(),):
        world.add_object(obj)
    beliefs = BeliefStore()
    log = []
    actor = Actor(tile=(0, 0))
    ctx = {
        "Zone": None, "LastUsed": None, "Target": None, "Claim": None,
        "Interaction": None, "InteractionElapsed": 0.0, "Path": None,
        "actor": actor, "rng": random.Random(0), "log": log.append, "beliefs": beliefs,
    }
    ctx["body"] = Body(world, actor, beliefs, log.append)
    return ctx, world, log


def see(ctx, *objects, tiles=(), dt=0.1):
    """One belief tick in which exactly `objects` (at their true tiles) and `tiles` are seen."""
    beliefs = ctx["beliefs"]
    beliefs.begin_tick(dt)
    beliefs.observe_tiles(tiles, [])
    for obj in objects:
        beliefs.observe_object(Observation(obj.name, obj.tags, obj.tile, obj.next_tile,
                                           tuple(s.direction for s in obj.slots), False))
    return beliefs.apply_negative_evidence()


def run(task, ctx, dt=0.1, max_ticks=1000):
    for _ in range(max_ticks):
        status = task.tick(ctx, dt)
        if status is not Status.RUNNING:
            return status
    raise AssertionError("task never finished")


def test_zone_evaluator_sets_zone_from_actor_tile():
    ctx, _, _ = make_ctx()
    ctx["actor"].tile = (-3, 0)
    ZoneEvaluator().tick(ctx, 0.1)
    assert ctx["Zone"] == "NW"


# --- ChooseTarget ---------------------------------------------------------------


def test_choose_target_prefers_point_over_a_nearer_region_belief():
    far, near = make_object("A", (8, 0)), make_object("B", (0, 3))
    ctx, _, log = make_ctx(far, near)
    see(ctx, far, near)
    ctx["beliefs"].beliefs["B"].radius_floor = 6.0  # REGION
    task = ChooseTarget(set())
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.SUCCEEDED
    assert ctx["Target"] == "A"
    assert log == ["target A (POINT)"]


def test_choose_target_takes_the_nearest_of_a_level_and_falls_back_to_region():
    a, b = make_object("A", (8, 0)), make_object("B", (0, 3))
    ctx, _, log = make_ctx(a, b)
    see(ctx, a, b)
    task = ChooseTarget(set())
    task.enter(ctx)
    assert ctx["Target"] == "B"
    for belief in ctx["beliefs"].beliefs.values():
        belief.radius_floor = 6.0
    task.enter(ctx)
    assert ctx["Target"] == "B" and log[-1] == "target B (REGION)"


def test_choose_target_ignores_lost_beliefs_and_non_matching_tags():
    a = make_object("A", (8, 0))
    ctx, _, _ = make_ctx(a)
    see(ctx, a)
    task = ChooseTarget({"Object.B"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED
    ctx["beliefs"].beliefs["A"].radius_floor = LOST_RADIUS + 1
    ctx["Target"] = "stale"
    task = ChooseTarget({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert ctx["Target"] is None


# --- MoveTo ------------------------------------------------------------------------


def test_move_to_speed_is_tiles_per_second():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    assert move.tick(ctx, 1.0) is Status.RUNNING  # speed 3 -> exactly 3 tiles in 1s
    assert ctx["actor"].tile == (3, 0)
    assert ctx["Path"] == [(3, 0), (4, 0), (5, 0)]


def test_move_to_plans_through_never_seen_tiles_and_ignores_true_objects_it_does_not_know():
    ctx, world, _ = make_ctx(make_object("A", (3, 0)))  # A really sits on the straight line
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    assert ctx["Path"] == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]


def test_move_to_fails_without_a_path_on_the_believed_map():
    ctx, _, _ = make_ctx()
    goal = (0, 8)
    ctx["beliefs"].known_walls |= {add(goal, d) for d in DIRECTIONS}
    move = MoveTo(lambda ctx: {goal})
    move.enter(ctx)
    assert ctx["Path"] is None
    assert move.tick(ctx, 0.1) is Status.FAILED


def test_move_to_replans_around_a_newly_known_wall():
    ctx, _, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    ctx["beliefs"].known_walls.add(ctx["Path"][3])
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0)
    assert "replan: path blocked" in log


def test_move_to_replans_around_a_seen_object_stepping_into_the_path():
    obj = make_object("A", (2, -2))
    ctx, _, log = make_ctx(obj)
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    obj.next_tile = ctx["Path"][2]
    see(ctx, obj)
    assert run(move, ctx) is Status.SUCCEEDED
    assert "replan: path blocked" in log


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


def test_random_tile_goal_picks_a_believed_walkable_tile():
    ctx, _, _ = make_ctx()
    ctx["beliefs"].known_walls |= set(all_tiles()) - {(1, 1), (2, 2)}
    (tile,) = random_tile_goal(ctx)
    assert tile in {(1, 1), (2, 2)}


def test_target_goal_is_every_believed_walkable_slot_then_the_claimed_one():
    obj = make_object("A", (6, 0), slot_directions=(3, 0, 1))  # slots (5, 0), (7, 0), (7, -1)
    ctx, _, _ = make_ctx(obj)
    assert target_goal(ctx) is None
    see(ctx, obj)
    ctx["Target"] = "A"
    ctx["beliefs"].known_walls.add((7, -1))
    assert target_goal(ctx) == {(5, 0), (7, 0)}
    ctx["Claim"] = ("A", 1)
    assert target_goal(ctx) == {(7, 0)}


def test_move_to_claims_on_sight_and_walks_to_the_claimed_slot_facing_the_object():
    obj = make_object("A", (5, 1), slot_directions=(2, 1))  # slots (5, 0) and (6, 0)
    ctx, world, log = make_ctx(obj)
    see(ctx, obj)
    ctx["Target"] = "A"
    move = MoveTo(target_goal, chase=True, claim=True)
    move.enter(ctx)
    assert ctx["Claim"] == ("A", 0)  # (5, 0) is the nearer slot
    assert log == ["claim A / slot 0"]
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0) and ctx["actor"].facing == 5


def test_move_to_does_not_claim_an_object_out_of_view_and_fails_on_arrival_without_a_claim():
    obj = make_object()
    ctx, world, log = make_ctx(obj)
    see(ctx, obj)
    see(ctx)  # A is no longer in view, but still believed at (6, 0)
    ctx["Target"] = "A"
    move = MoveTo(target_goal, chase=True, claim=True)
    move.enter(ctx)
    assert run(move, ctx) is Status.FAILED
    assert ctx["actor"].tile == (5, 0)
    assert ctx["Claim"] is None
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert not any(text.startswith("claim") for text in log)


def test_move_to_chases_a_ghost_that_moves():
    obj = make_object("A", (6, 0))
    ctx, _, log = make_ctx(obj)
    see(ctx, obj)
    see(ctx)
    ctx["Target"] = "A"
    move = MoveTo(target_goal, chase=True, claim=True)
    move.enter(ctx)
    move.tick(ctx, 0.5)
    ctx["beliefs"].beliefs["A"].datum_tile = (6, 2)  # the belief moves: the slot is now (5, 2)
    assert run(move, ctx) is Status.FAILED  # arrives, but A was never in view to claim
    assert ctx["actor"].tile == (5, 2)
    assert "replan: target moved" in log


# --- Search ---------------------------------------------------------------------


def region_belief(ctx, obj, unseen_seconds=10.0):
    see(ctx, obj)
    for _ in range(round(unseen_seconds / 0.1)):
        see(ctx)
    ctx["Target"] = obj.name


def test_search_walks_toward_the_first_area_tile():
    obj = make_object("A", (-3, 8))
    ctx, _, _ = make_ctx(obj)
    region_belief(ctx, obj)
    search = Search()
    search.enter(ctx)
    assert search.tick(ctx, 0.1) is Status.RUNNING
    assert search.tile == ctx["beliefs"].search_area("A")[0] == (-3, 8)
    assert ctx["Path"][-1] == (-3, 8)


def test_search_moves_on_when_its_tile_is_cleared():
    obj = make_object("A", (-3, 8))
    ctx, _, _ = make_ctx(obj)
    region_belief(ctx, obj)
    search = Search()
    search.enter(ctx)
    search.tick(ctx, 0.0)  # dt 0: decide at the current tile without stepping
    assert search.tile == (-3, 8)
    see(ctx, tiles=[(-3, 8)])  # the first tile is seen empty
    search.tick(ctx, 0.0)
    assert search.tile != (-3, 8)
    assert search.tile == ctx["beliefs"].search_area("A")[0]


def test_search_gives_up_when_the_target_is_lost():
    obj = make_object("A", (-3, 8))
    ctx, _, log = make_ctx(obj)
    region_belief(ctx, obj)
    ctx["beliefs"].beliefs["A"].radius_floor = LOST_RADIUS + 1
    search = Search()
    search.enter(ctx)
    assert search.tick(ctx, 0.1) is Status.FAILED
    assert log[-1] == "search: give up on A"


def test_search_gives_up_when_every_area_tile_is_cleared():
    obj = make_object("A", (-3, 8))
    ctx, _, log = make_ctx(obj)
    region_belief(ctx, obj)
    see(ctx, tiles=all_tiles())
    search = Search()
    search.enter(ctx)
    assert search.tick(ctx, 0.1) is Status.FAILED
    assert log[-1] == "search: give up on A"


# --- Explore --------------------------------------------------------------------


def test_explore_walks_to_the_frontier_and_succeeds_on_arrival():
    ctx, _, log = make_ctx()
    see(ctx, tiles=[(0, 0)])
    explore = Explore(set())
    explore.enter(ctx)
    frontier = explore.tile
    assert distance(frontier, (0, 0)) == 3
    assert log == [f"explore -> ({frontier[0]},{frontier[1]})"]
    assert run(explore, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == frontier


def test_explore_succeeds_early_when_its_tile_is_seen_from_a_distance():
    ctx, _, _ = make_ctx()
    explore = Explore(set())
    explore.enter(ctx)
    assert explore.tick(ctx, 0.0) is Status.RUNNING  # dt 0: decide at the current tile without stepping
    see(ctx, tiles=[explore.tile])
    assert explore.tick(ctx, 0.0) is Status.SUCCEEDED
    assert ctx["actor"].tile == (0, 0)


def test_explore_fails_with_no_frontier():
    ctx, _, _ = make_ctx()
    see(ctx, tiles=all_tiles())
    explore = Explore(set())
    explore.enter(ctx)
    assert explore.tile is None
    assert explore.tick(ctx, 0.1) is Status.FAILED


# --- Interact, Wait, release_claim --------------------------------------------


def claimed_at_slot(ctx, obj):
    see(ctx, obj)
    ctx["Target"] = obj.name
    index = ctx["body"].claim(obj.name)
    ctx["Claim"] = (obj.name, index)
    ctx["actor"].tile = add(obj.tile, DIRECTIONS[obj.slots[index].direction])


def test_interact_applies_effects_after_duration_and_marks_in_use():
    obj = make_object(duration=0.5)
    ctx, world, _ = make_ctx(obj)
    claimed_at_slot(ctx, obj)
    task = Interact()
    task.enter(ctx)
    assert ctx["Interaction"].name == "A.Only"
    assert world.smart_objects.is_in_use(obj)
    assert task.tick(ctx, 0.3) is Status.RUNNING
    assert ctx["LastUsed"] is None
    assert ctx["InteractionElapsed"] == pytest.approx(0.3)
    assert task.tick(ctx, 0.3) is Status.SUCCEEDED
    assert ctx["LastUsed"] == "A" and ctx["Interaction"] is None
    task.exit(ctx)
    assert not world.smart_objects.is_in_use(obj)


def test_interact_fails_when_the_believed_slot_drifts_away():
    obj = make_object(duration=5.0, pauses=False)
    ctx, world, log = make_ctx(obj)
    claimed_at_slot(ctx, obj)
    task = Interact()
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.RUNNING
    obj.tile = (7, 0)
    see(ctx, obj)  # perception sees A move: the slot is now (6, 0)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert "interact: slot drifted away" in log
    task.exit(ctx)
    assert not world.smart_objects.is_in_use(obj)


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


def test_release_claim_releases_logs_and_always_drops_the_target():
    obj = make_object()
    ctx, world, log = make_ctx(obj)
    ctx["Target"] = "A"
    release_claim(ctx)
    assert ctx["Target"] is None and log == []
    claimed_at_slot(ctx, obj)
    release_claim(ctx)
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert log == ["release A / slot 0"]


# --- A GoUse branch with real perception ------------------------------------------


def go_use_tree(world):
    return StateTree(State("Root", children=[
        go_use_state("GoUse(A)", {"Object.A"}, [Condition("LastUsed==None", lambda ctx: ctx["LastUsed"] is None)], Mode.ALL),
        State("Wander", task=Wait(100.0)),
    ]), evaluators=[PerceptionEvaluator(world), ZoneEvaluator()])


def run_until(tree, ctx, leaf_path, max_ticks=2000):
    for _ in range(max_ticks):
        tree.tick(ctx, 0.1)
        if tree.leaf is not None and tree.leaf.path == leaf_path:
            return
    raise AssertionError(f"tree never reached {leaf_path}")


def test_go_use_sees_claims_uses_and_releases():
    obj = make_object()  # A at (6, 0) is in view straight ahead of the actor
    ctx, world, log = make_ctx(obj)
    tree = go_use_tree(world)
    run_until(tree, ctx, "Wander")
    assert ctx["LastUsed"] == "A"
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert not world.smart_objects.is_in_use(obj)
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert log.index("see A at (6,0)") < log.index("claim A / slot 0") < log.index("release A / slot 0")


def test_go_use_explores_when_nothing_is_known_then_goes_to_the_object():
    obj = make_object("A", (-6, 0), slot_directions=(0,))  # behind the actor, out of view
    ctx, world, log = make_ctx(obj)
    tree = go_use_tree(world)
    tree.tick(ctx, 0.1)
    tree.tick(ctx, 0.1)
    assert tree.leaf.path == "GoUse(A)/Explore"
    run_until(tree, ctx, "Wander")
    assert ctx["LastUsed"] == "A"


def test_in_use_and_claim_cleared_when_tree_resets_mid_interaction():
    obj = make_object(duration=5.0)
    ctx, world, _ = make_ctx(obj)
    tree = go_use_tree(world)
    run_until(tree, ctx, "GoUse(A)/Interact")
    assert world.smart_objects.is_in_use(obj)
    tree.reset(ctx)
    assert not world.smart_objects.is_in_use(obj)
    assert not world.smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None and ctx["Target"] is None
