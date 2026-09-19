"""Loaders, their tiered windows, and the chunk store with its time-budgeted load queue.

A chunk key is (level, parent): the children at `level` of the parent cell at level + 1. The world
chunk is (RI, (0, 0)) and is always requested. Loading never depends on order: a chunk's contents
are a pure function of its key and the seed.
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from hexaddr import CHO, KEN, LEVEL_NAMES, RI, SHAKU, WINDOW_RINGS, Tile, axial_to_metres, in_world, up, window

ChunkKey = tuple[int, Tile]
WORLD_KEY: ChunkKey = (RI, (0, 0))
LOAD_BUDGET_S = 0.008
RATE_WINDOW_S = 1.0


@dataclass
class Loader:
    """Anything that needs the world loaded around it. `focus` is a global shaku coordinate."""
    name: str
    focus: Tile


def window_parents(focus: Tile, level: int) -> list[Tile]:
    """The parent cells (at level + 1) whose children make up a loader's `level` tier."""
    p = level + 1
    cells = window(up(focus, SHAKU, p), WINDOW_RINGS)
    if p == RI:
        return [c for c in cells if in_world(c)]
    return [c for c in cells if in_world(up(c, p, RI))]


def requested(loader: Loader) -> set[ChunkKey]:
    keys = {WORLD_KEY}
    for level in (SHAKU, KEN, CHO):
        keys.update((level, parent) for parent in window_parents(loader.focus, level))
    return keys


def chunk_distance(key: ChunkKey, loaders: list[Loader]) -> float:
    """Metres from the nearest loader focus to the chunk's parent centre."""
    level, parent = key
    if key == WORLD_KEY:
        return 0.0
    px, pz = axial_to_metres(*parent, level + 1)
    best = math.inf
    for loader in loaders:
        fx, fz = axial_to_metres(*loader.focus)
        best = min(best, math.hypot(px - fx, pz - fz))
    return best


@dataclass
class TierStats:
    chunks: int = 0
    cells: int = 0
    triangles: int = 0
    queued: int = 0
    loads: deque = field(default_factory=deque)     # times of recent loads
    unloads: deque = field(default_factory=deque)   # times of recent unloads
    gen_ms_last: float = 0.0
    gen_ms_mean: float = 0.0

    def rate(self, events: deque, now: float) -> int:
        while events and events[0] < now - RATE_WINDOW_S:
            events.popleft()
        return len(events)


class ChunkStore:
    def __init__(self, generate: Callable[[int, Tile], object], on_load=None, on_unload=None,
                 clock: Callable[[], float] = time.perf_counter):
        self.generate = generate
        self.on_load = on_load or (lambda chunk: None)
        self.on_unload = on_unload or (lambda chunk: None)
        self.clock = clock
        self.loaded: dict[ChunkKey, object] = {}
        self.queue: list[ChunkKey] = []
        self.stats = {level: TierStats() for level in range(RI + 1)}

    def update(self, loaders: list[Loader], budget_s: float = LOAD_BUDGET_S) -> int:
        """Unload what nobody wants, queue what is missing, then load within the time budget.

        A chunk is skipped until the next call if its level's mean generation time would take the
        frame past the budget. At least one queued chunk loads per call. Returns the number loaded.
        """
        want: set[ChunkKey] = set()
        for loader in loaders:
            want |= requested(loader)
        now = self.clock()
        for key in [k for k in self.loaded if k not in want]:
            chunk = self.loaded.pop(key)
            self.on_unload(chunk)
            self._count(chunk, -1)
            self.stats[key[0]].unloads.append(now)
        queued = set(self.queue)
        self.queue = [k for k in self.queue if k in want]
        self.queue += [k for k in want if k not in self.loaded and k not in queued]
        # coarsest level first (a parent before its children), then nearest, then by key
        self.queue.sort(key=lambda k: (-k[0], chunk_distance(k, loaders), k))

        start = self.clock()
        count = 0
        while self.queue:
            expected_s = self.stats[self.queue[0][0]].gen_ms_mean / 1000
            if count and self.clock() - start + expected_s >= budget_s:
                break
            key = self.queue.pop(0)
            chunk = self.generate(*key)
            self.loaded[key] = chunk
            self.on_load(chunk)
            self._count(chunk, +1)
            stats = self.stats[key[0]]
            stats.loads.append(self.clock())
            stats.gen_ms_last = chunk.gen_ms
            stats.gen_ms_mean = chunk.gen_ms if stats.gen_ms_mean == 0 else 0.9 * stats.gen_ms_mean + 0.1 * chunk.gen_ms
            count += 1
        for level, stats in self.stats.items():
            stats.queued = sum(1 for k in self.queue if k[0] == level)
        return count

    def drain(self, loaders: list[Loader]) -> int:
        return self.update(loaders, budget_s=math.inf)

    def _count(self, chunk, sign: int) -> None:
        stats = self.stats[chunk.level]
        stats.chunks += sign
        stats.cells += sign * len(chunk.cells)
        stats.triangles += sign * chunk.triangle_count

    def is_loaded(self, level: int, parent: Tile) -> bool:
        return (level, parent) in self.loaded

    def summary(self) -> list[tuple[str, TierStats, int, int]]:
        """(tier name, stats, loads in the last second, unloads in the last second), fine to coarse."""
        now = self.clock()
        return [(LEVEL_NAMES[level], s, s.rate(s.loads, now), s.rate(s.unloads, now))
                for level, s in self.stats.items()]
