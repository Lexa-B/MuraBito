# exp-00 StateTree Visualizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pygame window with a hexagon-shaped hex map where one actor, driven by a small UE5-style StateTree, keeps claiming and using UE5-style Smart Objects. A side panel shows its "brain" live.

**Architecture:**
- **Pure-Python core, no pygame:**
  - `hexgrid.py`: hex math;
  - `smartobjects.py`: objects, slots, claims;
  - `world.py`: map and actor;
  - `ai/pathing.py`: A\*;
  - `ai/statetree.py`: the engine;
  - `ai/tasks.py`: tasks and evaluators;
  - `ai/tree_def.py`: the example tree;
  - `layout.py`: the starting map;
  - `sim.py`: wiring.
- **Everything is test-driven with pytest.**
- **A thin pygame layer on top:**
  - `camera.py`: follow camera;
  - `render.py`: world view and brain panel;
  - `main.py`: loop, input, headless screenshot mode.

**Tech Stack:** Python 3.13, pygame 2.6.1, pytest 9, uv.

**Spec:** `Experiments/exp-00/docs/specs/2026-09-17-exp-00-statetree-visualizer-design.md`. Read it before starting any task.

## Global Constraints

- **Paths.** Repo root: `/home/lexa/DevProjects/_GameDev/MuraBito`. Experiment dir: `/home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00`. Work happens on branch `exp-00-impl`.
- **Git.** Every git command uses `git -C /home/lexa/DevProjects/_GameDev/MuraBito ...`; never run a bare `git`. Before each commit, check that `git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD` prints `exp-00-impl`.
- **Shell state doesn't persist between commands.** Every command either `cd`s to an absolute path in the same invocation or uses absolute paths.
- **Python deps: uv only.** Use `uv add` / `uv run`, never `pip` or `uv pip`. No new dependencies are needed.
- **Running tests.** `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest ...`. `pyproject.toml` already sets `pythonpath = ["src"]` and `testpaths = ["tests"]`.
- **Imports.** Modules are imported relative to `src/`: `import hexgrid`, `from ai.statetree import ...`. Never import `src.` anything.
- **No pygame imports** in `hexgrid.py`, `smartobjects.py`, `world.py`, `layout.py`, `sim.py`, `camera.py`, or anything under `src/ai/`.
- **Hex grid.** Pointy-top hexes, axial `(q, r)` coordinates. Map radius 12 (25 tiles across, 469 tiles). `DIRECTIONS` index 0 is E, then counter-clockwise: `((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))`.
- **Zones.** West if `2q + r < 0`, otherwise East.
- **Commit trailer.** Every commit message ends with the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`. Pass it as a second `-m`.
- **Style.** Short module docstrings, and comments only where the why isn't obvious.
- **Rule glyphs.** Log and panel text use ASCII only (`->`, not `→`), because pygame's default font lacks arrows and check marks. The panel draws pass/fail marks as colored circles.

## File Structure

```
Experiments/exp-00/
├─ src/
│  ├─ hexgrid.py        Task 1  axial hex math
│  ├─ smartobjects.py   Task 2  Slot, Interaction, SmartObject, ClaimHandle, SmartObjectSubsystem
│  ├─ world.py          Task 3  World (walls, blocked set, zones), Actor
│  ├─ layout.py         Task 6  starting layout + placeholder interactions
│  ├─ sim.py            Task 6  Sim + build_sim(seed)
│  ├─ camera.py         Task 7  follow camera
│  ├─ render.py         Task 7  world view; Task 8 brain panel
│  ├─ main.py           Task 7  loop, input, --frames/--screenshot-dir headless mode
│  └─ ai/
│     ├─ __init__.py    (exists, empty)
│     ├─ pathing.py     Task 3  astar
│     ├─ statetree.py   Task 4  engine
│     ├─ tasks.py       Task 5  FindAndClaim, MoveTo, Interact, Wait, ZoneEvaluator, release_claim
│     └─ tree_def.py    Task 6  example tree + placeholder rules
└─ tests/
   ├─ test_hexgrid.py       Task 1
   ├─ test_smartobjects.py  Task 2
   ├─ test_world.py         Task 3
   ├─ test_pathing.py       Task 3
   ├─ test_statetree.py     Task 4
   ├─ test_tasks.py         Task 5
   ├─ test_layout.py        Task 6
   ├─ test_tree_def.py      Task 6
   ├─ test_sim.py           Task 6
   └─ test_main.py          Task 7
```

---

### Task 1: Hex grid math

**Files:**
- Create: `Experiments/exp-00/src/hexgrid.py`
- Test: `Experiments/exp-00/tests/test_hexgrid.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Tile = tuple[int, int]`
  - `MAP_RADIUS = 12`
  - `DIRECTIONS: tuple[Tile, ...]`
  - `add(a: Tile, b: Tile) -> Tile`
  - `distance(a: Tile, b: Tile) -> int`
  - `in_bounds(tile: Tile, radius: int = MAP_RADIUS) -> bool`
  - `neighbors(tile: Tile, radius: int = MAP_RADIUS) -> list[Tile]`, returned in `DIRECTIONS` order
  - `all_tiles(radius: int = MAP_RADIUS) -> list[Tile]`
  - `direction_index(from_tile: Tile, to_tile: Tile) -> int`, which raises `ValueError` if the tiles aren't adjacent

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_hexgrid.py`:

```python
import pytest

from hexgrid import DIRECTIONS, add, all_tiles, direction_index, distance, in_bounds, neighbors


def test_map_has_469_tiles():
    tiles = all_tiles()
    assert len(tiles) == 469
    assert len(set(tiles)) == 469
    assert all(in_bounds(t) for t in tiles)


def test_interior_tile_has_six_neighbors_in_direction_order():
    assert neighbors((0, 0)) == [add((0, 0), d) for d in DIRECTIONS]


def test_corner_tile_has_three_neighbors():
    assert sorted(neighbors((12, 0))) == sorted([(12, -1), (11, 0), (11, 1)])


def test_edge_tile_has_four_neighbors():
    assert sorted(neighbors((12, -6))) == sorted([(12, -7), (11, -6), (11, -5), (12, -5)])


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ((0, 0), (5, 0), 5),    # q axis
        ((0, 0), (0, -4), 4),   # r axis
        ((0, 0), (-3, 3), 3),   # s axis
        ((0, 0), (2, 1), 3),    # off-axis
        ((1, -2), (-2, 3), 5),  # off-axis, neither at origin
    ],
)
def test_distance(a, b, expected):
    assert distance(a, b) == expected
    assert distance(b, a) == expected


def test_in_bounds_rejects_distance_13():
    assert in_bounds((12, 0))
    assert not in_bounds((13, 0))
    assert not in_bounds((0, -13))
    assert not in_bounds((7, 6))  # distance 13, off-axis


def test_direction_index():
    assert direction_index((0, 0), (1, 0)) == 0
    assert direction_index((2, 2), (2, 3)) == 5
    with pytest.raises(ValueError):
        direction_index((0, 0), (2, 0))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_hexgrid.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'hexgrid'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/hexgrid.py`:

```python
"""Axial-coordinate math for a hexagon-shaped map of pointy-top hexes."""

Tile = tuple[int, int]

MAP_RADIUS = 12

# Index 0 is E, then counter-clockwise on screen (screen y grows downward, so "up" is -r).
DIRECTIONS: tuple[Tile, ...] = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def add(a: Tile, b: Tile) -> Tile:
    return (a[0] + b[0], a[1] + b[1])


def distance(a: Tile, b: Tile) -> int:
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def in_bounds(tile: Tile, radius: int = MAP_RADIUS) -> bool:
    return distance(tile, (0, 0)) <= radius


def neighbors(tile: Tile, radius: int = MAP_RADIUS) -> list[Tile]:
    return [n for d in DIRECTIONS if in_bounds(n := add(tile, d), radius)]


def all_tiles(radius: int = MAP_RADIUS) -> list[Tile]:
    return [
        (q, r)
        for q in range(-radius, radius + 1)
        for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1)
    ]


def direction_index(from_tile: Tile, to_tile: Tile) -> int:
    """Index into DIRECTIONS of the step from one tile to an adjacent one."""
    delta = (to_tile[0] - from_tile[0], to_tile[1] - from_tile[1])
    if delta not in DIRECTIONS:
        raise ValueError(f"{from_tile} and {to_tile} are not adjacent")
    return DIRECTIONS.index(delta)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_hexgrid.py -v`
Expected: all PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/hexgrid.py Experiments/exp-00/tests/test_hexgrid.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: hex grid math" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Smart Objects

**Files:**
- Create: `Experiments/exp-00/src/smartobjects.py`
- Test: `Experiments/exp-00/tests/test_smartobjects.py`

**Interfaces:**
- Consumes (Task 1): `Tile` and `distance` from `hexgrid`.
- Produces:
  - `Slot(index: int, tile: Tile, facing: int)`: frozen dataclass; `facing` indexes `hexgrid.DIRECTIONS`.
  - `Interaction(name: str, duration: float, effects: tuple = ())`: frozen dataclass; each effect is `fn(ctx: dict) -> None`.
  - `SmartObject(name: str, tile: Tile, tags: frozenset[str], slots: list[Slot], interactions: list[Interaction])`: dataclass with `eq=False`, so it compares by identity.
  - `ClaimHandle(object: SmartObject, slot: Slot, actor: object)`: frozen dataclass with `eq=False`.
  - `SmartObjectSubsystem`:
    - `.objects: list[SmartObject]`
    - `.register(obj) -> None`
    - `.find(tag_query: set[str] | frozenset[str], near: Tile) -> list[tuple[SmartObject, Slot]]`
    - `.claim(obj, slot, actor) -> ClaimHandle | None`
    - `.release(handle) -> None`
    - `.is_claimed(obj, slot) -> bool`

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_smartobjects.py`:

```python
from smartobjects import Interaction, Slot, SmartObject, SmartObjectSubsystem


def make_object(name, tile, slot_tiles):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, tile=t, facing=0) for i, t in enumerate(slot_tiles)],
        interactions=[Interaction(f"{name}.Short", 1.5)],
    )


def make_subsystem():
    subsystem = SmartObjectSubsystem()
    a = make_object("A", (0, 0), [(1, 0), (-1, 0)])
    b = make_object("B", (6, 0), [(5, 0)])
    subsystem.register(a)
    subsystem.register(b)
    return subsystem, a, b


