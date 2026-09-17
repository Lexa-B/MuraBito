"""StateTree tasks and evaluators for the actor: find/claim Smart Objects, walk, interact, wait."""

from ai.pathing import astar
from ai.statetree import Evaluator, Status, Task
from hexgrid import direction_index
from smartobjects import slot_facing, slot_tile


class ZoneEvaluator(Evaluator):
    def tick(self, ctx, dt):
        ctx["Zone"] = ctx["world"].zone_of(ctx["actor"].tile)


class FindAndClaim(Task):
    """Claims the nearest free slot on an object matching the tag query."""

    def __init__(self, tag_query):
        self.tag_query = frozenset(tag_query)
        self.status = Status.FAILED

    def enter(self, ctx):
        self.status = Status.FAILED
        subsystem = ctx["world"].smart_objects
        actor = ctx["actor"]
        for obj, slot in subsystem.find(self.tag_query, near=actor.tile):
            handle = subsystem.claim(obj, slot, actor)
            if handle is not None:
                ctx["Claim"] = handle
                ctx["Target"] = obj.name
                ctx["log"](f"claim {obj.name} / slot {slot.index}")
                self.status = Status.SUCCEEDED
                return

    def tick(self, ctx, dt):
        return self.status


class MoveTo(Task):
    """Plans an A* path on enter, then walks the actor along it."""

    def __init__(self, goal_fn):
        self.goal_fn = goal_fn
        self.path = None
        self.index = 0

    def enter(self, ctx):
        actor = ctx["actor"]
        actor.next_tile = None
        actor.progress = 0.0
        goals = self.goal_fn(ctx)
        self.path = astar(ctx["world"], actor.tile, goals) if goals else None
        self.index = 0
        ctx["Path"] = self.path

    def tick(self, ctx, dt):
        if self.path is None:
            return Status.FAILED
        actor, world = ctx["actor"], ctx["world"]
        remaining = actor.speed * dt
        while True:
            if actor.next_tile is None:
                if self.index == len(self.path) - 1:
                    self._face_claimed_object(ctx)
                    return Status.SUCCEEDED
                if remaining <= 0:
                    return Status.RUNNING
                next_tile = self.path[self.index + 1]
                if not world.is_walkable(next_tile):
                    return Status.FAILED
                actor.facing = direction_index(actor.tile, next_tile)
                actor.next_tile = next_tile
                actor.progress = 0.0
            needed = 1.0 - actor.progress
            if remaining < needed:
                actor.progress += remaining
                return Status.RUNNING
            remaining -= needed
            actor.tile = actor.next_tile
            actor.next_tile = None
            actor.progress = 0.0
            self.index += 1
            ctx["Path"] = self.path[self.index:]

    def exit(self, ctx):
        actor = ctx["actor"]
        actor.next_tile = None
        actor.progress = 0.0
        ctx["Path"] = None

    @staticmethod
    def _face_claimed_object(ctx):
        claim = ctx.get("Claim")
        actor = ctx["actor"]
        if claim is not None and actor.tile == slot_tile(claim.object, claim.slot):
            actor.facing = slot_facing(claim.slot)


class Interact(Task):
    """Runs one of the claimed object's advertised interactions, picked at random."""

    def __init__(self):
        self.interaction = None
        self.elapsed = 0.0

    def enter(self, ctx):
        claim = ctx.get("Claim")
        options = claim.object.interactions if claim is not None else []
        self.interaction = ctx["rng"].choice(options) if options else None
        self.elapsed = 0.0
        ctx["Interaction"] = self.interaction
        ctx["InteractionElapsed"] = 0.0

    def tick(self, ctx, dt):
        if self.interaction is None:
            return Status.FAILED
        self.elapsed += dt
        ctx["InteractionElapsed"] = min(self.elapsed, self.interaction.duration)
        if self.elapsed < self.interaction.duration:
            return Status.RUNNING
        for effect in self.interaction.effects:
            effect(ctx)
        ctx["Interaction"] = None
        return Status.SUCCEEDED

    def exit(self, ctx):
        ctx["Interaction"] = None
        ctx["InteractionElapsed"] = 0.0


class Wait(Task):
    def __init__(self, duration: float):
        self.duration = duration
        self.elapsed = 0.0

    def enter(self, ctx):
        self.elapsed = 0.0

    def tick(self, ctx, dt):
        self.elapsed += dt
        return Status.SUCCEEDED if self.elapsed >= self.duration else Status.RUNNING


def claimed_slot_goal(ctx):
    claim = ctx.get("Claim")
    return {slot_tile(claim.object, claim.slot)} if claim is not None else None


def random_tile_goal(ctx):
    return {ctx["rng"].choice(ctx["world"].walkable_tiles())}


def release_claim(ctx):
    """on_exit hook for GoUse states: frees the claim however the state ended."""
    claim = ctx.get("Claim")
    if claim is None:
        return
    ctx["world"].smart_objects.release(claim)
    ctx["log"](f"release {claim.object.name} / slot {claim.slot.index}")
    ctx["Claim"] = None
    ctx["Target"] = None
