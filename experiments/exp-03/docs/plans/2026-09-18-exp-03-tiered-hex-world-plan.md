# exp-03 Tiered Hex World Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build exp-03: hierarchical shaku / ken / cho / ri hex addresses at historical ratios, a procedural 3D world of radius 12 ri that loads in tiers of detail around any loader, and a moderngl view from a camera on a 4-ri rail with every tier's borders drawn on the ground and a stats panel.

**Architecture:** `hexaddr.py` is the coordinate system (pure Python ints). `terrain.py` and `noise.py` define the world as pure functions of `(seed, position, tier)`. A chunk is one parent cell's children: `chunkgeom.py` builds each level's chunk template once, `chunkgen.py` fills a chunk with heights, colours, a mesh and props. `loading.py` turns loaders into requested chunks and loads them nearest first within a per-frame budget. `gfx/` draws the loaded chunks; its fragment shader repeats `hexaddr`'s integer maths to clip each chunk to its owned territory, hand over between tiers, and draw borders. `main.py` runs the rail, the store, the renderer and the panel.

**Tech Stack:** Python 3.13, pygame 2.6.1, moderngl (OpenGL 3.3 core, EGL when headless), numpy, pytest, uv.

**Spec:** `experiments/exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md`. Read it before starting; this plan implements it.

## Global Constraints