def test_find_filters_by_tag():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.B"}, near=(0, 0)) == [(b, b.slots[0])]


def test_find_requires_every_tag_in_the_query():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.A", "Something.Else"}, near=(0, 0)) == []


def test_empty_query_matches_every_object():
    subsystem, a, b = make_subsystem()
    assert len(subsystem.find(set(), near=(0, 0))) == 3


def test_find_sorts_by_hex_distance():
    subsystem, a, b = make_subsystem()
    results = subsystem.find(set(), near=(4, 0))
    assert [slot.tile for _, slot in results] == [(5, 0), (1, 0), (-1, 0)]


def test_claimed_slots_are_excluded_from_find():
    subsystem, a, b = make_subsystem()
    subsystem.claim(a, a.slots[0], actor="actor")
    assert subsystem.find({"Object.A"}, near=(0, 0)) == [(a, a.slots[1])]


def test_claiming_a_claimed_slot_returns_none():
    subsystem, a, b = make_subsystem()
    handle = subsystem.claim(a, a.slots[0], actor="actor")
    assert handle is not None
    assert handle.object is a and handle.slot == a.slots[0] and handle.actor == "actor"
    assert subsystem.is_claimed(a, a.slots[0])
    assert subsystem.claim(a, a.slots[0], actor="someone else") is None


def test_release_frees_the_slot_and_is_idempotent():
    subsystem, a, b = make_subsystem()
    handle = subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(handle)
    subsystem.release(handle)
    assert not subsystem.is_claimed(a, a.slots[0])
    assert subsystem.claim(a, a.slots[0], actor="actor") is not None


def test_releasing_a_stale_handle_does_not_free_a_newer_claim():
    subsystem, a, b = make_subsystem()
    old = subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(old)
    subsystem.claim(a, a.slots[0], actor="actor")
    subsystem.release(old)
    assert subsystem.is_claimed(a, a.slots[0])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_smartobjects.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'smartobjects'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/smartobjects.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_smartobjects.py -v`
Expected: all PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/smartobjects.py Experiments/exp-00/tests/test_smartobjects.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: Smart Object subsystem (find, claim, release)" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: World, actor and A\* pathing

**Files:**
- Create: `Experiments/exp-00/src/world.py`
- Create: `Experiments/exp-00/src/ai/pathing.py`
- Test: `Experiments/exp-00/tests/test_world.py`
- Test: `Experiments/exp-00/tests/test_pathing.py`

**Interfaces:**
- Consumes:
  - Task 1: `MAP_RADIUS`, `Tile`, `all_tiles`, `in_bounds`, `distance`, `neighbors`.
  - Task 2: `SmartObject`, `SmartObjectSubsystem`.
- Produces:
  - `World(radius: int = MAP_RADIUS, walls=())`:
    - `.radius`, `.walls: set[Tile]`, `.blocked: set[Tile]`, `.smart_objects: SmartObjectSubsystem`
    - `.add_wall(tile)`
    - `.add_object(obj: SmartObject)`: registers the object and blocks its tile
    - `.is_walkable(tile) -> bool`
    - `.walkable_tiles() -> list[Tile]`
    - `.zone_of(tile) -> "West" | "East"`
  - `Actor(tile: Tile, facing: int = 0, next_tile: Tile | None = None, progress: float = 0.0, speed: float = 3.0)`: a dataclass. `progress` runs 0..1 from `tile` toward `next_tile`; `speed` is in tiles per second.
  - `ai.pathing.astar(world, start: Tile, goals) -> list[Tile] | None`: the path includes both start and goal; returns `None` if unreachable or `goals` is empty.

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_world.py`:

```python
from smartobjects import Slot, SmartObject
from world import Actor, World


def test_zone_west_is_strictly_left_of_center_column():
    world = World()
    assert world.zone_of((-1, 0)) == "West"
    assert world.zone_of((-2, 3)) == "West"
    assert world.zone_of((3, -5)) == "East"


def test_center_column_is_east():
    world = World()
    for tile in [(0, 0), (-1, 2), (1, -2), (-6, 12)]:
        assert world.zone_of(tile) == "East"


def test_walls_objects_and_out_of_bounds_are_not_walkable():
    world = World(walls=[(2, 0)])
    obj = SmartObject("A", (4, 0), frozenset({"Object.A"}), [Slot(0, (3, 0), 0)], [])
    world.add_object(obj)
    assert world.smart_objects.objects == [obj]
    assert not world.is_walkable((2, 0))
    assert not world.is_walkable((4, 0))
    assert not world.is_walkable((13, 0))
    assert world.is_walkable((3, 0))


def test_add_wall_blocks_at_runtime():
    world = World()
    assert world.is_walkable((1, 0))
    world.add_wall((1, 0))
    assert not world.is_walkable((1, 0))
    assert (1, 0) in world.walls


def test_walkable_tiles_excludes_blocked():
    assert len(World(walls=[(0, 0)]).walkable_tiles()) == 468


def test_actor_defaults():
    actor = Actor(tile=(1, 2))
    assert (actor.facing, actor.next_tile, actor.progress, actor.speed) == (0, None, 0.0, 3.0)
```

`Experiments/exp-00/tests/test_pathing.py`:

```python
from ai.pathing import astar
from hexgrid import DIRECTIONS, add, distance
from world import World


def assert_connected(path):
    for a, b in zip(path, path[1:]):
        assert distance(a, b) == 1


def test_straight_path_on_open_map():
    path = astar(World(), (0, 0), {(5, 0)})
    assert path[0] == (0, 0) and path[-1] == (5, 0)
    assert len(path) == distance((0, 0), (5, 0)) + 1
    assert_connected(path)


def test_path_routes_around_a_wall_segment():
    wall = [(0, r) for r in range(-4, 5)]
    world = World(walls=wall)
    path = astar(world, (-3, 0), {(3, 0)})
    assert path is not None
    assert not set(path) & set(wall)
    assert len(path) - 1 > distance((-3, 0), (3, 0))
    assert_connected(path)


def test_unreachable_goal_returns_none():
    goal = (5, 0)
    world = World(walls=[add(goal, d) for d in DIRECTIONS])
    assert astar(world, (0, 0), {goal}) is None


def test_multiple_goals_path_ends_at_nearest():
    path = astar(World(), (0, 0), {(3, 0), (-8, 0)})
    assert path[-1] == (3, 0)


def test_start_already_at_goal():
    assert astar(World(), (2, 2), {(2, 2)}) == [(2, 2)]


def test_empty_goals_returns_none():
    assert astar(World(), (0, 0), set()) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_world.py tests/test_pathing.py -v`
Expected: collection errors, `No module named 'world'` and `No module named 'ai.pathing'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/world.py`:

```python
"""The hex map (walls, objects, zones) and the actor."""

from dataclasses import dataclass

from hexgrid import MAP_RADIUS, Tile, all_tiles, in_bounds
from smartobjects import SmartObject, SmartObjectSubsystem


class World:
    def __init__(self, radius: int = MAP_RADIUS, walls=()):
        self.radius = radius
        self.walls: set[Tile] = set(walls)
        self.smart_objects = SmartObjectSubsystem()
        self.blocked: set[Tile] = set(self.walls)

    def add_wall(self, tile: Tile) -> None:
        self.walls.add(tile)
        self.blocked.add(tile)

    def add_object(self, obj: SmartObject) -> None:
        self.smart_objects.register(obj)
        self.blocked.add(obj.tile)

    def is_walkable(self, tile: Tile) -> bool:
        return in_bounds(tile, self.radius) and tile not in self.blocked

    def walkable_tiles(self) -> list[Tile]:
        return [t for t in all_tiles(self.radius) if t not in self.blocked]

    def zone_of(self, tile: Tile) -> str:
        q, r = tile
        return "West" if 2 * q + r < 0 else "East"


@dataclass
class Actor:
    tile: Tile
    facing: int = 0
    next_tile: Tile | None = None
    progress: float = 0.0  # 0..1 from tile toward next_tile
    speed: float = 3.0  # tiles per second
```

`Experiments/exp-00/src/ai/pathing.py`:

```python
"""A* on the hex grid."""

import heapq

from hexgrid import Tile, distance, neighbors


def astar(world, start: Tile, goals) -> list[Tile] | None:
    """Shortest path from start to the cheapest-to-reach goal, inclusive of both ends."""
    goals = set(goals)
    if not goals:
        return None

    def heuristic(tile: Tile) -> int:
        return min(distance(tile, goal) for goal in goals)

    came_from: dict[Tile, Tile | None] = {start: None}
    cost: dict[Tile, int] = {start: 0}
    counter = 0  # tie-breaker so the heap never compares tiles
    frontier = [(heuristic(start), 0, counter, start)]

    while frontier:
        _, g, _, current = heapq.heappop(frontier)
        if g > cost[current]:
            continue
        if current in goals:
            path = [current]
            while came_from[path[-1]] is not None:
                path.append(came_from[path[-1]])
            return path[::-1]
        for nxt in neighbors(current, world.radius):
            if not world.is_walkable(nxt):
                continue
            new_cost = g + 1
            if new_cost < cost.get(nxt, new_cost + 1):
                cost[nxt] = new_cost
                came_from[nxt] = current
                counter += 1
                heapq.heappush(frontier, (new_cost + heuristic(nxt), new_cost, counter, nxt))
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_world.py tests/test_pathing.py -v`
Expected: all PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/world.py Experiments/exp-00/src/ai/pathing.py Experiments/exp-00/tests/test_world.py Experiments/exp-00/tests/test_pathing.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: world, actor and hex A* pathing" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: StateTree engine

