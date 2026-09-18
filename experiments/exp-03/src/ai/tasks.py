"""StateTree tasks and evaluators for the actor: choose a target, walk, search, explore, interact, wait.

Tasks read the actor's beliefs (ctx["beliefs"]) and affect other objects only through its body
(ctx["body"]). None of them can see the world.
"""

from ai.beliefs import LOST, POINT, REGION
from ai.pathing import astar
from ai.statetree import Evaluator, Status, Task
from hexgrid import direction_index, distance
from zones import zone_of


def fmt(tile) -> str:
    return f"({tile[0]},{tile[1]})"


class ZoneEvaluator(Evaluator):
    def tick(self, ctx, dt):
        ctx["Zone"] = zone_of(ctx["actor"].tile)


class ChooseTarget(Task):
    """Picks the nearest believed object matching the tag query: POINT beliefs first, then REGION."""

    def __init__(self, tag_query):
        self.tag_query = frozenset(tag_query)
        self.status = Status.FAILED

    def enter(self, ctx):
        self.status = Status.FAILED
        ctx["Target"] = None
        beliefs, actor = ctx["beliefs"], ctx["actor"]
        for level in (POINT, REGION):
            options = [name for name in beliefs.matching(self.tag_query) if beliefs.level(name) == level]
            if options:
                name = min(options, key=lambda n: (distance(actor.tile, beliefs.ghost_tile(n)), n))
                ctx["Target"] = name
                ctx["log"](f"target {name} ({level})")
                self.status = Status.SUCCEEDED
                return

    def tick(self, ctx, dt):
        return self.status


class MoveTo(Task):
    """Walks the actor to the goal tiles along an A* path on the believed map.

    Re-plans when the next path tile is believed blocked. With `chase=True` the goal is re-read
    each time the actor reaches a tile, and a changed goal triggers a re-plan. With `claim=True`
    (the GoUse approach) it claims the target through the body as soon as the target is in view,
    and only succeeds standing on the claimed slot.
    """

    def __init__(self, goal_fn, chase: bool = False, claim: bool = False):
        self.goal_fn = goal_fn
        self.chase = chase
        self.claim = claim
        self.goals = None
        self.path = None
        self.index = 0

    def enter(self, ctx):
        actor = ctx["actor"]
        actor.next_tile = None
        actor.progress = 0.0
        if self.claim:
            self._try_claim(ctx)
        self.goals = self.goal_fn(ctx)
        self._plan(ctx)

    def tick(self, ctx, dt):
        actor, beliefs = ctx["actor"], ctx["beliefs"]
        remaining = actor.speed * dt
        while True:
            if actor.next_tile is None:
                status = self.at_tile(ctx)
                if status is not None:
                    return status
                if remaining <= 0:
                    return Status.RUNNING
                next_tile = self.path[self.index + 1]
                if not beliefs.is_walkable(next_tile):
                    ctx["log"]("replan: path blocked")
                    self._plan(ctx)
                    continue
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

    def at_tile(self, ctx):
        """Called whenever the actor stands on a tile with no step in progress.

        Returns a finished status, or None to keep walking the current path.
        """
        if self.claim:
            self._try_claim(ctx)
        if self.chase:
            goals = self.goal_fn(ctx)
            if goals != self.goals:
                self.goals = goals
                ctx["log"]("replan: target moved")
                self._plan(ctx)
        if self.path is None:
            return Status.FAILED
        if self.index == len(self.path) - 1:
            return self.arrived(ctx)
        return None

    def arrived(self, ctx):
        if not self.claim:
            return Status.SUCCEEDED
        self._try_claim(ctx)
        claim = ctx.get("Claim")
        if claim is None:
            return Status.FAILED
        name, index = claim
        beliefs = ctx["beliefs"]
        if ctx["actor"].tile != dict(beliefs.slot_tiles(name))[index]:
            return Status.RUNNING  # just claimed a different slot: re-plan to it next tick
        ctx["actor"].facing = beliefs.slot_facing(name, index)
        return Status.SUCCEEDED

    def _plan(self, ctx):
        self.path = astar(ctx["beliefs"], ctx["actor"].tile, self.goals) if self.goals else None
        self.index = 0
        ctx["Path"] = self.path

    @staticmethod
    def _try_claim(ctx):
        """Claim on sight: once the target is in view, claim a slot through the body."""
        name = ctx.get("Target")
        if ctx.get("Claim") is not None or name is None or name not in ctx["beliefs"].seen_now:
            return
        index = ctx["body"].claim(name)
        if index is not None:
            ctx["Claim"] = (name, index)
            ctx["log"](f"claim {name} / slot {index}")