- Work in `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`, the worktree's copy of exp-03, on branch `worktree-exp-03-impl`. Do not push.
- Every git command uses `git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl`. Before each commit, check `pwd` and that the branch is `worktree-exp-03-impl`. Never run git against `/home/lexa/DevProjects/_GameDev/MuraBito` (the main checkout).
- Python dependencies are managed with uv only (`uv run`, `uv add`). Never `pip install` or `uv pip`. Task 1 runs `uv add moderngl numpy`; nothing else is added.
- Imports are relative to `src/` (`pythonpath = ["src"]`). Run tests with `uv run pytest` from the exp-03 directory.
- Only `src/gfx/` and `src/main.py` import pygame or moderngl.
- Panel text is ASCII only (pygame's default font lacks arrows and check marks).
- Nothing under `experiments/exp-00/`, `experiments/exp-01/` or `experiments/exp-02/` changes.
- Units: 1 shaku = 10/33 m; 6 shaku per ken, 60 ken per cho, 36 cho per ri; world radius 12 ri; windows are a cell plus 3 rings.
- Placeholder constants use exactly the values in the code: rail radius 4 ri at 2.5 m/s, eye 8 m back and 3 m up, load budget 8 ms, morph 1.3 to 2.0 parent widths, at most 0.05 trees per ken.
- The GL tests (`tests/test_gfx.py`, and the headless runs in `tests/test_main.py`) skip themselves without a GL context. On the development machine they must **run**, not skip: the expected counts below include them.

## How to use this plan

- **Every code block is complete and was run before this plan was written.** The whole plan was built in a scratchpad copy, then replayed task by task onto a fresh copy of exp-03, recording the test count after each task; the counts below are those real counts. Copy code exactly; do not retype or "improve" it.
- **File blocks** (`**File:** ... (create or replace the whole file)`) give a file's entire contents. Task 10 also has **edit blocks**: an exact `Find:` text and its `Replace with:` text; the `Find:` text occurs exactly once in the file.
- Code blocks in this plan start at column 0, even under a numbered step. They are **not** indented under list items, so copy them as they are.
- If a test fails that this plan says should pass, stop and report it with the output. Do not change tests to make them pass.

## Differences from the spec, found while building this plan

These came up while the plan's code was run. The code below already reflects them, and Task 10 records the behavioural ones in the spec.

1. **Cracks between tiers are closed by geomorphing, not skirts.** Each vertex stores its tier's height and the coarser tier's mesh height at its position (`h_coarse`); the vertex shader blends from one to the other between 1.3 and 2.0 parent widths from the loader focus. A loader's window edge is never nearer than 2.26 parent widths (measured at every level before the plan was written), so at every window edge the finer tier lies exactly on the coarser mesh. Props blend the same way.
2. **The tier partition is `hexaddr.tier_cell(x, z, t, L)`:** where tier *t* is drawn, round the point to the nearest tier-*t* cell, then take owners upward to level *L*. At the shaku tier this is exactly the shaku address. The shader uses the same test on both sides of each handover, so the finer tier's owned territory and the coarser tier's discarded pixels always match.
3. **Chunk meshes draw every triangle that touches an owned cell** (each cell anchors two triangles, halves of the parallelogram `c, c+(1,0), c+(1,1), c+(0,1)`). Neighbouring chunks therefore overlap by a triangle, and the fragment shader discards everything outside the chunk's owned territory.
4. **New modules `chunkgeom.py` and `chunkgen.py`,** split out of `terrain.py`. Because ownership is the same for every parent at a level, each level's chunk template (owned offsets, two rings, neighbour table, triangles) is built once from `hexaddr`, and there is no numpy twin of `owner`.
5. **The load queue is predictive:** it stops before a chunk whose level's mean generation time would take the frame past the 8 ms budget, and always loads at least one. Measured on the development machine: median frame 7.7 ms, worst 24 ms (one ken chunk at a cho crossing), against the spec's 33 ms.
6. **Hex lines** get their width from the pixel footprint projected on the edge's normal (distance-to-edge derivatives break down where a pixel quad straddles a line). A border fades out where the bordered cells are less than about 10 px deep, and a tier's own grid fades where its cells are smaller than 4 to 10 px. Without this, distant ri and cho borders wash over the horizon.
7. **Props carry three ground heights:** full detail, the ken mesh and the cho mesh at their shaku. The prop shader stands a prop on the shaku tier if its ken has shaku loaded, otherwise on the ken tier, with each tier's blend.
8. **Placeholder tuning:** at most 0.05 trees per ken (at 0.15 the canopy closed and hid the horizon), forest density `1.8 n - 0.1`, and a dirt threshold of -0.17 (measured to give 30% dirt).
9. **The rail starts on the centre of ri (4, 0), heading due north** along a column of ken edges, so for the first stretch the shaku window changes many times a second. This is correct behaviour for that alignment, not a bug, and there is no hysteresis (as the spec says).
10. **Rendering extras:** a sky pass (a gradient from horizon to zenith), 30 km fog, near and far planes at 0.5 m and 120 km, and two debug modes in the renderer (owner ids, flat grey with lines) used by the GL tests.
11. **The panel's NEIGHBOURHOOD section is three diagrams,** one per window: ken → shaku, cho → ken, ri → cho.
12. **Tests:** there are also `tests/test_chunkgeom.py` and `tests/test_chunkgen.py`. The rail's horizon check tests that the pitch stays below half the vertical field of view.

## File map

| File | Task | Responsibility |
|---|---|---|
| `src/hexgrid.py` | kept | axial hex maths (unchanged) |
| `src/hexaddr.py` | 2 | units, packing B ownership, addresses, conversions, windows |
| `src/noise.py` | 3 | hashed gradient noise and integer hashing, numpy |
| `src/terrain.py` | 3 | height per tier, ground type, colour, forest density |
| `src/chunkgeom.py` | 4 | chunk templates, triangulation, heights on a tier's mesh |
| `src/chunkgen.py` | 5 | `ChunkData`, `generate_chunk`, props and details, morph ranges |
| `src/rail.py` | 6 | the camera rail and eye |
| `src/loading.py` | 7 | `Loader`, windows, `ChunkStore` and its queue, stats |
| `src/gfx/` | 8, 9 | context, matrices, prop meshes, renderer and shaders (8); panel (9) |
| `src/main.py` | 9 | loop, flags, headless screenshots |

Starting point: `uv run pytest -q` in `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` passes **401** tests (the exp-02 copy).

## Models and reviews (for the controller)

Tasks 1 to 7 and 9 are transcription: Haiku is enough. Task 8 (the renderer and shaders) is the largest: use Sonnet, and Opus for its review. Opus does the final whole-branch review.

---

### Task 1: Clear out the exp-02 code and add the new dependencies

**Files:**
- Delete: `src/ai/` (the whole directory), `src/body.py`, `src/camera.py`, `src/layout.py`, `src/mapgen.py`, `src/render.py`, `src/sim.py`, `src/smartobjects.py`, `src/wander.py`, `src/world.py`, `src/zones.py`, `src/main.py`
- Delete: every file in `tests/` except `tests/test_hexgrid.py`
- Modify: `pyproject.toml`, `uv.lock` (through `uv add`)

**Interfaces:**
- Consumes: nothing.
- Produces: an exp-03 with only `src/hexgrid.py` and `tests/test_hexgrid.py`, and `moderngl` and `numpy` as dependencies. `main.py` comes back in Task 9.

- [ ] **Step 1: Delete the exp-02 modules and tests**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
rm -r src/ai
rm src/body.py src/camera.py src/layout.py src/mapgen.py src/render.py src/sim.py src/smartobjects.py src/wander.py src/world.py src/zones.py src/main.py
find tests -maxdepth 1 -name 'test_*.py' ! -name test_hexgrid.py -delete
ls src tests
```

Expected: `src` lists only `hexgrid.py` (and possibly `__pycache__`); `tests` lists only `test_hexgrid.py` (and possibly `__pycache__`).

- [ ] **Step 2: Add the dependencies**

```bash
uv add moderngl numpy
```

Expected: `pyproject.toml`'s `dependencies` now lists `moderngl`, `numpy` and `pygame`.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **11 passed**.

- [ ] **Step 4: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add -A experiments/exp-03
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl status --short
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: clear out the exp-02 code, add moderngl and numpy

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`, the branch must be `worktree-exp-03-impl`, and `status --short` must list only deletions under `experiments/exp-03/` plus `pyproject.toml` and `uv.lock`. Use your own model's name in the trailer.

---

### Task 2: Hex addresses (`hexaddr.py`)

**Files:**
- Create: `src/hexaddr.py`
- Test: `tests/test_hexaddr.py`

**Interfaces:**
- Consumes: `hexgrid.DIRECTIONS`, `Tile`, `distance`.
- Produces:
  - levels `SHAKU, KEN, CHO, RI = 0, 1, 2, 3`, `LEVELS`, `LEVEL_NAMES`; `PACKING = (1, 6, 60, 36)`; `SCALE = (1, 6, 360, 12960)`; `SHAKU_M = 10 / 33`; `WIDTH_M` (metres per cell width, per level); `WORLD_RADIUS = 12`; `WINDOW_RINGS = 3`; `SQRT3`; `Address`
  - `d2(dq, dr) -> int`; `owner(cell, n) -> Tile`; `parent(cell, level)`; `up(cell, from_level, to_level)`
  - `centre_child(cell, level)`, `centre_shaku(cell, level)`, `local(cell, level)`
  - `address(shaku) -> Address`, `from_address(addr) -> Tile`, `format_address(addr) -> str`
  - `axial_to_metres(q, r, level=SHAKU) -> (x, z)`, `metres_to_axial(x, z, level=SHAKU)`, `hex_round(fq, fr)`, `round_at(x, z, level)`, `shaku_at(x, z)`, `tier_cell(x, z, tier, level)`
  - `in_world(ri)`, `world_ri()`, `window(cell, rings=3)`, `child_offsets(level)` (cached), `children(cell, level)`, `neighbours(cell)`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_hexaddr.py` (create or replace the whole file)

```python
import math
import random

import pytest

from hexaddr import (
    CHO, KEN, PACKING, RI, SCALE, SHAKU, SHAKU_M, WIDTH_M, address, axial_to_metres, centre_child,
    centre_shaku, child_offsets, children, d2, format_address, from_address, hex_round, in_world,
    local, metres_to_axial, owner, parent, round_at, shaku_at, tier_cell, up, window, world_ri,
)


def brute_owner(cell, n):
    """Nearest parent centre by exact integer distance, ties to the greatest (a, b), searched wide."""
    q, r = cell
    best = None
    for a in range(round(q / n) - 3, round(q / n) + 4):
        for b in range(round(r / n) - 3, round(r / n) + 4):
            key = (d2(q - n * a, r - n * b), -a, -b)
            if best is None or key < best[0]:
                best = (key, (a, b))
    return best[1]


def test_unit_lengths():
    assert SHAKU_M == pytest.approx(0.30303, abs=1e-5)
    assert WIDTH_M[KEN] == pytest.approx(6 * SHAKU_M)
    assert WIDTH_M[CHO] == pytest.approx(360 * SHAKU_M)
    assert WIDTH_M[RI] == pytest.approx(3927.27, abs=0.01)
    assert SCALE == (1, 6, 360, 12960)


@pytest.mark.parametrize("n", [6, 60, 36])
def test_owner_matches_brute_force(n):
    rng = random.Random(n)
    for _ in range(3000):
        cell = (rng.randint(-5 * n, 5 * n), rng.randint(-5 * n, 5 * n))
        assert owner(cell, n) == brute_owner(cell, n)


@pytest.mark.parametrize("level, expected", [(KEN, 36), (CHO, 3600), (RI, 1296)])
def test_every_parent_owns_exactly_n_squared(level, expected):
    assert len(child_offsets(level)) == expected
    n = PACKING[level]
    for p in [(0, 0), (1, 0), (-2, 3), (5, -7)]:
        for c in children(p, level):
            assert owner(c, n) == p


@pytest.mark.parametrize("level", [KEN, CHO, RI])
def test_split_children_have_one_owner_by_the_tie_rule(level):
    n = PACKING[level]
    offsets = set(child_offsets(level))
    # the six edge-midpoint children: (n/2) along each neighbour direction
    halved = [(n // 2, 0), (-n // 2, 0), (0, n // 2), (0, -n // 2), (n // 2, -n // 2), (-n // 2, n // 2)]
    owned_halved = [h for h in halved if h in offsets]
    assert len(owned_halved) == 3
    # the six corners: n/3 along each diagonal
    k = n // 3
    corners = [(k, k), (-k, -k), (2 * k, -k), (-2 * k, k), (k, -2 * k), (-k, 2 * k)]
    assert len([c for c in corners if c in offsets]) == 2
    # the owner of a split child is the greatest tied candidate
    for h in halved:
        assert owner(h, n) == brute_owner(h, n)


def test_children_tile_the_plane_without_overlap():
    seen = {}
    for p in window((0, 0), 2):
        for c in children(p, KEN):
            assert c not in seen
            seen[c] = p
    # every shaku near the middle is covered
    for q in range(-6, 7):
        for r in range(-6, 7):
            assert (q, r) in seen


def test_centres_nest():
    assert centre_child((2, -1), KEN) == (12, -6)
    assert centre_shaku((2, -1), CHO) == (720, -360)
    assert up(centre_shaku((3, -2), RI), SHAKU, RI) == (3, -2)
    assert up(centre_shaku((7, 4), CHO), SHAKU, CHO) == (7, 4)


def test_address_round_trip():
    rng = random.Random(1)
    for _ in range(2000):
        s = (rng.randint(-150000, 150000), rng.randint(-150000, 150000))
        addr = address(s)
        assert from_address(addr) == s
        ri, cho, ken, sh = addr
        assert sh in child_offsets(KEN)
        assert ken in child_offsets(CHO)
        assert cho in child_offsets(RI)
        assert up(s, SHAKU, RI) == ri


def test_address_of_the_world_centre():
    assert address((0, 0)) == ((0, 0), (0, 0), (0, 0), (0, 0))
    assert format_address(address((0, 0))) == "ri (0,0) / cho (0,0) / ken (0,0) / shaku (0,0)"


def test_local_offset():
    # shaku (13, -6) belongs to ken (2, -1), centred on shaku (12, -6)
    assert parent((13, -6), SHAKU) == (2, -1)
    assert local((13, -6), SHAKU) == (1, 0)
    # ken (61, 2) belongs to cho (1, 0), centred on ken (60, 0)
    assert local((61, 2), KEN) == (1, 2)


def test_neighbouring_addresses_across_borders():
    # walking east along r = 0 crosses ken, cho and ri borders; each step moves one shaku
    prev = address((0, 0))
    crossings = {"ken": 0, "cho": 0, "ri": 0}
    for q in range(1, 13000):
        cur = address((q, 0))
        assert from_address(cur) == (q, 0)
        if cur[0] != prev[0]:
            crossings["ri"] += 1
        if up((q, 0), SHAKU, CHO) != up((q - 1, 0), SHAKU, CHO):
            crossings["cho"] += 1
        if up((q, 0), SHAKU, KEN) != up((q - 1, 0), SHAKU, KEN):
            crossings["ken"] += 1
        prev = cur
    # a straight line along a neighbour axis crosses a ken every 6 shaku, a cho every 360, a ri every 12960
    assert crossings["ken"] == pytest.approx(13000 / 6, abs=2)
    assert crossings["cho"] == pytest.approx(13000 / 360, abs=2)
    assert crossings["ri"] == 1


def test_metres_round_trip_and_rounding():
    x, z = axial_to_metres(5, -3)
    q, r = metres_to_axial(x, z)
    assert (q, r) == (pytest.approx(5), pytest.approx(-3))
    assert shaku_at(x + 0.1 * SHAKU_M, z) == (5, -3)
    assert axial_to_metres(1, 0, RI) == (pytest.approx(WIDTH_M[RI]), 0.0)
    assert hex_round(0.4, 0.4) == (0, 1)
    assert hex_round(-0.2, 0.9) == (0, 1)
    assert round_at(*axial_to_metres(2, 3, CHO), CHO) == (2, 3)


def test_neighbour_spacing_is_one_width():
    x0, z0 = axial_to_metres(0, 0, KEN)
    for d in [(1, 0), (0, 1), (-1, 1)]:
        x, z = axial_to_metres(*d, KEN)
        assert math.hypot(x - x0, z - z0) == pytest.approx(WIDTH_M[KEN])


def test_tier_cell_agrees_with_address_at_shaku_tier():
    rng = random.Random(2)
    for _ in range(500):
        s = (rng.randint(-5000, 5000), rng.randint(-5000, 5000))
        x, z = axial_to_metres(*s)
        assert tier_cell(x, z, SHAKU, CHO) == up(s, SHAKU, CHO)
        assert tier_cell(x, z, KEN, KEN) == round_at(x, z, KEN)


def test_world_and_windows():
    assert len(world_ri()) == 469
    assert all(in_world(ri) for ri in world_ri())
    assert not in_world((13, 0))
    w = window((4, -1))
    assert len(w) == 37 and (4, -1) in w and (7, -1) in w and (8, -1) not in w
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 11 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/hexaddr.py` (create or replace the whole file)

```python
"""Hierarchical hex addresses: shaku, ken, cho and ri.

Every level is a pointy-top axial hex lattice with the same orientation (packing B): a level-L
cell (a, b) is centred on the level-(L-1) cell (N*a, N*b), N = PACKING[L]. A child belongs to
exactly one parent: the nearest parent centre, ties to the lexicographically greatest (a, b).
Pure Python ints; the numpy twin for whole chunks is in chunkgeom.py.
"""

import math
from functools import cache

from hexgrid import DIRECTIONS, Tile, distance

SHAKU, KEN, CHO, RI = 0, 1, 2, 3
LEVELS = (SHAKU, KEN, CHO, RI)
LEVEL_NAMES = ("shaku", "ken", "cho", "ri")
PACKING = (1, 6, 60, 36)          # PACKING[L]: level L-1 cells per side of a level-L cell
SCALE = (1, 6, 360, 12960)        # shaku per side of a level-L cell
SHAKU_M = 10 / 33                 # metres, flat to flat
WIDTH_M = tuple(s * SHAKU_M for s in SCALE)
WORLD_RADIUS = 12                 # ri
WINDOW_RINGS = 3
SQRT3 = math.sqrt(3)

Address = tuple[Tile, Tile, Tile, Tile]  # ri (world position), cho, ken, shaku (local offsets)


def d2(dq: int, dr: int) -> int:
    """Squared hex-plane distance of an axial offset, times 1 (exact integer)."""
    return dq * dq + dq * dr + dr * dr


def owner(cell: Tile, n: int) -> Tile:
    """The parent (on the lattice scaled by n) that owns this child cell."""
    q, r = cell
    a0, b0 = round(q / n), round(r / n)
    best = None
    best_key = None
    for a in (a0 - 1, a0, a0 + 1):
        for b in (b0 - 1, b0, b0 + 1):
            key = (d2(q - n * a, r - n * b), -a, -b)
            if best_key is None or key < best_key:
                best_key, best = key, (a, b)
    return best


def parent(cell: Tile, level: int) -> Tile:
    """The level+1 cell that owns this level cell."""
    return owner(cell, PACKING[level + 1])


def up(cell: Tile, from_level: int, to_level: int) -> Tile:
    for level in range(from_level, to_level):
        cell = parent(cell, level)
    return cell


def centre_child(cell: Tile, level: int) -> Tile:
    """The level-1 cell at the centre of this level cell."""
    n = PACKING[level]
    return (cell[0] * n, cell[1] * n)


def centre_shaku(cell: Tile, level: int) -> Tile:
    s = SCALE[level]
    return (cell[0] * s, cell[1] * s)


def local(cell: Tile, level: int) -> Tile:
    """Offset of a cell from its parent's centre, in cells of its own level."""
    p = parent(cell, level)
    n = PACKING[level + 1]
    return (cell[0] - n * p[0], cell[1] - n * p[1])


def address(shaku: Tile) -> Address:
    ken = parent(shaku, SHAKU)
    cho = parent(ken, KEN)
    ri = parent(cho, CHO)
    return (ri, local(cho, CHO), local(ken, KEN), local(shaku, SHAKU))


def from_address(addr: Address) -> Tile:
    ri, cho_off, ken_off, shaku_off = addr
    cho = (ri[0] * PACKING[RI] + cho_off[0], ri[1] * PACKING[RI] + cho_off[1])
    ken = (cho[0] * PACKING[CHO] + ken_off[0], cho[1] * PACKING[CHO] + ken_off[1])
    return (ken[0] * PACKING[KEN] + shaku_off[0], ken[1] * PACKING[KEN] + shaku_off[1])


def format_address(addr: Address) -> str:
    parts = zip(("ri", "cho", "ken", "shaku"), addr)
    return " / ".join(f"{name} ({q},{r})" for name, (q, r) in parts)


def axial_to_metres(q: float, r: float, level: int = SHAKU) -> tuple[float, float]:
    """Centre of axial (q, r) at a level, in world metres (x east, z north)."""
    w = WIDTH_M[level]
    return ((q + r / 2) * w, r * SQRT3 / 2 * w)


def metres_to_axial(x: float, z: float, level: int = SHAKU) -> tuple[float, float]:
    w = WIDTH_M[level]
    r = z / (SQRT3 / 2 * w)
    return (x / w - r / 2, r)


def hex_round(fq: float, fr: float) -> Tile:
    fs = -fq - fr
    q, r, s = round(fq), round(fr), round(fs)
    dq, dr, ds = abs(q - fq), abs(r - fr), abs(s - fs)
    if dq > dr and dq > ds:
        q = -r - s
    elif dr > ds:
        r = -q - s
    return (q, r)


def round_at(x: float, z: float, level: int) -> Tile:
    """The level cell whose ideal hexagon contains the point (nearest centre at that level)."""
    return hex_round(*metres_to_axial(x, z, level))


def shaku_at(x: float, z: float) -> Tile:
    return round_at(x, z, SHAKU)


def tier_cell(x: float, z: float, tier: int, level: int) -> Tile:
    """The level cell a point belongs to where tier `tier` is drawn: round at the tier, then own upward."""
    return up(round_at(x, z, tier), tier, level)


def in_world(ri: Tile) -> bool:
    return distance(ri, (0, 0)) <= WORLD_RADIUS


def world_ri() -> list[Tile]:
    n = WORLD_RADIUS
    return [(q, r) for q in range(-n, n + 1) for r in range(max(-n, -q - n), min(n, -q + n) + 1)]


def window(cell: Tile, rings: int = WINDOW_RINGS) -> list[Tile]:
    """The cell plus `rings` rings of neighbours at the same level."""
    q0, r0 = cell
    return [
        (q0 + q, r0 + r)
        for q in range(-rings, rings + 1)
        for r in range(max(-rings, -q - rings), min(rings, -q + rings) + 1)
    ]


@cache
def child_offsets(level: int) -> tuple[Tile, ...]:
    """Local offsets of the level-1 cells a level cell owns (the same for every cell)."""
    n = PACKING[level]
    reach = n  # owned children lie within hex distance 2n/3 of the centre
    return tuple(
        (q, r)
        for q in range(-reach, reach + 1)
        for r in range(-reach, reach + 1)
        if owner((q, r), n) == (0, 0)
    )


def children(cell: Tile, level: int) -> list[Tile]:
    cq, cr = centre_child(cell, level)
    return [(cq + q, cr + r) for q, r in child_offsets(level)]


def neighbours(cell: Tile) -> list[Tile]:
    return [(cell[0] + dq, cell[1] + dr) for dq, dr in DIRECTIONS]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **31 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/hexaddr.py experiments/exp-03/tests/test_hexaddr.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: hierarchical hex addresses (shaku, ken, cho, ri)

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 3: Noise and terrain fields

**Files:**
- Create: `src/noise.py`, `src/terrain.py`
- Test: `tests/test_noise.py`, `tests/test_terrain.py`

**Interfaces:**
- Consumes: `hexaddr.RI`, `SHAKU`, `WIDTH_M`.
- Produces:
  - `noise.hash_ints(seed, *parts) -> uint64 array`, `noise.hash01(seed, *parts) -> float array in [0, 1)`, `noise.gradient_noise(x, y, seed)`, `noise.octave_offset(seed, k)`
  - `terrain.height(x, z, tier, seed)`, `terrain.ground_height(x, z, seed) -> float` (full detail at one point), `terrain.keeps(wavelength, tier)`, `terrain.octave_count(tier)`, `terrain.mountain_mask(x, z)`
  - `terrain.ground_type(x, z, h, slope_deg, seed)` with `GRASS, DIRT, ROCK, SNOW = 0, 1, 2, 3`, `terrain.ground_colour(x, z, kind, tier, seed)`, `terrain.forest_density(x, z, seed)`, `terrain.GROUND_NAMES`, `terrain.GROUND_COLOURS`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_noise.py` (create or replace the whole file)

```python
import numpy as np

from noise import gradient_noise, hash01, hash_ints, octave_offset


def test_hash_is_deterministic_and_seed_dependent():
    q = np.arange(-50, 50)
    assert np.array_equal(hash_ints(7, q, 3), hash_ints(7, q, 3))
    assert not np.array_equal(hash_ints(7, q, 3), hash_ints(8, q, 3))
    assert not np.array_equal(hash_ints(7, q, 3), hash_ints(7, q, 4))


def test_hash01_is_uniform_in_unit_interval():
    u = hash01(1, np.arange(200000), 5)
    assert u.min() >= 0.0 and u.max() < 1.0
    assert abs(u.mean() - 0.5) < 0.005
    hist, _ = np.histogram(u, bins=10, range=(0, 1))
    assert hist.min() > 19000


def test_gradient_noise_range_and_lattice_zeros():
    rng = np.random.default_rng(0)
    x = rng.uniform(-1000, 1000, 100000)
    y = rng.uniform(-1000, 1000, 100000)
    n = gradient_noise(x, y, 3)
    assert -1.0 <= n.min() and n.max() <= 1.0
    assert 0.25 < n.std() < 0.35
    assert abs(n.mean()) < 0.01
    ints = np.arange(-20, 20, dtype=float)
    assert np.allclose(gradient_noise(ints, ints, 3), 0.0)


def test_gradient_noise_is_continuous():
    x = np.linspace(0, 10, 100001)
    n = gradient_noise(x, np.full_like(x, 0.37), 9)
    assert np.abs(np.diff(n)).max() < 0.001


def test_gradient_noise_is_deterministic_and_order_free():
    x = np.array([3.2, -7.9, 100.5])
    y = np.array([0.1, 4.4, -2.2])
    a = gradient_noise(x, y, 11)
    b = gradient_noise(x[::-1], y[::-1], 11)[::-1]
    assert np.array_equal(a, b)
    assert gradient_noise(x[1], y[1], 11) == a[1]


def test_octave_offsets_differ():
    assert octave_offset(1, 0) != octave_offset(1, 1)
    assert octave_offset(1, 0) == octave_offset(1, 0)
```

**File:** `tests/test_terrain.py` (create or replace the whole file)

```python
import numpy as np
import pytest

from hexaddr import CHO, KEN, RI, SHAKU, WIDTH_M
from terrain import (
    COUNTRY_AMPS, COUNTRY_WAVELENGTHS, DIRT, GRASS, MOUNTAIN_WAVELENGTHS, ROCK, SNOW, _field, forest_density,
    ground_height, ground_type, height, keeps, mountain_mask, octave_count,
)


@pytest.fixture(scope="module")
def points():
    rng = np.random.default_rng(4)
    return rng.uniform(-40000, 40000, 20000), rng.uniform(-40000, 40000, 20000)


def test_octave_counts_per_tier():
    assert octave_count(RI) == (2, 2)
    assert octave_count(CHO) == (7, 4)
    assert octave_count(KEN) == (13, 4)
    assert octave_count(SHAKU) == (16, 4)
    assert COUNTRY_WAVELENGTHS[-1] == pytest.approx(0.61, abs=0.01)
    assert all(keeps(w, SHAKU) for w in COUNTRY_WAVELENGTHS + MOUNTAIN_WAVELENGTHS)


def test_height_is_deterministic(points):
    x, z = points
    assert np.array_equal(height(x, z, KEN, 3), height(x, z, KEN, 3))
    assert not np.array_equal(height(x, z, KEN, 3), height(x, z, KEN, 4))


def test_coarse_tier_is_fine_tier_minus_dropped_octaves(points):
    x, z = points
    fine = height(x, z, SHAKU, 0)
    coarse = height(x, z, CHO, 0)
    dropped = sum(a * _field(x, z, w, 0, 1, k)
                  for k, (w, a) in enumerate(zip(COUNTRY_WAVELENGTHS, COUNTRY_AMPS)) if not keeps(w, CHO))
    assert np.allclose(fine - coarse, dropped)


def test_detail_amplitudes(points):
    x, z = points
    # what the ken tier adds over the cho tier: bumps under about a metre
    assert np.abs(height(x, z, KEN, 0) - height(x, z, CHO, 0)).max() < 3.0
    # what the shaku tier adds over the ken tier: centimetres
    assert np.abs(height(x, z, SHAKU, 0) - height(x, z, KEN, 0)).max() < 0.15


def test_rim_rises_above_the_country():
    a = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    rail = height(4 * WIDTH_M[RI] * np.cos(a), 4 * WIDTH_M[RI] * np.sin(a), CHO, 0)
    rim = height(11 * WIDTH_M[RI] * np.cos(a), 11 * WIDTH_M[RI] * np.sin(a), CHO, 0)
    assert np.abs(rail).max() < 60
    assert rim.mean() > 500
    assert mountain_mask(0.0, 0.0) == 0.0
    assert mountain_mask(12 * WIDTH_M[RI], 0.0) == 1.0


def test_ground_height_matches_the_shaku_tier():
    assert ground_height(123.4, -567.8, 2) == pytest.approx(float(height(123.4, -567.8, SHAKU, 2)))


def test_ground_type_rules():
    x = np.zeros(4)
    z = np.zeros(4)
    kinds = ground_type(x, z, np.array([1500.0, 950.0, 10.0, 10.0]), np.array([0.0, 0.0, 40.0, 0.0]), 0)
    assert list(kinds[:3]) == [SNOW, ROCK, ROCK]
    assert kinds[3] in (GRASS, DIRT)


def test_dirt_covers_about_thirty_percent(points):
    x, z = points
    kinds = ground_type(x, z, np.zeros_like(x), np.zeros_like(x), 0)
    assert 0.25 < (kinds == DIRT).mean() < 0.35


def test_forest_density_has_woods_and_clearings(points):
    x, z = points
    f = forest_density(x, z, 0)
    assert f.min() == 0.0 and f.max() == 1.0
    assert 0.25 < (f > 0).mean() < 0.6
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 31 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/noise.py` (create or replace the whole file)

```python
"""Hashed-lattice gradient noise and integer hashing, vectorized with numpy.

Everything is a pure function of its inputs and a seed, so any chunk can be generated in any order.
"""

from functools import cache

import numpy as np

_M1 = np.uint64(0x9E3779B97F4A7C15)
_M2 = np.uint64(0xBF58476D1CE4E5B9)
_M3 = np.uint64(0x94D049BB133111EB)
_S30, _S27, _S31 = np.uint64(30), np.uint64(27), np.uint64(31)

# Eight unit gradients, evenly spaced.
_ANGLES = np.arange(8) * (np.pi / 4) + np.pi / 8
_GX = np.cos(_ANGLES)
_GY = np.sin(_ANGLES)


def _mix(h: np.ndarray) -> np.ndarray:
    h = (h ^ (h >> _S30)) * _M2
    h = (h ^ (h >> _S27)) * _M3
    return h ^ (h >> _S31)


def hash_ints(seed: int, *parts) -> np.ndarray:
    """A 64-bit hash of integer arrays (broadcast together) and a seed."""
    with np.errstate(over="ignore"):
        h = np.full(np.broadcast(*parts).shape, np.uint64(seed & 0xFFFFFFFFFFFFFFFF) * _M1, dtype=np.uint64)
        for p in parts:
            h = _mix(h ^ (np.asarray(p, dtype=np.int64).view(np.uint64) + _M1))
    return h


def hash01(seed: int, *parts) -> np.ndarray:
    """Uniform floats in [0, 1) from integer arrays and a seed."""
    return (hash_ints(seed, *parts) >> np.uint64(11)).astype(np.float64) * (1.0 / (1 << 53))


def gradient_noise(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """2D gradient noise with unit lattice spacing, roughly in [-1, 1], 0 on lattice points."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    fx0 = np.floor(x)
    fy0 = np.floor(y)
    ix = fx0.astype(np.int64)
    iy = fy0.astype(np.int64)
    fx = x - fx0
    fy = y - fy0

    with np.errstate(over="ignore"):
        s = np.uint64(seed & 0xFFFFFFFFFFFFFFFF) * _M1

    def corner(dx, dy):
        with np.errstate(over="ignore"):
            h = ((ix + dx).view(np.uint64) * _M2) ^ ((iy + dy).view(np.uint64) * _M3) ^ s
            g = (_mix(h) & np.uint64(7)).astype(np.intp)
        return _GX[g] * (fx - dx) + _GY[g] * (fy - dy)

    ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    uy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    n00, n10 = corner(0, 0), corner(1, 0)
    n01, n11 = corner(0, 1), corner(1, 1)
    nx0 = n00 + ux * (n10 - n00)
    nx1 = n01 + ux * (n11 - n01)
    return (nx0 + uy * (nx1 - nx0)) * 1.41421356


@cache
def octave_offset(seed: int, k: int) -> tuple[float, float]:
    """A per-octave shift, so no two octaves share lattice points."""
    u = hash01(seed, k, 101)
    v = hash01(seed, k, 202)
    return float(u) * 1000.0, float(v) * 1000.0
```

**File:** `src/terrain.py` (create or replace the whole file)

```python
"""The procedural world: height, ground type and props, per tier. Placeholder numbers throughout.

A tier is named by the cell size it draws (SHAKU..RI) and keeps only the noise octaves whose
wavelength is at least twice its cell spacing, so a coarse sample is the fine terrain minus the
detail it cannot show.
"""

import numpy as np

from hexaddr import RI, SHAKU, WIDTH_M
from noise import gradient_noise, hash01, octave_offset

# Country: 16 octaves, 20 km down to 0.61 m.
COUNTRY_WAVELENGTHS = tuple(20000.0 / 2**k for k in range(16))
COUNTRY_AMPS = (25.0, 20.0, 15.0, 10.0, 6.0, 3.5, 2.0, 1.0, 0.5, 0.3, 0.2, 0.12, 0.08, 0.04, 0.025, 0.015)
# Rim mountains: ridged noise, 20 km down to 2.5 km, masked by distance from the centre.
MOUNTAIN_WAVELENGTHS = (20000.0, 10000.0, 5000.0, 2500.0)
MOUNTAIN_AMPS = (700.0, 450.0, 250.0, 100.0)
MOUNTAIN_INNER_M = 6 * WIDTH_M[RI]
MOUNTAIN_OUTER_M = 11 * WIDTH_M[RI]

GRASS, DIRT, ROCK, SNOW = 0, 1, 2, 3
GROUND_NAMES = ("grass", "dirt", "rock", "snow")
GROUND_COLOURS = np.array([
    (0.36, 0.55, 0.25),
    (0.52, 0.40, 0.26),
    (0.48, 0.47, 0.45),
    (0.92, 0.94, 0.96),
])
SNOW_LINE_M = 1200.0
ROCK_LINE_M = 900.0
ROCK_SLOPE_DEG = 35.0
DIRT_WAVELENGTH_M = 300.0
DIRT_THRESHOLD = -0.17          # about 30% of the dirt field lies below this
FOREST_WAVELENGTH_M = 800.0

# Salts keep the separate noise fields independent.
_COUNTRY, _MOUNTAIN, _SNOW, _DIRT, _FOREST, _SHADE = 1, 2, 3, 4, 5, 6


def keeps(wavelength: float, tier: int) -> bool:
    return wavelength >= 2 * WIDTH_M[tier]


def octave_count(tier: int) -> tuple[int, int]:
    """(country octaves, mountain octaves) kept at a tier."""
    return (sum(keeps(w, tier) for w in COUNTRY_WAVELENGTHS), sum(keeps(w, tier) for w in MOUNTAIN_WAVELENGTHS))


def _field(x, z, wavelength, seed, salt, k=0):
    ox, oz = octave_offset(seed * 16 + salt, k)
    return gradient_noise(x / wavelength + ox, z / wavelength + oz, seed * 64 + salt * 16 + k)


def mountain_mask(x, z):
    d = np.hypot(x, z)
    t = np.clip((d - MOUNTAIN_INNER_M) / (MOUNTAIN_OUTER_M - MOUNTAIN_INNER_M), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def height(x, z, tier: int, seed: int) -> np.ndarray:
    """Terrain height in metres at world points, with the octaves a tier keeps."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    h = np.zeros(np.broadcast(x, z).shape)
    for k, (w, a) in enumerate(zip(COUNTRY_WAVELENGTHS, COUNTRY_AMPS)):
        if keeps(w, tier):
            h += a * _field(x, z, w, seed, _COUNTRY, k)
    ridges = np.zeros_like(h)
    for k, (w, a) in enumerate(zip(MOUNTAIN_WAVELENGTHS, MOUNTAIN_AMPS)):
        if keeps(w, tier):
            n = 1.0 - np.abs(_field(x, z, w, seed, _MOUNTAIN, k))
            ridges += a * n * n
    return h + mountain_mask(x, z) * ridges


def ground_height(x: float, z: float, seed: int) -> float:
    """Full-detail height at one point."""
    return float(height(np.array([x]), np.array([z]), SHAKU, seed)[0])


def ground_type(x, z, h, slope_deg, seed: int) -> np.ndarray:
    snow_line = SNOW_LINE_M + 80.0 * _field(x, z, 2000.0, seed, _SNOW)
    dirt = _field(x, z, DIRT_WAVELENGTH_M, seed, _DIRT) < DIRT_THRESHOLD
    kind = np.where(dirt, DIRT, GRASS)
    kind = np.where((slope_deg > ROCK_SLOPE_DEG) | (h > ROCK_LINE_M), ROCK, kind)
    return np.where(h > snow_line, SNOW, kind)


def ground_colour(x, z, kind, tier: int, seed: int) -> np.ndarray:
    shade_wavelength = max(7.0, 4 * WIDTH_M[tier])
    shade = 1.0 + 0.08 * _field(x, z, shade_wavelength, seed, _SHADE)
    return GROUND_COLOURS[kind] * shade[..., None]


def forest_density(x, z, seed: int) -> np.ndarray:
    """0 in clearings, up to 1 in the thick of the woods."""
    return np.clip(_field(x, z, FOREST_WAVELENGTH_M, seed, _FOREST) * 1.8 - 0.1, 0.0, 1.0)


def prop_roll(seed: int, q, r, salt: int) -> np.ndarray:
    return hash01(seed, q, r, salt)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **46 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/noise.py experiments/exp-03/src/terrain.py experiments/exp-03/tests/test_noise.py experiments/exp-03/tests/test_terrain.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: noise and terrain fields with per-tier octave cuts

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 4: Chunk geometry (`chunkgeom.py`)

**Files:**
- Create: `src/chunkgeom.py`
- Test: `tests/test_chunkgeom.py`

**Interfaces:**
- Consumes: `hexaddr.RI`, `SQRT3`, `WIDTH_M`, `child_offsets`, `world_ri`; `hexgrid.DIRECTIONS`.
- Produces:
  - `Template` (frozen dataclass: `level`, `owned`, `vertex_count`, `cells` (H, 2) int64, `neighbours` (V, 6), `triangles` (T, 3) uint32, `grid`, `grid_lo`; method `index_of(offsets) -> indices or -1`)
  - `template(level) -> Template` (cached; `RI` gives the world chunk)
  - `TRI_A`, `TRI_B`, `DIRS_PLANAR`
  - `axial_to_metres_np(q, r, level)`, `mesh_triangle(fq, fr) -> (corners, weights)`, `mesh_height(fq, fr, level, height_fn)`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_chunkgeom.py` (create or replace the whole file)

```python
import numpy as np
import pytest

from chunkgeom import axial_to_metres_np, mesh_height, mesh_triangle, template
from hexaddr import CHO, KEN, RI, SHAKU, axial_to_metres, child_offsets, neighbours


@pytest.mark.parametrize("level, owned", [(SHAKU, 36), (KEN, 3600), (CHO, 1296), (RI, 469)])
def test_template_owns_the_parents_children(level, owned):
    tpl = template(level)
    assert tpl.owned == owned
    cells = [tuple(c) for c in tpl.cells]
    assert len(set(cells)) == len(cells)
    if level != RI:
        assert set(cells[:owned]) == set(child_offsets(level + 1))


def test_template_rings_and_neighbours():
    tpl = template(KEN)
    cells = [tuple(c) for c in tpl.cells]
    vertices = set(cells[:tpl.vertex_count])
    for i, c in enumerate(cells[:tpl.vertex_count]):
        assert [cells[j] for j in tpl.neighbours[i]] == neighbours(c)
    # every owned cell's neighbours are vertices (ring 1)
    for c in cells[:tpl.owned]:
        assert set(neighbours(c)) <= vertices


def test_triangles_are_adjacent_and_cover_every_owned_vertex():
    tpl = template(KEN)
    cells = tpl.cells
    tri = tpl.triangles
    assert tri.max() < tpl.vertex_count
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d = cells[tri[:, a]] - cells[tri[:, b]]
        dist = (np.abs(d[:, 0]) + np.abs(d[:, 1]) + np.abs(d[:, 0] + d[:, 1])) // 2
        assert (dist == 1).all()
    # six triangles around every owned vertex
    counts = np.bincount(tri.ravel(), minlength=tpl.vertex_count)
    assert (counts[:tpl.owned] == 6).all()
    # every triangle touches an owned cell
    assert (tri.min(axis=1) < tpl.owned).all()


def test_neighbouring_chunks_share_their_border_triangles():
    tpl = template(SHAKU)
    base_a = np.array((0, 0))
    base_b = np.array((6, 0))  # the next ken east
    tris = lambda base: {tuple(sorted(map(tuple, tpl.cells[t] + base))) for t in tpl.triangles}  # noqa: E731
    shared = tris(base_a) & tris(base_b)
    assert shared  # triangles straddling the border are drawn by both, clipped by ownership


def test_index_of_finds_template_cells():
    tpl = template(KEN)
    idx = tpl.index_of(tpl.cells[:50])
    assert list(idx) == list(range(50))
    assert tpl.index_of(np.array([[1000, 1000]]))[0] == -1


def test_mesh_triangle_weights():
    corners, weights = mesh_triangle(np.array([0.0, 0.25, 0.75, 2.0]), np.array([0.0, 0.25, 0.75, -1.0]))
    assert np.allclose(weights.sum(axis=-1), 1.0)
    assert (weights >= -1e-12).all()
    # a lattice point is its own corner with weight 1
    assert np.allclose(weights[0], [1, 0, 0]) and tuple(corners[0][0]) == (0, 0)
    assert np.allclose(weights[3], [1, 0, 0]) and tuple(corners[3][0]) == (2, -1)
    # the weighted corners reproduce the point
    p = (corners * weights[..., None]).sum(axis=-2)
    assert np.allclose(p, [[0, 0], [0.25, 0.25], [0.75, 0.75], [2, -1]])


def test_mesh_height_is_exact_at_vertices_and_linear_between():
    plane = lambda x, z, tier: 2.0 * x - 3.0 * z + 5.0  # noqa: E731
    fq = np.array([0.0, 1.3, -4.7, 10.5])
    fr = np.array([0.0, 2.2, 0.4, -3.9])
    x, z = axial_to_metres_np(fq, fr, CHO)
    assert np.allclose(mesh_height(fq, fr, CHO, plane), plane(x, z, CHO))
    bumpy = lambda x, z, tier: np.sin(x) + np.cos(z)  # noqa: E731
    cx, cz = axial_to_metres(3, -2, KEN)
    assert mesh_height(np.array([3.0]), np.array([-2.0]), KEN, bumpy)[0] == pytest.approx(bumpy(cx, cz, KEN))
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 46 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/chunkgeom.py` (create or replace the whole file)

```python
"""Chunk geometry: which cells a chunk holds, its triangles, and heights on a tier's mesh.

A chunk is one parent cell's children. Its template (offsets, neighbour table, triangles) is the
same for every parent at a level, so it is built once. Cells are ordered: owned children first,
then ring 1 (together, the mesh vertices), then ring 2 (only for slopes at ring-1 vertices).
"""

from dataclasses import dataclass
from functools import cache

import numpy as np

from hexaddr import RI, SQRT3, WIDTH_M, child_offsets, world_ri
from hexgrid import DIRECTIONS

# The triangulation of every level: each cell anchors two triangles of mutually adjacent cells,
# the two halves of the parallelogram (c, c+(1,0), c+(1,1), c+(0,1)).
TRI_A = ((0, 0), (1, 0), (0, 1))
TRI_B = ((1, 0), (1, 1), (0, 1))

# Unit vectors of the six neighbour directions in the plane (in cell widths).
DIRS_PLANAR = np.array([(q + r / 2, r * SQRT3 / 2) for q, r in DIRECTIONS])


@dataclass(frozen=True)
class Template:
    level: int                # level of the cells (the chunk's children)
    owned: int                # the first `owned` cells are the chunk's own children
    vertex_count: int         # the first `vertex_count` cells are mesh vertices (owned + ring 1)
    cells: np.ndarray         # (H, 2) int64 offsets from the parent's centre child (world: absolute ri)
    neighbours: np.ndarray    # (vertex_count, 6) indices into cells, in DIRECTIONS order
    triangles: np.ndarray     # (T, 3) uint32 indices into the vertices
    grid: np.ndarray          # dense lookup: grid[q - lo, r - lo] = index into cells, or -1
    grid_lo: int

    def index_of(self, offsets: np.ndarray) -> np.ndarray:
        """Indices into cells of (N, 2) template offsets (-1 where the template has no such cell)."""
        i = offsets[:, 0] - self.grid_lo
        j = offsets[:, 1] - self.grid_lo
        n = len(self.grid)
        inside = (i >= 0) & (i < n) & (j >= 0) & (j < n)
        found = self.grid[np.clip(i, 0, n - 1), np.clip(j, 0, n - 1)]
        return np.where(inside, found, -1)


def _neighbours(c):
    return [(c[0] + dq, c[1] + dr) for dq, dr in DIRECTIONS]


def _build(level: int, owned: list) -> Template:
    owned_set = set(owned)
    ring1 = sorted({n for c in owned for n in _neighbours(c)} - owned_set)
    ring1_set = set(ring1)
    ring2 = sorted({n for c in ring1 for n in _neighbours(c)} - owned_set - ring1_set)
    cells = list(owned) + ring1 + ring2
    index = {c: i for i, c in enumerate(cells)}
    vertex_count = len(owned) + len(ring1)
    neighbours = [[index[n] for n in _neighbours(c)] for c in cells[:vertex_count]]
    triangles = set()
    for v in owned:
        for tri in (TRI_A, TRI_B):
            for corner in tri:
                anchor = (v[0] - corner[0], v[1] - corner[1])
                triangles.add(tuple((anchor[0] + a, anchor[1] + b) for a, b in tri))
    tri_idx = sorted([index[a], index[b], index[c]] for a, b, c in triangles)
    arr = np.array(cells, dtype=np.int64)
    lo = int(arr.min()) - 1
    size = int(arr.max()) - lo + 2
    grid = np.full((size, size), -1, dtype=np.int64)
    grid[arr[:, 0] - lo, arr[:, 1] - lo] = np.arange(len(cells))
    return Template(
        level=level,
        owned=len(owned),
        vertex_count=vertex_count,
        cells=arr,
        neighbours=np.array(neighbours, dtype=np.int64),
        triangles=np.array(tri_idx, dtype=np.uint32),
        grid=grid,
        grid_lo=lo,
    )


@cache
def template(level: int) -> Template:
    """The template for chunks whose children are at `level` (RI: the world chunk)."""
    if level == RI:
        return _build(RI, world_ri())
    return _build(level, list(child_offsets(level + 1)))


def axial_to_metres_np(q, r, level: int):
    w = WIDTH_M[level]
    q = np.asarray(q, dtype=np.float64)
    r = np.asarray(r, dtype=np.float64)
    return (q + r / 2) * w, r * (SQRT3 / 2) * w


def mesh_triangle(fq, fr):
    """The mesh triangle containing fractional axial points: three corner cells and their weights."""
    fq = np.asarray(fq, dtype=np.float64)
    fr = np.asarray(fr, dtype=np.float64)
    i = np.floor(fq)
    j = np.floor(fr)
    u = fq - i
    v = fr - j
    upper = u + v >= 1.0
    i = i.astype(np.int64)
    j = j.astype(np.int64)
    # lower half: (i,j), (i+1,j), (i,j+1); upper half: (i+1,j), (i+1,j+1), (i,j+1)
    ax = np.where(upper, i + 1, i)
    bx = np.where(upper, i + 1, i + 1)
    by = np.where(upper, j + 1, j)
    corners = np.stack([
        np.stack([ax, j], -1),
        np.stack([bx, by], -1),
        np.stack([i, j + 1], -1),
    ], axis=-2)
    weights = np.stack([
        np.where(upper, 1.0 - v, 1.0 - u - v),
        np.where(upper, u + v - 1.0, u),
        np.where(upper, 1.0 - u, v),
    ], axis=-1)
    return corners, weights


def mesh_height(fq, fr, level: int, height_fn) -> np.ndarray:
    """Height of the tier-`level` mesh at fractional axial points on the `level` lattice.

    height_fn(x, z, tier) gives heights at world points; the mesh is the linear interpolation of
    its values at the three corner cells.
    """
    corners, weights = mesh_triangle(fq, fr)
    flat = corners.reshape(-1, 2)
    # unique on a packed 1-D key is much faster than np.unique(axis=0)
    key = (flat[:, 0] << 32) + (flat[:, 1] & 0xFFFFFFFF)
    _, first, inverse = np.unique(key, return_index=True, return_inverse=True)
    unique = flat[first]
    x, z = axial_to_metres_np(unique[:, 0], unique[:, 1], level)
    h = height_fn(x, z, level)[inverse.reshape(-1)].reshape(corners.shape[:-1])
    return (h * weights).sum(axis=-1)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **56 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/chunkgeom.py experiments/exp-03/tests/test_chunkgeom.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: chunk templates, triangulation and mesh heights

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 5: Chunk generation (`chunkgen.py`)

**Files:**
- Create: `src/chunkgen.py`
- Test: `tests/test_chunkgen.py`

**Interfaces:**
- Consumes: `chunkgeom` (Task 4), `terrain` and `noise` (Task 3), `hexaddr` (Task 2).
- Produces:
  - `ChunkData` (dataclass: `level`, `parent`, `origin`, `cells`, `vertices` (V, 7) float32 = x, z, h, h_coarse, r, g, b, `triangles`, `props` {kind: (K, 10) float32}, `gen_ms`; properties `key`, `triangle_count`)
  - `generate_chunk(level, parent, seed) -> ChunkData`
  - `morph_range(level) -> (start_m, end_m)`, `tier_height(seed)`
  - prop kinds `TREE, ROCK_PROP, TUFT, PEBBLE = 0, 1, 2, 3`, `PROP_NAMES`, `PROP_FIELDS = 10` (x, z, h_full, h_mid, h_far, scale, yaw, tint, cell q, cell r), `INNER_SHAKU`, `MORPH_START`, `MORPH_END`, `TREE_MAX`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_chunkgen.py` (create or replace the whole file)

```python
import numpy as np
import pytest

from chunkgen import (
    INNER_SHAKU, MORPH_END, MORPH_START, PEBBLE, ROCK_PROP, TREE, TUFT, generate_chunk, morph_range, tier_height,
)
from chunkgeom import mesh_height, template
from hexaddr import CHO, KEN, PACKING, RI, SHAKU, WIDTH_M, axial_to_metres, parent, shaku_at, up
from terrain import height

SEED = 0


@pytest.fixture(scope="module")
def ken_chunk():
    return generate_chunk(KEN, (144, 0), SEED)


def test_chunk_contents_match_the_template():
    for level, parent_cell in ((SHAKU, (8640, 0)), (KEN, (144, 0)), (CHO, (4, 0)), (RI, (0, 0))):
        c = generate_chunk(level, parent_cell, SEED)
        tpl = template(level)
        assert c.key == (level, parent_cell)
        assert len(c.cells) == tpl.owned
        assert c.vertices.shape == (tpl.vertex_count, 7) and c.vertices.dtype == np.float32
        assert c.triangle_count == len(tpl.triangles)
        if level != RI:
            assert all(up(tuple(cell), level, level + 1) == parent_cell for cell in c.cells[:50])


def test_generation_is_deterministic():
    a = generate_chunk(KEN, (5, -3), SEED)
    b = generate_chunk(KEN, (5, -3), SEED)
    assert np.array_equal(a.vertices, b.vertices)
    for kind in a.props:
        assert np.array_equal(a.props[kind], b.props[kind])
    assert not np.array_equal(a.vertices, generate_chunk(KEN, (5, -3), SEED + 1).vertices)


def test_vertices_are_relative_to_the_parent_centre(ken_chunk):
    ox, oz = axial_to_metres(144, 0, CHO)
    assert ken_chunk.origin == (pytest.approx(ox), pytest.approx(oz))
    x = ken_chunk.vertices[:, 0] + ox
    z = ken_chunk.vertices[:, 1] + oz
    assert np.allclose(ken_chunk.vertices[:, 2], height(x, z, KEN, SEED), atol=1e-3)
    assert np.abs(ken_chunk.vertices[:, :2]).max() < 0.7 * WIDTH_M[CHO]


def test_coarse_height_is_the_coarser_mesh(ken_chunk):
    tpl = template(KEN)
    cells = tpl.cells[:tpl.vertex_count] + np.array((144 * 60, 0))
    n = PACKING[CHO]
    expected = mesh_height(cells[:, 0] / n, cells[:, 1] / n, CHO, tier_height(SEED))
    assert np.allclose(ken_chunk.vertices[:, 3], expected, atol=1e-3)
    world = generate_chunk(RI, (0, 0), SEED)
    assert np.array_equal(world.vertices[:, 2], world.vertices[:, 3])


def test_same_tier_neighbours_agree_on_shared_vertices():
    a = generate_chunk(SHAKU, (0, 0), SEED)
    b = generate_chunk(SHAKU, (1, 0), SEED)
    tpl = template(SHAKU)
    ca = {tuple(c): i for i, c in enumerate(tpl.cells[:tpl.vertex_count] + np.array((0, 0)))}
    cb = {tuple(c): i for i, c in enumerate(tpl.cells[:tpl.vertex_count] + np.array((6, 0)))}
    shared = set(ca) & set(cb)
    assert shared
    for cell in shared:
        va = a.vertices[ca[cell]]
        vb = b.vertices[cb[cell]]
        assert va[2:].tolist() == pytest.approx(vb[2:].tolist(), abs=1e-4)


def test_ken_props(ken_chunk):
    trees, rocks = ken_chunk.props[TREE], ken_chunk.props[ROCK_PROP]
    assert len(trees) + len(rocks) > 0
    ox, oz = ken_chunk.origin
    for rows in (trees, rocks):
        for row in rows[:40]:
            ken = (int(row[8]), int(row[9]))
            assert parent(ken, KEN) == (144, 0)
            # the prop stands on one of its ken's inner 19 shaku
            px, pz = row[0] + ox, row[1] + oz
            s = shaku_at(px, pz)
            offset = (s[0] - 6 * ken[0], s[1] - 6 * ken[1])
            assert offset in {tuple(o) for o in INNER_SHAKU}
            assert row[2] == pytest.approx(float(height(px, pz, SHAKU, SEED)), abs=1e-3)


def test_prop_rates_over_many_ken():
    counts = {TREE: 0, ROCK_PROP: 0}
    kens = 0
    for q in range(-3, 3):
        c = generate_chunk(KEN, (q * 7, q * 3), SEED)
        kens += len(c.cells)
        for kind in counts:
            counts[kind] += len(c.props[kind])
    assert 0.0 < counts[TREE] / kens < 0.05
    assert 0.01 < counts[ROCK_PROP] / kens < 0.10


def test_a_prop_stands_on_the_shaku_tier_ground(ken_chunk):
    # the prop's full-detail and ken-mesh heights are exactly the shaku chunk's vertex heights there
    ox, oz = ken_chunk.origin
    rows = np.concatenate([ken_chunk.props[TREE], ken_chunk.props[ROCK_PROP]])[:10]
    for row in rows:
        ken = (int(row[8]), int(row[9]))
        shaku_chunk = generate_chunk(SHAKU, ken, SEED)
        s = shaku_at(row[0] + ox, row[1] + oz)
        i = [tuple(c) for c in shaku_chunk.cells].index(s)
        assert row[2] == pytest.approx(float(shaku_chunk.vertices[i, 2]), abs=1e-3)
        assert row[3] == pytest.approx(float(shaku_chunk.vertices[i, 3]), abs=1e-3)


def test_shaku_details_sit_on_their_shaku():
    c = generate_chunk(SHAKU, (8640, 3), SEED)
    rows = np.concatenate([c.props[TUFT], c.props[PEBBLE]])
    ox, oz = c.origin
    for row in rows:
        assert row[2] == pytest.approx(float(height(row[0] + ox, row[1] + oz, SHAKU, SEED)), abs=1e-3)
        assert (int(row[8]), int(row[9])) == (8640, 3)


def test_morph_ranges():
    assert morph_range(SHAKU) == (pytest.approx(MORPH_START * WIDTH_M[KEN]), pytest.approx(MORPH_END * WIDTH_M[KEN]))
    assert morph_range(CHO) == (pytest.approx(MORPH_START * WIDTH_M[RI]), pytest.approx(MORPH_END * WIDTH_M[RI]))
    assert morph_range(RI) == (0.0, 0.0)
    # the blend ends before the nearest possible window edge (2.26 parent widths, measured)
    assert MORPH_END < 2.26
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 56 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/chunkgen.py` (create or replace the whole file)

```python
"""Generating one chunk: heights, colours, mesh and props. A pure function of (level, parent, seed)."""

import time
from dataclasses import dataclass, field

import numpy as np

from chunkgeom import DIRS_PLANAR, axial_to_metres_np, mesh_height, mesh_triangle, template
from hexaddr import CHO, KEN, PACKING, RI, SHAKU, WIDTH_M, Tile, axial_to_metres, centre_child, window
from noise import hash01, hash_ints
from terrain import DIRT, GRASS, forest_density, ground_colour, ground_type, height

TREE, ROCK_PROP, TUFT, PEBBLE = 0, 1, 2, 3
PROP_NAMES = ("tree", "rock", "tuft", "pebble")
TREE_MAX = 0.05                                  # per ken, in the thick of the woods
ROCK_CHANCE = np.array([0.02, 0.06, 0.10, 0.0])  # per ken, by ground type
TUFT_CHANCE = 0.30                               # per grass shaku
PEBBLE_CHANCE = 0.15                             # per dirt shaku
INNER_SHAKU = np.array(window((0, 0), 2), dtype=np.int64)  # the 19 shaku a ken always owns whole
PROP_FIELDS = 10  # x, z (rel. origin), h_full, h_mid, h_far, scale, yaw, tint, cell q, cell r
MORPH_START, MORPH_END = 1.3, 2.0  # in parent widths from the loader focus (see the window margin)


@dataclass
class ChunkData:
    level: int                     # level of the children (the tier this chunk draws)
    parent: Tile                   # parent cell at level + 1 (world chunk: (0, 0))
    origin: tuple[float, float]    # world metres of the parent's centre; vertices are relative to it
    cells: np.ndarray              # (M, 2) global cells of the owned children
    vertices: np.ndarray           # (V, 7) float32: x, z, h, h_coarse, r, g, b
    triangles: np.ndarray          # (T, 3) uint32
    props: dict = field(default_factory=dict)  # kind -> (K, PROP_FIELDS) float32
    gen_ms: float = 0.0

    @property
    def key(self) -> tuple[int, Tile]:
        return (self.level, self.parent)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)


def tier_height(seed: int):
    return lambda x, z, tier: height(x, z, tier, seed)


def morph_range(level: int) -> tuple[float, float]:
    """Metres from the loader focus over which a tier's heights blend into the coarser mesh."""
    if level == RI:
        return (0.0, 0.0)
    w = WIDTH_M[level + 1]
    return (MORPH_START * w, MORPH_END * w)


def generate_chunk(level: int, parent: Tile, seed: int) -> ChunkData:
    t0 = time.perf_counter()
    tpl = template(level)
    if level == RI:
        base = np.zeros(2, dtype=np.int64)
        origin = (0.0, 0.0)
    else:
        base = np.array(centre_child(parent, level + 1), dtype=np.int64)
        origin = axial_to_metres(*parent, level + 1)
    cells = tpl.cells + base
    x, z = axial_to_metres_np(cells[:, 0], cells[:, 1], level)
    h = height(x, z, level, seed)

    v = tpl.vertex_count
    xv, zv, hv = x[:v], z[:v], h[:v]
    diffs = h[tpl.neighbours] - hv[:, None]
    grad = diffs @ DIRS_PLANAR / (3 * WIDTH_M[level])
    slope = np.degrees(np.arctan(np.hypot(grad[:, 0], grad[:, 1])))
    kind = ground_type(xv, zv, hv, slope, seed)
    colour = ground_colour(xv, zv, kind, level, seed)
    if level == RI:
        coarse = hv
    else:
        n = PACKING[level + 1]
        coarse = mesh_height(cells[:v, 0] / n, cells[:v, 1] / n, level + 1, tier_height(seed))

    vertices = np.column_stack([xv - origin[0], zv - origin[1], hv, coarse, colour]).astype(np.float32)
    owned = cells[:tpl.owned]
    props = {}
    if level == KEN:
        props = _ken_props(owned, kind[:tpl.owned], h, tpl, base, origin, seed)
    elif level == SHAKU:
        m = tpl.owned
        props = _shaku_details(owned, kind[:m], hv[:m], coarse[:m], parent, origin, seed)
    return ChunkData(
        level=level, parent=tuple(parent), origin=origin, cells=owned, vertices=vertices,
        triangles=tpl.triangles, props=props, gen_ms=(time.perf_counter() - t0) * 1000,
    )


def _pack(x, z, h_full, h_mid, h_far, scale, yaw, tint, cell_q, cell_r, origin):
    return np.column_stack([
        x - origin[0], z - origin[1], h_full, h_mid, h_far, scale, yaw, tint, cell_q, cell_r,
    ]).astype(np.float32)


def _ken_props(kens, kind, h, tpl, base, origin, seed) -> dict:
    q, r = kens[:, 0], kens[:, 1]
    kx, kz = axial_to_metres_np(q, r, KEN)
    forest = forest_density(kx, kz, seed)
    roll_tree = hash01(seed, q, r, 11)
    roll_rock = hash01(seed, q, r, 12)
    is_tree = ((kind == GRASS) | (kind == DIRT)) & (roll_tree < TREE_MAX * forest)
    is_rock = ~is_tree & (roll_rock < ROCK_CHANCE[kind])
    has_prop = is_tree | is_rock
    pick = (hash_ints(seed, q, r, 13) % np.uint64(len(INNER_SHAKU))).astype(np.intp)
    k = kens[has_prop]
    s = k * PACKING[KEN] + INNER_SHAKU[pick[has_prop]]
    px, pz = axial_to_metres_np(s[:, 0], s[:, 1], SHAKU)
    h_full = height(px, pz, SHAKU, seed)
    # the ken mesh at the prop: its triangle's corners are all cells of this chunk
    corners, weights = mesh_triangle(s[:, 0] / PACKING[KEN], s[:, 1] / PACKING[KEN])
    idx = tpl.index_of(corners.reshape(-1, 2) - base).reshape(corners.shape[:-1])
    h_mid = (h[idx] * weights).sum(axis=-1)
    n_cho = PACKING[KEN] * PACKING[CHO]
    h_far = mesh_height(s[:, 0] / n_cho, s[:, 1] / n_cho, CHO, tier_height(seed))
    tree = is_tree[has_prop]
    lo = np.where(tree, 0.8, 0.5)
    hi = np.where(tree, 1.3, 1.5)
    scale = lo + (hi - lo) * hash01(seed, k[:, 0], k[:, 1], 14)
    yaw = 2 * np.pi * hash01(seed, k[:, 0], k[:, 1], 15)
    tint = 0.85 + 0.3 * hash01(seed, k[:, 0], k[:, 1], 16)
    packed = _pack(px, pz, h_full, h_mid, h_far, scale, yaw, tint, k[:, 0], k[:, 1], origin)
    return {TREE: packed[tree], ROCK_PROP: packed[~tree]}


def _shaku_details(shaku, kind, h, h_ken, ken, origin, seed) -> dict:
    """Tufts and pebbles. A detail sits on its shaku's centre: the shaku vertex height, and the
    ken mesh there is the vertex's coarse height."""
    q, r = shaku[:, 0], shaku[:, 1]
    roll = hash01(seed, q, r, 21)
    props = {}
    for kind_id, mask in ((TUFT, (kind == GRASS) & (roll < TUFT_CHANCE)),
                          (PEBBLE, (kind == DIRT) & (roll < PEBBLE_CHANCE))):
        s = shaku[mask]
        px, pz = axial_to_metres_np(s[:, 0], s[:, 1], SHAKU)
        scale = 0.7 + 0.6 * hash01(seed, s[:, 0], s[:, 1], 22)
        yaw = 2 * np.pi * hash01(seed, s[:, 0], s[:, 1], 23)
        tint = 0.85 + 0.3 * hash01(seed, s[:, 0], s[:, 1], 24)
        cells = np.broadcast_to(np.array(ken, dtype=np.int64), s.shape)
        props[kind_id] = _pack(px, pz, h[mask], h_ken[mask], np.zeros(len(s)), scale, yaw, tint,
                               cells[:, 0], cells[:, 1], origin)
    return props

```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **66 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/chunkgen.py experiments/exp-03/tests/test_chunkgen.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: chunk generation with blended heights, props and details

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 6: The camera rail (`rail.py`)

**Files:**
- Create: `src/rail.py`
- Test: `tests/test_rail.py`

**Interfaces:**
- Consumes: `hexaddr.RI`, `WIDTH_M`, `Tile`, `shaku_at`; the test uses `terrain.ground_height`.
- Produces:
  - `RAIL_RADIUS_M`, `SPEED_M_S = 2.5`, `EYE_BACK_M = 8.0`, `EYE_UP_M = 3.0`, `EYE_MIN_CLEARANCE_M = 1.5`, `EYE_SMOOTH_S = 0.5`, `FOV_Y_DEG = 60.0`
  - `focus_xz(t)`, `heading(t)`, `lap_seconds()`
  - `Rail(ground, start=0.0)`: `advance(dt)`, properties `focus` (x, h, z), `focus_shaku`, `eye` (x, y, z), `lap_fraction`, attribute `t`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_rail.py` (create or replace the whole file)

```python
import math

import pytest

from hexaddr import RI, WIDTH_M, axial_to_metres
from rail import (
    EYE_BACK_M, EYE_MIN_CLEARANCE_M, FOV_Y_DEG, RAIL_RADIUS_M, SPEED_M_S, Rail, focus_xz, heading, lap_seconds,
)
from terrain import ground_height


def test_radius_speed_and_lap():
    assert RAIL_RADIUS_M == pytest.approx(4 * WIDTH_M[RI])
    assert SPEED_M_S == 2.5
    assert lap_seconds() == pytest.approx(2 * math.pi * RAIL_RADIUS_M / 2.5)
    for t in (0.0, 1000.0, 20000.0):
        x, z = focus_xz(t)
        assert math.hypot(x, z) == pytest.approx(RAIL_RADIUS_M)
    x0, z0 = focus_xz(100.0)
    x1, z1 = focus_xz(101.0)
    assert math.hypot(x1 - x0, z1 - z0) == pytest.approx(2.5, rel=1e-6)


def test_anticlockwise_from_due_east():
    assert focus_xz(0.0) == (pytest.approx(RAIL_RADIUS_M), pytest.approx(0.0))
    x, z = focus_xz(1000.0)
    assert z > 0  # heading north first, i.e. anticlockwise seen from above (x east, z north)
    assert heading(0.0) == (pytest.approx(0.0), pytest.approx(1.0))


def test_start_offsets_the_rail():
    a = Rail(lambda x, z: 0.0, start=500.0)
    b = Rail(lambda x, z: 0.0)
    for _ in range(500):
        b.advance(1.0)
    assert a.focus == pytest.approx(b.focus)


def test_focus_shaku_is_where_the_focus_is():
    rail = Rail(lambda x, z: 0.0, start=123.0)
    x, _, z = rail.focus
    sx, sz = axial_to_metres(*rail.focus_shaku)
    assert math.hypot(sx - x, sz - z) < WIDTH_M[0]


def test_eye_trails_and_clears_the_ground():
    ground = lambda x, z: ground_height(x, z, 0)  # noqa: E731
    rail = Rail(ground, start=0.0)
    for _ in range(600):
        rail.advance(1 / 30)
        ex, ey, ez = rail.eye
        fx, fy, fz = rail.focus
        assert math.hypot(ex - fx, ez - fz) == pytest.approx(EYE_BACK_M)
        assert ey >= ground(ex, ez) + EYE_MIN_CLEARANCE_M - 1e-9


def test_horizon_stays_in_view():
    rail = Rail(lambda x, z: ground_height(x, z, 0), start=0.0)
    for _ in range(300):
        rail.advance(0.2)
        ex, ey, ez = rail.eye
        fx, fy, fz = rail.focus
        pitch = math.degrees(math.atan2(ey - fy, math.hypot(fx - ex, fz - ez)))
        assert 0 < pitch < FOV_Y_DEG / 2  # looking down, with the horizon still above the bottom edge


def test_lap_fraction():
    rail = Rail(lambda x, z: 0.0, start=lap_seconds() * 1.25)
    assert rail.lap_fraction == pytest.approx(0.25)
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 66 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/rail.py` (create or replace the whole file)

```python
"""The camera rail: a jog round a 4-ri circle about the world centre, with a low trailing eye."""

import math
from typing import Callable

from hexaddr import RI, WIDTH_M, Tile, shaku_at

RAIL_RADIUS_M = 4 * WIDTH_M[RI]
SPEED_M_S = 2.5
EYE_BACK_M = 8.0
EYE_UP_M = 3.0
EYE_MIN_CLEARANCE_M = 1.5
EYE_SMOOTH_S = 0.5
FOV_Y_DEG = 60.0


def focus_xz(t: float) -> tuple[float, float]:
    """Where the focus point is after t seconds (anticlockwise, starting due east)."""
    a = t * SPEED_M_S / RAIL_RADIUS_M
    return (RAIL_RADIUS_M * math.cos(a), RAIL_RADIUS_M * math.sin(a))


def heading(t: float) -> tuple[float, float]:
    """Unit direction of travel after t seconds."""
    a = t * SPEED_M_S / RAIL_RADIUS_M
    return (-math.sin(a), math.cos(a))


def lap_seconds() -> float:
    return 2 * math.pi * RAIL_RADIUS_M / SPEED_M_S


class Rail:
    """The camera's position over time. `ground(x, z)` is the full-detail terrain height."""

    def __init__(self, ground: Callable[[float, float], float], start: float = 0.0):
        self.ground = ground
        self.t = start
        self.eye_y = self._eye_target()

    def advance(self, dt: float) -> None:
        self.t += dt
        target = self._eye_target()
        self.eye_y += (target - self.eye_y) * (1 - math.exp(-dt / EYE_SMOOTH_S))
        self.eye_y = max(self.eye_y, self._eye_floor())

    @property
    def focus(self) -> tuple[float, float, float]:
        x, z = focus_xz(self.t)
        return (x, self.ground(x, z), z)

    @property
    def focus_shaku(self) -> Tile:
        return shaku_at(*focus_xz(self.t))

    @property
    def eye(self) -> tuple[float, float, float]:
        x, z = self._eye_xz()
        return (x, self.eye_y, z)

    @property
    def lap_fraction(self) -> float:
        return (self.t / lap_seconds()) % 1.0

    def _eye_xz(self) -> tuple[float, float]:
        fx, fz = focus_xz(self.t)
        hx, hz = heading(self.t)
        return (fx - EYE_BACK_M * hx, fz - EYE_BACK_M * hz)

    def _eye_floor(self) -> float:
        return self.ground(*self._eye_xz()) + EYE_MIN_CLEARANCE_M

    def _eye_target(self) -> float:
        return max(self.focus[1] + EYE_UP_M, self._eye_floor())
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **73 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/rail.py experiments/exp-03/tests/test_rail.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: the camera rail

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 7: Loaders and the chunk store (`loading.py`)

**Files:**
- Create: `src/loading.py`
- Test: `tests/test_loading.py`

**Interfaces:**
- Consumes: `hexaddr` (Task 2); the tests also use `chunkgen.generate_chunk` (Task 5) and `rail.Rail` (Task 6).
- Produces:
  - `ChunkKey = tuple[int, Tile]`, `WORLD_KEY = (RI, (0, 0))`, `LOAD_BUDGET_S = 0.008`
  - `Loader(name, focus)` (dataclass; `focus` is a global shaku, mutable)
  - `window_parents(focus, level) -> list[Tile]`, `requested(loader) -> set[ChunkKey]`, `chunk_distance(key, loaders)`
  - `TierStats` (`chunks`, `cells`, `triangles`, `queued`, `loads`, `unloads`, `gen_ms_last`, `gen_ms_mean`)
  - `ChunkStore(generate, on_load=None, on_unload=None, clock=time.perf_counter)`: `update(loaders, budget_s=LOAD_BUDGET_S) -> int`, `drain(loaders)`, `is_loaded(level, parent)`, `summary() -> [(name, TierStats, loads/s, unloads/s)]`, attributes `loaded`, `queue`, `stats`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_loading.py` (create or replace the whole file)

```python
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
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 73 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/loading.py` (create or replace the whole file)

```python
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
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **87 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/loading.py experiments/exp-03/tests/test_loading.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: loaders, tiered windows and the budgeted chunk store

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 8: The renderer and shaders (`gfx/`)

**Files:**
- Create: `src/gfx/__init__.py`, `src/gfx/context.py`, `src/gfx/matrices.py`, `src/gfx/meshes.py`, `src/gfx/shaders/hex.glsl`, `src/gfx/shaders/terrain.vert`, `src/gfx/shaders/terrain.frag`, `src/gfx/shaders/prop.vert`, `src/gfx/shaders/prop.frag`, `src/gfx/shaders/sky.vert`, `src/gfx/shaders/sky.frag`, `src/gfx/shaders/panel.vert`, `src/gfx/shaders/panel.frag`, `src/gfx/renderer.py`
- Test: `tests/test_gfx.py`

**Interfaces:**
- Consumes: `chunkgen` (`morph_range`, prop kinds), `hexaddr`, `loading` (tests).
- Produces:
  - `gfx.context.headless() -> bool`, `gfx.context.create(size, title) -> (ctx, target framebuffer)` (EGL offscreen when `SDL_VIDEODRIVER=dummy`, else a pygame OpenGL window)
  - `gfx.matrices.perspective`, `ortho`, `look_at`, `gl_bytes`
  - `gfx.meshes.MESHES` {kind: () -> (N, 9) float32}
  - `gfx.renderer`: `WINDOW_SIZE = (1600, 900)`, `VIEW_SIZE = (1180, 900)`, `PANEL_SIZE = (420, 900)`, `View(origin, eye, target, up=(0, 1, 0), projection=None)`, `Renderer(ctx, target)` with `load_chunk(chunk)`, `unload_chunk(chunk)`, `upload_panel(surface)`, `draw(view, draw_panel=True)`, `read_rgb(viewport=None) -> (H, W, 3) uint8`, attributes `chunks`, `debug`, `debug_level`, `debug_base`
  - shaders: `hex.glsl` is pasted into `terrain.frag` at `#include "hex.glsl"` by `renderer.shader_source`

**Note:** `tests/test_gfx.py` renders through an EGL context. On the development machine all 8 tests must pass, not skip; if they skip, report it. The shaders are GLSL files: create them exactly as given, including `#include "hex.glsl"` (the renderer substitutes it; GLSL itself has no include).

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_gfx.py` (create or replace the whole file)

```python
"""The shader's hex maths against hexaddr: top-down orthographic renders of the real loaded world.

Debug mode 1 writes, per pixel, the tier that drew it and the low bytes of its cell id at a chosen
level; debug mode 2 draws flat grey with the border lines. Skipped when no GL context is available.
"""

import random

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from chunkgen import generate_chunk  # noqa: E402
from gfx.matrices import ortho  # noqa: E402
from gfx.renderer import VIEW_SIZE, WINDOW_SIZE, Renderer, View  # noqa: E402
from hexaddr import (  # noqa: E402
    CHO, KEN, RI, SHAKU, SQRT3, WIDTH_M, axial_to_metres, centre_shaku, hex_round, metres_to_axial, tier_cell,
)
from loading import ChunkStore, Loader  # noqa: E402

FOCUS = (centre_shaku((4, 0), RI)[0] + 40, 17)  # near the rail start, not on any centre
W, H = VIEW_SIZE


@pytest.fixture(scope="module")
def world():
    try:
        ctx = moderngl.create_standalone_context(backend="egl", require=330)
    except Exception as exc:  # no EGL / GPU here
        pytest.skip(f"no GL context: {exc}")
    target = ctx.framebuffer(color_attachments=[ctx.renderbuffer(WINDOW_SIZE)],
                             depth_attachment=ctx.depth_renderbuffer(WINDOW_SIZE))
    renderer = Renderer(ctx, target)
    store = ChunkStore(lambda level, parent: generate_chunk(level, parent, 0), renderer.load_chunk,
                       renderer.unload_chunk)
    store.drain([Loader("camera", FOCUS)])
    yield renderer, set(store.loaded)
    ctx.release()


def top_down(renderer, half_height_m, mode, level=SHAKU, base=(0, 0)):
    ox, oz = axial_to_metres(*FOCUS)
    aspect = W / H
    proj = ortho(-half_height_m * aspect, half_height_m * aspect, -half_height_m, half_height_m, 1.0, 20000.0)
    renderer.debug, renderer.debug_level, renderer.debug_base = mode, level, base
    renderer.draw(View(origin=FOCUS, eye=(ox, 5000.0, oz), target=(ox, 0.0, oz), up=(0.0, 0.0, -1.0),
                       projection=proj), draw_panel=False)
    renderer.debug = 0
    return renderer.read_rgb((0, 0, W, H))


def pixel_to_world(i, j, half_height_m):
    """Centre of pixel column i, row j (top row first) in world metres."""
    ox, oz = axial_to_metres(*FOCUS)
    aspect = W / H
    x = -half_height_m * aspect + (i + 0.5) * 2 * half_height_m * aspect / W
    view_y = half_height_m - (j + 0.5) * 2 * half_height_m / H
    return ox + x, oz - view_y  # screen up is world -z


def world_to_pixel(x, z, half_height_m):
    ox, oz = axial_to_metres(*FOCUS)
    aspect = W / H
    i = (x - ox + half_height_m * aspect) / (2 * half_height_m * aspect) * W - 0.5
    j = (half_height_m - (oz - z)) / (2 * half_height_m) * H - 0.5
    return int(round(i)), int(round(j))


def expected_tier(x, z, loaded):
    for t in (SHAKU, KEN, CHO):
        if (t, tier_cell(x, z, t, t + 1)) in loaded:
            return t
    return RI


def classify(x, z, loaded, level):
    t = expected_tier(x, z, loaded)
    return t, tier_cell(x, z, t, max(level, t))


def stable(x, z, loaded, level, px_m):
    """The classification, if it is the same across the pixel's footprint; else None."""
    c = classify(x, z, loaded, level)
    for dx, dz in ((0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45)):
        if classify(x + dx * px_m, z + dz * px_m, loaded, level) != c:
            return None
    return c


@pytest.mark.parametrize("half_height_m, level", [(8.0, KEN), (8.0, CHO), (400.0, CHO), (400.0, RI)])
def test_shader_tiers_and_owners_match_hexaddr(world, half_height_m, level):
    renderer, loaded = world
    base = (0, 0)
    img = top_down(renderer, half_height_m, 1, level, base)
    px_m = 2 * half_height_m / H
    rng = random.Random(level * 1000 + int(half_height_m))
    checked = 0
    mismatches = 0
    tiers_seen = set()
    for _ in range(1500):
        i, j = rng.randrange(W), rng.randrange(H)
        x, z = pixel_to_world(i, j, half_height_m)
        c = stable(x, z, loaded, level, px_m)
        if c is None:
            continue
        tier, cell = c
        r, g, b = (int(v) for v in img[j, i])
        got_tier = round(b / 255 * 3)
        want = ((cell[0] - base[0]) & 255, (cell[1] - base[1]) & 255)
        checked += 1
        tiers_seen.add(tier)
        if got_tier != tier or (r, g) != want:
            mismatches += 1
    assert checked > 1000
    assert mismatches <= checked * 0.002
    assert len(tiers_seen) >= 2  # each view straddles a tier handover


def edge_distance_px(x, z, tier, px_m):
    fq, fr = metres_to_axial(x, z, tier)
    c = hex_round(fq, fr)
    dq, dr = fq - c[0], fr - c[1]
    dx, dy = dq + dr / 2, dr * SQRT3 / 2
    dirs = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
    best = max(dx * (q + r / 2) + dy * (r * SQRT3 / 2) for q, r in dirs)
    return (0.5 - best) * WIDTH_M[tier] / px_m


def test_flat_grey_away_from_every_edge(world):
    renderer, loaded = world
    half = 4.0
    img = top_down(renderer, half, 2)
    px_m = 2 * half / H
    rng = random.Random(5)
    checked = 0
    for _ in range(3000):
        i, j = rng.randrange(W), rng.randrange(H)
        x, z = pixel_to_world(i, j, half)
        tier = expected_tier(x, z, loaded)
        if tier != SHAKU or edge_distance_px(x, z, SHAKU, px_m) < 3:
            continue
        checked += 1
        assert tuple(img[j, i]) == pytest.approx((127, 127, 127), abs=2)
    assert checked > 500


def border_points(loaded, level, count, rng, half):
    """Midpoints of shaku edges inside the shaku window where the owners at `level` differ."""
    ox, oz = axial_to_metres(*FOCUS)
    found = []
    tries = 0
    while len(found) < count and tries < 200000:
        tries += 1
        x = ox + rng.uniform(-half, half)
        z = oz + rng.uniform(-half * 0.9, half * 0.9)
        s = hex_round(*metres_to_axial(x, z))
        d = rng.choice(((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)))
        n = (s[0] + d[0], s[1] + d[1])
        (ax, az), (bx, bz) = axial_to_metres(*s), axial_to_metres(*n)
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        if expected_tier(mx, mz, loaded) != SHAKU:
            continue
        top = max(L for L in (SHAKU, KEN, CHO, RI)
                  if L == SHAKU or tier_cell(ax, az, SHAKU, L) != tier_cell(bx, bz, SHAKU, L))
        if top == level:
            found.append((mx, mz))
    return found


@pytest.mark.parametrize("level, check", [
    (SHAKU, lambda rgb: max(rgb) < 100),                    # dark shaku lines
    (KEN, lambda rgb: min(rgb) > 160),                      # light ken borders
])
def test_border_pixels_carry_their_levels_colour(world, level, check):
    renderer, loaded = world
    half = 3.0
    img = top_down(renderer, half, 2)
    points = border_points(loaded, level, 60, random.Random(level), half)
    assert len(points) >= 30
    good = 0
    for x, z in points:
        i, j = world_to_pixel(x, z, half)
        if 0 <= i < W and 0 <= j < H and check(tuple(int(v) for v in img[j, i])):
            good += 1
    assert good >= 0.9 * len(points)


def test_parent_pixels_are_discarded_where_children_are_loaded(world):
    renderer, loaded = world
    # with every child chunk hidden from the lookup, the coarse tiers draw everywhere they own
    img_all = top_down(renderer, 400.0, 1, CHO)
    saved = dict(renderer.chunks)
    try:
        for key in [k for k in renderer.chunks if k[0] == SHAKU]:
            del renderer.chunks[key]
        img = top_down(renderer, 400.0, 1, CHO)
    finally:
        renderer.chunks.update(saved)
    tier_all = np.rint(img_all[:, :, 2] / 255 * 3)
    tier = np.rint(img[:, :, 2] / 255 * 3)
    # where the shaku tier drew, the ken tier now draws instead; nothing is left empty
    assert (tier_all == SHAKU).sum() > 0
    assert ((tier_all == SHAKU) & (tier != KEN)).sum() <= 0.01 * (tier_all == SHAKU).sum()
    assert (tier == SHAKU).sum() == 0
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 87 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/gfx/__init__.py` (create or replace the whole file)

```python

```

**File:** `src/gfx/context.py` (create or replace the whole file)

```python
"""Creating the GL context: a pygame OpenGL window, or an offscreen EGL context when headless."""

import os

import moderngl
import pygame


def headless() -> bool:
    return os.environ.get("SDL_VIDEODRIVER") == "dummy"


def create(size: tuple[int, int], title: str):
    """Returns (ctx, target framebuffer). Call after pygame.init()."""
    if headless():
        ctx = moderngl.create_standalone_context(backend="egl", require=330)
        target = ctx.framebuffer(
            color_attachments=[ctx.renderbuffer(size)],
            depth_attachment=ctx.depth_renderbuffer(size),
        )
        return ctx, target
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption(title)
    ctx = moderngl.create_context(require=330)
    return ctx, ctx.screen
```

**File:** `src/gfx/matrices.py` (create or replace the whole file)

```python
"""4x4 camera matrices in numpy (row-major; send `.T` to GL, which reads column-major)."""

import math

import numpy as np


def perspective(fov_y_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov_y_deg) / 2)
    return np.array([
        [f / aspect, 0, 0, 0],
        [0, f, 0, 0],
        [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)],
        [0, 0, -1, 0],
    ])


def ortho(left: float, right: float, bottom: float, top: float, near: float, far: float) -> np.ndarray:
    return np.array([
        [2 / (right - left), 0, 0, -(right + left) / (right - left)],
        [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
        [0, 0, -2 / (far - near), -(far + near) / (far - near)],
        [0, 0, 0, 1],
    ])


def look_at(eye, target, up=(0.0, 1.0, 0.0)) -> np.ndarray:
    eye = np.asarray(eye, dtype=np.float64)
    f = np.asarray(target, dtype=np.float64) - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def gl_bytes(m: np.ndarray) -> bytes:
    return m.T.astype("f4").tobytes()
```

**File:** `src/gfx/meshes.py` (create or replace the whole file)

```python
"""Low-poly prop meshes, in metres, as flat-shaded triangle lists: (N, 9) float32 rows of
position, face normal and colour. The base sits slightly below y = 0 so props never float."""

import math

import numpy as np

from chunkgen import PEBBLE, ROCK_PROP, TREE, TUFT

TRUNK = (0.40, 0.28, 0.17)
LEAVES = (0.17, 0.36, 0.16)
STONE = (0.55, 0.54, 0.51)
BLADE = (0.42, 0.62, 0.28)


def _faces(tris, colour) -> np.ndarray:
    rows = []
    for a, b, c in tris:
        a, b, c = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n) or 1.0
        rows += [(*p, *n, *colour) for p in (a, b, c)]
    return np.array(rows, dtype=np.float32)


def _ring(radius, y, sides=6, turn=0.0):
    return [(radius * math.cos(2 * math.pi * i / sides + turn), y, radius * math.sin(2 * math.pi * i / sides + turn))
            for i in range(sides)]


def _cone(radius, y0, y1, sides=6, turn=0.0):
    ring = _ring(radius, y0, sides, turn)
    tip = (0.0, y1, 0.0)
    return [(ring[i], tip, ring[(i + 1) % sides]) for i in range(sides)]


def tree() -> np.ndarray:
    lo, hi = _ring(0.18, -0.2), _ring(0.14, 2.0)
    trunk = []
    for i in range(6):
        j = (i + 1) % 6
        trunk += [(lo[i], hi[i], lo[j]), (lo[j], hi[i], hi[j])]
    leaves = _cone(1.7, 1.5, 5.2, 7) + _cone(1.2, 3.6, 7.2, 7, 0.4)
    return np.concatenate([_faces(trunk, TRUNK), _faces(leaves, LEAVES)])


def _icosahedron():
    t = (1 + math.sqrt(5)) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
         (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
         (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v[0]), f


def rock(radius=0.6, squash=0.6, colour=STONE) -> np.ndarray:
    v, f = _icosahedron()
    jitter = 1 + 0.18 * np.sin(np.arange(len(v)) * 2.39996)  # fixed, so every rock mesh is the same
    v = v * jitter[:, None] * radius
    v[:, 1] = v[:, 1] * squash + radius * squash * 0.55
    return _faces([(v[a], v[b], v[c]) for a, b, c in f], colour)


def tuft() -> np.ndarray:
    tris = []
    for k in range(3):
        a = math.pi * k / 3
        dx, dz = 0.04 * math.cos(a), 0.04 * math.sin(a)
        p0, p1 = (-dx, -0.01, -dz), (dx, -0.01, dz)
        top = (0.01 * math.sin(a), 0.14, 0.01 * math.cos(a))
        tris += [(p0, top, p1), (p1, top, p0)]
    return _faces(tris, BLADE)


def pebble() -> np.ndarray:
    return rock(radius=0.05, squash=0.5)


MESHES = {TREE: tree, ROCK_PROP: rock, TUFT: tuft, PEBBLE: pebble}
```

**File:** `src/gfx/shaders/hex.glsl` (create or replace the whole file)

```glsl
// Hex addressing in the shader: the same integer maths as hexaddr.py.
// Positions are metres relative to the origin shaku O (the loader focus). For each level L the
// origin is split as O = SCALE[L] * u_k[L] + u_m[L], so rounding stays in small numbers.

const int PACK[4] = int[4](1, 6, 60, 36);
const float SCALE[4] = float[4](1.0, 6.0, 360.0, 12960.0);
const float SHAKU_M = 10.0 / 33.0;
const float SQ3 = 1.7320508075688772;
const ivec2 DIRS[6] = ivec2[6](ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, 0), ivec2(-1, 1), ivec2(0, 1));
const int WORLD_RADIUS = 12;

uniform ivec2 u_k[4];
uniform ivec2 u_m[4];

vec2 shaku_axial(vec2 xz) {
    float r = xz.y / (SQ3 * 0.5 * SHAKU_M);
    return vec2(xz.x / SHAKU_M - r * 0.5, r);
}

ivec2 hex_round(vec2 f) {
    float fs = -f.x - f.y;
    float q = floor(f.x + 0.5);
    float r = floor(f.y + 0.5);
    float s = floor(fs + 0.5);
    float dq = abs(q - f.x);
    float dr = abs(r - f.y);
    float ds = abs(s - fs);
    if (dq > dr && dq > ds) {
        q = -r - s;
    } else if (dr > ds) {
        r = -q - s;
    }
    return ivec2(int(q), int(r));
}

// Fractional axial position at level L, relative to the level-L cell u_k[L].
vec2 level_frac(vec2 xz, int L) {
    return (vec2(u_m[L]) + shaku_axial(xz)) / SCALE[L];
}

ivec2 round_at(vec2 xz, int L) {
    return hex_round(level_frac(xz, L)) + u_k[L];
}

int d2(ivec2 d) {
    return d.x * d.x + d.x * d.y + d.y * d.y;
}

// The parent (on the lattice scaled by n) that owns a child: nearest centre, ties to the
// lexicographically greatest parent.
ivec2 owner(ivec2 c, int n) {
    ivec2 a0 = ivec2(floor(vec2(c) / float(n) + 0.5));
    ivec2 best = a0;
    int best_d = 2147483647;
    for (int i = -1; i <= 1; ++i) {
        for (int j = -1; j <= 1; ++j) {
            ivec2 a = a0 + ivec2(i, j);
            int d = d2(c - n * a);
            if (d < best_d || (d == best_d && (a.x > best.x || (a.x == best.x && a.y > best.y)))) {
                best = a;
                best_d = d;
            }
        }
    }
    return best;
}

ivec2 up(ivec2 c, int from_level, int to_level) {
    for (int L = from_level; L < to_level; ++L) {
        c = owner(c, PACK[L + 1]);
    }
    return c;
}

int hex_len(ivec2 c) {
    return (abs(c.x) + abs(c.y) + abs(c.x + c.y)) / 2;
}
```

**File:** `src/gfx/shaders/terrain.vert` (create or replace the whole file)

```glsl
#version 330 core

// One chunk of one tier. Heights blend into the coarser tier's mesh (in_hc) between u_morph.x and
// u_morph.y metres from the loader focus (the origin), so tiers meet without cracks.

in vec2 in_pos;     // metres, relative to the chunk's parent centre
in float in_h;      // this tier's height
in float in_hc;     // the coarser tier's mesh height here
in vec3 in_col;

uniform mat4 u_viewproj;
uniform vec2 u_offset;   // chunk parent centre, relative to the origin
uniform vec2 u_morph;    // start, end (end <= start: no morph)

out vec3 v_rel;
out vec3 v_col;

void main() {
    vec2 xz = in_pos + u_offset;
    float w = u_morph.y > u_morph.x ? smoothstep(u_morph.x, u_morph.y, length(xz)) : 0.0;
    v_rel = vec3(xz.x, mix(in_h, in_hc, w), xz.y);
    v_col = in_col;
    gl_Position = u_viewproj * vec4(v_rel, 1.0);
}
```

**File:** `src/gfx/shaders/terrain.frag` (create or replace the whole file)

```glsl
#version 330 core

#include "hex.glsl"

// A chunk draws exactly the pixels its parent owns (as its tier sees them), minus the pixels a
// finer tier draws, and outlines every cell border at the resolution of its own tier.

in vec3 v_rel;
in vec3 v_col;
out vec4 f_color;

uniform int u_level;        // the tier: level of this chunk's cells
uniform ivec2 u_parent;     // the chunk's parent cell (level u_level + 1)
uniform ivec2 u_lc[4];      // centre cell of each loaded-children texture (levels 1..3)
uniform usampler2D u_loaded1;
uniform usampler2D u_loaded2;
uniform usampler2D u_loaded3;
uniform vec3 u_eye;
uniform vec3 u_sun;
uniform vec3 u_fog_col;
uniform float u_fog_dist;
uniform int u_debug;        // 0 normal, 1 owner id at u_debug_level, 2 flat grey with lines
uniform int u_debug_level;
uniform ivec2 u_debug_base;

const vec3 LINE_COL[4] = vec3[4](vec3(0.08, 0.08, 0.06), vec3(0.95, 0.95, 0.88), vec3(1.0, 0.82, 0.15), vec3(0.9, 0.12, 0.08));
const float LINE_ALPHA[4] = float[4](0.45, 0.55, 0.85, 1.0);
const float LINE_HALF_PX[4] = float[4](0.5, 0.6, 1.0, 1.6);

// Has this level-L cell got its children loaded (so a finer tier draws there)?
bool children_loaded(int L, ivec2 cell) {
    ivec2 o = cell - u_lc[L] + ivec2(4);
    if (any(lessThan(o, ivec2(0))) || any(greaterThan(o, ivec2(8)))) {
        return false;
    }
    uint v;
    if (L == 1) {
        v = texelFetch(u_loaded1, o, 0).r;
    } else if (L == 2) {
        v = texelFetch(u_loaded2, o, 0).r;
    } else {
        v = texelFetch(u_loaded3, o, 0).r;
    }
    return v != 0u;
}

void main() {
    vec2 p = v_rel.xz;
    int c = u_level;

    // Nearest edge of this tier's cell. Derivatives are taken here, before any discard, while
    // every pixel of the 2x2 quad is still running.
    vec2 f = level_frac(p, c);
    ivec2 cr = hex_round(f);
    vec2 d = f - vec2(cr);
    vec2 dp = vec2(d.x + 0.5 * d.y, SQ3 * 0.5 * d.y);
    int bi = 0;
    float bp = -1.0;
    vec2 normal = vec2(1.0, 0.0);  // unit normal of the nearest edge, in world x/z
    for (int i = 0; i < 6; ++i) {
        vec2 u = vec2(float(DIRS[i].x) + 0.5 * float(DIRS[i].y), SQ3 * 0.5 * float(DIRS[i].y));
        float pr = dot(dp, u);
        if (pr > bp) {
            bp = pr;
            bi = i;
            normal = u;
        }
    }
    float cell_m = SCALE[c] * SHAKU_M;
    float edge_m = (0.5 - bp) * cell_m;
    vec3 dx = dFdx(v_rel);
    vec3 dy = dFdy(v_rel);
    // metres per pixel across the edge: the pixel footprint projected on the edge normal
    float edge_fw = max(abs(dot(dx.xz, normal)) + abs(dot(dy.xz, normal)), 1e-6);
    float px_mean = max(sqrt(length(dx.xz) * length(dy.xz)), 1e-6);

    if (c < 3) {
        if (owner(round_at(p, c), PACK[c + 1]) != u_parent) discard;
    } else if (hex_len(round_at(p, 3)) > WORLD_RADIUS) {
        discard;
    }
    if (c > 0 && children_loaded(c, owner(round_at(p, c - 1), PACK[c]))) discard;

    if (u_debug == 1) {
        ivec2 id = up(round_at(p, c), c, u_debug_level) - u_debug_base;
        f_color = vec4(float(id.x & 255) / 255.0, float(id.y & 255) / 255.0, float(c) / 3.0, 1.0);
        return;
    }

    // the highest level whose border this edge is
    ivec2 a = cr + u_k[c];
    ivec2 b = a + DIRS[bi];
    int top = c;
    for (int L = c; L < 3; ++L) {
        a = owner(a, PACK[L + 1]);
        b = owner(b, PACK[L + 1]);
        if (a != b) top = L + 1;
    }
    float line = 1.0 - smoothstep(LINE_HALF_PX[top] - 0.5, LINE_HALF_PX[top] + 0.5, edge_m / edge_fw);
    if (top == c) {
        line *= smoothstep(4.0, 10.0, cell_m / px_mean);  // fade a tier's own grid when its cells get tiny
    }
    // no border lines where the bordered cells are only a few pixels deep on screen
    line *= smoothstep(6.0, 16.0, SCALE[top] * SHAKU_M / edge_fw);
    line *= LINE_ALPHA[top];

    if (u_debug == 2) {
        f_color = vec4(mix(vec3(0.5), LINE_COL[top], line), 1.0);
        return;
    }

    vec3 n = normalize(cross(dx, dy));
    if (n.y < 0.0) n = -n;
    float light = 0.45 + 0.55 * max(dot(n, u_sun), 0.0);
    vec3 col = mix(v_col * light, LINE_COL[top], line);
    float fog = 1.0 - exp(-length(v_rel - u_eye) / u_fog_dist);
    f_color = vec4(mix(col, u_fog_col, fog), 1.0);
}
```

**File:** `src/gfx/shaders/prop.vert` (create or replace the whole file)

```glsl
#version 330 core

// Instanced props. A prop stands on whichever ground is drawn under it: the shaku tier if its ken
// has shaku loaded (or it is a shaku detail), else the ken tier; each blends like the terrain.

in vec3 in_vert;
in vec3 in_normal;
in vec3 in_vcol;
in vec4 i_a;    // x, z (relative to the chunk parent centre), h_full, h_mid
in vec4 i_b;    // h_far, scale, yaw, tint
in vec2 i_cell; // the prop's ken

uniform mat4 u_viewproj;
uniform vec2 u_offset;
uniform vec2 u_morph_fine;   // the shaku tier's morph range
uniform vec2 u_morph_mid;    // the ken tier's morph range
uniform int u_detail;        // 1: a shaku detail (always on the shaku tier)
uniform usampler2D u_loaded1;
uniform ivec2 u_lc1;

out vec3 v_rel;
out vec3 v_n;
out vec3 v_col;

float morph(vec2 range, float d) {
    return range.y > range.x ? smoothstep(range.x, range.y, d) : 0.0;
}

bool shaku_loaded(ivec2 ken) {
    ivec2 o = ken - u_lc1 + ivec2(4);
    if (any(lessThan(o, ivec2(0))) || any(greaterThan(o, ivec2(8)))) {
        return false;
    }
    return texelFetch(u_loaded1, o, 0).r != 0u;
}

void main() {
    vec2 xz = i_a.xy + u_offset;
    float d = length(xz);
    float ground;
    if (u_detail == 1 || shaku_loaded(ivec2(round(i_cell)))) {
        ground = mix(i_a.z, i_a.w, morph(u_morph_fine, d));
    } else {
        ground = mix(i_a.w, i_b.x, morph(u_morph_mid, d));
    }
    float c = cos(i_b.z);
    float s = sin(i_b.z);
    vec3 v = in_vert * i_b.y;
    v = vec3(c * v.x - s * v.z, v.y, s * v.x + c * v.z);
    v_n = vec3(c * in_normal.x - s * in_normal.z, in_normal.y, s * in_normal.x + c * in_normal.z);
    v_col = in_vcol * i_b.w;
    v_rel = vec3(xz.x, ground, xz.y) + v;
    gl_Position = u_viewproj * vec4(v_rel, 1.0);
}
```

**File:** `src/gfx/shaders/prop.frag` (create or replace the whole file)

```glsl
#version 330 core

in vec3 v_rel;
in vec3 v_n;
in vec3 v_col;
out vec4 f_color;

uniform vec3 u_eye;
uniform vec3 u_sun;
uniform vec3 u_fog_col;
uniform float u_fog_dist;

void main() {
    float light = 0.45 + 0.55 * max(dot(normalize(v_n), u_sun), 0.0);
    float fog = 1.0 - exp(-length(v_rel - u_eye) / u_fog_dist);
    f_color = vec4(mix(v_col * light, u_fog_col, fog), 1.0);
}
```

**File:** `src/gfx/shaders/sky.vert` (create or replace the whole file)

```glsl
#version 330 core

// One triangle covering the viewport; the fragment shader turns each pixel into a view ray.

out vec2 v_ndc;

void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2)) * 2.0 - 1.0;
    v_ndc = p;
    gl_Position = vec4(p, 0.0, 1.0);
}
```

**File:** `src/gfx/shaders/sky.frag` (create or replace the whole file)

```glsl
#version 330 core