**Files:**
- Create: `Experiments/exp-00/src/ai/statetree.py`
- Test: `Experiments/exp-00/tests/test_statetree.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ROOT = "ROOT"`
  - Enums:
    - `Status.RUNNING` / `.SUCCEEDED` / `.FAILED`, with values `"Running"` / `"Succeeded"` / `"Failed"`
    - `Trigger.ON_COMPLETED` / `.ON_FAILED` / `.ON_CONDITION`
    - `Mode.ALL` / `.ANY`, with values `"all"` / `"any"`
  - `Condition(name: str, test: Callable[[dict], bool])`: has `.last_result: bool | None` and `.evaluate(ctx) -> bool`.
  - `Task` base class: `enter(ctx)`, `tick(ctx, dt) -> Status`, `exit(ctx)`.
  - `Evaluator` base class: `tick(ctx, dt)`.
  - `Transition(trigger: Trigger, target: str, condition: Condition | None = None)`. The target is a state path such as `"GoUse(A)/MoveTo"` or `ROOT`.
  - `State(name, children=(), conditions=(), mode=Mode.ALL, task=None, transitions=(), on_exit=None)`:
    - `.parent` is set by the parent's constructor.
    - `.path` is `""` for root, otherwise names joined with `/` starting from root's child.
    - `.conditions_pass(ctx) -> bool`
    - `.is_at_or_below(other) -> bool`
  - `StateTree(root: State, evaluators=(), log_size=200)`:
    - `.root`, `.evaluators`
    - `.active: list[State]`: the path from root's child down to the leaf; empty means idle
    - `.leaf: State | None`
    - `.last_status: Status | None`
    - `.time: float`
    - `.log: deque[tuple[float, str]]`
    - `.write_log(text)`
    - `.find(path) -> State`: raises `KeyError`
    - `.walk()`: yields `(state, depth)` depth-first in child order, root first at depth 0
    - `.select(state, ctx) -> list[State] | None`
    - `.tick(ctx, dt)`
    - `.reset(ctx)`

**Behavior (from the spec, plus two clarifications the spec now includes):**
- **Each tick:**
  1. `time += dt`.
  2. Run the evaluators.
  3. If idle, select from `ROOT`, enter the new leaf's task and log `select -> <leaf path>`. If still idle, return; the error `error: no state selectable, idle` is logged once until something is selected again.
  4. Tick the leaf's task. A leaf without a task counts as `SUCCEEDED`.
  5. Store `last_status`.
  6. Find a transition, checking states from the leaf up to root. Within each state, check its transitions in order:
     - `ON_CONDITION` fires when its condition evaluates true;
     - `ON_COMPLETED` fires on `SUCCEEDED`;
     - `ON_FAILED` fires on `FAILED`.
  7. **If a transition matched:** log `<leaf path> -> <Succeeded|Failed|condition name>` and take it.
  8. **If nothing matched and the status isn't `RUNNING`:** log `<leaf path> -> <status value> (no transition, back to ROOT)` and take a transition to `ROOT`.
- **Taking a transition to a target:**
  1. Exit the old leaf's task.
  2. `new = select_from(target)`. That is the target's ancestors below root plus `select(target)`. If `select(target)` is `None` and the target isn't root, log `<target path> not selectable, reselecting from ROOT` and use `select(root)`, or `[]` if that also fails.
  3. For each old state, deepest first, where `state not in new or state.is_at_or_below(target)`: call `on_exit(ctx)`, if it has one.
  4. Set `last_status = None`, then activate `new`: enter its leaf's task and log `select -> ...`, or log the idle error.
- **`select(state, ctx)`:**
  - If the state isn't root and its conditions fail, return `None`.
  - A leaf returns `[state]`, or `None` if it's root.
  - Otherwise try each child in order and return the first success, prefixed with the state unless the state is root. If no child succeeds, return `None`.
- **`State.conditions_pass`:** evaluates every condition, without short-circuiting, so each gets a `last_result`. With no conditions it's `True`. Otherwise apply `all` or `any` according to the mode.
- **`reset(ctx)`:** if active, exit the leaf's task, then call `on_exit` on every active state, deepest first. Then set `active = []` and `last_status = None`.
- **Construction checks:**
  - A state with both a task and children raises `ValueError`.
  - An `ON_CONDITION` transition without a condition, or any other trigger with one, raises `ValueError`.
  - A transition target that doesn't resolve raises `KeyError`.
  - Duplicate state paths raise `ValueError`.

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_statetree.py`:

```python
import pytest

from ai.statetree import (
    ROOT,
    Condition,
    Evaluator,
    Mode,
    State,
    StateTree,
    Status,
    Task,
    Transition,
    Trigger,
)


class ScriptedTask(Task):
    """Returns the given statuses in order, then RUNNING forever."""

    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.entered = 0
        self.exited = 0

    def enter(self, ctx):
        self.entered += 1

    def tick(self, ctx, dt):
        return self.statuses.pop(0) if self.statuses else Status.RUNNING

    def exit(self, ctx):
        self.exited += 1


def flag(key):
    return Condition(key, lambda ctx: ctx.get(key, False))


def leaf(name, *statuses, **kwargs):
    return State(name, task=ScriptedTask(*statuses), **kwargs)


def test_selects_first_child_whose_conditions_pass():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a")]),
        leaf("B", conditions=[flag("b")]),
        leaf("C", conditions=[flag("c")]),
    ]))
    tree.tick({"b": True, "c": True}, 0.1)
    assert tree.leaf.path == "B"


def test_falls_back_to_next_sibling_when_a_subtree_fails():
    tree = StateTree(State("Root", children=[
        State("P", children=[leaf("X", conditions=[flag("x")])]),
        leaf("Q"),
    ]))
    tree.tick({}, 0.1)
    assert [s.path for s in tree.active] == ["Q"]


def test_any_mode_passes_when_one_condition_passes():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a"), flag("b")], mode=Mode.ANY),
        leaf("Z"),
    ]))
    tree.tick({"b": True}, 0.1)
    assert tree.leaf.path == "A"


def test_all_mode_fails_when_one_condition_fails():
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[flag("a"), flag("b")], mode=Mode.ALL),
        leaf("Z"),
    ]))
    tree.tick({"b": True}, 0.1)
    assert tree.leaf.path == "Z"


@pytest.mark.parametrize("status, expected", [(Status.SUCCEEDED, "Done"), (Status.FAILED, "Broken")])
def test_completed_and_failed_transitions(status, expected):
    tree = StateTree(State("Root", children=[
        leaf("Start", status, transitions=[
            Transition(Trigger.ON_COMPLETED, "Done"),
            Transition(Trigger.ON_FAILED, "Broken"),
        ]),
        leaf("Done"),
        leaf("Broken"),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == expected


def test_parent_transition_used_when_leaf_has_no_match():
    tree = StateTree(State("Root", children=[
        State("P", transitions=[Transition(Trigger.ON_COMPLETED, "Z")], children=[leaf("L", Status.SUCCEEDED)]),
        leaf("Z"),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "Z"


def test_condition_transition_fires_while_running():
    tree = StateTree(State("Root", children=[
        leaf("A", transitions=[Transition(Trigger.ON_CONDITION, "B", condition=flag("go"))]),
        leaf("B"),
    ]))
    ctx = {}
    tree.tick(ctx, 0.1)
    assert tree.leaf.path == "A"
    ctx["go"] = True
    tree.tick(ctx, 0.1)
    assert tree.leaf.path == "B"


def test_finished_task_without_any_transition_returns_to_root():
    task = ScriptedTask(Status.SUCCEEDED)
    tree = StateTree(State("Root", children=[State("A", task=task)]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "A"
    assert (task.entered, task.exited) == (2, 1)


def test_unselectable_target_reselects_from_root():
    class FinishOnce(Task):
        def tick(self, ctx, dt):
            ctx["first"] = False
            return Status.SUCCEEDED

    tree = StateTree(State("Root", children=[
        State("A", task=FinishOnce(), conditions=[flag("first")],
              transitions=[Transition(Trigger.ON_COMPLETED, "B")]),
        leaf("B", conditions=[flag("b")]),
        leaf("C"),
    ]))
    tree.tick({"first": True}, 0.1)
    assert tree.leaf.path == "C"
    assert "B not selectable, reselecting from ROOT" in [text for _, text in tree.log]


def test_evaluators_run_before_selection_and_tasks():
    seen = []

    class Mark(Evaluator):
        def tick(self, ctx, dt):
            ctx["evaluated"] = True

    class Probe(Task):
        def tick(self, ctx, dt):
            seen.append(ctx.get("evaluated", False))
            return Status.RUNNING

    tree = StateTree(
        State("Root", children=[State("A", task=Probe(), conditions=[flag("evaluated")]), leaf("Z")]),
        evaluators=[Mark()],
    )
    tree.tick({}, 0.1)
    assert tree.leaf.path == "A"
    assert seen == [True]


def test_condition_results_are_recorded():
    a, b, c = flag("a"), flag("b"), flag("c")
    tree = StateTree(State("Root", children=[
        leaf("A", conditions=[a]),
        leaf("B", conditions=[b]),
        leaf("C", conditions=[c]),
    ]))
    tree.tick({"b": True}, 0.1)
    assert (a.last_result, b.last_result, c.last_result) == (False, True, None)


def test_on_exit_runs_deepest_first_and_root_target_reenters_same_branch():
    exits = []
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("Q", on_exit=lambda ctx: exits.append("Q"), children=[
                leaf("L", Status.SUCCEEDED, transitions=[Transition(Trigger.ON_COMPLETED, ROOT)]),
            ]),
        ]),
    ]))
    tree.tick({}, 0.1)
    assert exits == ["Q", "P"]
    assert tree.leaf.path == "P/Q/L"


def test_sibling_leaf_transition_keeps_parent_active():
    exits = []
    first, second = ScriptedTask(Status.SUCCEEDED), ScriptedTask()
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("L1", task=first, transitions=[Transition(Trigger.ON_COMPLETED, "P/L2")]),
            State("L2", task=second),
        ]),
    ]))
    tree.tick({}, 0.1)
    assert tree.leaf.path == "P/L2"
    assert exits == []
    assert (first.exited, second.entered) == (1, 1)


def test_reset_exits_the_whole_active_path():
    exits = []
    task = ScriptedTask()
    tree = StateTree(State("Root", children=[
        State("P", on_exit=lambda ctx: exits.append("P"), children=[
            State("Q", on_exit=lambda ctx: exits.append("Q"), children=[State("L", task=task)]),
        ]),
    ]))
    tree.tick({}, 0.1)
    tree.reset({})
    assert exits == ["Q", "P"]
    assert task.exited == 1
    assert tree.active == [] and tree.leaf is None and tree.last_status is None


def test_log_records_selection_and_transitions_with_time():
    tree = StateTree(State("Root", children=[
        leaf("Start", Status.SUCCEEDED, transitions=[Transition(Trigger.ON_COMPLETED, "Done")]),
        leaf("Done"),
    ]))
    tree.tick({}, 0.5)
    assert list(tree.log) == [(0.5, "select -> Start"), (0.5, "Start -> Succeeded"), (0.5, "select -> Done")]


