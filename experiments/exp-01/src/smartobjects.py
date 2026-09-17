"""A small model of UE5 Smart Objects: objects advertise interactions and slots,
users find them by tag, claim a slot, use it, and release it."""

from dataclasses import dataclass

from hexgrid import Tile, distance


@dataclass(frozen=True)
class Slot:
    index: int
    tile: Tile
    facing: int  # index into hexgrid.DIRECTIONS, pointing at the object


@dataclass(frozen=True)
class Interaction:
    name: str
    duration: float
    effects: tuple = ()  # each is fn(ctx) -> None


@dataclass(eq=False)
class SmartObject:
    name: str
    tile: Tile
    tags: frozenset[str]
    slots: list[Slot]
    interactions: list[Interaction]


@dataclass(frozen=True, eq=False)
class ClaimHandle:
    object: SmartObject
    slot: Slot
    actor: object


class SmartObjectSubsystem:
    def __init__(self):
        self.objects: list[SmartObject] = []
        self._claims: dict[tuple[int, int], ClaimHandle] = {}

    def register(self, obj: SmartObject) -> None:
        self.objects.append(obj)

    def find(self, tag_query, near: Tile) -> list[tuple[SmartObject, Slot]]:
        """Unclaimed slots on objects carrying every tag in the query, nearest first."""
        query = set(tag_query)
        results = [
            (obj, slot)
            for obj in self.objects
            if query <= obj.tags
            for slot in obj.slots
            if not self.is_claimed(obj, slot)
        ]
        results.sort(key=lambda pair: (distance(pair[1].tile, near), pair[0].name, pair[1].index))
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

    @staticmethod
    def _key(obj: SmartObject, slot: Slot) -> tuple[int, int]:
        return (id(obj), slot.index)