in vec2 v_ndc;
out vec4 f_color;

uniform mat4 u_inv_viewproj;
uniform vec3 u_eye;
uniform vec3 u_fog_col;      // the horizon
uniform vec3 u_zenith_col;

void main() {
    vec4 far = u_inv_viewproj * vec4(v_ndc, 1.0, 1.0);
    vec3 dir = normalize(far.xyz / far.w - u_eye);
    float up = clamp(dir.y, 0.0, 1.0);
    f_color = vec4(mix(u_fog_col, u_zenith_col, pow(up, 0.6)), 1.0);
}
```

**File:** `src/gfx/shaders/panel.vert` (create or replace the whole file)

```glsl
#version 330 core

// The side panel: one triangle covering the panel viewport, sampling the pygame surface.

out vec2 v_uv;

void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    v_uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
```

**File:** `src/gfx/shaders/panel.frag` (create or replace the whole file)

```glsl
#version 330 core

in vec2 v_uv;
out vec4 f_color;

uniform sampler2D u_panel;

void main() {
    f_color = texture(u_panel, v_uv);
}
```

**File:** `src/gfx/renderer.py` (create or replace the whole file)

```python
"""Drawing the loaded world with moderngl: sky, terrain chunks, instanced props, and the panel.

Everything is drawn relative to the origin shaku (the loader focus), so the GPU only sees small
numbers. The renderer hears about chunks through load_chunk / unload_chunk.
"""