def test_idle_error_logged_once():
    tree = StateTree(State("Root", children=[leaf("A", conditions=[flag("a")])]))
    tree.tick({}, 0.1)
    tree.tick({}, 0.1)
    assert [text for _, text in tree.log] == ["error: no state selectable, idle"]
    assert tree.leaf is None


def test_walk_is_depth_first_in_child_order():
    tree = StateTree(State("Root", children=[State("P", children=[leaf("X"), leaf("Y")]), leaf("Q")]))
    assert [(s.path, d) for s, d in tree.walk()] == [("", 0), ("P", 1), ("P/X", 2), ("P/Y", 2), ("Q", 1)]


def test_construction_checks():
    with pytest.raises(KeyError):
        StateTree(State("Root", children=[leaf("A", transitions=[Transition(Trigger.ON_COMPLETED, "Nope")])]))
    with pytest.raises(ValueError):
        State("Bad", task=ScriptedTask(), children=[leaf("X")])
    with pytest.raises(ValueError):
        Transition(Trigger.ON_CONDITION, ROOT)
    with pytest.raises(ValueError):
        StateTree(State("Root", children=[leaf("A"), leaf("A")]))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_statetree.py -v`
Expected: collection error `No module named 'ai.statetree'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/ai/statetree.py`:

```python
"""A small StateTree engine modeled on UE5's StateTree: hierarchical states with
enter conditions, leaf tasks, transitions, and evaluators writing to a shared context."""

from collections import deque
from enum import Enum

ROOT = "ROOT"


class Status(Enum):
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


class Trigger(Enum):
    ON_COMPLETED = "OnCompleted"
    ON_FAILED = "OnFailed"
    ON_CONDITION = "OnCondition"


class Mode(Enum):
    ALL = "all"
    ANY = "any"


class Condition:
    def __init__(self, name, test):
        self.name = name
        self.test = test
        self.last_result: bool | None = None  # read by the brain panel

    def evaluate(self, ctx) -> bool:
        self.last_result = bool(self.test(ctx))
        return self.last_result


class Task:
    def enter(self, ctx):
        pass

    def tick(self, ctx, dt) -> Status:
        return Status.SUCCEEDED

    def exit(self, ctx):
        pass


class Evaluator:
    def tick(self, ctx, dt):
        pass


class Transition:
    def __init__(self, trigger: Trigger, target: str, condition: Condition | None = None):
        if (trigger is Trigger.ON_CONDITION) != (condition is not None):
            raise ValueError("ON_CONDITION transitions need a condition; other triggers must not have one")
        self.trigger = trigger
        self.target = target
        self.condition = condition

    def matches(self, status: Status, ctx) -> bool:
        if self.trigger is Trigger.ON_CONDITION:
            return self.condition.evaluate(ctx)
        if self.trigger is Trigger.ON_COMPLETED:
            return status is Status.SUCCEEDED
        return status is Status.FAILED

    def describe(self, status: Status) -> str:
        return self.condition.name if self.condition is not None else status.value


class State:
    def __init__(self, name, children=(), conditions=(), mode=Mode.ALL, task=None, transitions=(), on_exit=None):
        if task is not None and children:
            raise ValueError(f"{name}: only leaf states can have a task")
        self.name = name
        self.children = list(children)
        self.conditions = list(conditions)
        self.mode = mode
        self.task = task
        self.transitions = list(transitions)
        self.on_exit = on_exit
        self.parent: State | None = None
        for child in self.children:
            child.parent = self

    @property
    def path(self) -> str:
        names = []
        state = self
        while state.parent is not None:
            names.append(state.name)
            state = state.parent
        return "/".join(reversed(names))

    def conditions_pass(self, ctx) -> bool:
        # Evaluate every condition (no short-circuit) so the panel can mark each one.
        results = [condition.evaluate(ctx) for condition in self.conditions]
        if not results:
            return True
        return all(results) if self.mode is Mode.ALL else any(results)

    def is_at_or_below(self, other: "State") -> bool:
        state = self
        while state is not None:
            if state is other:
                return True
            state = state.parent
        return False


class StateTree:
    def __init__(self, root: State, evaluators=(), log_size: int = 200):
        self.root = root
        self.evaluators = list(evaluators)
        self.active: list[State] = []
        self.last_status: Status | None = None
        self.time = 0.0
        self.log: deque[tuple[float, str]] = deque(maxlen=log_size)
        self._idle_logged = False
        self._states: dict[str, State] = {}
        for state, _ in self.walk():
            if state.path in self._states:
                raise ValueError(f"duplicate state path: {state.path}")
            self._states[state.path] = state
        for state, _ in self.walk():
            for transition in state.transitions:
                self.find(transition.target)

    @property
    def leaf(self) -> State | None:
        return self.active[-1] if self.active else None

    def write_log(self, text: str) -> None:
        self.log.append((self.time, text))

    def find(self, path: str) -> State:
        if path == ROOT:
            return self.root
        if path not in self._states or path == "":
            raise KeyError(f"unknown state path: {path!r}")
        return self._states[path]

    def walk(self):
        stack = [(self.root, 0)]
        while stack:
            state, depth = stack.pop()
            yield state, depth
            stack.extend((child, depth + 1) for child in reversed(state.children))

    def select(self, state: State, ctx) -> list[State] | None:
        if state is not self.root and not state.conditions_pass(ctx):
            return None
        if not state.children:
            return None if state is self.root else [state]
        for child in state.children:
            selected = self.select(child, ctx)
            if selected is not None:
                return selected if state is self.root else [state] + selected
        return None

    def tick(self, ctx, dt: float) -> None:
        self.time += dt
        for evaluator in self.evaluators:
            evaluator.tick(ctx, dt)

        if not self.active:
            self._activate(self._select_from(self.root, ctx), ctx)
            if not self.active:
                return

        leaf = self.leaf
        status = leaf.task.tick(ctx, dt) if leaf.task is not None else Status.SUCCEEDED
        self.last_status = status

        transition = self._find_transition(status, ctx)
        if transition is not None:
            self.write_log(f"{leaf.path} -> {transition.describe(status)}")
            self._take(self.find(transition.target), ctx)
        elif status is not Status.RUNNING:
            self.write_log(f"{leaf.path} -> {status.value} (no transition, back to ROOT)")
            self._take(self.root, ctx)

    def reset(self, ctx) -> None:
        if self.active:
            leaf = self.leaf
            if leaf.task is not None:
                leaf.task.exit(ctx)
            for state in reversed(self.active):
                if state.on_exit is not None:
                    state.on_exit(ctx)
        self.active = []
        self.last_status = None

    def _find_transition(self, status: Status, ctx) -> Transition | None:
        for state in [*reversed(self.active), self.root]:
            for transition in state.transitions:
                if transition.matches(status, ctx):
                    return transition
        return None

    def _ancestors(self, state: State) -> list[State]:
        """States between root and `state`, top-down, excluding both."""
        chain = []
        parent = state.parent
        while parent is not None and parent is not self.root:
            chain.append(parent)
            parent = parent.parent
        return chain[::-1]

    def _select_from(self, target: State, ctx) -> list[State]:
        selected = self.select(target, ctx)
        if selected is not None:
            return self._ancestors(target) + selected
        if target is not self.root:
            self.write_log(f"{target.path} not selectable, reselecting from ROOT")
            return self.select(self.root, ctx) or []
        return []

    def _take(self, target: State, ctx) -> None:
        old = self.active
        if old[-1].task is not None:
            old[-1].task.exit(ctx)
        new = self._select_from(target, ctx)
        for state in reversed(old):
            # Targeting a state re-enters it, so everything at or below the target exits.
            if state not in new or state.is_at_or_below(target):
                if state.on_exit is not None:
                    state.on_exit(ctx)
        self.last_status = None
        self.active = []
        self._activate(new, ctx)

    def _activate(self, path: list[State], ctx) -> None:
        self.active = path
        if path:
            self._idle_logged = False
            if path[-1].task is not None:
                path[-1].task.enter(ctx)
            self.write_log(f"select -> {path[-1].path}")
        elif not self._idle_logged:
            self._idle_logged = True
            self.write_log("error: no state selectable, idle")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_statetree.py -v`
Expected: all PASS (19 tests).

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/ai/statetree.py Experiments/exp-00/tests/test_statetree.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: StateTree engine" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Tasks and evaluators

**Files:**
- Create: `Experiments/exp-00/src/ai/tasks.py`
- Test: `Experiments/exp-00/tests/test_tasks.py`

**Interfaces:**
- Consumes:
  - Task 1: `direction_index`.
  - Task 3: `astar`, and `Actor` fields `tile`, `facing`, `next_tile`, `progress`, `speed`.
  - Task 4: `Task`, `Evaluator`, `Status`.
  - Task 2: `SmartObjectSubsystem.find`, `.claim`, `.release`, and `ClaimHandle.object` / `.slot`.
- Context keys used:
  - Data: `Zone`, `LastUsed`, `Target`, `Claim`, `Interaction`, `InteractionElapsed`, `Path`.
  - References: `actor`, `world`, `rng` (a `random.Random`), and `log`, a callable `log(text: str)`.
- Produces:
  - `ZoneEvaluator()`
  - `FindAndClaim(tag_query)`
  - `MoveTo(goal_fn)`, where `goal_fn(ctx) -> set[Tile] | None` is called once on enter
  - `Interact()`
  - `Wait(duration: float)`
  - `claimed_slot_goal(ctx)`
  - `random_tile_goal(ctx)`
  - `release_claim(ctx)`
  - Log texts: `claim <X> / slot <i>` and `release <X> / slot <i>`

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_tasks.py`:

