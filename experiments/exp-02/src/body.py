"""The actor's body: the truth-side actuator. Tasks affect other objects only through it.

It keeps the real Smart Object claim handle private, and refuses to claim an object the actor
can't currently see. Arbitration (is the slot free, is its tile really walkable) is its call,
as the Smart Object subsystem's would be in UE5.
"""


class Body:
    def __init__(self, world, actor, beliefs, log):
        self.world = world
        self.actor = actor
        self.beliefs = beliefs
        self.log = log
        self._handle = None
        self._in_use_object = None
        self._last_failure: dict[str, str] = {}  # object name -> last failure line logged

    def claim(self, name: str) -> int | None:
        """Claim the named object's nearest free slot on a truly walkable tile. Returns the slot index."""
        if self._handle is not None:
            return None
        if name not in self.beliefs.seen_now:
            self._fail(name, f"body: claim {name} refused (not in view)")
            return None
        subsystem = self.world.smart_objects
        obj = next(o for o in subsystem.objects if o.name == name)
        found = subsystem.find(obj.tags, near=self.actor.tile, blocked_fn=lambda t: not self.world.is_walkable(t))
        for candidate, slot in found:
            if candidate is obj:
                handle = subsystem.claim(obj, slot, self.actor)
                if handle is not None:
                    self._handle = handle
                    self._last_failure.pop(name, None)
                    return slot.index
        self._fail(name, f"body: claim {name} failed (no free slot)")
        return None

    def release(self) -> None:
        if self._handle is not None:
            self.world.smart_objects.release(self._handle)
            self._handle = None

    def set_in_use(self, in_use: bool) -> None:
        """Mark the claimed object in use, or clear whichever object was marked (even after release)."""
        subsystem = self.world.smart_objects
        if in_use:
            if self._handle is not None:
                self._in_use_object = self._handle.object
                subsystem.set_in_use(self._in_use_object, True)
        elif self._in_use_object is not None:
            subsystem.set_in_use(self._in_use_object, False)
            self._in_use_object = None

    def interactions(self) -> list:
        return list(self._handle.object.interactions) if self._handle is not None else []

    def claimed_slot(self) -> tuple[str, int] | None:
        if self._handle is None:
            return None
        return (self._handle.object.name, self._handle.slot.index)

    def _fail(self, name: str, text: str) -> None:
        # Tasks retry every tile, so only log a failure when it changes.
        if self._last_failure.get(name) != text:
            self.log(text)
            self._last_failure[name] = text