from dataclasses import dataclass
from pathlib import Path

import moderngl
import numpy as np

from chunkgen import PEBBLE, TUFT, morph_range
from gfx.matrices import gl_bytes, look_at, perspective
from gfx.meshes import MESHES
from hexaddr import KEN, RI, SCALE, SHAKU, Tile, axial_to_metres, up

WINDOW_SIZE = (1600, 900)
VIEW_SIZE = (1180, 900)
PANEL_SIZE = (420, 900)
FOV_Y_DEG = 60.0
NEAR_M, FAR_M = 0.5, 120000.0
SUN = tuple(np.array((0.4, 0.8, 0.3)) / np.linalg.norm((0.4, 0.8, 0.3)))
FOG_COL = (0.72, 0.80, 0.88)
ZENITH_COL = (0.32, 0.52, 0.82)
FOG_DIST_M = 30000.0
LOOKUP_RADIUS = 4  # the loaded-children textures cover the camera's cell +- 4 at each level
SHADERS = Path(__file__).parent / "shaders"


def shader_source(name: str) -> str:
    text = (SHADERS / name).read_text()
    return text.replace('#include "hex.glsl"', (SHADERS / "hex.glsl").read_text())


def split_origin(origin: Tile) -> tuple[list, list]:
    """origin = SCALE[L] * k[L] + m[L] per level, with 0 <= m < SCALE[L]."""
    ks, ms = [], []
    for s in SCALE:
        k = (origin[0] // s, origin[1] // s)
        ks.append(k)
        ms.append((origin[0] - s * k[0], origin[1] - s * k[1]))
    return ks, ms


@dataclass
class View:
    origin: Tile                         # the loader focus (global shaku)
    eye: tuple[float, float, float]      # world metres
    target: tuple[float, float, float]   # world metres
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)
    projection: np.ndarray | None = None  # default: the perspective camera