```python
import random

import pytest

from ai.statetree import ROOT, Condition, State, StateTree, Status, Transition, Trigger
from ai.tasks import (
    FindAndClaim,
    Interact,
    MoveTo,
    Wait,
    ZoneEvaluator,
    claimed_slot_goal,
    random_tile_goal,
    release_claim,
)
from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject
from world import Actor, World


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def make_ctx(object_tile=(6, 0), slot_tile=(5, 0), facing=0, duration=0.5):
    world = World()
    obj = SmartObject(
        "A", object_tile, frozenset({"Object.A"}), [Slot(0, slot_tile, facing)],
        [Interaction("A.Only", duration, (set_last_used("A"),))],
    )
    world.add_object(obj)
    log = []
    ctx = {
        "Zone": None, "LastUsed": None, "Target": None, "Claim": None,
        "Interaction": None, "InteractionElapsed": 0.0, "Path": None,
        "actor": Actor(tile=(0, 0)), "world": world, "rng": random.Random(0), "log": log.append,
    }
    return ctx, obj, log


def run(task, ctx, dt=0.1, max_ticks=1000):
    for _ in range(max_ticks):
        status = task.tick(ctx, dt)
        if status is not Status.RUNNING:
            return status
    raise AssertionError("task never finished")


def test_zone_evaluator_sets_zone_from_actor_tile():
    ctx, _, _ = make_ctx()
    ctx["actor"].tile = (-3, 0)
    ZoneEvaluator().tick(ctx, 0.1)
    assert ctx["Zone"] == "West"


def test_find_and_claim_success():
    ctx, obj, log = make_ctx()
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.SUCCEEDED
    assert ctx["Target"] == "A"
    assert ctx["Claim"].slot.tile == (5, 0)
    assert ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert log == ["claim A / slot 0"]


def test_find_and_claim_fails_when_no_object_matches():
    ctx, _, _ = make_ctx()
    task = FindAndClaim({"Object.Z"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert ctx["Claim"] is None


def test_find_and_claim_fails_when_every_slot_is_claimed():
    ctx, obj, _ = make_ctx()
    ctx["world"].smart_objects.claim(obj, obj.slots[0], actor="someone else")
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_move_to_walks_to_claimed_slot_and_faces_object():
    # Object is SE of the slot, so the last step (heading E) must not decide the final facing.
    ctx, obj, _ = make_ctx(object_tile=(5, 1), slot_tile=(5, 0), facing=5)
    claim = FindAndClaim({"Object.A"})
    claim.enter(ctx)
    claim.tick(ctx, 0.1)
    move = MoveTo(claimed_slot_goal)
    move.enter(ctx)
    assert ctx["Path"][0] == (0, 0) and ctx["Path"][-1] == (5, 0)
    assert run(move, ctx) is Status.SUCCEEDED
    actor = ctx["actor"]
    assert actor.tile == (5, 0) and actor.next_tile is None
    assert actor.facing == 5
    assert ctx["Path"] == [(5, 0)]


def test_move_to_speed_is_tiles_per_second():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    assert move.tick(ctx, 1.0) is Status.RUNNING  # speed 3 -> exactly 3 tiles in 1s
    assert ctx["actor"].tile == (3, 0)
    assert ctx["Path"] == [(3, 0), (4, 0), (5, 0)]  # a straight axis line has one shortest path


def test_move_to_fails_without_a_path():
    ctx, _, _ = make_ctx()
    goal = (0, 8)
    for d in DIRECTIONS:
        ctx["world"].add_wall(add(goal, d))
    move = MoveTo(lambda ctx: {goal})
    move.enter(ctx)
    assert ctx["Path"] is None
    assert move.tick(ctx, 0.1) is Status.FAILED


def test_move_to_fails_when_path_gets_blocked():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    planned = list(ctx["Path"])
    ctx["world"].add_wall(planned[3])
    assert run(move, ctx) is Status.FAILED
    assert ctx["actor"].tile == planned[2]  # stopped on the last tile before the new wall


def test_move_to_exit_clears_mid_step_movement():
    ctx, _, _ = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    move.tick(ctx, 0.1)
    assert ctx["actor"].next_tile is not None
    move.exit(ctx)
    assert ctx["actor"].next_tile is None and ctx["actor"].progress == 0.0
    assert ctx["Path"] is None


def test_random_tile_goal_picks_a_walkable_tile():
    ctx, _, _ = make_ctx()
    (tile,) = random_tile_goal(ctx)
    assert ctx["world"].is_walkable(tile)


def test_interact_applies_effects_after_duration():
    ctx, _, _ = make_ctx(duration=0.5)
    claim = FindAndClaim({"Object.A"})
    claim.enter(ctx)
    claim.tick(ctx, 0.1)
    task = Interact()
    task.enter(ctx)
    assert ctx["Interaction"].name == "A.Only"
    assert task.tick(ctx, 0.3) is Status.RUNNING
    assert ctx["LastUsed"] is None
    assert ctx["InteractionElapsed"] == pytest.approx(0.3)
    assert task.tick(ctx, 0.3) is Status.SUCCEEDED
    assert ctx["LastUsed"] == "A"
    assert ctx["Interaction"] is None


def test_interact_fails_without_a_claim():
    ctx, _, _ = make_ctx()
    task = Interact()
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_wait():
    task = Wait(1.0)
    task.enter({})
    assert task.tick({}, 0.6) is Status.RUNNING
    assert task.tick({}, 0.6) is Status.SUCCEEDED


def test_release_claim_clears_and_logs_and_is_a_noop_without_claim():
    ctx, obj, log = make_ctx()
    release_claim(ctx)
    assert log == []
    claim = FindAndClaim({"Object.A"})
    claim.enter(ctx)
    release_claim(ctx)
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert log == ["claim A / slot 0", "release A / slot 0"]


def go_use_tree():
    return StateTree(State("Root", children=[
        State("GoUse(A)", conditions=[Condition("LastUsed==None", lambda ctx: ctx["LastUsed"] is None)],
              on_exit=release_claim, children=[
            State("FindAndClaim", task=FindAndClaim({"Object.A"}), transitions=[
                Transition(Trigger.ON_COMPLETED, "GoUse(A)/MoveTo"),
                Transition(Trigger.ON_FAILED, "Idle"),
            ]),
            State("MoveTo", task=MoveTo(claimed_slot_goal), transitions=[
                Transition(Trigger.ON_COMPLETED, "GoUse(A)/Interact"),
                Transition(Trigger.ON_FAILED, "Idle"),
            ]),
            State("Interact", task=Interact(), transitions=[Transition(Trigger.ON_COMPLETED, ROOT)]),
        ]),
        State("Idle", task=Wait(100.0)),
    ]), evaluators=[ZoneEvaluator()])


def run_until_idle(tree, ctx, max_ticks=1000):
    for _ in range(max_ticks):
        tree.tick(ctx, 0.1)
        if tree.leaf is not None and tree.leaf.path == "Idle":
            return
    raise AssertionError("tree never reached Idle")


def test_claim_released_when_go_use_completes():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    run_until_idle(tree, ctx)
    assert ctx["LastUsed"] == "A"
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert "release A / slot 0" in log


def test_claim_released_when_move_fails_partway():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    tree.tick(ctx, 0.1)  # claims, then moves on to MoveTo, which plans its path
    assert tree.leaf.path == "GoUse(A)/MoveTo"
    ctx["world"].add_wall(ctx["Path"][3])
    run_until_idle(tree, ctx)
    assert ctx["LastUsed"] is None
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None
    assert ctx["actor"].tile != (5, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_tasks.py -v`
Expected: collection error `No module named 'ai.tasks'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/ai/tasks.py`:

```python
"""StateTree tasks and evaluators for the actor: find/claim Smart Objects, walk, interact, wait."""

from ai.pathing import astar
from ai.statetree import Evaluator, Status, Task
from hexgrid import direction_index


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
        if claim is not None and actor.tile == claim.slot.tile:
            actor.facing = claim.slot.facing


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
    return {claim.slot.tile} if claim is not None else None


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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_tasks.py -v`
Expected: all PASS (16 tests).

- [ ] **Step 5: Run the whole suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/ai/tasks.py Experiments/exp-00/tests/test_tasks.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: StateTree tasks for Smart Object use" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Starting layout, example tree, and sim wiring

**Files:**
- Create: `Experiments/exp-00/src/layout.py`
- Create: `Experiments/exp-00/src/ai/tree_def.py`
- Create: `Experiments/exp-00/src/sim.py`
- Test: `Experiments/exp-00/tests/test_layout.py`
- Test: `Experiments/exp-00/tests/test_tree_def.py`
- Test: `Experiments/exp-00/tests/test_sim.py`

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces:
  - `layout`: `ACTOR_START: Tile`, `WALLS: list[Tile]`, `OBJECTS`, `set_last_used(name)`, `placeholder_interactions(name)`, `make_object(name, tile, slot_directions)`, `build_world() -> World`.
  - `ai.tree_def`: `RULES: dict[str, list[tuple[str, str]]]`, `rule_condition(last_used, zone)`, `go_use_state(name, tag_query, conditions, mode)`, `build_tree() -> StateTree`.
  - `sim`:
    - `Sim(world, actor, tree, ctx)`, a dataclass with `.step(dt)`.
    - `build_sim(seed: int = 0) -> Sim`. It sets `ctx["log"] = tree.write_log` and `ctx["rng"] = random.Random(seed)`.

**Layout values** (radius-12 map, checked by hand):
- **A** at `(-8, 2)`, West. Slots in directions 0 (E) and 5 (SE): `(-7, 2)` and `(-8, 3)`.
- **B** at `(0, 0)`, on the center column so it counts as East. Slots in directions 3 (W) and 0 (E): `(-1, 0)`, which is West, and `(1, 0)`, which is East.
- **C** at `(8, -2)`, East. Slots in directions 3 (W) and 4 (SW): `(7, -2)` and `(7, -1)`.
- **Actor start:** `(-10, 4)`, West.
- **Walls, 34 tiles:**
  - `q=-4` for `r` in -4..4;
  - `q=4` for `r` in -5..3;
  - `r=-6` for `q` in -2..2;
  - `r=7` for `q` in -3..1;
  - `r=9` for `q` in -6..-1.
- **Expected cycle** (nearest slot by hex distance, ties broken by slot index): A → B (West slot) → C → B (East slot) → A.

- [ ] **Step 1: Write the failing tests**

`Experiments/exp-00/tests/test_layout.py`:

