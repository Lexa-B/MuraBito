"""Wires the world, actor, object mover, StateTree and shared context together."""

import random
from dataclasses import dataclass

from ai.statetree import StateTree
from ai.tree_def import build_tree
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

    def step(self, dt: float) -> None:
        self.mover.tick(dt)
        self.tree.tick(self.ctx, dt)


def build_sim(seed: int = 0) -> Sim:
    rng = random.Random(seed)
    world, actor = build_world(rng)
    tree = build_tree()
    ctx = {
        "Zone": None,
        "LastUsed": None,
        "Target": None,
        "Claim": None,
        "Interaction": None,
        "InteractionElapsed": 0.0,
        "Path": None,
        "actor": actor,
        "world": world,
        "rng": rng,
        "log": tree.write_log,
    }
    return Sim(world, actor, tree, ctx, ObjectMover(world, actor, rng))