class Search(MoveTo):
    """Sweeps the target's search area (see BeliefStore.search_area), nearest the ghost first.

    Gives up (FAILED) when the target is LOST or no uncleared tile is left. Finding the target is
    handled by the tree, which leaves Search once the belief is POINT again.
    """

    def __init__(self):
        super().__init__(lambda ctx: {self.tile} if self.tile is not None else None)
        self.tile = None

    def enter(self, ctx):
        actor = ctx["actor"]
        actor.next_tile = None
        actor.progress = 0.0
        self.tile = None
        self.goals = None
        self.path = None
        self.index = 0

    def at_tile(self, ctx):
        beliefs, actor, name = ctx["beliefs"], ctx["actor"], ctx.get("Target")
        area = beliefs.search_area(name) if name in beliefs.beliefs and beliefs.level(name) != LOST else []
        area = [t for t in area if t != actor.tile]
        if not area:
            drop_claim(ctx)
            ctx["log"](f"search: give up on {name}")
            return Status.FAILED
        if self.tile not in area or self.path is None or self.index == len(self.path) - 1:
            self.tile = area[0]
            self.goals = {self.tile}
            self._plan(ctx)
            if self.path is None:  # the nearest-to-ghost tile is unreachable: take any reachable one
                self.goals = set(area)
                self._plan(ctx)
                if self.path is None:
                    drop_claim(ctx)
                    ctx["log"](f"search: give up on {name}")
                    return Status.FAILED
                self.tile = self.path[-1]
        return None


class Explore(MoveTo):
    """Walks to the frontier (see BeliefStore.frontier). Succeeds on arrival, or as soon as the
    frontier tile has been seen from a distance. Seeing a match is handled by the tree."""

    def __init__(self, tag_query):
        super().__init__(lambda ctx: {self.tile} if self.tile is not None else None)
        self.tag_query = frozenset(tag_query)
        self.tile = None
        self.entered_at = 0.0

    def enter(self, ctx):
        actor, beliefs = ctx["actor"], ctx["beliefs"]
        actor.next_tile = None
        actor.progress = 0.0
        self.entered_at = beliefs.now
        self.tile = beliefs.frontier(actor.tile)
        if self.tile is not None:
            ctx["log"](f"explore -> {fmt(self.tile)}")
        self.goals = self.goal_fn(ctx)
        self._plan(ctx)

    def at_tile(self, ctx):
        if self.path is None:
            return Status.FAILED
        if ctx["beliefs"].last_seen.get(self.tile, -1.0) > self.entered_at:
            return Status.SUCCEEDED
        if self.index == len(self.path) - 1:
            return Status.SUCCEEDED
        return None


class Interact(Task):
    """Runs one of the claimed object's advertised interactions, picked at random.

    Marks the object in use through the body, and fails if the claimed slot drifts away from the actor.
    """

    def __init__(self):
        self.interaction = None
        self.elapsed = 0.0

    def enter(self, ctx):
        body = ctx["body"]
        body.set_in_use(True)
        options = body.interactions()
        self.interaction = ctx["rng"].choice(options) if options else None
        self.elapsed = 0.0
        ctx["Interaction"] = self.interaction
        ctx["InteractionElapsed"] = 0.0

    def tick(self, ctx, dt):
        if self.interaction is None:
            return Status.FAILED
        claim = ctx.get("Claim")
        if claim is None or ctx["actor"].tile != dict(ctx["beliefs"].slot_tiles(claim[0]))[claim[1]]:
            ctx["log"]("interact: slot drifted away")
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
        ctx["body"].set_in_use(False)
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


def target_goal(ctx):
    """The claimed slot's believed tile once claimed; before that, every believed-walkable slot tile of the target."""
    beliefs = ctx["beliefs"]
    claim = ctx.get("Claim")
    if claim is not None:
        name, index = claim
        return {dict(beliefs.slot_tiles(name))[index]}
    name = ctx.get("Target")
    if name is None or name not in beliefs.beliefs:
        return None
    return {tile for _, tile in beliefs.slot_tiles(name) if beliefs.is_walkable(tile)}


def random_tile_goal(ctx):
    return {ctx["rng"].choice(ctx["beliefs"].walkable_tiles())}


def drop_claim(ctx):
    """Frees a held claim, if any, through the body, and logs the release."""
    claim = ctx.get("Claim")
    if claim is not None:
        ctx["body"].release()
        ctx["log"](f"release {claim[0]} / slot {claim[1]}")
        ctx["Claim"] = None


def release_claim(ctx):
    """on_exit hook for GoUse states: frees the claim and drops the intention, however the state ended."""
    drop_claim(ctx)
    ctx["Target"] = None