@dataclass
class ChunkGPU:
    level: int
    parent: Tile
    origin: tuple[float, float]
    vao: moderngl.VertexArray
    buffers: list
    props: list  # (kind, vao, instance count)


class Renderer:
    def __init__(self, ctx: moderngl.Context, target: moderngl.Framebuffer):
        self.ctx = ctx
        self.target = target
        self.terrain = ctx.program(vertex_shader=shader_source("terrain.vert"),
                                   fragment_shader=shader_source("terrain.frag"))
        self.prop = ctx.program(vertex_shader=shader_source("prop.vert"), fragment_shader=shader_source("prop.frag"))
        self.sky = ctx.program(vertex_shader=shader_source("sky.vert"), fragment_shader=shader_source("sky.frag"))
        self.panel = ctx.program(vertex_shader=shader_source("panel.vert"), fragment_shader=shader_source("panel.frag"))
        self.empty = ctx.vertex_array(self.sky, [])
        self.panel_vao = ctx.vertex_array(self.panel, [])
        self.mesh_vbos = {kind: ctx.buffer(make().tobytes()) for kind, make in MESHES.items()}
        size = 2 * LOOKUP_RADIUS + 1
        self.lookup = {level: ctx.texture((size, size), 1, dtype="u1") for level in (1, 2, 3)}
        for tex in self.lookup.values():
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.panel_tex = ctx.texture(PANEL_SIZE, 4)
        self.chunks: dict = {}
        self.debug = 0          # 0 normal, 1 owner ids, 2 flat grey with lines
        self.debug_level = 0
        self.debug_base = (0, 0)
        self.terrain["u_loaded1"] = 1
        self.terrain["u_loaded2"] = 2
        self.terrain["u_loaded3"] = 3
        self.prop["u_loaded1"] = 1

    # --- chunks -------------------------------------------------------------------------------

    def load_chunk(self, chunk) -> None:
        vbo = self.ctx.buffer(chunk.vertices.tobytes())
        ibo = self.ctx.buffer(chunk.triangles.tobytes())
        vao = self.ctx.vertex_array(self.terrain, [(vbo, "2f 1f 1f 3f", "in_pos", "in_h", "in_hc", "in_col")],
                                    index_buffer=ibo, index_element_size=4)
        buffers = [vbo, ibo]
        props = []
        for kind, rows in chunk.props.items():
            if len(rows) == 0:
                continue
            inst = self.ctx.buffer(np.ascontiguousarray(rows).tobytes())
            buffers.append(inst)
            pvao = self.ctx.vertex_array(self.prop, [
                (self.mesh_vbos[kind], "3f 3f 3f", "in_vert", "in_normal", "in_vcol"),
                (inst, "4f 4f 2f/i", "i_a", "i_b", "i_cell"),
            ])
            props.append((kind, pvao, len(rows)))
        self.chunks[chunk.key] = ChunkGPU(chunk.level, chunk.parent, chunk.origin, vao, buffers, props)

    def unload_chunk(self, chunk) -> None:
        gpu = self.chunks.pop(chunk.key, None)
        if gpu is None:
            return
        gpu.vao.release()
        for _, pvao, _ in gpu.props:
            pvao.release()
        for b in gpu.buffers:
            b.release()

    # --- frame --------------------------------------------------------------------------------

    def upload_panel(self, surface) -> None:
        import pygame
        self.panel_tex.write(pygame.image.tobytes(surface, "RGBA", True))

    def draw(self, view: View, draw_panel: bool = True) -> None:
        ctx = self.ctx
        ox, oz = axial_to_metres(*view.origin)
        eye = (view.eye[0] - ox, view.eye[1], view.eye[2] - oz)
        target = (view.target[0] - ox, view.target[1], view.target[2] - oz)
        proj = view.projection
        if proj is None:
            proj = perspective(FOV_Y_DEG, VIEW_SIZE[0] / VIEW_SIZE[1], NEAR_M, FAR_M)
        viewproj = proj @ look_at(eye, target, view.up)
        ks, ms = split_origin(view.origin)
        centres = [up(view.origin, SHAKU, level) for level in range(RI + 1)]
        self._write_lookups(centres)

        self.target.use()
        ctx.viewport = (0, 0, *VIEW_SIZE)
        ctx.clear(*FOG_COL, 1.0, depth=1.0)

        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.sky["u_inv_viewproj"].write(gl_bytes(np.linalg.inv(viewproj)))
        self.sky["u_eye"] = eye
        self.sky["u_fog_col"] = FOG_COL
        self.sky["u_zenith_col"] = ZENITH_COL
        self.empty.render(moderngl.TRIANGLES, vertices=3)

        ctx.enable(moderngl.DEPTH_TEST)
        t = self.terrain
        t["u_viewproj"].write(gl_bytes(viewproj))
        t["u_k"].write(np.array(ks, dtype="i4").tobytes())
        t["u_m"].write(np.array(ms, dtype="i4").tobytes())
        t["u_lc"].write(np.array(centres, dtype="i4").tobytes())
        t["u_eye"] = eye
        t["u_sun"] = SUN
        t["u_fog_col"] = FOG_COL
        t["u_fog_dist"] = FOG_DIST_M
        t["u_debug"] = self.debug
        t["u_debug_level"] = self.debug_level
        t["u_debug_base"] = self.debug_base
        for level, tex in self.lookup.items():
            tex.use(location=level)
        for gpu in self.chunks.values():
            t["u_level"] = gpu.level
            t["u_parent"] = gpu.parent
            t["u_offset"] = (gpu.origin[0] - ox, gpu.origin[1] - oz)
            t["u_morph"] = morph_range(gpu.level)
            gpu.vao.render()

        if self.debug == 0:
            p = self.prop
            p["u_viewproj"].write(gl_bytes(viewproj))
            p["u_morph_fine"] = morph_range(SHAKU)
            p["u_morph_mid"] = morph_range(KEN)
            p["u_lc1"] = centres[1]
            p["u_eye"] = eye
            p["u_sun"] = SUN
            p["u_fog_col"] = FOG_COL
            p["u_fog_dist"] = FOG_DIST_M
            for gpu in self.chunks.values():
                if not gpu.props:
                    continue
                p["u_offset"] = (gpu.origin[0] - ox, gpu.origin[1] - oz)
                for kind, pvao, count in gpu.props:
                    p["u_detail"] = 1 if kind in (TUFT, PEBBLE) else 0
                    pvao.render(instances=count)

        if draw_panel:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.viewport = (VIEW_SIZE[0], 0, *PANEL_SIZE)
            self.panel_tex.use(location=0)
            self.panel["u_panel"] = 0
            self.panel_vao.render(moderngl.TRIANGLES, vertices=3)

    def _write_lookups(self, centres) -> None:
        size = 2 * LOOKUP_RADIUS + 1
        grids = {level: np.zeros((size, size), dtype="u1") for level in self.lookup}
        for level, parent in self.chunks:
            cell_level = level + 1  # the chunk is the children of this cell
            if cell_level not in grids:
                continue
            c = centres[cell_level]
            dq, dr = parent[0] - c[0], parent[1] - c[1]
            if abs(dq) <= LOOKUP_RADIUS and abs(dr) <= LOOKUP_RADIUS:
                grids[cell_level][dr + LOOKUP_RADIUS, dq + LOOKUP_RADIUS] = 1
        for level, grid in grids.items():
            self.lookup[level].write(grid.tobytes())

    def read_rgb(self, viewport=None) -> np.ndarray:
        """The target's pixels as an (H, W, 3) uint8 array, top row first."""
        viewport = viewport or (0, 0, *WINDOW_SIZE)
        data = self.target.read(viewport=viewport, components=3)
        w, h = viewport[2], viewport[3]
        return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)[::-1]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **95 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/gfx experiments/exp-03/tests/test_gfx.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: moderngl renderer: tiered terrain, borders, props, sky

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

