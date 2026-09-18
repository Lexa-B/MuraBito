"""A small model of UE5 Smart Objects: objects advertise interactions and slots,
users find them by tag, claim a slot, use it, and release it. Objects can move;
slots ride along with their object."""

from dataclasses import dataclass

from hexgrid import DIRECTIONS, Tile, add, distance


@dataclass(frozen=True)
class Slot:
    index: int
    direction: int  # index into hexgrid.DIRECTIONS, from the object to the slot


@dataclass(frozen=True)
class Interaction:
    name: str
    duration: float
    effects: tuple = ()  # each is fn(ctx) -> None


@dataclass(eq=False)
class SmartObject:
    name: str
    tile: Tile  # logical tile; updated when a step completes
    tags: frozenset[str]
    slots: list[Slot]
    interactions: list[Interaction]
    home_zone: str = ""
    pauses_during_use: bool = True
    casts_shadow: bool = False  # blocks the actor's line of sight from its logical tile
    heading: int = 0  # index into hexgrid.DIRECTIONS
    next_tile: Tile | None = None
    progress: float = 0.0  # 0..1 from tile toward next_tile


def slot_tile(obj: SmartObject, slot: Slot) -> Tile:
    return add(obj.tile, DIRECTIONS[slot.direction])


def slot_facing(slot: Slot) -> int:
    """Direction a user standing on the slot faces: back toward the object."""
    return (slot.direction + 3) % 6


@dataclass(frozen=True, eq=False)
class ClaimHandle:
    object: SmartObject
    slot: Slot
    actor: object


class SmartObjectSubsystem:
    def __init__(self):
        self.objects: list[SmartObject] = []
        self._claims: dict[tuple[int, int], ClaimHandle] = {}
        self._in_use: set[int] = set()

    def register(self, obj: SmartObject) -> None:
        self.objects.append(obj)

    def find(self, tag_query, near: Tile, blocked_fn=None) -> list[tuple[SmartObject, Slot]]:
        """Unclaimed, unblocked slots on objects carrying every tag in the query, nearest first."""
        query = set(tag_query)
        results = [
            (obj, slot)
            for obj in self.objects
            if query <= obj.tags
            for slot in obj.slots
            if not self.is_claimed(obj, slot)
            and not (blocked_fn is not None and blocked_fn(slot_tile(obj, slot)))
        ]
        results.sort(key=lambda pair: (distance(slot_tile(*pair), near), pair[0].name, pair[1].index))
        return results

    def claim(self, obj: SmartObject, slot: Slot, actor) -> ClaimHandle | None:
        key = self._key(obj, slot)
        if key in self._claims:
            return None
        handle = ClaimHandle(obj, slot, actor)
        self._claims[key] = handle
        return handle

    def release(self, handle: ClaimHandle) -> None:
        key = self._key(handle.object, handle.slot)
        # Only the handle that holds the claim can release it.
        if self._claims.get(key) is handle:
            del self._claims[key]

    def is_claimed(self, obj: SmartObject, slot: Slot) -> bool:
        return self._key(obj, slot) in self._claims

    def set_in_use(self, obj: SmartObject, in_use: bool) -> None:
        if in_use:
            self._in_use.add(id(obj))
        else:
            self._in_use.discard(id(obj))

    def is_in_use(self, obj: SmartObject) -> bool:
        return id(obj) in self._in_use

    @staticmethod
    def _key(obj: SmartObject, slot: Slot) -> tuple[int, int]:
        return (id(obj), slot.index)
