"""Wires the world, actor, object mover, beliefs, body, StateTree and shared context together."""

import random
from dataclasses import dataclass

from ai.beliefs import BeliefStore
from ai.perception import PerceptionEvaluator
from ai.statetree import StateTree
from ai.tree_def import build_tree
from body import Body
from layout import build_world
from wander import ObjectMover
from world import Actor, World


@dataclass
class Sim:
    world: World
    actor: Actor
    tree: StateTree
    ctx: dict
    mover: ObjectMover
    beliefs: BeliefStore
    body: Body
    seed: int

    def step(self, dt: float) -> None:
        self.mover.tick(dt)
        self.tree.tick(self.ctx, dt)


def build_sim(seed: int = 0) -> Sim:
    rng = random.Random(seed)
    world, actor = build_world(rng)
    tree = build_tree(PerceptionEvaluator(world))
    beliefs = BeliefStore(world.radius)
    ctx = {
        "Zone": None,
        "LastUsed": None,
        "Target": None,
        "Claim": None,
        "Interaction": None,
        "InteractionElapsed": 0.0,
        "Path": None,
        "actor": actor,
        "rng": rng,
        "log": tree.write_log,
        "beliefs": beliefs,
    }
    # The body logs through ctx["log"] at call time, so a replaced logger is honoured.
    body = Body(world, actor, beliefs, lambda text: ctx["log"](text))
    ctx["body"] = body
    return Sim(world, actor, tree, ctx, ObjectMover(world, actor, rng), beliefs, body, seed)