### Task 9: The panel and the main loop

**Files:**
- Create: `src/gfx/panel.py`, `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `gfx.panel.PanelInfo` (dataclass: `focus`, `position`, `lap_fraction`, `sim_seconds`, `tiers`, `loaded`, `queued`, `loaders`, `fps`, `frame_ms`, `seed`, `paused`), `gfx.panel.Panel` with `draw(info) -> pygame.Surface`
  - `main.parse_args(argv)` (`--frames`, `--seed`, `--start`, `--no-preload`, `--screenshot-dir`, `--screenshot-every`), `main.main(argv)`, `main.save_screenshot(renderer, path)`, `main.DT`

- [ ] **Step 1: Write the failing tests**

**File:** `tests/test_main.py` (create or replace the whole file)

```python
import pytest


def test_parse_args_defaults():
    import main

    args = main.parse_args([])
    assert (args.frames, args.seed, args.start, args.no_preload, args.screenshot_dir, args.screenshot_every) == (
        0, 0, 0.0, False, None, 60
    )
    assert main.parse_args(["--start", "90.5", "--no-preload"]).start == 90.5


@pytest.mark.parametrize("extra", [[], ["--no-preload", "--start", "600"]])
def test_headless_run_saves_screenshots(tmp_path, monkeypatch, extra):
    pytest.importorskip("moderngl")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import main

    try:
        main.main(["--frames", "120", "--screenshot-dir", str(tmp_path), "--screenshot-every", "60", *extra])
    except Exception as exc:  # no EGL / GPU here
        if "EGL" in str(exc) or "context" in str(exc).lower():
            pytest.skip(f"no GL context: {exc}")
        raise
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frame_00060.png", "frame_00120.png"]
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: a `ModuleNotFoundError` for the module this task creates. A test file that imports it at the top is a collection error, which stops the run; Task 9's `test_main.py` imports `main` inside its tests, so there the new tests fail and the other 95 pass.