```python
from ai.pathing import astar
from hexgrid import DIRECTIONS, add, in_bounds
from layout import ACTOR_START, WALLS, build_world


def objects_by_name(world):
    return {obj.name: obj for obj in world.smart_objects.objects}


def test_slots_are_walkable_and_face_their_object():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert world.is_walkable(slot.tile)
            assert add(slot.tile, DIRECTIONS[slot.facing]) == obj.tile


def test_every_slot_is_reachable_from_actor_start():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert astar(world, ACTOR_START, {slot.tile}) is not None, (obj.name, slot.index)


def test_layout_zones_match_spec():
    world = build_world()
    objects = objects_by_name(world)
    assert sorted(objects) == ["A", "B", "C"]
    assert world.zone_of(objects["A"].tile) == "West"
    assert world.zone_of(objects["B"].tile) == "East"
    assert world.zone_of(objects["C"].tile) == "East"
    assert [world.zone_of(s.tile) for s in objects["B"].slots] == ["West", "East"]
    assert world.zone_of(ACTOR_START) == "West"
    assert world.is_walkable(ACTOR_START)


def test_walls_are_in_bounds_and_within_spec_range():
    assert 30 <= len(set(WALLS)) <= 40
    assert all(in_bounds(t) for t in WALLS)


def test_objects_advertise_short_and_long_placeholder_interactions():
    world = build_world()
    for obj in world.smart_objects.objects:
        assert [(i.name, i.duration) for i in obj.interactions] == [(f"{obj.name}.Short", 1.5), (f"{obj.name}.Long", 3.0)]
        assert obj.tags == frozenset({f"Object.{obj.name}"})
        ctx = {}
        for effect in obj.interactions[0].effects:
            effect(ctx)
        assert ctx == {"LastUsed": obj.name}
```

`Experiments/exp-00/tests/test_tree_def.py`:

```python
import pytest

from ai.tree_def import build_tree

# Copied from the spec's rules table.
EXPECTED = {
    (None, "West"): "GoUse(Nearest)",
    (None, "East"): "GoUse(Nearest)",
    ("A", "West"): "GoUse(B)",
    ("A", "East"): "GoUse(C)",
    ("B", "West"): "GoUse(C)",
    ("B", "East"): "GoUse(A)",
    ("C", "West"): "GoUse(A)",
    ("C", "East"): "GoUse(B)",
}


@pytest.mark.parametrize("last_used, zone", sorted(EXPECTED, key=str))
def test_rules_select_expected_branch(last_used, zone):
    tree = build_tree()
    path = tree.select(tree.root, {"LastUsed": last_used, "Zone": zone})
    assert path[0].name == EXPECTED[(last_used, zone)]
    assert path[-1].name == "FindAndClaim"


def test_tree_shape_matches_spec():
    go_use = lambda name: [name, f"{name}/FindAndClaim", f"{name}/MoveTo", f"{name}/Interact"]
    assert [state.path for state, _ in build_tree().walk()] == [
        "",
        *go_use("GoUse(A)"),
        *go_use("GoUse(B)"),
        *go_use("GoUse(C)"),
        *go_use("GoUse(Nearest)"),
        "Wander", "Wander/MoveTo", "Wander/Wait",
    ]


def test_condition_names_are_readable():
    tree = build_tree()
    assert [c.name for c in tree.find("GoUse(A)").conditions] == [
        "LastUsed==C & Zone==West",
        "LastUsed==B & Zone==East",
    ]
    assert [c.name for c in tree.find("GoUse(Nearest)").conditions] == ["LastUsed==None"]
```

`Experiments/exp-00/tests/test_sim.py`:

```python
from layout import ACTOR_START
from sim import build_sim


def test_build_sim_wires_context():
    sim = build_sim(seed=0)
    assert sim.actor.tile == ACTOR_START
    assert sim.ctx["actor"] is sim.actor and sim.ctx["world"] is sim.world
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def test_actor_cycles_through_objects_as_the_spec_predicts():
    sim = build_sim(seed=0)
    used = []
    for _ in range(180 * 60):  # 180 sim-seconds at 60 Hz
        sim.step(1 / 60)
        last = sim.ctx["LastUsed"]
        if last is not None and (not used or used[-1] != last):
            used.append(last)
    assert used[:5] == ["A", "B", "C", "B", "A"]
    assert not any("error" in text for _, text in sim.tree.log)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_layout.py tests/test_tree_def.py tests/test_sim.py -v`
Expected: collection errors, `No module named 'layout'` / `'ai.tree_def'` / `'sim'`.

- [ ] **Step 3: Implement**

`Experiments/exp-00/src/layout.py`:

```python
"""The starting layout for exp-00. All placeholder content: edit freely."""

from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject
from world import World

ACTOR_START = (-10, 4)

WALLS = (
    [(-4, r) for r in range(-4, 5)]  # between A and B
    + [(4, r) for r in range(-5, 4)]  # between B and C
    + [(q, -6) for q in range(-2, 3)]
    + [(q, 7) for q in range(-3, 2)]
    + [(q, 9) for q in range(-6, 0)]
)

# (name, tile, directions from the object to its slots)
OBJECTS = (
    ("A", (-8, 2), (0, 5)),
    ("B", (0, 0), (3, 0)),  # one slot each side of the center column
    ("C", (8, -2), (3, 4)),
)


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def placeholder_interactions(name):
    return [
        Interaction(f"{name}.Short", 1.5, (set_last_used(name),)),
        Interaction(f"{name}.Long", 3.0, (set_last_used(name),)),
    ]


def make_object(name, tile, slot_directions):
    """Slots sit on the neighbors in `slot_directions`, each facing back at the object."""
    slots = [
        Slot(index=i, tile=add(tile, DIRECTIONS[d]), facing=(d + 3) % 6)
        for i, d in enumerate(slot_directions)
    ]
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=slots,
        interactions=placeholder_interactions(name),
    )


def build_world() -> World:
    world = World(walls=WALLS)
    for name, tile, slot_directions in OBJECTS:
        world.add_object(make_object(name, tile, slot_directions))
    return world
```

`Experiments/exp-00/src/ai/tree_def.py`:

```python
"""The example StateTree for exp-00. The rules are placeholders: edit freely."""

from ai.statetree import ROOT, Condition, Mode, State, StateTree, Transition, Trigger
from ai.tasks import (
    FindAndClaim,
    Interact,
    MoveTo,
    Wait,
    ZoneEvaluator,
    claimed_slot_goal,
    random_tile_goal,
    release_claim,
)

# For each object: the (LastUsed, Zone) pairs that send the actor to it.
RULES = {
    "A": [("C", "West"), ("B", "East")],
    "B": [("A", "West"), ("C", "East")],
    "C": [("B", "West"), ("A", "East")],
}


def rule_condition(last_used, zone):
    return Condition(
        f"LastUsed=={last_used} & Zone=={zone}",
        lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") == zone,
    )


def go_use_state(name, tag_query, conditions, mode):
    return State(name, conditions=conditions, mode=mode, on_exit=release_claim, children=[
        State("FindAndClaim", task=FindAndClaim(tag_query), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/MoveTo"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("MoveTo", task=MoveTo(claimed_slot_goal), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/Interact"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Interact", task=Interact(), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
        ]),
    ])


def build_tree() -> StateTree:
    children = [
        go_use_state(f"GoUse({target})", {f"Object.{target}"}, [rule_condition(*pair) for pair in pairs], Mode.ANY)
        for target, pairs in RULES.items()
    ]
    children.append(go_use_state(
        "GoUse(Nearest)", set(),
        [Condition("LastUsed==None", lambda ctx: ctx.get("LastUsed") is None)], Mode.ALL,
    ))
    children.append(State("Wander", children=[
        State("MoveTo", task=MoveTo(random_tile_goal), transitions=[
            Transition(Trigger.ON_COMPLETED, "Wander/Wait"),
            Transition(Trigger.ON_FAILED, ROOT),
        ]),
        State("Wait", task=Wait(1.0), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
        ]),
    ]))
    return StateTree(State("Root", children=children), evaluators=[ZoneEvaluator()])
```

`Experiments/exp-00/src/sim.py`:

```python
"""Wires the world, actor, StateTree and shared context together."""

import random
from dataclasses import dataclass

from ai.statetree import StateTree
from ai.tree_def import build_tree
from layout import ACTOR_START, build_world
from world import Actor, World


@dataclass
class Sim:
    world: World
    actor: Actor
    tree: StateTree
    ctx: dict

    def step(self, dt: float) -> None:
        self.tree.tick(self.ctx, dt)


def build_sim(seed: int = 0) -> Sim:
    world = build_world()
    actor = Actor(tile=ACTOR_START)
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
        "rng": random.Random(seed),
        "log": tree.write_log,
    }
    return Sim(world, actor, tree, ctx)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_layout.py tests/test_tree_def.py tests/test_sim.py -v`
Expected: all PASS (17 tests).

**If `test_actor_cycles_through_objects_as_the_spec_predicts` fails, don't change the expected sequence to match.** Print `used` and `list(sim.tree.log)[:60]`, find which leg diverged from the hand-checked distances above, and report it as a blocker. The cycle is part of the spec.

- [ ] **Step 5: Run the whole suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/layout.py Experiments/exp-00/src/ai/tree_def.py Experiments/exp-00/src/sim.py Experiments/exp-00/tests/test_layout.py Experiments/exp-00/tests/test_tree_def.py Experiments/exp-00/tests/test_sim.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: starting layout, example tree, sim wiring" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Camera, world view and main loop

**Files:**
- Create: `Experiments/exp-00/src/camera.py`
- Create: `Experiments/exp-00/src/render.py`
- Create: `Experiments/exp-00/src/main.py`
- Test: `Experiments/exp-00/tests/test_main.py`

**Interfaces:**
- Consumes: `Sim`, `build_sim` (Task 6); `all_tiles`, `DIRECTIONS` (Task 1); `SmartObjectSubsystem.is_claimed` (Task 2).
- Produces:
  - `camera.Camera(view_size, sharpness=5.0)` with `.x`, `.y`, `.snap(target)`, `.follow(target, dt)` and `.world_to_screen(point)`.
  - `render`:
    - constants `WINDOW_SIZE`, `VIEW_SIZE`, `PANEL_RECT`, `LINE`, `COLORS`;
    - `tile_to_world_px(tile)`, `actor_world_px(actor)`, `hex_corners(center, scale=1.0, lift=0.0)`;
    - `Renderer(screen)` with `.draw(sim, camera, paused, speed)`, `.draw_world(sim, camera, paused, speed)` and `.draw_panel(sim)`. `draw_panel` is minimal in this task and completed in Task 8.
  - `main`: `parse_args(argv)`, `main(argv=None)`.
- CLI flags:
  - `--frames N`: headless-friendly; each frame advances exactly one fixed tick × speed, then exits after N frames.
  - `--screenshot-dir PATH`
  - `--screenshot-every N` (default 60)
  - `--speed` (one of 0.25/0.5/1/2/4/8)
  - `--seed`

- [ ] **Step 1: Write the failing test**

`Experiments/exp-00/tests/test_main.py`:

