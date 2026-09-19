"""Wandering Smart Objects: stochastic momentum steps that stay inside each object's home zone."""

from hexgrid import DIRECTIONS, add

# Placeholder tuning.
MOVE_RATE = 0.5  # expected step starts per second while idle
STEP_SPEED = 1.5  # tiles per second while stepping
TURN_FALLOFF = 0.3  # weight multiplier per 60 degrees of divergence from the heading


def divergence(heading: int, direction: int) -> int:
    """Turn between two direction indices in 60-degree increments (0..3)."""
    d = abs(direction - heading) % 6
    return min(d, 6 - d)


def direction_weights(heading: int, falloff: float = TURN_FALLOFF) -> list[float]:
    return [falloff ** divergence(heading, d) for d in range(6)]


def choose_direction(heading: int, allowed, rng, falloff: float = TURN_FALLOFF) -> int | None:
    """Sample one of the allowed directions, favoring small turns; None if nothing is allowed."""
    candidates = [d for d in range(6) if d in allowed]
    if not candidates:
        return None
    weights = direction_weights(heading, falloff)
    return rng.choices(candidates, weights=[weights[d] for d in candidates])[0]


class ObjectMover:
    def __init__(self, world, actor, rng, move_rate=MOVE_RATE, step_speed=STEP_SPEED, falloff=TURN_FALLOFF):
        self.world = world
        self.actor = actor
        self.rng = rng
        self.move_rate = move_rate
        self.step_speed = step_speed
        self.falloff = falloff

    def tick(self, dt: float) -> None:
        for obj in self.world.smart_objects.objects:
            self.tick_object(obj, dt)

    def tick_object(self, obj, dt: float) -> None:
        if obj.pauses_during_use and self.world.smart_objects.is_in_use(obj):
            return  # frozen in place, even mid-step
        if obj.next_tile is not None:
            obj.progress += self.step_speed * dt
            if obj.progress >= 1.0:
                obj.tile = obj.next_tile
                obj.next_tile = None
                obj.progress = 0.0
            return
        if self.rng.random() >= self.move_rate * dt:
            return
        allowed = {
            d for d in range(6)
            if self.world.can_object_enter(obj, add(obj.tile, DIRECTIONS[d]), self.actor)
        }
        direction = choose_direction(obj.heading, allowed, self.rng, self.falloff)
        if direction is None:
            return
        obj.heading = direction
        obj.next_tile = add(obj.tile, DIRECTIONS[direction])
        obj.progress = 0.0