- [ ] **Step 3: Write the implementation**

**File:** `src/gfx/panel.py` (create or replace the whole file)

```python
"""The side panel, drawn with pygame onto a 420 x 900 surface (ASCII text only)."""

import math
from dataclasses import dataclass

import pygame

from hexaddr import (
    CHO, KEN, LEVEL_NAMES, SHAKU, WINDOW_RINGS, Tile, address, axial_to_metres, format_address,
    metres_to_axial, up, window,
)

COLORS = {
    "panel": (24, 26, 32),
    "edge": (60, 64, 76),
    "title": (236, 238, 242),
    "head": (150, 190, 255),
    "text": (214, 218, 226),
    "dim": (130, 136, 150),
    "loaded": (86, 160, 98),
    "queued": (214, 170, 60),
    "missing": (54, 58, 68),
    "camera": (255, 255, 255),
}
LINE = 19


@dataclass
class PanelInfo:
    focus: Tile                              # the camera's global shaku
    position: tuple[float, float, float]     # focus point, world metres
    lap_fraction: float
    sim_seconds: float
    tiers: list                              # ChunkStore.summary()
    loaded: set                              # chunk keys loaded
    queued: set                              # chunk keys queued
    loaders: list                            # Loader objects
    fps: float
    frame_ms: float
    seed: int
    paused: bool


class Panel:
    def __init__(self, size=(420, 900)):
        self.surface = pygame.Surface(size)
        self.font = pygame.font.Font(None, 22)
        self.small = pygame.font.Font(None, 18)

    def draw(self, info: PanelInfo) -> pygame.Surface:
        s = self.surface
        s.fill(COLORS["panel"])
        pygame.draw.line(s, COLORS["edge"], (0, 0), (0, s.get_height()), 2)
        y = 12
        y = self._text("MURABITO EXP-03  tiered hex world", 14, y, "title", self.font) + 6

        y = self._head("CAMERA", y)
        addr = format_address(address(info.focus)).split(" / ")
        y = self._text(f"{addr[0]}   {addr[1]}", 14, y)
        y = self._text(f"{addr[2]}   {addr[3]}", 14, y)
        x, h, z = info.position
        y = self._text(f"x {x:10.1f} m   z {z:10.1f} m   h {h:7.1f} m", 14, y)
        t = int(info.sim_seconds)
        state = "   PAUSED" if info.paused else ""
        y = self._text(f"lap {100 * info.lap_fraction:6.3f} %   t {t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"
                       f"   seed {info.seed}{state}", 14, y) + 6

        y = self._head("TIERS", y)
        y = self._text("tier     chunks    cells     tris   +/s  -/s   gen ms  queue", 14, y, "dim", self.small)
        for name, stats, loads, unloads in info.tiers:
            y = self._text(f"{name:<6} {stats.chunks:>6} {stats.cells:>8} {stats.triangles:>8} {loads:>5} {unloads:>4}"
                           f" {stats.gen_ms_mean:>8.1f} {stats.queued:>6}", 14, y, "text", self.small)
        y += 8

        y = self._head("NEIGHBOURHOOD", y)
        y = self._text("windows: loaded / queued / not loaded; white = camera's cell", 14, y, "dim", self.small)
        for i, level in enumerate((SHAKU, KEN, CHO)):
            self._window_diagram(info, level, 14 + i * 134, y + 4)
        y += 150

        y = self._head("LOADERS", y)
        for loader in info.loaders:
            y = self._text(f"{loader.name}: focus shaku {loader.focus}", 14, y)
            y = self._text("  37 ken -> shaku, 37 cho -> ken, 37 ri -> cho, world -> ri", 14, y, "dim", self.small)
        y += 6

        y = self._head("FRAME", y)
        self._text(f"{info.fps:5.1f} fps   {info.frame_ms:5.1f} ms", 14, y)
        return s

    def _window_diagram(self, info: PanelInfo, level: int, x0: int, y0: int) -> None:
        """The loader's window at one tier: the parent cells (level + 1) around the camera."""
        parent_level = level + 1
        centre = up(info.focus, SHAKU, parent_level)
        size = 9.5  # hex corner radius, px
        cx, cy = x0 + 60, y0 + 70
        s = self.surface
        for cell in window(centre, WINDOW_RINGS):
            dq, dr = cell[0] - centre[0], cell[1] - centre[1]
            px = cx + math.sqrt(3) * size * (dq + dr / 2)
            py = cy - 1.5 * size * dr
            key = (level, cell)
            state = "loaded" if key in info.loaded else "queued" if key in info.queued else "missing"
            colour = COLORS[state]
            pts = [(px + size * 0.95 * math.cos(math.radians(30 + 60 * i)),
                    py + size * 0.95 * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
            pygame.draw.polygon(s, colour, pts)
            if cell == centre:
                pygame.draw.polygon(s, COLORS["camera"], pts, 2)
        # the camera inside its cell
        fx, fz = axial_to_metres(*info.focus)
        fq, fr = metres_to_axial(fx, fz, parent_level)
        dq, dr = fq - centre[0], fr - centre[1]
        pygame.draw.circle(s, COLORS["camera"], (cx + math.sqrt(3) * size * (dq + dr / 2), cy - 1.5 * size * dr), 2)
        label = f"{LEVEL_NAMES[parent_level]} -> {LEVEL_NAMES[level]}"
        s.blit(self.small.render(label, True, COLORS["dim"]), (x0 + 22, y0 + 130))

    def _head(self, text: str, y: int) -> int:
        return self._text(text, 14, y, "head", self.font)

    def _text(self, text: str, x: int, y: int, colour: str = "text", font=None) -> int:
        self.surface.blit((font or self.font).render(text, True, COLORS[colour]), (x, y))
        return y + LINE

```