```python
def test_headless_run_saves_screenshots(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import main

    main.main(["--frames", "120", "--speed", "4", "--screenshot-dir", str(tmp_path), "--screenshot-every", "60"])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frame_00060.png", "frame_00120.png"]


def test_parse_args_defaults():
    import main

    args = main.parse_args([])
    assert (args.frames, args.screenshot_dir, args.screenshot_every, args.speed, args.seed) == (0, None, 60, 1.0, 0)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_main.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'main'`.

- [ ] **Step 3: Implement the camera**

`Experiments/exp-00/src/camera.py`:

```python
"""A camera that eases toward a point in world pixels."""

import math


class Camera:
    def __init__(self, view_size, sharpness: float = 5.0):
        self.view_width, self.view_height = view_size
        self.sharpness = sharpness  # higher = catches up faster
        self.x = 0.0
        self.y = 0.0

    def snap(self, target) -> None:
        self.x, self.y = target

    def follow(self, target, dt: float) -> None:
        # Frame-rate independent exponential smoothing.
        blend = 1.0 - math.exp(-self.sharpness * dt)
        self.x += (target[0] - self.x) * blend
        self.y += (target[1] - self.y) * blend

    def world_to_screen(self, point):
        return (point[0] - self.x + self.view_width / 2, point[1] - self.y + self.view_height / 2)
```

- [ ] **Step 4: Implement the renderer (world view and minimal panel)**

`Experiments/exp-00/src/render.py`:

```python
"""Pygame drawing: the isometric hex world view and the brain panel."""

import math

import pygame

from hexgrid import DIRECTIONS, all_tiles

WINDOW_SIZE = (1600, 900)
VIEW_SIZE = (1180, 900)
PANEL_RECT = pygame.Rect(1180, 0, 420, 900)
LINE = 17

HEX_SIZE = 64 / math.sqrt(3)  # corner radius; a pointy-top hex is sqrt(3) * size = 64px across
SQUASH = 0.6  # vertical squash for the tilted look
WALL_HEIGHT = 20
OBJECT_HEIGHT = 30
CULL_MARGIN = 80

COLORS = {
    "void": (18, 20, 26),
    "west": (70, 96, 78),
    "east": (104, 94, 70),
    "grid": (40, 46, 44),
    "path": (240, 220, 120),
    "claimed": (250, 240, 170),
    "wall": (120, 118, 128),
    "outline": (30, 30, 36),
    "actor": (236, 236, 240),
    "shadow": (12, 14, 16),
    "ring_bg": (60, 60, 70),
    "ring": (250, 210, 90),
    "text": (230, 230, 235),
    "text_dim": (150, 154, 165),
    "text_active": (255, 255, 255),
    "panel": (26, 28, 36),
    "panel_edge": (60, 64, 80),
    "active_row": (52, 70, 110),
    "header": (140, 180, 255),
    "pass": (110, 200, 120),
    "fail": (220, 90, 90),
    "unknown": (110, 110, 120),
}
OBJECT_COLORS = {"A": (214, 96, 77), "B": (110, 180, 100), "C": (90, 140, 215)}


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def tile_to_world_px(tile):
    q, r = tile
    return (math.sqrt(3) * HEX_SIZE * (q + r / 2), 1.5 * HEX_SIZE * r * SQUASH)


def actor_world_px(actor):
    x0, y0 = tile_to_world_px(actor.tile)
    if actor.next_tile is None:
        return (x0, y0)
    x1, y1 = tile_to_world_px(actor.next_tile)
    t = actor.progress
    return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)


def hex_corners(center, scale=1.0, lift=0.0):
    """Corners of a squashed pointy-top hex; corner 1 is the bottom point, corner 4 the top."""
    cx, cy = center
    return [
        (
            cx + HEX_SIZE * scale * math.cos(math.radians(30 + 60 * i)),
            cy - lift + HEX_SIZE * scale * math.sin(math.radians(30 + 60 * i)) * SQUASH,
        )
        for i in range(6)
    ]


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.view = screen.subsurface(pygame.Rect((0, 0), VIEW_SIZE))  # clips world drawing
        self.font = pygame.font.Font(None, 20)
        self.small = pygame.font.Font(None, 18)
        self.big = pygame.font.Font(None, 28)
        self.floor_tiles = sorted(all_tiles(), key=lambda t: (tile_to_world_px(t)[1], tile_to_world_px(t)[0]))

    def draw(self, sim, camera, paused, speed):
        self.draw_world(sim, camera, paused, speed)
        self.draw_panel(sim)

    # --- world view -------------------------------------------------------

    def draw_world(self, sim, camera, paused, speed):
        view = self.view
        world, ctx = sim.world, sim.ctx
        to_screen = camera.world_to_screen
        view.fill(COLORS["void"])

        for tile in self.floor_tiles:
            center = to_screen(tile_to_world_px(tile))
            if not self._visible(center):
                continue
            base = COLORS["west"] if world.zone_of(tile) == "West" else COLORS["east"]
            corners = hex_corners(center)
            pygame.draw.polygon(view, shade(base, 1.0 - 0.05 * ((tile[0] - tile[1]) % 3)), corners)
            pygame.draw.polygon(view, COLORS["grid"], corners, 1)

        for tile in (ctx.get("Path") or [])[1:]:
            pygame.draw.circle(view, COLORS["path"], to_screen(tile_to_world_px(tile)), 4)

        for obj in world.smart_objects.objects:
            color = OBJECT_COLORS.get(obj.name, COLORS["wall"])
            object_center = to_screen(tile_to_world_px(obj.tile))
            for slot in obj.slots:
                center = to_screen(tile_to_world_px(slot.tile))
                corners = hex_corners(center, scale=0.45)
                if world.smart_objects.is_claimed(obj, slot):
                    pygame.draw.polygon(view, COLORS["claimed"], corners)
                pygame.draw.polygon(view, color, corners, 2)
                tip = (center[0] + (object_center[0] - center[0]) * 0.35, center[1] + (object_center[1] - center[1]) * 0.35)
                pygame.draw.line(view, color, center, tip, 2)

        # Raised things and the actor, back to front.
        drawables = [(tile_to_world_px(t)[1], "wall", t) for t in world.walls]
        drawables += [(tile_to_world_px(o.tile)[1], "object", o) for o in world.smart_objects.objects]
        actor_px = actor_world_px(sim.actor)
        drawables.append((actor_px[1] + 0.1, "actor", actor_px))
        for _, kind, item in sorted(drawables, key=lambda d: d[0]):
            if kind == "wall":
                center = to_screen(tile_to_world_px(item))
                if self._visible(center):
                    self._draw_column(center, WALL_HEIGHT, COLORS["wall"])
            elif kind == "object":
                center = to_screen(tile_to_world_px(item.tile))
                if self._visible(center):
                    self._draw_column(center, OBJECT_HEIGHT, OBJECT_COLORS.get(item.name, COLORS["wall"]))
                    label = self.big.render(item.name, True, COLORS["text_active"])
                    view.blit(label, label.get_rect(center=(center[0], center[1] - OBJECT_HEIGHT)))
            else:
                self._draw_actor(sim, to_screen(item))

        status = f"{speed:g}x" + ("   PAUSED" if paused else "")
        view.blit(self.big.render(status, True, COLORS["text"]), (12, 10))
        hint = "Space pause  |  N step  |  +/- speed  |  R reset  |  Esc quit"
        view.blit(self.small.render(hint, True, COLORS["text_dim"]), (12, VIEW_SIZE[1] - 24))

    def _visible(self, point):
        x, y = point
        return -CULL_MARGIN <= x <= VIEW_SIZE[0] + CULL_MARGIN and -CULL_MARGIN <= y <= VIEW_SIZE[1] + CULL_MARGIN

    def _draw_column(self, center, height, color):
        ground = hex_corners(center)
        top = hex_corners(center, lift=height)
        # Visible side faces: right (5-0), lower-right (0-1), lower-left (1-2), left (2-3).
        for (a, b), factor in zip(((5, 0), (0, 1), (1, 2), (2, 3)), (0.75, 0.6, 0.5, 0.65)):
            pygame.draw.polygon(self.view, shade(color, factor), [ground[a], ground[b], top[b], top[a]])
        pygame.draw.polygon(self.view, color, top)
        pygame.draw.polygon(self.view, COLORS["outline"], top, 1)

    def _draw_actor(self, sim, center):
        view = self.view
        x, y = center
        pygame.draw.ellipse(view, COLORS["shadow"], pygame.Rect(x - 10, y - 4, 20, 8))
        pygame.draw.circle(view, COLORS["actor"], (x, y - 12), 8)
        head = (x, y - 26)
        pygame.draw.circle(view, COLORS["actor"], head, 6)
        fx, fy = tile_to_world_px(DIRECTIONS[sim.actor.facing])
        length = math.hypot(fx, fy)
        pygame.draw.circle(view, COLORS["outline"], (head[0] + fx / length * 4, head[1] + fy / length * 4), 2)

        interaction = sim.ctx.get("Interaction")
        if interaction is not None:
            fraction = min(sim.ctx.get("InteractionElapsed", 0.0) / interaction.duration, 1.0)
            ring = pygame.Rect(0, 0, 36, 36)
            ring.center = (round(head[0]), round(head[1]))
            pygame.draw.circle(view, COLORS["ring_bg"], ring.center, 18, 3)
            if fraction > 0:
                pygame.draw.arc(view, COLORS["ring"], ring, math.pi / 2, math.pi / 2 + 2 * math.pi * fraction, 3)
            label = self.small.render(interaction.name, True, COLORS["text"])
            view.blit(label, label.get_rect(midbottom=(head[0], head[1] - 22)))

    # --- brain panel (completed in Task 8) --------------------------------

    def draw_panel(self, sim):
        pygame.draw.rect(self.screen, COLORS["panel"], PANEL_RECT)
        pygame.draw.line(self.screen, COLORS["panel_edge"], PANEL_RECT.topleft, PANEL_RECT.bottomleft, 2)
```

- [ ] **Step 5: Implement the main loop**

`Experiments/exp-00/src/main.py`:

