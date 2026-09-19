from dataclasses import dataclass

import pytest

from hexaddr import CHO, KEN, RI, SHAKU, SCALE, centre_shaku, up, window
from loading import WORLD_KEY, ChunkStore, Loader, requested, window_parents
from rail import Rail

RAIL_START = centre_shaku((4, 0), RI)


@dataclass
class FakeChunk:
    level: int
    parent: tuple
    gen_ms: float = 1.0

    @property
    def key(self):
        return (self.level, self.parent)

    @property
    def cells(self):
        return range({SHAKU: 36, KEN: 3600, CHO: 1296, RI: 469}[self.level])

    @property
    def triangle_count(self):
        return 2 * len(self.cells)


class FakeClock:
    """Each generated chunk costs `step` seconds."""

    def __init__(self, step=0.003):
        self.t = 0.0
        self.step = step

    def __call__(self):
        return self.t


def make_store(clock=None, log=None):
    clock = clock or FakeClock(0.0)

    def generate(level, parent):
        clock.t += clock.step
        if log is not None:
            log.append((level, parent))
        return FakeChunk(level, parent, gen_ms=clock.step * 1000)

    return ChunkStore(generate, clock=clock)


def test_window_sizes():
    keys = requested(Loader("a", RAIL_START))
    counts = {level: sum(1 for k in keys if k[0] == level) for level in (SHAKU, KEN, CHO, RI)}
    assert counts == {SHAKU: 37, KEN: 37, CHO: 37, RI: 1}
    assert WORLD_KEY in keys


def test_windows_are_the_loaders_cells_plus_three_rings():
    focus = (51831, 18)
    assert set(window_parents(focus, SHAKU)) == set(window(up(focus, SHAKU, KEN)))
    assert set(window_parents(focus, KEN)) == set(window(up(focus, SHAKU, CHO)))
    assert set(window_parents(focus, CHO)) == set(window(up(focus, SHAKU, RI)))


def test_windows_clip_at_the_world_edge():
    edge = centre_shaku((12, 0), RI)
    parents = window_parents(edge, CHO)
    assert len(parents) < 37
    assert all(abs(q) + abs(r) + abs(q + r) <= 24 for q, r in parents)


def test_drained_store_holds_the_windows_cell_counts():
    store = make_store()
    store.drain([Loader("a", RAIL_START)])
    cells = {name: s.cells for name, s, _, _ in store.summary()}
    assert cells == {"shaku": 1332, "ken": 133200, "cho": 47952, "ri": 469}
    assert not store.queue


def test_union_of_two_loaders():
    a = Loader("a", RAIL_START)
    b = Loader("b", (RAIL_START[0] + 5 * SCALE[CHO], RAIL_START[1]))
    store = make_store()
    store.drain([a, b])
    assert set(store.loaded) == requested(a) | requested(b)
    store.update([a])
    assert set(store.loaded) == requested(a)


def test_parents_load_before_children():
    log = []
    clock = FakeClock(0.003)
    store = make_store(clock, log)
    loader = Loader("a", RAIL_START)
    loaded = set()
    for _ in range(200):
        store.update([loader])
    for level, parent in log:
        if level < RI:
            container = WORLD_KEY if level == CHO else (level + 1, up(parent, level + 1, level + 2))
            assert container in loaded
        loaded.add((level, parent))


def test_budget_loads_at_least_one_and_stops_before_overrunning():
    clock = FakeClock(0.003)
    store = make_store(clock)
    loader = Loader("a", RAIL_START)
    assert store.update([loader], budget_s=0.0) == 1
    n = store.update([loader], budget_s=0.008)
    assert n == 2  # 3 ms each: a third would end at 9 ms
    assert store.update([loader], budget_s=0.1) >= 30


def test_queue_is_nearest_first_within_a_level():
    store = make_store()
    loader = Loader("a", RAIL_START)
    store.update([loader], budget_s=0.0)  # loads the world chunk, queues the rest
    cho_queue = [k for k in store.queue if k[0] == CHO]
    assert cho_queue[0] == (CHO, (4, 0))
    assert [k[0] for k in store.queue] == sorted((k[0] for k in store.queue), reverse=True)


def test_unloads_are_immediate_and_reported():
    unloaded = []
    clock = FakeClock(0.0)
    store = ChunkStore(lambda level, parent: FakeChunk(level, parent), on_unload=unloaded.append, clock=clock)
    loader = Loader("a", RAIL_START)
    store.drain([loader])
    loader.focus = (RAIL_START[0] + SCALE[KEN], RAIL_START[1])  # one ken east
    store.update([loader], budget_s=0.0)
    assert len(unloaded) == 7 and all(c.level == SHAKU for c in unloaded)
    assert all(c.key not in store.loaded for c in unloaded)


def test_contents_do_not_depend_on_load_order():
    from chunkgen import generate_chunk
    import numpy as np
    keys = [(KEN, (144, 0)), (SHAKU, (8640, 0)), (CHO, (4, 0))]
    first = {k: generate_chunk(*k, 0).vertices for k in keys}
    second = {k: generate_chunk(*k, 0).vertices for k in reversed(keys)}
    assert all(np.array_equal(first[k], second[k]) for k in keys)


def test_camera_run_keeps_its_windows_loaded():
    rail = Rail(lambda x, z: 0.0, start=0.0)
    camera = Loader("camera", rail.focus_shaku)
    store = make_store(FakeClock(0.001))
    store.drain([camera])
    for _ in range(60 * 60):  # one minute of jogging: many ken and one cho crossing
        rail.advance(1 / 60)
        camera.focus = rail.focus_shaku
        store.update([camera])
        store.drain([camera])
        assert set(store.loaded) == requested(camera)


@pytest.mark.parametrize("level", [SHAKU, KEN, CHO])
def test_stats_count_chunks(level):
    store = make_store()
    store.drain([Loader("a", RAIL_START)])
    s = store.stats[level]
    assert s.chunks == 37 and s.queued == 0 and s.triangles == 2 * s.cells