**File:** `src/main.py` (create or replace the whole file)

```python
"""exp-03 entry point. Run from experiments/exp-03: `uv run src/main.py`."""

import argparse
import time
from pathlib import Path

import numpy as np
import pygame

from chunkgen import generate_chunk
from gfx import context
from gfx.panel import Panel, PanelInfo
from gfx.renderer import WINDOW_SIZE, Renderer, View
from loading import ChunkStore, Loader
from rail import Rail
from terrain import ground_height

DT = 1 / 60
MAX_FRAME_TIME = 0.25  # avoid a catch-up spiral after a stall
PANEL_EVERY = 6        # frames between panel redraws


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="MuraBito exp-03: tiered hex world")
    parser.add_argument("--frames", type=int, default=0,
                        help="exit after N frames (0 = run until quit); each frame advances one fixed tick")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--start", type=float, default=0.0, help="begin S seconds along the rail")
    parser.add_argument("--no-preload", action="store_true", help="skip loading everything before the first frame")
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--screenshot-every", type=int, default=60)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    pygame.init()
    ctx, target = context.create(WINDOW_SIZE, "MuraBito exp-03")
    renderer = Renderer(ctx, target)
    panel = Panel()
    store = ChunkStore(lambda level, parent: generate_chunk(level, parent, args.seed),
                       on_load=renderer.load_chunk, on_unload=renderer.unload_chunk)
    rail = Rail(lambda x, z: ground_height(x, z, args.seed), start=args.start)
    camera = Loader("camera", rail.focus_shaku)
    if not args.no_preload:
        store.drain([camera])
    clock = pygame.time.Clock()
    paused = False
    accumulator = 0.0
    frame = 0
    frame_ms = 0.0
    if args.screenshot_dir is not None:
        args.screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_SPACE:
                        paused = not paused

            started = time.perf_counter()
            # Headless runs are deterministic: one fixed frame time, no waiting on the clock.
            frame_time = DT if args.frames else min(clock.tick(60) / 1000, MAX_FRAME_TIME)
            if not paused:
                accumulator += frame_time
                while accumulator >= DT:
                    rail.advance(DT)
                    accumulator -= DT
            camera.focus = rail.focus_shaku
            store.update([camera])

            if frame % PANEL_EVERY == 0:
                renderer.upload_panel(panel.draw(PanelInfo(
                    focus=camera.focus, position=rail.focus, lap_fraction=rail.lap_fraction,
                    sim_seconds=rail.t - args.start, tiers=store.summary(), loaded=set(store.loaded),
                    queued=set(store.queue), loaders=[camera], fps=clock.get_fps(), frame_ms=frame_ms,
                    seed=args.seed, paused=paused,
                )))
            renderer.draw(View(origin=camera.focus, eye=rail.eye, target=rail.focus))
            if not context.headless():
                pygame.display.flip()
            frame_ms = (time.perf_counter() - started) * 1000
            frame += 1

            if args.screenshot_dir is not None and frame % args.screenshot_every == 0:
                save_screenshot(renderer, args.screenshot_dir / f"frame_{frame:05d}.png")
            if args.frames and frame >= args.frames:
                return
    finally:
        pygame.quit()


def save_screenshot(renderer: Renderer, path: Path) -> None:
    pixels = np.ascontiguousarray(renderer.read_rgb())
    pygame.image.save(pygame.image.frombuffer(pixels.tobytes(), WINDOW_SIZE, "RGB"), str(path))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **98 passed**.


- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/exp-03/src/gfx/panel.py experiments/exp-03/src/main.py experiments/exp-03/tests/test_main.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: the stats panel and the main loop

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.

---

**After the commit, check the app by eye (not a test):**

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 120 --start 1200 --screenshot-dir screenshots --screenshot-every 120
```

Open `screenshots/frame_00120.png`. Expected: a jogging-height view over dirt with rocks, the small shaku hexes of the shaku window with ken borders battlementing through them, a yellow cho border, the rim mountains on the horizon, and the panel on the right showing 1332 / 133200 / 47952 / 469 cells. `screenshots/` is gitignored.

---

### Task 10: Docs: manifest, spec amendments, handoff note

**Files:**
- Modify: `experiments/manifest.md` (the exp-03 entry)
- Modify: `experiments/exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md` (append a section)
- Modify: `experiments/exp-03/docs/HANDOFF.md` (prepend a note)

**Interfaces:**
- Consumes: nothing in code.
- Produces: docs only; the test count stays at 98.

- [ ] **Step 1: Replace the exp-03 manifest entry**

**Edit:** `experiments/manifest.md`

Find:

```markdown
## exp-03

- **Started:** 2026-09-18
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd experiments/exp-03 && uv run src/main.py`
- **Test:** `cd experiments/exp-03 && uv run pytest`
- **Design:** not written yet

### Why

Not decided yet.

### What

Starts as a copy of exp-02. What changes is not decided yet.
```

Replace with:

```markdown
## exp-03 — Tiered hex world

- **Started:** 2026-09-18
- **Stack:** Python 3.13 + pygame + moderngl (OpenGL 3.3) + numpy, managed with uv
- **Run:** `cd experiments/exp-03 && uv run src/main.py`
- **Test:** `cd experiments/exp-03 && uv run pytest`
- **Design:** [`exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md`](exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md)

### Why

Groundwork for tiered pathfinding: fine A\* only close in, coarser regions further out. exp-03 builds the hierarchical coordinate system at historical Japanese scale, and a procedural world that loads in tiers of detail around whoever needs it. There is no pathfinding yet. exp-05 will merge this into the exp-00 to exp-02 line.

### What

A new line. From exp-02 it keeps only the scaffolding: the uv project, the shape of the main loop, and the axial hex maths.

- **Units.** shaku (10/33 m, flat to flat), ken = 6 shaku, cho = 60 ken, ri = 36 cho. Every level is a hex grid with the same orientation. A parent owns the children nearest its centre, and split children go to exactly one owner, so every ken owns 36 shaku, every cho 3,600 ken and every ri 1,296 cho. Every position has a `ri / cho / ken / shaku` address.
- **World.** A hexagon of radius 12 ri: about 98 km across and 6,270 km², the size of a typical prefecture. Gentle country with mountains around the rim; grass, dirt, bare rock and snow; woods and clearings; trees, rocks, grass tufts and pebbles.
- **Tiers.** Any loader (for now only the camera) gets shaku detail in its ken plus 3 rings, ken detail in its cho plus 3 rings, cho detail in its ri plus 3 rings, and ri detail across the whole world. A queue loads the chunks nearest first, within a time budget per frame. Each finer tier blends into the coarser one before its window edge, so tiers meet without cracks.
- **View.** A 3D camera on a rail: a circle of radius 4 ri round the world centre at 2.5 m/s, about 11 h per lap. Every tier's cell borders are drawn on the ground. A side panel shows the camera's address, per-tier stats and the load windows.

### Layout

- `src/`: `hexgrid.py` (kept), `hexaddr.py` (units, ownership, addresses), `noise.py`, `terrain.py` (height, ground type, forests), `chunkgeom.py` (chunk templates and meshes), `chunkgen.py` (chunk contents and props), `loading.py` (loaders, windows, the load queue), `rail.py`, `main.py`.
- `src/gfx/`: the moderngl context, the renderer, the GLSL shaders, prop meshes and the panel.
- `tests/`: one file per module. `test_gfx.py` checks the shader's hex maths against `hexaddr` on real renders; it skips itself when no GL context is available.

### Controls

Space pause/resume · Esc quit. The camera cannot be steered.

### Headless

`cd experiments/exp-03 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --seed K --start S --screenshot-dir screenshots --screenshot-every M`. `--no-preload` shows the world loading in; `screenshots/` is gitignored. Headless runs need a GPU driver with EGL.
```

- [ ] **Step 2: Append the amendments to the spec**

Append this at the end of `experiments/exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md`, after the "Out of scope" section (the file ends with a newline; keep exactly one blank line between the sections):

```markdown
## Amendments from planning (2026-09-18)

Found while running the implementation plan's code in a scratchpad. The plan (`docs/plans/2026-09-18-exp-03-tiered-hex-world-plan.md`, "Differences from the spec") has the full list. The behavioural ones:

- **Cracks between tiers: geomorphing, not skirts.** Each vertex also stores the coarser tier's mesh height at its position, and the vertex shader blends toward it between 1.3 and 2.0 parent widths from the loader focus. A loader's window edge is never nearer than 2.26 parent widths (measured at every level), so at every window edge the finer tier matches the coarser mesh exactly. Props blend the same way.
- **The tier partition.** Where tier *t* is drawn, a point belongs to the level-*L* cell `tier_cell(x, z, t, L)`: round to the nearest tier-*t* cell, then take owners upward. At the shaku tier this is exactly the address. Both sides of every handover use the same test, so tiers meet without gaps or overlaps.
- **Chunk meshes** draw every triangle that touches one of the chunk's owned cells; the fragment shader clips them to the owned territory.
- **The load queue** stops before a chunk whose level's mean generation time would take the frame past 8 ms, but always loads at least one. Measured: a median frame of 7.7 ms, and a worst frame of 24 ms at a cho crossing (one ken chunk).
- **Hex lines** get their width from the pixel footprint across the edge. They fade out where the bordered cells are only a few pixels deep, and a tier's own grid fades where its cells get small, so distant borders do not wash over the horizon.
- **Placeholder tuning:** at most 0.05 trees per ken (0.15 made a closed canopy that hid the horizon), forest density `1.8 n - 0.1`, and a dirt threshold of -0.17 (measured 30%).
- **Modules:** `chunkgeom.py` (chunk templates, built once per level) and `chunkgen.py` (chunk contents) are split out of `terrain.py`. `owner` has no numpy twin: templates are computed once from `hexaddr`, because ownership is the same for every parent at a level.
- **Rail start:** the rail starts on the centre of ri (4, 0), heading due north along a column of ken edges, so the shaku window changes many times a second for the first stretch. This is correct behaviour for that alignment, not a bug.
```

- [ ] **Step 3: Mark the handoff note as superseded**

Insert this at the top of `experiments/exp-03/docs/HANDOFF.md`, above the first line (`# exp-03 handoff`):

```markdown
> **Superseded.** exp-03 has since been designed and built on branch `worktree-exp-03-impl` (2026-09-18); this file records the state *before* that work and is kept for history. Current documents: the spec (`docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md`), the plan (`docs/plans/2026-09-18-exp-03-tiered-hex-world-plan.md`) and the exp-03 entry in `experiments/manifest.md`.
```

followed by one blank line.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q` (from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`)
Expected: **98 passed**.

- [ ] **Step 5: Commit**

Run from `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03`:

```bash
pwd
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl rev-parse --abbrev-ref HEAD
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl add experiments/manifest.md experiments/exp-03/docs/specs/2026-09-18-exp-03-tiered-hex-world-design.md experiments/exp-03/docs/HANDOFF.md
git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl commit -m "exp-03: manifest entry, spec amendments, handoff note

Co-Authored-By: <your model name> <noreply@anthropic.com>"
```

`pwd` must print `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-03-impl/experiments/exp-03` and the branch must be `worktree-exp-03-impl`. Use your own model's name in the trailer.