```python
"""exp-00 entry point. Run from Experiments/exp-00: `uv run src/main.py`."""

import argparse
from pathlib import Path

import pygame

from camera import Camera
from render import VIEW_SIZE, WINDOW_SIZE, Renderer, actor_world_px
from sim import build_sim

DT = 1 / 60
SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
MAX_FRAME_TIME = 0.25  # avoid a catch-up spiral after a stall


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="MuraBito exp-00: StateTree + Smart Objects visualizer")
    parser.add_argument("--frames", type=int, default=0,
                        help="exit after N frames (0 = run until quit); each frame advances one fixed tick x speed")
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--screenshot-every", type=int, default=60)
    parser.add_argument("--speed", type=float, default=1.0, choices=SPEEDS)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    pygame.init()
    pygame.display.set_caption("MuraBito exp-00")
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    sim = build_sim(args.seed)
    camera = Camera(VIEW_SIZE)
    camera.snap(actor_world_px(sim.actor))
    speed_index = SPEEDS.index(args.speed)
    paused = False
    accumulator = 0.0
    frame = 0
    if args.screenshot_dir is not None:
        args.screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_n and paused:
                    sim.step(DT)
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed_index = min(speed_index + 1, len(SPEEDS) - 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed_index = max(speed_index - 1, 0)
                elif event.key == pygame.K_r:
                    sim.tree.reset(sim.ctx)
                    sim = build_sim(args.seed)
                    camera.snap(actor_world_px(sim.actor))
                    accumulator = 0.0

            speed = SPEEDS[speed_index]
            # Headless runs are deterministic: one fixed frame time, no waiting on the clock.
            frame_time = DT if args.frames else min(clock.tick(60) / 1000, MAX_FRAME_TIME)
            if not paused:
                accumulator += frame_time * speed
                while accumulator >= DT:
                    sim.step(DT)
                    accumulator -= DT
            camera.follow(actor_world_px(sim.actor), frame_time)

            renderer.draw(sim, camera, paused, speed)
            pygame.display.flip()
            frame += 1

            if args.screenshot_dir is not None and frame % args.screenshot_every == 0:
                pygame.image.save(screen, str(args.screenshot_dir / f"frame_{frame:05d}.png"))
            if args.frames and frame >= args.frames:
                return
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest tests/test_main.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Visual check of the world view**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && rm -rf screenshots && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 1200 --speed 2 --screenshot-dir screenshots --screenshot-every 150`

`screenshots/` is gitignored. Open at least `frame_00150.png`, `frame_00600.png` and `frame_01200.png` with the Read tool and confirm:
- The hex floor is a tiling of squashed pointy-top hexes with no gaps or overlaps. West tiles are green-tinted and East tiles tan-tinted, split along a zig-zag center column.
- Walls and the A/B/C objects are raised hex columns with lettered tops, drawn back to front so nearer columns cover farther ones.
- Slot markers are visible next to each object; a claimed slot is filled pale yellow.
- The actor stays near the center of the world view, and the map scrolls between screenshots.
- Yellow path dots lead from the actor to its target slot.
- While the actor is interacting, the progress ring and interaction name appear above its head.
- The speed label is at the top-left and the controls hint at the bottom-left. The right 420px is the empty dark panel.

If something is wrong, fix `render.py` and re-run. Describe what you saw in your report.

- [ ] **Step 8: Run the whole suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest -q`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/camera.py Experiments/exp-00/src/render.py Experiments/exp-00/src/main.py Experiments/exp-00/tests/test_main.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: follow camera, hex world view, main loop" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Brain panel

**Files:**
- Modify: `Experiments/exp-00/src/render.py`. Replace the `draw_panel` method, add helper methods, and add the `LOG_LINES = 12` constant next to `LINE`.
- Test: `Experiments/exp-00/tests/test_main.py` (existing; the headless run covers the panel code path).

**Interfaces:**
- Consumes:
  - `StateTree.walk()`, `.active`, `.leaf`, `.last_status`, `.log` and `.root` (Task 4);
  - `State.conditions`, `.mode`, `.name`, `.path`;
  - `Condition.last_result` and `.name`;
  - context keys `Zone`, `LastUsed`, `Target`, `Claim`, `Interaction`, `InteractionElapsed`, `Path`.
- Produces: `Renderer.draw_panel(sim)`, which draws three sections: STATE TREE, CONTEXT and TRANSITION LOG.

**What the panel shows** (from the spec):
- **STATE TREE:** every state from `tree.walk()`, indented 16px per depth.
  - The root and every state in `tree.active` get a highlighted row, but root only while something is active.
  - A state with more than one condition gets `  (any of)` or `  (all of)` appended to its label.
  - The active leaf's label gets `   [Running]` (etc.) when `last_status` is set.
  - Under each state, one row per enter condition. Draw a filled green circle for `True`, a filled red circle for `False`, or a hollow gray circle for `None`, followed by the condition name.
- **CONTEXT:**
  - `Zone: <zone>    LastUsed: <x>`
  - `Target: <x>    Claim: <X / slot i | None>`
  - `Interaction: <name elapsed / durations | None>`, e.g. `A.Long 1.2 / 3.0s`
  - `Path: <n> tiles | None`, where n is `len(Path) - 1`
  - `Task: <leaf path | (idle)>  [<status | ->]`
- **TRANSITION LOG:** the last `LOG_LINES` entries of `tree.log`, oldest at the top, formatted `f"{time:7.1f}s  {text}"`.

- [ ] **Step 1: Implement the panel**

In `Experiments/exp-00/src/render.py`, add `LOG_LINES = 12` right after `LINE = 17`. Then replace the whole `draw_panel` method, including its section comment, with:

```python
    # --- brain panel ------------------------------------------------------

    def draw_panel(self, sim):
        pygame.draw.rect(self.screen, COLORS["panel"], PANEL_RECT)
        pygame.draw.line(self.screen, COLORS["panel_edge"], PANEL_RECT.topleft, PANEL_RECT.bottomleft, 2)
        x0 = PANEL_RECT.x + 14
        y = self._draw_tree(sim.tree, x0, 10)
        y = self._draw_context(sim, x0, y + 8)
        self._draw_log(sim.tree, x0, y + 8)

    def _header(self, text, x, y):
        self.screen.blit(self.font.render(text, True, COLORS["header"]), (x, y))
        return y + LINE + 4

    def _draw_tree(self, tree, x0, y):
        screen = self.screen
        y = self._header("STATE TREE", x0, y)
        marks = {True: COLORS["pass"], False: COLORS["fail"], None: COLORS["unknown"]}
        for state, depth in tree.walk():
            is_active = bool(tree.active) and (state is tree.root or state in tree.active)
            x = x0 + depth * 16
            if is_active:
                pygame.draw.rect(screen, COLORS["active_row"], pygame.Rect(PANEL_RECT.x + 6, y - 1, PANEL_RECT.w - 12, LINE))
            label = state.name
            if len(state.conditions) > 1:
                label += f"  ({state.mode.value} of)"
            if state is tree.leaf and tree.last_status is not None:
                label += f"   [{tree.last_status.value}]"
            color = COLORS["text_active"] if is_active else COLORS["text_dim"]
            screen.blit(self.font.render(label, True, color), (x, y))
            y += LINE
            for condition in state.conditions:
                cx, cy = x + 22, y + LINE // 2 - 1
                width = 1 if condition.last_result is None else 0
                pygame.draw.circle(screen, marks[condition.last_result], (cx, cy), 4, width)
                screen.blit(self.small.render(condition.name, True, COLORS["text_dim"]), (cx + 10, y))
                y += LINE
        return y

    def _draw_context(self, sim, x0, y):
        ctx, tree = sim.ctx, sim.tree
        y = self._header("CONTEXT", x0, y)
        claim = ctx.get("Claim")
        interaction = ctx.get("Interaction")
        path = ctx.get("Path")
        claim_text = f"{claim.object.name} / slot {claim.slot.index}" if claim is not None else "None"
        if interaction is not None:
            interaction_text = f"{interaction.name} {ctx.get('InteractionElapsed', 0.0):.1f} / {interaction.duration:.1f}s"
        else:
            interaction_text = "None"
        path_text = f"{len(path) - 1} tiles" if path else "None"
        leaf_text = tree.leaf.path if tree.leaf is not None else "(idle)"
        status_text = tree.last_status.value if tree.last_status is not None else "-"
        lines = [
            f"Zone: {ctx.get('Zone')}    LastUsed: {ctx.get('LastUsed')}",
            f"Target: {ctx.get('Target')}    Claim: {claim_text}",
            f"Interaction: {interaction_text}",
            f"Path: {path_text}",
            f"Task: {leaf_text}  [{status_text}]",
        ]
        for line in lines:
            self.screen.blit(self.font.render(line, True, COLORS["text"]), (x0, y))
            y += LINE
        return y

    def _draw_log(self, tree, x0, y):
        y = self._header("TRANSITION LOG", x0, y)
        for time, text in list(tree.log)[-LOG_LINES:]:
            self.screen.blit(self.small.render(f"{time:7.1f}s  {text}", True, COLORS["text_dim"]), (x0, y))
            y += LINE
        return y
```

- [ ] **Step 2: Run the tests**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest -q`
Expected: all PASS.

- [ ] **Step 3: Visual check of the brain panel**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && rm -rf screenshots && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 1800 --speed 2 --screenshot-dir screenshots --screenshot-every 150`

Open at least four screenshots spread across the run with the Read tool and confirm:
- STATE TREE lists Root, GoUse(A), GoUse(B), GoUse(C), GoUse(Nearest) and Wander with their children, indented.
  - The active branch rows are highlighted.
  - The active leaf shows `[Running]` or a similar status.
  - GoUse(A/B/C) show `(any of)` with two condition rows each.
- Condition circles change between screenshots as `LastUsed` changes: green for the passing rule, red for evaluated failures, hollow gray for conditions not evaluated yet.
- CONTEXT values match the world view: Target and Claim match the highlighted slot, and Interaction shows a name with elapsed / duration while the ring is visible.
- TRANSITION LOG shows lines like `claim B / slot 0`, `GoUse(A)/Interact -> Succeeded`, `release A / slot 1` and `select -> GoUse(B)/FindAndClaim`, with increasing timestamps.
- Nothing overflows the bottom of the panel. The last log line is above y = 900.

If something is wrong, fix `render.py` and re-run. Describe what you saw in your report.

- [ ] **Step 4: Verify the manifest's commands work as written**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && uv run pytest`
Expected: all PASS.

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: exits 0 without a traceback. This is the manifest's `uv run src/main.py` run headless for 30 frames.

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-00-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-00/src/render.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-00: brain panel (state tree, context, transition log)" -m "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```
