# exp-01 Wandering Smart Objects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy exp-00 into a new experiment, exp-01, where the three Smart Objects slowly wander inside their own zone of a three-sector hex map, and the actor chases their moving slots.

**Architecture:**
- **Tasks 1–5 leave the suite green, and Task 6 keeps it green.** Every task ends with the whole suite passing.
- **Task 1** copies exp-00 unchanged.
- **Task 2** makes slots derive their tile from their object.
- **Task 3** swaps West/East for three sector zones, live blocking, the new layout and the new rules.
- **Task 4** adds the stochastic object mover.
- **Task 5** makes the actor's tasks chase, re-plan, and track in-use.
- **Task 6** renders the moving objects.
- **The engine and pathing are untouched.**

**Tech Stack:** Python 3.13, pygame 2.6.1, pytest 9, uv.

**Spec:** `Experiments/exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md`. Read it before starting any task.

## Global Constraints

- **Paths.** Repo root: `/home/lexa/DevProjects/_GameDev/MuraBito`. Experiment dir: `/home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01`. Source for the copy: `/home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00`, which is frozen and never modified.
- **Branch.** Work happens on branch `exp-01-impl`.
- **Git.** Every git command uses `git -C /home/lexa/DevProjects/_GameDev/MuraBito ...`; never run a bare `git`. Before each commit, check that `git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD` prints `exp-01-impl`.
- **Shell state doesn't persist between commands.** Every command either `cd`s to an absolute path in the same invocation or uses absolute paths.
- **Python deps: uv only.** Use `uv add` / `uv run` / `uv lock`, never `pip` or `uv pip`. No new dependencies are needed.
- **Running tests.** `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest ...`. `pyproject.toml` sets `pythonpath = ["src"]` and `testpaths = ["tests"]`.
- **Imports.** Modules are imported relative to `src/`: `import hexgrid`, `from ai.statetree import ...`. Never import `src.` anything.
- **No pygame imports** in `hexgrid.py`, `smartobjects.py`, `world.py`, `wander.py`, `layout.py`, `sim.py`, `camera.py`, or anything under `src/ai/`.
- **Hex grid.** Pointy-top hexes, axial `(q, r)`, map radius 12. `DIRECTIONS` index 0 is E, then counter-clockwise: `((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))`.
- **Zones.** For `(q, r)` with `s = -q - r`: NE if `q >= r and q >= s`; else S if `r >= s`; else NW.
- **Home zones and pausing.** A = NW (pauses during use), B = S (pauses), C = NE (never pauses).
- **Wander placeholders.** `MOVE_RATE = 0.5` steps/s while idle, `STEP_SPEED = 1.5` tiles/s, `TURN_FALLOFF = 0.3`.
- **Log text is ASCII only.** New lines are exactly `replan: slot moved`, `replan: path blocked` and `interact: slot drifted away`.
- **Commit trailer.** Each commit message ends with the `Co-Authored-By` attribution line the committing agent's own environment specifies. Pass it as a second `-m`.
- **Style.** Short module docstrings, and comments only where the why isn't obvious.
- **Nested code blocks.** Code blocks inside Markdown list items (the "exact edits") are indented by the list's two spaces. Strip that list indentation when matching or inserting; the code's own indentation is what's inside.
- **Pre-validated code.** Every code block and exact edit in this plan was applied in order to a scratch copy of exp-00, and each task's end state passed its expected test count. Transcribe exactly. If something fails, investigate the cause; don't edit tests to fit.

## File Structure

```
Experiments/exp-01/                 (copied from exp-00 in Task 1)
├─ pyproject.toml                   Task 1  project renamed murabito-exp-01
├─ src/
│  ├─ hexgrid.py                    unchanged
│  ├─ smartobjects.py               Task 2  direction slots, slot_tile/slot_facing, in-use, find(blocked_fn), movement fields
│  ├─ world.py                      Task 3  NE/S/NW zones, live blocking, can_object_enter
│  ├─ wander.py                     Task 4  NEW: divergence weights, choose_direction, ObjectMover
│  ├─ layout.py                     Task 2 edit; Task 3 rewrite: 3-zone layout
│  ├─ sim.py                        Task 4  Sim.mover, step ticks mover then tree
│  ├─ camera.py                     unchanged
│  ├─ render.py                     Task 2 edit; Task 6 rewrite: zone tints, moving objects/slots, heading tick, pause marker
│  ├─ main.py                       Task 1  exp-01 names
│  └─ ai/
│     ├─ pathing.py, statetree.py   unchanged
│     ├─ tasks.py                   Task 2 edit, Task 5 rewrite: chase/replan MoveTo, in-use + drift Interact
│     └─ tree_def.py                Task 3 edit (rules), Task 5 rewrite (chase MoveTo, Interact ON_FAILED)
└─ tests/
   ├─ test_hexgrid.py, test_pathing.py, test_statetree.py, test_main.py   unchanged
   ├─ test_smartobjects.py          Task 2
   ├─ test_world.py                 Task 2 edit, Task 3 rewrite
   ├─ test_layout.py                Task 2 edit, Task 3 rewrite
   ├─ test_tree_def.py              Task 3, Task 5
   ├─ test_tasks.py                 Task 2 edit, Task 3 edit, Task 5 rewrite
   ├─ test_wander.py                Task 4  NEW
   └─ test_sim.py                   Task 3, Task 4, Task 5
```

**Expected suite size at the end of each task:** 88, 92, 114, 140, 149, 149.

---

### Task 1: Scaffold exp-01 as a copy of exp-00

**Files:**
- Create: `Experiments/exp-01/{src,tests,pyproject.toml,uv.lock,.python-version}`, copied from exp-00
- Modify: `Experiments/exp-01/pyproject.toml`, `Experiments/exp-01/src/main.py`, `Experiments/exp-01/uv.lock` (via `uv lock`)
- Modify: `Experiments/manifest.md` (append the exp-01 entry)

**Interfaces:**
- Consumes: exp-00 at HEAD of `exp-01-impl`.
- Produces: an exp-01 project identical to exp-00 except for its names, with 88 passing tests.

- [ ] **Step 1: Copy the project**

```bash
mkdir -p /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01
cp -r /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00/src /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00/tests /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00/pyproject.toml /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00/uv.lock /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-00/.python-version /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/
find /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 -name __pycache__ -prune -exec rm -rf {} +
ls -a /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01
```

Expected listing: `.python-version`, `docs`, `pyproject.toml`, `src`, `tests`, `uv.lock`. `docs/` already exists from the spec commit. There's no `.venv` yet.

- [ ] **Step 2: Rename the project**

In `Experiments/exp-01/pyproject.toml`, replace `name = "murabito-exp-00"` with `name = "murabito-exp-01"`.

In `Experiments/exp-01/src/main.py`, make these three replacements:
- `"""exp-00 entry point. Run from Experiments/exp-00: `uv run src/main.py`."""` → `"""exp-01 entry point. Run from Experiments/exp-01: `uv run src/main.py`."""`
- `description="MuraBito exp-00: StateTree + Smart Objects visualizer"` → `description="MuraBito exp-01: StateTree + wandering Smart Objects visualizer"`
- `pygame.display.set_caption("MuraBito exp-00")` → `pygame.display.set_caption("MuraBito exp-01")`

- [ ] **Step 3: Re-lock and run the copied suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv lock && uv run pytest -q`
Expected:
- `uv lock` updates the project name in `uv.lock`.
- uv creates `.venv` (installing pygame can take up to a minute).
- `88 passed`.

Then run `rg -n "exp-00" /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/src /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/pyproject.toml /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/uv.lock`.
Expected: matches only in `src/layout.py` and `src/ai/tree_def.py` docstrings. Later tasks rewrite those files.

- [ ] **Step 4: Add the manifest entry**

Append this to the end of `/home/lexa/DevProjects/_GameDev/MuraBito/Experiments/manifest.md`, keeping one blank line before it:

```markdown
---

## exp-01 — Wandering Smart Objects

- **Started:** 2026-09-17
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd Experiments/exp-01 && uv run src/main.py`
- **Test:** `cd Experiments/exp-01 && uv run pytest`
- **Design:** [`exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md`](exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md)

### Why

Built on exp-00. It's almost the same, but the targets slowly wander around.

### What

Starts as a copy of exp-00: same hex map, camera, StateTree engine, Smart Objects, A\* pathing and brain panel.

**What changes:**
- **Three zones.** The map is split into three 120° sectors (NE, S, NW).
- **Wandering objects.** Each Smart Object wanders inside its own zone, with stochastic momentum. It usually keeps its heading, and sharper turns are less likely. Slots ride along with their object and can poke across a zone border.
- **Chasing.** The actor re-plans when its claimed slot moves or its path gets blocked.
- **Pausing.** Some objects hold still while in use. The others keep moving, and the interaction fails if the slot drifts away.
- **Rules.** The placeholder rules still key on the last object used and the actor's zone. Finishing in that object's home zone moves forward (A→B→C), and finishing across a border moves backward.

### Layout

- `src/`: same as exp-00, plus `wander.py`, the stochastic object mover.
- `src/ai/`: same as exp-00. `tasks.py` gains chasing, re-planning and in-use tracking.
- `tests/`: same as exp-00, plus `test_wander.py`. The sim tests check invariants over seeded runs instead of a fixed cycle.

### Controls

Same as exp-00: Space pause/resume · N step one tick while paused · +/- sim speed (0.25x-8x) · R reset · Esc quit.

### Headless

`cd Experiments/exp-01 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --screenshot-dir screenshots --screenshot-every K` (screenshots/ is gitignored).
```

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src Experiments/exp-01/tests Experiments/exp-01/pyproject.toml Experiments/exp-01/uv.lock Experiments/exp-01/.python-version Experiments/manifest.md
git -C /home/lexa/DevProjects/_GameDev/MuraBito status --short   # must not list .venv or __pycache__
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: scaffold as a copy of exp-00" -m "<your Co-Authored-By trailer>"
```

---

### Task 2: Slots that ride on their object

**Files:**
- Replace: `Experiments/exp-01/src/smartobjects.py` (full content below)
- Replace: `Experiments/exp-01/tests/test_smartobjects.py` (full content below)
- Modify (exact edits below): `src/layout.py`, `src/ai/tasks.py`, `src/render.py`, `tests/test_tasks.py`, `tests/test_layout.py`, `tests/test_world.py`

**Interfaces:**
- Consumes: `hexgrid.DIRECTIONS`, `add`, `distance`.
- Produces:
  - `Slot(index: int, direction: int)`, frozen.
  - `SmartObject(name, tile, tags, slots, interactions, home_zone="", pauses_during_use=True, heading=0, next_tile=None, progress=0.0)`, with `eq=False`.
  - `slot_tile(obj, slot) -> Tile`
  - `slot_facing(slot) -> int`
  - `ClaimHandle(object, slot, actor)`
  - `SmartObjectSubsystem`:
    - `.objects`
    - `.register(obj)`
    - `.find(tag_query, near, blocked_fn=None)`
    - `.claim(obj, slot, actor)`
    - `.release(handle)`
    - `.is_claimed(obj, slot)`
    - `.set_in_use(obj, bool)`
    - `.is_in_use(obj)`

- [ ] **Step 1: Write the new Smart Object tests**

Replace `Experiments/exp-01/tests/test_smartobjects.py` with:

```python
from hexgrid import DIRECTIONS, add
from smartobjects import Interaction, Slot, SmartObject, SmartObjectSubsystem, slot_facing, slot_tile


def make_object(name, tile, slot_directions):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, direction=d) for i, d in enumerate(slot_directions)],
        interactions=[Interaction(f"{name}.Short", 1.5)],
    )


def make_subsystem():
    subsystem = SmartObjectSubsystem()
    a = make_object("A", (0, 0), [0, 3])  # slots at (1, 0) and (-1, 0)
    b = make_object("B", (6, 0), [3])  # slot at (5, 0)
    subsystem.register(a)
    subsystem.register(b)
    return subsystem, a, b


def test_new_object_movement_defaults():
    obj = make_object("A", (0, 0), [0])
    assert (obj.home_zone, obj.pauses_during_use, obj.heading, obj.next_tile, obj.progress) == ("", True, 0, None, 0.0)


def test_slot_tile_and_facing_follow_the_object():
    subsystem, a, b = make_subsystem()
    slot = a.slots[0]
    assert slot_tile(a, slot) == (1, 0)
    assert slot_facing(slot) == 3
    a.tile = (2, 2)
    assert slot_tile(a, slot) == (3, 2)
    assert add(slot_tile(a, slot), DIRECTIONS[slot_facing(slot)]) == a.tile


def test_find_filters_by_tag():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.B"}, near=(0, 0)) == [(b, b.slots[0])]


def test_find_requires_every_tag_in_the_query():
    subsystem, a, b = make_subsystem()
    assert subsystem.find({"Object.A", "Something.Else"}, near=(0, 0)) == []


def test_empty_query_matches_every_object():
    subsystem, a, b = make_subsystem()
    assert len(subsystem.find(set(), near=(0, 0))) == 3


def test_find_sorts_by_hex_distance_of_the_live_slot_tile():
    subsystem, a, b = make_subsystem()
    results = subsystem.find(set(), near=(4, 0))
    assert [slot_tile(obj, slot) for obj, slot in results] == [(5, 0), (1, 0), (-1, 0)]
    b.tile = (-6, 0)  # B's slot moves to (-7, 0)
    results = subsystem.find(set(), near=(4, 0))
    assert [slot_tile(obj, slot) for obj, slot in results] == [(1, 0), (-1, 0), (-7, 0)]


def test_find_skips_blocked_slots():
    subsystem, a, b = make_subsystem()
    found = subsystem.find({"Object.A"}, near=(0, 0), blocked_fn=lambda tile: tile == (1, 0))
    assert found == [(a, a.slots[1])]


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


def test_in_use_set_and_clear():
    subsystem, a, b = make_subsystem()
    assert not subsystem.is_in_use(a)
    subsystem.set_in_use(a, True)
    assert subsystem.is_in_use(a) and not subsystem.is_in_use(b)
    subsystem.set_in_use(a, False)
    subsystem.set_in_use(a, False)
    assert not subsystem.is_in_use(a)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest tests/test_smartobjects.py -q`
Expected: collection error `ImportError: cannot import name 'slot_facing' from 'smartobjects'`.

- [ ] **Step 3: Replace `smartobjects.py`**

Replace `Experiments/exp-01/src/smartobjects.py` with:

```python
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
```

- [ ] **Step 4: Update the consumers (exact edits)**

`Experiments/exp-01/src/layout.py`:
- Replace
  ```python
  from hexgrid import DIRECTIONS, add
  from smartobjects import Interaction, Slot, SmartObject
  ```
  with
  ```python
  from smartobjects import Interaction, Slot, SmartObject
  ```
- Replace
  ```python
      slots = [
          Slot(index=i, tile=add(tile, DIRECTIONS[d]), facing=(d + 3) % 6)
          for i, d in enumerate(slot_directions)
      ]
  ```
  with
  ```python
      slots = [Slot(index=i, direction=d) for i, d in enumerate(slot_directions)]
  ```

`Experiments/exp-01/src/ai/tasks.py`:
- Replace `from hexgrid import direction_index` with two lines:
  ```python
  from hexgrid import direction_index
  from smartobjects import slot_facing, slot_tile
  ```
- Replace
  ```python
          if claim is not None and actor.tile == claim.slot.tile:
              actor.facing = claim.slot.facing
  ```
  with
  ```python
          if claim is not None and actor.tile == slot_tile(claim.object, claim.slot):
              actor.facing = slot_facing(claim.slot)
  ```
- Replace `    return {claim.slot.tile} if claim is not None else None` with `    return {slot_tile(claim.object, claim.slot)} if claim is not None else None`.

`Experiments/exp-01/src/render.py`:
- Replace `from hexgrid import DIRECTIONS, all_tiles` with two lines:
  ```python
  from hexgrid import DIRECTIONS, all_tiles
  from smartobjects import slot_tile
  ```
- Replace `                center = to_screen(tile_to_world_px(slot.tile))` with `                center = to_screen(tile_to_world_px(slot_tile(obj, slot)))`.

`Experiments/exp-01/tests/test_tasks.py`:
- Replace `from smartobjects import Interaction, Slot, SmartObject` with `from smartobjects import Interaction, Slot, SmartObject, slot_tile`.
- Replace
  ```python
  def make_ctx(object_tile=(6, 0), slot_tile=(5, 0), facing=0, duration=0.5):
      world = World()
      obj = SmartObject(
          "A", object_tile, frozenset({"Object.A"}), [Slot(0, slot_tile, facing)],
  ```
  with
  ```python
  def make_ctx(object_tile=(6, 0), slot_direction=3, duration=0.5):
      """One object A; with the defaults its only slot is at (5, 0) and the actor starts at (0, 0)."""
      world = World()
      obj = SmartObject(
          "A", object_tile, frozenset({"Object.A"}), [Slot(0, slot_direction)],
  ```
- Replace `    assert ctx["Claim"].slot.tile == (5, 0)` with `    assert slot_tile(ctx["Claim"].object, ctx["Claim"].slot) == (5, 0)`.
- Replace `    ctx, obj, _ = make_ctx(object_tile=(5, 1), slot_tile=(5, 0), facing=5)` with `    ctx, obj, _ = make_ctx(object_tile=(5, 1), slot_direction=2)`.

`Experiments/exp-01/tests/test_layout.py`:
- Replace `from layout import ACTOR_START, WALLS, build_world` with two lines:
  ```python
  from layout import ACTOR_START, WALLS, build_world
  from smartobjects import slot_facing, slot_tile
  ```
- Replace
  ```python
              assert world.is_walkable(slot.tile)
              assert add(slot.tile, DIRECTIONS[slot.facing]) == obj.tile
  ```
  with
  ```python
              assert world.is_walkable(slot_tile(obj, slot))
              assert add(slot_tile(obj, slot), DIRECTIONS[slot_facing(slot)]) == obj.tile
  ```
- Replace `            assert astar(world, ACTOR_START, {slot.tile}) is not None, (obj.name, slot.index)` with `            assert astar(world, ACTOR_START, {slot_tile(obj, slot)}) is not None, (obj.name, slot.index)`.
- Replace `    assert [world.zone_of(s.tile) for s in objects["B"].slots] == ["West", "East"]` with `    assert [world.zone_of(slot_tile(objects["B"], s)) for s in objects["B"].slots] == ["West", "East"]`.

`Experiments/exp-01/tests/test_world.py`:
- Replace `[Slot(0, (3, 0), 0)]` with `[Slot(0, 3)]`.

- [ ] **Step 5: Run the full suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest -q && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: `92 passed`, and the headless run exits 0 with no traceback.
Also run `rg -n "slot\.tile|slot\.facing" /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/src /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01/tests`. Expected: no matches.

- [ ] **Step 6: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src Experiments/exp-01/tests
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: slots derive their tile from their object; in-use tracking" -m "<your Co-Authored-By trailer>"
```

---

### Task 3: Three zones, live blocking, new layout and rules

**Files:**
- Replace (full content below): `src/world.py`, `src/layout.py`, `tests/test_world.py`, `tests/test_layout.py`, `tests/test_tree_def.py`, `tests/test_sim.py`
- Modify (exact edits below): `src/ai/tree_def.py`, `tests/test_tasks.py`

**Interfaces:**
- Consumes: Task 2's `SmartObject` (`home_zone`, `next_tile`), `Slot(index, direction)`, `SmartObjectSubsystem`.
- Produces:
  - **`world`:**
    - `ZONES = ("NE", "S", "NW")`
    - `zone_of(tile) -> str`
    - `World(radius=MAP_RADIUS, walls=())` with `.radius`, `.walls`, `.smart_objects`, `.add_wall`, `.add_object`, the live `.blocked` property, `.is_walkable`, `.walkable_tiles`, `.zone_of` and `.can_object_enter(obj, tile, actor)`
    - `Actor`, unchanged
  - **`layout`:**
    - `ACTOR_START`, `WALLS`
    - `OBJECTS`: rows of (name, tile, slot_directions, home_zone, pauses)
    - `set_last_used`, `placeholder_interactions`
    - `make_object(name, tile, slot_directions, home_zone="", pauses_during_use=True)`
    - `build_world()`
  - **`ai.tree_def`:** `RULES` as `{target: [(last_used, "==" | "!=", zone), ...]}` and `rule_condition(last_used, op, zone)`.

- [ ] **Step 1: Write the new tests**

Replace `Experiments/exp-01/tests/test_world.py` with:

```python
from collections import Counter

import pytest

from hexgrid import all_tiles
from smartobjects import Slot, SmartObject
from world import ZONES, Actor, World, zone_of


def make_object(tile, home_zone="NE"):
    return SmartObject("A", tile, frozenset({"Object.A"}), [Slot(0, 3)], [], home_zone=home_zone)


@pytest.mark.parametrize(
    "tile, zone",
    [
        ((6, -3), "NE"), ((12, 0), "NE"), ((12, -12), "NE"),  # q largest
        ((-3, 6), "S"), ((0, 12), "S"), ((-12, 12), "S"),  # r largest
        ((-3, -3), "NW"), ((-12, 0), "NW"), ((0, -12), "NW"),  # s largest
    ],
)
def test_zone_sectors(tile, zone):
    assert zone_of(tile) == zone
    assert World().zone_of(tile) == zone


@pytest.mark.parametrize(
    "tile, zone",
    [
        ((0, 0), "NE"),  # q == r == s
        ((2, 2), "NE"),  # q == r > s
        ((1, -2), "NE"),  # q == s > r
        ((-2, 1), "S"),  # r == s > q
    ],
)
def test_zone_ties_break_q_then_r_then_s(tile, zone):
    assert zone_of(tile) == zone


def test_every_tile_is_in_one_of_three_zones():
    counts = Counter(zone_of(t) for t in all_tiles())
    assert set(counts) == set(ZONES)
    assert counts == {"NE": 163, "S": 156, "NW": 150}


def test_walls_objects_and_out_of_bounds_are_not_walkable():
    world = World(walls=[(2, 0)])
    obj = make_object((4, 0))
    world.add_object(obj)
    assert world.smart_objects.objects == [obj]
    assert not world.is_walkable((2, 0))
    assert not world.is_walkable((4, 0))
    assert not world.is_walkable((13, 0))
    assert world.is_walkable((3, 0))


def test_object_next_tile_is_blocked_while_stepping():
    world = World()
    obj = make_object((4, 0))
    world.add_object(obj)
    obj.next_tile = (5, 0)
    assert not world.is_walkable((5, 0))
    assert world.blocked == {(4, 0), (5, 0)}
    obj.next_tile = None
    assert world.is_walkable((5, 0))


def test_blocking_follows_object_moves():
    world = World()
    obj = make_object((4, 0))
    world.add_object(obj)
    obj.tile = (1, 1)
    assert world.is_walkable((4, 0))
    assert not world.is_walkable((1, 1))
    assert world.blocked == {(1, 1)}


def test_add_wall_blocks_at_runtime():
    world = World()
    assert world.is_walkable((1, 0))
    world.add_wall((1, 0))
    assert not world.is_walkable((1, 0))
    assert (1, 0) in world.walls


def test_walkable_tiles_excludes_walls_and_objects():
    world = World(walls=[(0, 0)])
    assert len(world.walkable_tiles()) == 468
    world.add_object(make_object((3, 0)))
    assert len(world.walkable_tiles()) == 467


def test_can_object_enter():
    world = World(walls=[(5, -1)])
    obj = make_object((3, 0), home_zone="NE")
    world.add_object(obj)
    actor = Actor(tile=(8, 0), next_tile=(9, 0))
    assert world.can_object_enter(obj, (4, 0), actor)
    assert not world.can_object_enter(obj, (0, 5), actor)  # S zone
    assert not world.can_object_enter(obj, (5, -1), actor)  # wall
    assert not world.can_object_enter(obj, (8, 0), actor)  # actor tile
    assert not world.can_object_enter(obj, (9, 0), actor)  # actor next tile


def test_actor_defaults():
    actor = Actor(tile=(1, 2))
    assert (actor.facing, actor.next_tile, actor.progress, actor.speed) == (0, None, 0.0, 3.0)
```

Replace `Experiments/exp-01/tests/test_layout.py` with:

```python
from ai.pathing import astar
from hexgrid import DIRECTIONS, add, all_tiles, in_bounds, neighbors
from layout import ACTOR_START, WALLS, build_world
from smartobjects import slot_facing, slot_tile
from world import zone_of


def objects_by_name(world):
    return {obj.name: obj for obj in world.smart_objects.objects}


def test_slots_are_walkable_and_face_their_object():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert world.is_walkable(slot_tile(obj, slot))
            assert add(slot_tile(obj, slot), DIRECTIONS[slot_facing(slot)]) == obj.tile


def test_every_slot_is_reachable_from_actor_start():
    world = build_world()
    for obj in world.smart_objects.objects:
        for slot in obj.slots:
            assert astar(world, ACTOR_START, {slot_tile(obj, slot)}) is not None, (obj.name, slot.index)


def test_objects_match_spec():
    objects = objects_by_name(build_world())
    assert sorted(objects) == ["A", "B", "C"]
    assert [(o.home_zone, o.pauses_during_use, len(o.slots)) for o in (objects["A"], objects["B"], objects["C"])] == [
        ("NW", True, 2),
        ("S", True, 2),
        ("NE", False, 2),
    ]
    for obj in objects.values():
        assert zone_of(obj.tile) == obj.home_zone


def test_actor_starts_walkable_in_nw_and_not_on_a_slot():
    world = build_world()
    assert zone_of(ACTOR_START) == "NW"
    assert world.is_walkable(ACTOR_START)
    slot_tiles = {slot_tile(o, s) for o in world.smart_objects.objects for s in o.slots}
    assert ACTOR_START not in slot_tiles


def test_walls_are_in_range_in_bounds_and_away_from_zone_borders():
    assert 30 <= len(set(WALLS)) <= 40
    for wall in WALLS:
        assert in_bounds(wall)
        assert all(zone_of(n) == zone_of(wall) for n in neighbors(wall)), wall


def test_each_zone_stays_connected_around_walls():
    walls = set(WALLS)
    for zone in ("NE", "S", "NW"):
        tiles = {t for t in all_tiles() if zone_of(t) == zone and t not in walls}
        start = next(iter(tiles))
        seen, stack = {start}, [start]
        while stack:
            for n in neighbors(stack.pop()):
                if n in tiles and n not in seen:
                    seen.add(n)
                    stack.append(n)
        assert seen == tiles, zone


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

Replace `Experiments/exp-01/tests/test_tree_def.py` with:

```python
import pytest

from ai.tree_def import build_tree, rule_condition

# Copied from the spec's rules table.
EXPECTED = {
    (None, "NW"): "GoUse(Nearest)",
    (None, "S"): "GoUse(Nearest)",
    (None, "NE"): "GoUse(Nearest)",
    ("A", "NW"): "GoUse(B)",
    ("A", "S"): "GoUse(C)",
    ("A", "NE"): "GoUse(C)",
    ("B", "NW"): "GoUse(A)",
    ("B", "S"): "GoUse(C)",
    ("B", "NE"): "GoUse(A)",
    ("C", "NW"): "GoUse(B)",
    ("C", "S"): "GoUse(B)",
    ("C", "NE"): "GoUse(A)",
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
        "LastUsed==C & Zone==NE",
        "LastUsed==B & Zone!=S",
    ]
    assert [c.name for c in tree.find("GoUse(Nearest)").conditions] == ["LastUsed==None"]


def test_rule_condition_rejects_unknown_operator():
    with pytest.raises(ValueError):
        rule_condition("A", "<", "NW")
```

Replace `Experiments/exp-01/tests/test_sim.py` with:

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


def test_long_run_has_no_errors_and_one_claim_at_most():
    sim = build_sim(seed=0)
    subsystem = sim.world.smart_objects
    for _ in range(120 * 60):
        sim.step(1 / 60)
        claims = [(obj, slot) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert claims == ([] if claim is None else [(claim.object, claim.slot)])
    assert not any("error" in text for _, text in sim.tree.log)
    assert sim.ctx["LastUsed"] is not None
```

In `Experiments/exp-01/tests/test_tasks.py`, inside `test_zone_evaluator_sets_zone_from_actor_tile`, replace `    assert ctx["Zone"] == "West"` with `    assert ctx["Zone"] == "NW"`.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest tests/test_world.py tests/test_layout.py tests/test_tree_def.py -q`
Expected:
- `test_world.py` fails at collection with `ImportError: cannot import name 'ZONES' from 'world'`.
- `test_layout.py` and `test_tree_def.py` fail, because the zones are still West/East and the rules still have two arguments.

- [ ] **Step 3: Replace `world.py` and `layout.py`**

Replace `Experiments/exp-01/src/world.py` with:

```python
"""The hex map (walls, moving objects, three zones) and the actor."""

from dataclasses import dataclass

from hexgrid import MAP_RADIUS, Tile, all_tiles, in_bounds
from smartobjects import SmartObject, SmartObjectSubsystem

ZONES = ("NE", "S", "NW")


def zone_of(tile: Tile) -> str:
    """Three 120-degree sectors, by the largest cube coordinate; ties go q, then r, then s."""
    q, r = tile
    s = -q - r
    if q >= r and q >= s:
        return "NE"
    if r >= s:
        return "S"
    return "NW"


class World:
    def __init__(self, radius: int = MAP_RADIUS, walls=()):
        self.radius = radius
        self.walls: set[Tile] = set(walls)
        self.smart_objects = SmartObjectSubsystem()

    def add_wall(self, tile: Tile) -> None:
        self.walls.add(tile)

    def add_object(self, obj: SmartObject) -> None:
        self.smart_objects.register(obj)

    @property
    def blocked(self) -> set[Tile]:
        """Walls plus every object's tile and, while it steps, its next tile. Always live."""
        tiles = set(self.walls)
        for obj in self.smart_objects.objects:
            tiles.add(obj.tile)
            if obj.next_tile is not None:
                tiles.add(obj.next_tile)
        return tiles

    def is_walkable(self, tile: Tile) -> bool:
        if not in_bounds(tile, self.radius) or tile in self.walls:
            return False
        return not any(tile == obj.tile or tile == obj.next_tile for obj in self.smart_objects.objects)

    def walkable_tiles(self) -> list[Tile]:
        blocked = self.blocked
        return [t for t in all_tiles(self.radius) if t not in blocked]

    def zone_of(self, tile: Tile) -> str:
        return zone_of(tile)

    def can_object_enter(self, obj: SmartObject, tile: Tile, actor) -> bool:
        return (
            self.is_walkable(tile)
            and zone_of(tile) == obj.home_zone
            and tile != actor.tile
            and tile != actor.next_tile
        )


@dataclass
class Actor:
    tile: Tile
    facing: int = 0
    next_tile: Tile | None = None
    progress: float = 0.0  # 0..1 from tile toward next_tile
    speed: float = 3.0  # tiles per second
```

Replace `Experiments/exp-01/src/layout.py` with:

```python
"""The starting layout for exp-01. All placeholder content: edit freely."""

from smartobjects import Interaction, Slot, SmartObject
from world import World

ACTOR_START = (-8, 2)  # NW

# Short segments inside each zone, none on or next to a zone border.
WALLS = (
    [(-8, r) for r in range(-2, 2)] + [(q, -7) for q in range(-2, 2)]  # NW
    + [(-6, 6), (-5, 5), (-4, 4), (-3, 3)]  # NW
    + [(q, 8) for q in range(-6, -2)] + [(3, r) for r in range(6, 10)]  # S
    + [(-7, 10), (-6, 10), (-5, 10), (-4, 10)]  # S
    + [(8, r) for r in range(-6, -2)] + [(q, -9) for q in range(6, 10)]  # NE
    + [(5, 1), (6, 0), (7, -1), (8, 0)]  # NE
)

# (name, start tile, slot directions from the object, home zone, pauses during use)
OBJECTS = (
    ("A", (-5, -2), (0, 5), "NW", True),
    ("B", (-2, 5), (2, 1), "S", True),
    ("C", (5, -2), (3, 4), "NE", False),
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


def make_object(name, tile, slot_directions, home_zone="", pauses_during_use=True):
    return SmartObject(
        name=name,
        tile=tile,
        tags=frozenset({f"Object.{name}"}),
        slots=[Slot(index=i, direction=d) for i, d in enumerate(slot_directions)],
        interactions=placeholder_interactions(name),
        home_zone=home_zone,
        pauses_during_use=pauses_during_use,
    )


def build_world() -> World:
    world = World(walls=WALLS)
    for name, tile, slot_directions, home_zone, pauses in OBJECTS:
        world.add_object(make_object(name, tile, slot_directions, home_zone, pauses))
    return world
```

The wall layout was checked by script:
- 36 walls;
- no wall on or next to a zone border;
- every zone's non-wall tiles are connected;
- objects, slots and the actor start aren't walls, and every slot is reachable.

`test_layout.py` enforces all of this.

- [ ] **Step 4: Update the rules in `tree_def.py` (exact edits)**

In `Experiments/exp-01/src/ai/tree_def.py`:
- Replace `"""The example StateTree for exp-00. The rules are placeholders: edit freely."""` with `"""The example StateTree for exp-01. The rules are placeholders: edit freely."""`.
- Replace
  ```python
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
  ```
  with
  ```python
  # For each object: (LastUsed, "==" or "!=", Zone) rows that send the actor to it.
  # Finishing in the last object's home zone goes forward (A->B->C->A);
  # finishing across a border goes backward.
  RULES = {
      "A": [("C", "==", "NE"), ("B", "!=", "S")],
      "B": [("A", "==", "NW"), ("C", "!=", "NE")],
      "C": [("B", "==", "S"), ("A", "!=", "NW")],
  }


  def rule_condition(last_used, op, zone):
      if op == "==":
          test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") == zone
      elif op == "!=":
          test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") != zone
      else:
          raise ValueError(f"unknown zone operator: {op!r}")
      return Condition(f"LastUsed=={last_used} & Zone{op}{zone}", test)
  ```
- Replace
  ```python
  [rule_condition(*pair) for pair in pairs], Mode.ANY)
          for target, pairs in RULES.items()
  ```
  with
  ```python
  [rule_condition(*row) for row in rows], Mode.ANY)
          for target, rows in RULES.items()
  ```

- [ ] **Step 5: Run the full suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest -q && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: `114 passed`, and the headless run exits 0. Every floor tile renders in the old "east" tint until Task 6. That's expected; don't fix it here.

- [ ] **Step 6: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src Experiments/exp-01/tests
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: three sector zones, live blocking, new layout and rules" -m "<your Co-Authored-By trailer>"
```

---

### Task 4: Wandering objects

**Files:**
- Create: `Experiments/exp-01/src/wander.py`, `Experiments/exp-01/tests/test_wander.py`
- Replace (full content below): `src/sim.py`, `tests/test_sim.py`

**Interfaces:**
- Consumes:
  - Task 3: `World.can_object_enter`, `World.walls`, `zone_of`, `layout.build_world`, `layout.ACTOR_START`.
  - Task 2: `SmartObjectSubsystem.is_in_use`, and `SmartObject.heading` / `next_tile` / `progress` / `pauses_during_use` / `home_zone`.
- Produces:
  - **`wander`:**
    - `MOVE_RATE`, `STEP_SPEED`, `TURN_FALLOFF`
    - `divergence(heading, direction) -> int`
    - `direction_weights(heading, falloff=TURN_FALLOFF) -> list[float]`
    - `choose_direction(heading, allowed, rng, falloff=TURN_FALLOFF) -> int | None`
    - `ObjectMover(world, actor, rng, move_rate=MOVE_RATE, step_speed=STEP_SPEED, falloff=TURN_FALLOFF)` with `.tick(dt)` and `.tick_object(obj, dt)`
  - **`sim`:** `Sim(world, actor, tree, ctx, mover)` with `.step(dt)`, which ticks the mover and then the tree, plus `build_sim(seed=0)`.

- [ ] **Step 1: Write the tests**

Create `Experiments/exp-01/tests/test_wander.py`:

```python
import random
from collections import Counter

import pytest

from hexgrid import DIRECTIONS, add, direction_index
from layout import ACTOR_START, build_world
from smartobjects import Slot, SmartObject
from wander import MOVE_RATE, STEP_SPEED, TURN_FALLOFF, ObjectMover, choose_direction, direction_weights, divergence
from world import Actor, World, zone_of

ALWAYS = 1e9  # a move_rate high enough that every idle tick starts a step


def make_world(tile=(4, 0), home_zone="NE", pauses=True):
    world = World()
    obj = SmartObject("A", tile, frozenset({"Object.A"}), [Slot(0, 3)], [], home_zone=home_zone,
                      pauses_during_use=pauses)
    world.add_object(obj)
    return world, obj


def test_placeholder_parameters():
    assert (MOVE_RATE, STEP_SPEED, TURN_FALLOFF) == (0.5, 1.5, 0.3)


@pytest.mark.parametrize(
    "heading, direction, expected",
    [(0, 0, 0), (0, 1, 1), (0, 5, 1), (0, 2, 2), (0, 4, 2), (0, 3, 3), (4, 1, 3), (5, 0, 1)],
)
def test_divergence(heading, direction, expected):
    assert divergence(heading, direction) == expected


def test_direction_weights_fall_off_with_divergence():
    assert direction_weights(0) == pytest.approx([1.0, 0.3, 0.09, 0.027, 0.09, 0.3])
    assert direction_weights(2) == pytest.approx([0.09, 0.3, 1.0, 0.3, 0.09, 0.027])


def test_choose_direction_returns_none_when_nothing_is_allowed():
    assert choose_direction(0, set(), random.Random(0)) is None


def test_choose_direction_only_returns_allowed_directions():
    rng = random.Random(1)
    assert {choose_direction(0, {2, 4}, rng) for _ in range(200)} == {2, 4}


def test_choose_direction_prefers_going_straight():
    rng = random.Random(2)
    counts = Counter(choose_direction(0, set(range(6)), rng) for _ in range(20000))
    by_divergence = [counts[0], counts[1] + counts[5], counts[2] + counts[4], counts[3]]
    assert by_divergence[0] > by_divergence[1] > by_divergence[2] > by_divergence[3]
    assert counts[0] / 20000 == pytest.approx(1.0 / 1.807, abs=0.02)


def test_choose_direction_renormalizes_over_allowed_directions():
    rng = random.Random(3)
    counts = Counter(choose_direction(0, {1, 3}, rng) for _ in range(20000))
    assert counts[1] / 20000 == pytest.approx(0.3 / 0.327, abs=0.02)


def test_step_start_frequency_matches_move_rate():
    world, obj = make_world()
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(4))
    starts = 0
    for _ in range(60000):  # 1000 idle seconds at 60 Hz
        mover.tick_object(obj, 1 / 60)
        if obj.next_tile is not None:
            starts += 1
            obj.next_tile = None  # stay idle so every tick is a fresh roll
    assert 425 <= starts <= 575  # expected 500


def test_step_completes_after_one_over_step_speed():
    world, obj = make_world()
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(5), move_rate=ALWAYS, step_speed=2.0)
    mover.tick_object(obj, 0.25)  # starts a step
    start, target = obj.tile, obj.next_tile
    assert target is not None and obj.heading == direction_index(start, target)
    mover.tick_object(obj, 0.25)
    assert obj.tile == start and obj.progress == pytest.approx(0.5)
    mover.tick_object(obj, 0.25)  # 0.5s = 1 / step_speed
    assert obj.tile == target and obj.next_tile is None and obj.progress == 0.0
    assert zone_of(obj.tile) == "NE"


def test_pausing_object_in_use_freezes_even_mid_step():
    world, obj = make_world(pauses=True)
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(6), move_rate=ALWAYS)
    mover.tick_object(obj, 0.1)
    mover.tick_object(obj, 0.1)
    frozen = (obj.tile, obj.next_tile, obj.progress)
    assert obj.next_tile is not None and obj.progress > 0
    world.smart_objects.set_in_use(obj, True)
    for _ in range(50):
        mover.tick_object(obj, 0.1)
    assert (obj.tile, obj.next_tile, obj.progress) == frozen
    world.smart_objects.set_in_use(obj, False)
    mover.tick_object(obj, 0.1)
    assert obj.progress > frozen[2] or obj.tile == frozen[1]


def test_non_pausing_object_moves_while_in_use():
    world, obj = make_world(pauses=False)
    world.smart_objects.set_in_use(obj, True)
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(7), move_rate=ALWAYS)
    mover.tick_object(obj, 0.1)
    assert obj.next_tile is not None


def test_no_step_when_every_direction_is_blocked():
    world, obj = make_world()
    for d in DIRECTIONS:
        world.add_wall(add(obj.tile, d))
    mover = ObjectMover(world, Actor(tile=(-10, 5)), random.Random(8), move_rate=ALWAYS)
    for _ in range(100):
        mover.tick_object(obj, 0.1)
    assert obj.next_tile is None and obj.tile == (4, 0)


@pytest.mark.parametrize("seed", range(3))
def test_long_run_objects_stay_in_zone_and_never_overlap(seed):
    world = build_world()
    actor = Actor(tile=ACTOR_START)
    mover = ObjectMover(world, actor, random.Random(seed))
    objects = world.smart_objects.objects
    for _ in range(120 * 60):
        mover.tick(1 / 60)
        occupied = []
        for obj in objects:
            for tile in (obj.tile, obj.next_tile):
                if tile is None:
                    continue
                assert zone_of(tile) == obj.home_zone
                assert tile not in world.walls
                assert tile != actor.tile
                occupied.append(tile)
        assert len(occupied) == len(set(occupied))
```

Replace `Experiments/exp-01/tests/test_sim.py` with:

```python
import pytest

from layout import ACTOR_START
from sim import build_sim
from world import zone_of


def test_build_sim_wires_context_and_mover():
    sim = build_sim(seed=0)
    assert sim.actor.tile == ACTOR_START
    assert sim.ctx["actor"] is sim.actor and sim.ctx["world"] is sim.world
    assert sim.mover.world is sim.world and sim.mover.actor is sim.actor and sim.mover.rng is sim.ctx["rng"]
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def watch_errors(sim):
    """Record every error log line, even ones the bounded log deque later drops."""
    errors = []
    write = sim.tree.write_log

    def spy(text):
        if "error" in text:
            errors.append(text)
        write(text)

    sim.tree.write_log = spy
    sim.ctx["log"] = spy
    return errors


@pytest.mark.parametrize("seed", range(5))
def test_long_run_invariants(seed):
    sim = build_sim(seed)
    errors = watch_errors(sim)
    subsystem = sim.world.smart_objects
    for _ in range(120 * 60):
        sim.step(1 / 60)
        claims = [(obj, slot) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert claims == ([] if claim is None else [(claim.object, claim.slot)])
        actor_tiles = {sim.actor.tile, sim.actor.next_tile} - {None}
        for obj in subsystem.objects:
            object_tiles = {obj.tile, obj.next_tile} - {None}
            assert all(zone_of(t) == obj.home_zone for t in object_tiles)
            assert not object_tiles & actor_tiles
    assert errors == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest tests/test_wander.py tests/test_sim.py -q`
Expected:
- `test_wander.py` fails at collection with `ModuleNotFoundError: No module named 'wander'`.
- `test_sim.py` fails, because `Sim` has no `mover`.

- [ ] **Step 3: Implement**

Create `Experiments/exp-01/src/wander.py`:

```python
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
```

Replace `Experiments/exp-01/src/sim.py` with:

```python
"""Wires the world, actor, object mover, StateTree and shared context together."""

import random
from dataclasses import dataclass

from ai.statetree import StateTree
from ai.tree_def import build_tree
from layout import ACTOR_START, build_world
from wander import ObjectMover
from world import Actor, World


@dataclass
class Sim:
    world: World
    actor: Actor
    tree: StateTree
    ctx: dict
    mover: ObjectMover

    def step(self, dt: float) -> None:
        self.mover.tick(dt)
        self.tree.tick(self.ctx, dt)


def build_sim(seed: int = 0) -> Sim:
    world = build_world()
    actor = Actor(tile=ACTOR_START)
    tree = build_tree()
    rng = random.Random(seed)
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
        "rng": rng,
        "log": tree.write_log,
    }
    return Sim(world, actor, tree, ctx, ObjectMover(world, actor, rng))
```

- [ ] **Step 4: Run the full suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest -q && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: `140 passed`, and the headless run exits 0.

The actor's tasks don't chase or re-plan until Task 5, so it abandons moving targets more often in this intermediate state. The invariants still hold.

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src Experiments/exp-01/tests
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: stochastic momentum object mover, wired into the sim" -m "<your Co-Authored-By trailer>"
```

---

### Task 5: The actor chases, re-plans, and tracks in-use

**Files:**
- Replace (full content below): `src/ai/tasks.py`, `src/ai/tree_def.py`, `tests/test_tasks.py`, `tests/test_tree_def.py`, `tests/test_sim.py`

**Interfaces:**
- Consumes: Task 2's `slot_tile`, `slot_facing`, `set_in_use` and `find(..., blocked_fn=)`; Task 3's `World.is_walkable` and live blocking; Task 4's `build_sim`.
- Produces:
  - `MoveTo(goal_fn, chase=False)`, which logs `replan: slot moved` and `replan: path blocked`.
  - `Interact`, which marks the object in use on enter, clears it on exit, and fails with the log line `interact: slot drifted away`.
  - `FindAndClaim`, which skips blocked slots.
  - In the tree:
    - every GoUse `MoveTo` uses `chase=True`;
    - every GoUse `Interact` has transitions `[(ON_COMPLETED, ROOT), (ON_FAILED, ROOT)]`;
    - `Wander/MoveTo` keeps `chase=False`.

- [ ] **Step 1: Write the tests**

Replace `Experiments/exp-01/tests/test_tasks.py` with:

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
from smartobjects import Interaction, Slot, SmartObject, slot_tile
from world import Actor, World, zone_of


def set_last_used(name):
    def effect(ctx):
        ctx["LastUsed"] = name
    return effect


def make_ctx(object_tile=(6, 0), slot_direction=3, duration=0.5, pauses=True):
    """One object A; with the defaults its only slot is at (5, 0) and the actor starts at (0, 0)."""
    world = World()
    obj = SmartObject(
        "A", object_tile, frozenset({"Object.A"}), [Slot(0, slot_direction)],
        [Interaction("A.Only", duration, (set_last_used("A"),))],
        home_zone=zone_of(object_tile), pauses_during_use=pauses,
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


def claim_a(ctx):
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.SUCCEEDED


def test_zone_evaluator_sets_zone_from_actor_tile():
    ctx, _, _ = make_ctx()
    ctx["actor"].tile = (-3, 0)
    ZoneEvaluator().tick(ctx, 0.1)
    assert ctx["Zone"] == "NW"


def test_find_and_claim_success():
    ctx, obj, log = make_ctx()
    claim_a(ctx)
    assert ctx["Target"] == "A"
    assert slot_tile(ctx["Claim"].object, ctx["Claim"].slot) == (5, 0)
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


def test_find_and_claim_skips_a_blocked_slot():
    ctx, _, _ = make_ctx()
    ctx["world"].add_wall((5, 0))
    task = FindAndClaim({"Object.A"})
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.FAILED


def test_move_to_walks_to_claimed_slot_and_faces_object():
    # Object is SE of the slot, so the last step (heading E) must not decide the final facing.
    ctx, obj, _ = make_ctx(object_tile=(5, 1), slot_direction=2)
    claim_a(ctx)
    move = MoveTo(claimed_slot_goal, chase=True)
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


def test_move_to_replans_around_a_new_wall():
    ctx, _, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    wall = ctx["Path"][3]
    ctx["world"].add_wall(wall)
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0)
    assert "replan: path blocked" in log


def test_move_to_replans_around_an_object_stepping_into_the_path():
    ctx, obj, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    obj.next_tile = ctx["Path"][2]  # the object starts stepping onto the path
    assert run(move, ctx) is Status.SUCCEEDED
    assert "replan: path blocked" in log


def test_move_to_fails_when_the_goal_gets_walled_in():
    ctx, _, log = make_ctx()
    move = MoveTo(lambda ctx: {(5, 0)})
    move.enter(ctx)
    for tile in [(6, -1), (5, -1), (4, 0), (4, 1), (5, 1)]:  # (6, 0) is the object
        ctx["world"].add_wall(tile)
    assert run(move, ctx) is Status.FAILED
    assert "replan: path blocked" in log


def test_move_to_chases_a_moving_slot():
    ctx, obj, log = make_ctx()
    claim_a(ctx)
    move = MoveTo(claimed_slot_goal, chase=True)
    move.enter(ctx)
    move.tick(ctx, 0.5)
    obj.tile = (6, 2)  # the slot moves from (5, 0) to (5, 2)
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 2)
    assert "replan: slot moved" in log


def test_move_to_without_chase_keeps_its_first_goal():
    ctx, _, log = make_ctx()
    ctx["goal"] = {(5, 0)}
    move = MoveTo(lambda ctx: ctx["goal"])
    move.enter(ctx)
    ctx["goal"] = {(0, 5)}
    assert run(move, ctx) is Status.SUCCEEDED
    assert ctx["actor"].tile == (5, 0)
    assert not any(text.startswith("replan") for text in log)


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


def test_interact_applies_effects_after_duration_and_marks_in_use():
    ctx, obj, _ = make_ctx(duration=0.5)
    claim_a(ctx)
    ctx["actor"].tile = (5, 0)
    task = Interact()
    task.enter(ctx)
    subsystem = ctx["world"].smart_objects
    assert ctx["Interaction"].name == "A.Only"
    assert subsystem.is_in_use(obj)
    assert task.tick(ctx, 0.3) is Status.RUNNING
    assert ctx["LastUsed"] is None
    assert ctx["InteractionElapsed"] == pytest.approx(0.3)
    assert task.tick(ctx, 0.3) is Status.SUCCEEDED
    assert ctx["LastUsed"] == "A"
    assert ctx["Interaction"] is None
    task.exit(ctx)
    assert not subsystem.is_in_use(obj)


def test_interact_fails_when_the_slot_drifts_away():
    ctx, obj, log = make_ctx(duration=5.0, pauses=False)
    claim_a(ctx)
    ctx["actor"].tile = (5, 0)
    task = Interact()
    task.enter(ctx)
    assert task.tick(ctx, 0.1) is Status.RUNNING
    obj.tile = (7, 0)  # slot moves to (6, 0)
    assert task.tick(ctx, 0.1) is Status.FAILED
    assert ctx["LastUsed"] is None
    assert "interact: slot drifted away" in log
    task.exit(ctx)
    assert not ctx["world"].smart_objects.is_in_use(obj)


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
            State("MoveTo", task=MoveTo(claimed_slot_goal, chase=True), transitions=[
                Transition(Trigger.ON_COMPLETED, "GoUse(A)/Interact"),
                Transition(Trigger.ON_FAILED, "Idle"),
            ]),
            State("Interact", task=Interact(), transitions=[
                Transition(Trigger.ON_COMPLETED, ROOT),
                Transition(Trigger.ON_FAILED, ROOT),
            ]),
        ]),
        State("Idle", task=Wait(100.0)),
    ]), evaluators=[ZoneEvaluator()])


def run_until(tree, ctx, leaf_path, max_ticks=1000):
    for _ in range(max_ticks):
        tree.tick(ctx, 0.1)
        if tree.leaf is not None and tree.leaf.path == leaf_path:
            return
    raise AssertionError(f"tree never reached {leaf_path}")


def test_claim_released_when_go_use_completes():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    run_until(tree, ctx, "Idle")
    assert ctx["LastUsed"] == "A"
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert not ctx["world"].smart_objects.is_in_use(obj)
    assert ctx["Claim"] is None and ctx["Target"] is None
    assert "release A / slot 0" in log


def test_claim_released_when_move_fails_partway():
    ctx, obj, log = make_ctx()
    tree = go_use_tree()
    tree.tick(ctx, 0.1)  # claims, then moves on to MoveTo, which plans its path
    assert tree.leaf.path == "GoUse(A)/MoveTo"
    for tile in [(6, -1), (5, -1), (4, 0), (4, 1), (5, 1)]:  # wall the slot in
        ctx["world"].add_wall(tile)
    run_until(tree, ctx, "Idle")
    assert ctx["LastUsed"] is None
    assert not ctx["world"].smart_objects.is_claimed(obj, obj.slots[0])
    assert ctx["Claim"] is None
    assert ctx["actor"].tile != (5, 0)


def test_in_use_and_claim_cleared_when_tree_resets_mid_interaction():
    ctx, obj, _ = make_ctx(duration=5.0)
    tree = go_use_tree()
    run_until(tree, ctx, "GoUse(A)/Interact")
    subsystem = ctx["world"].smart_objects
    assert subsystem.is_in_use(obj)
    tree.reset(ctx)
    assert not subsystem.is_in_use(obj)
    assert not subsystem.is_claimed(obj, obj.slots[0])
```

Replace `Experiments/exp-01/tests/test_tree_def.py` with:

```python
import pytest

from ai.statetree import ROOT, Trigger
from ai.tree_def import build_tree, rule_condition

# Copied from the spec's rules table.
EXPECTED = {
    (None, "NW"): "GoUse(Nearest)",
    (None, "S"): "GoUse(Nearest)",
    (None, "NE"): "GoUse(Nearest)",
    ("A", "NW"): "GoUse(B)",
    ("A", "S"): "GoUse(C)",
    ("A", "NE"): "GoUse(C)",
    ("B", "NW"): "GoUse(A)",
    ("B", "S"): "GoUse(C)",
    ("B", "NE"): "GoUse(A)",
    ("C", "NW"): "GoUse(B)",
    ("C", "S"): "GoUse(B)",
    ("C", "NE"): "GoUse(A)",
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
        "LastUsed==C & Zone==NE",
        "LastUsed==B & Zone!=S",
    ]
    assert [c.name for c in tree.find("GoUse(Nearest)").conditions] == ["LastUsed==None"]


def test_rule_condition_rejects_unknown_operator():
    with pytest.raises(ValueError):
        rule_condition("A", "<", "NW")


def test_go_use_chases_and_interact_failure_returns_to_root():
    tree = build_tree()
    for name in ["GoUse(A)", "GoUse(B)", "GoUse(C)", "GoUse(Nearest)"]:
        assert tree.find(f"{name}/MoveTo").task.chase is True
        transitions = [(t.trigger, t.target) for t in tree.find(f"{name}/Interact").transitions]
        assert transitions == [(Trigger.ON_COMPLETED, ROOT), (Trigger.ON_FAILED, ROOT)]
    assert tree.find("Wander/MoveTo").task.chase is False
```

Replace `Experiments/exp-01/tests/test_sim.py` with:

```python
import pytest

from layout import ACTOR_START
from sim import build_sim
from world import zone_of


def test_build_sim_wires_context_and_mover():
    sim = build_sim(seed=0)
    assert sim.actor.tile == ACTOR_START
    assert sim.ctx["actor"] is sim.actor and sim.ctx["world"] is sim.world
    assert sim.mover.world is sim.world and sim.mover.actor is sim.actor and sim.mover.rng is sim.ctx["rng"]
    for key in ["Zone", "LastUsed", "Target", "Claim", "Interaction", "Path"]:
        assert sim.ctx[key] is None
    sim.ctx["log"]("hello")
    assert list(sim.tree.log)[-1][1] == "hello"


def watch_errors(sim):
    """Record every error log line, even ones the bounded log deque later drops."""
    errors = []
    write = sim.tree.write_log

    def spy(text):
        if "error" in text:
            errors.append(text)
        write(text)

    sim.tree.write_log = spy
    sim.ctx["log"] = spy
    return errors


@pytest.mark.parametrize("seed", range(5))
def test_long_run_invariants(seed):
    sim = build_sim(seed)
    errors = watch_errors(sim)
    subsystem = sim.world.smart_objects
    for _ in range(120 * 60):
        sim.step(1 / 60)
        claims = [(obj, slot) for obj in subsystem.objects for slot in obj.slots if subsystem.is_claimed(obj, slot)]
        claim = sim.ctx["Claim"]
        assert claims == ([] if claim is None else [(claim.object, claim.slot)])
        actor_tiles = {sim.actor.tile, sim.actor.next_tile} - {None}
        for obj in subsystem.objects:
            object_tiles = {obj.tile, obj.next_tile} - {None}
            assert all(zone_of(t) == obj.home_zone for t in object_tiles)
            assert not object_tiles & actor_tiles
    assert errors == []


def test_all_objects_get_used_within_a_minute_on_seed_0():
    sim = build_sim(seed=0)
    used = set()
    for _ in range(60 * 60):
        sim.step(1 / 60)
        if sim.ctx["LastUsed"] is not None:
            used.add(sim.ctx["LastUsed"])
    assert used == {"A", "B", "C"}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest tests/test_tasks.py tests/test_tree_def.py tests/test_sim.py -q`
Expected failures:
- `MoveTo() got an unexpected keyword argument 'chase'`;
- the re-plan and drift log assertions;
- `test_go_use_chases_and_interact_failure_returns_to_root`.

`test_all_objects_get_used_within_a_minute_on_seed_0` may pass or fail at this point. Record which.

- [ ] **Step 3: Implement**

Replace `Experiments/exp-01/src/ai/tasks.py` with:

```python
"""StateTree tasks and evaluators for the actor: find/claim Smart Objects, chase and walk, interact, wait."""

from ai.pathing import astar
from ai.statetree import Evaluator, Status, Task
from hexgrid import direction_index
from smartobjects import slot_facing, slot_tile


class ZoneEvaluator(Evaluator):
    def tick(self, ctx, dt):
        ctx["Zone"] = ctx["world"].zone_of(ctx["actor"].tile)


class FindAndClaim(Task):
    """Claims the nearest free, unblocked slot on an object matching the tag query."""

    def __init__(self, tag_query):
        self.tag_query = frozenset(tag_query)
        self.status = Status.FAILED

    def enter(self, ctx):
        self.status = Status.FAILED
        world = ctx["world"]
        subsystem = world.smart_objects
        actor = ctx["actor"]
        found = subsystem.find(self.tag_query, near=actor.tile, blocked_fn=lambda t: not world.is_walkable(t))
        for obj, slot in found:
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
    """Walks the actor to the goal tiles along an A* path.

    Re-plans when the next path tile gets blocked. With `chase=True` the goal is
    re-read each time the actor reaches a tile, and a moved goal triggers a re-plan.
    """

    def __init__(self, goal_fn, chase: bool = False):
        self.goal_fn = goal_fn
        self.chase = chase
        self.goals = None
        self.path = None
        self.index = 0

    def enter(self, ctx):
        actor = ctx["actor"]
        actor.next_tile = None
        actor.progress = 0.0
        self.goals = self.goal_fn(ctx)
        self._plan(ctx)

    def tick(self, ctx, dt):
        actor, world = ctx["actor"], ctx["world"]
        remaining = actor.speed * dt
        while True:
            if actor.next_tile is None:
                if self.chase:
                    goals = self.goal_fn(ctx)
                    if goals != self.goals:
                        self.goals = goals
                        ctx["log"]("replan: slot moved")
                        self._plan(ctx)
                if self.path is None:
                    return Status.FAILED
                if self.index == len(self.path) - 1:
                    self._face_claimed_object(ctx)
                    return Status.SUCCEEDED
                if remaining <= 0:
                    return Status.RUNNING
                next_tile = self.path[self.index + 1]
                if not world.is_walkable(next_tile):
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

    def _plan(self, ctx):
        actor = ctx["actor"]
        self.path = astar(ctx["world"], actor.tile, self.goals) if self.goals else None
        self.index = 0
        ctx["Path"] = self.path

    @staticmethod
    def _face_claimed_object(ctx):
        claim = ctx.get("Claim")
        actor = ctx["actor"]
        if claim is not None and actor.tile == slot_tile(claim.object, claim.slot):
            actor.facing = slot_facing(claim.slot)


class Interact(Task):
    """Runs one of the claimed object's advertised interactions, picked at random.

    Marks the object in use for the duration, and fails if the slot drifts away from the actor.
    """

    def __init__(self):
        self.interaction = None
        self.elapsed = 0.0
        self.object = None

    def enter(self, ctx):
        claim = ctx.get("Claim")
        self.object = claim.object if claim is not None else None
        if self.object is not None:
            ctx["world"].smart_objects.set_in_use(self.object, True)
        options = self.object.interactions if self.object is not None else []
        self.interaction = ctx["rng"].choice(options) if options else None
        self.elapsed = 0.0
        ctx["Interaction"] = self.interaction
        ctx["InteractionElapsed"] = 0.0

    def tick(self, ctx, dt):
        if self.interaction is None:
            return Status.FAILED
        claim = ctx.get("Claim")
        if claim is None or ctx["actor"].tile != slot_tile(claim.object, claim.slot):
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
        if self.object is not None:
            ctx["world"].smart_objects.set_in_use(self.object, False)
            self.object = None
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
```

Replace `Experiments/exp-01/src/ai/tree_def.py` with:

```python
"""The example StateTree for exp-01. The rules are placeholders: edit freely."""

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

# For each object: (LastUsed, "==" or "!=", Zone) rows that send the actor to it.
# Finishing in the last object's home zone goes forward (A->B->C->A);
# finishing across a border goes backward.
RULES = {
    "A": [("C", "==", "NE"), ("B", "!=", "S")],
    "B": [("A", "==", "NW"), ("C", "!=", "NE")],
    "C": [("B", "==", "S"), ("A", "!=", "NW")],
}


def rule_condition(last_used, op, zone):
    if op == "==":
        test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") == zone
    elif op == "!=":
        test = lambda ctx: ctx.get("LastUsed") == last_used and ctx.get("Zone") != zone
    else:
        raise ValueError(f"unknown zone operator: {op!r}")
    return Condition(f"LastUsed=={last_used} & Zone{op}{zone}", test)


def go_use_state(name, tag_query, conditions, mode):
    return State(name, conditions=conditions, mode=mode, on_exit=release_claim, children=[
        State("FindAndClaim", task=FindAndClaim(tag_query), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/MoveTo"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("MoveTo", task=MoveTo(claimed_slot_goal, chase=True), transitions=[
            Transition(Trigger.ON_COMPLETED, f"{name}/Interact"),
            Transition(Trigger.ON_FAILED, "Wander"),
        ]),
        State("Interact", task=Interact(), transitions=[
            Transition(Trigger.ON_COMPLETED, ROOT),
            Transition(Trigger.ON_FAILED, ROOT),
        ]),
    ])


def build_tree() -> StateTree:
    children = [
        go_use_state(f"GoUse({target})", {f"Object.{target}"}, [rule_condition(*row) for row in rows], Mode.ANY)
        for target, rows in RULES.items()
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

- [ ] **Step 4: Run the full suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest -q && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: `149 passed`, and the headless run exits 0.

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src Experiments/exp-01/tests
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: actor chases moving slots, re-plans, tracks in-use" -m "<your Co-Authored-By trailer>"
```

---

### Task 6: Render moving objects

**Files:**
- Replace (full content below): `Experiments/exp-01/src/render.py`
- Test: existing `tests/test_main.py` (headless path) plus a visual check

**Interfaces:**
- Consumes:
  - `zone_of` via `World.zone_of`, `World.is_walkable`;
  - `slot_tile`, `SmartObjectSubsystem.is_claimed` / `is_in_use`;
  - `SmartObject.tile` / `next_tile` / `progress` / `heading` / `pauses_during_use`.
- Produces:
  - `render.object_world_px(obj)`;
  - `COLORS` keys `zone_NE`, `zone_S`, `zone_NW`, `slot_blocked` and `pause`;
  - `Renderer._draw_object(world, obj, center)`.

  Everything else in `render.py` is unchanged from exp-00.

- [ ] **Step 1: Replace `render.py`**

Replace `Experiments/exp-01/src/render.py` with:

```python
"""Pygame drawing: the isometric hex world view and the brain panel."""

import math

import pygame

from hexgrid import DIRECTIONS, all_tiles
from smartobjects import slot_tile

WINDOW_SIZE = (1600, 900)
VIEW_SIZE = (1180, 900)
PANEL_RECT = pygame.Rect(1180, 0, 420, 900)
LINE = 17
LOG_LINES = 12

HEX_SIZE = 64 / math.sqrt(3)  # corner radius; a pointy-top hex is sqrt(3) * size = 64px across
SQUASH = 0.6  # vertical squash for the tilted look
WALL_HEIGHT = 20
OBJECT_HEIGHT = 30
CULL_MARGIN = 80

COLORS = {
    "void": (18, 20, 26),
    "zone_NE": (104, 94, 70),
    "zone_S": (70, 96, 78),
    "zone_NW": (78, 84, 112),
    "grid": (40, 46, 44),
    "path": (240, 220, 120),
    "claimed": (250, 240, 170),
    "slot_blocked": (90, 90, 96),
    "pause": (250, 250, 250),
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


def object_world_px(obj):
    x0, y0 = tile_to_world_px(obj.tile)
    if obj.next_tile is None:
        return (x0, y0)
    x1, y1 = tile_to_world_px(obj.next_tile)
    t = obj.progress
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
            base = COLORS[f"zone_{world.zone_of(tile)}"]
            corners = hex_corners(center)
            pygame.draw.polygon(view, shade(base, 1.0 - 0.05 * ((tile[0] - tile[1]) % 3)), corners)
            pygame.draw.polygon(view, COLORS["grid"], corners, 1)

        for tile in (ctx.get("Path") or [])[1:]:
            pygame.draw.circle(view, COLORS["path"], to_screen(tile_to_world_px(tile)), 4)

        for obj in world.smart_objects.objects:
            object_px = object_world_px(obj)
            object_center = to_screen(object_px)
            base_x, base_y = tile_to_world_px(obj.tile)
            for slot in obj.slots:
                tile = slot_tile(obj, slot)
                # Slots ride along with the object's in-between position.
                slot_x, slot_y = tile_to_world_px(tile)
                center = to_screen((object_px[0] + slot_x - base_x, object_px[1] + slot_y - base_y))
                color = OBJECT_COLORS.get(obj.name, COLORS["wall"]) if world.is_walkable(tile) else COLORS["slot_blocked"]
                corners = hex_corners(center, scale=0.45)
                if world.smart_objects.is_claimed(obj, slot):
                    pygame.draw.polygon(view, COLORS["claimed"], corners)
                pygame.draw.polygon(view, color, corners, 2)
                tip = (center[0] + (object_center[0] - center[0]) * 0.35, center[1] + (object_center[1] - center[1]) * 0.35)
                pygame.draw.line(view, color, center, tip, 2)

        # Raised things and the actor, back to front.
        drawables = [(tile_to_world_px(t)[1], "wall", t) for t in world.walls]
        drawables += [(object_world_px(o)[1], "object", o) for o in world.smart_objects.objects]
        actor_px = actor_world_px(sim.actor)
        drawables.append((actor_px[1] + 0.1, "actor", actor_px))
        for _, kind, item in sorted(drawables, key=lambda d: d[0]):
            if kind == "wall":
                center = to_screen(tile_to_world_px(item))
                if self._visible(center):
                    self._draw_column(center, WALL_HEIGHT, COLORS["wall"])
            elif kind == "object":
                center = to_screen(object_world_px(item))
                if self._visible(center):
                    self._draw_object(world, item, center)
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

    def _draw_object(self, world, obj, center):
        view = self.view
        self._draw_column(center, OBJECT_HEIGHT, OBJECT_COLORS.get(obj.name, COLORS["wall"]))
        top = (center[0], center[1] - OBJECT_HEIGHT)
        label = self.big.render(obj.name, True, COLORS["text_active"])
        view.blit(label, label.get_rect(center=top))
        # Heading tick from the edge of the column top.
        hx, hy = tile_to_world_px(DIRECTIONS[obj.heading])
        length = math.hypot(hx, hy)
        ux, uy = hx / length, hy / length
        start = (top[0] + ux * HEX_SIZE * 0.55, top[1] + uy * HEX_SIZE * 0.55)
        end = (top[0] + ux * HEX_SIZE * 0.95, top[1] + uy * HEX_SIZE * 0.95)
        pygame.draw.line(view, COLORS["text_active"], start, end, 3)
        if obj.pauses_during_use and world.smart_objects.is_in_use(obj):
            for dx in (-12, 8):
                pygame.draw.rect(view, COLORS["pause"], pygame.Rect(top[0] + dx, top[1] - 34, 4, 12))

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

- [ ] **Step 2: Run the suite**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest -q`
Expected: `149 passed`.

- [ ] **Step 3: Visual check**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && rm -rf screenshots && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 2400 --speed 2 --screenshot-dir screenshots --screenshot-every 150`

`screenshots/` is gitignored. Open at least six screenshots spread across the run with the Read tool and confirm:
- **Zone tints:** three floor tints (tan NE, green S, blue NW) meeting at the map center along straight hex lines.
- **Objects move:** A, B and C are in different positions across screenshots, each staying inside its own tint. Each has a short white heading tick on its column top.
- **Slots:** markers sit next to their object and move with it. The claimed slot is filled pale yellow. A slot on a wall or another object is drawn dim grey, if one occurs.
- **Path and log:** path dots lead from the actor to its target slot. The TRANSITION LOG shows at least one `replan: slot moved` or `replan: path blocked` line across the run.
- **Pause marker:** while the actor interacts with A or B, a two-bar pause marker shows above that object's column and the object doesn't move between nearby screenshots.
- **Brain panel:** the tree shows conditions like `LastUsed==C & Zone==NE` and `LastUsed==B & Zone!=S`. The CONTEXT `Zone:` shows NE, S or NW.
- **No clipping:** nothing overflows the panel.

If something is wrong, fix `render.py` within the spec's "Rendering" section and re-run. Describe what you saw in your report.

- [ ] **Step 4: Verify the manifest's commands**

Run: `cd /home/lexa/DevProjects/_GameDev/MuraBito/Experiments/exp-01 && uv run pytest && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames 30`
Expected: all pass, and the run exits 0.

- [ ] **Step 5: Commit**

```bash
git -C /home/lexa/DevProjects/_GameDev/MuraBito rev-parse --abbrev-ref HEAD   # must print exp-01-impl
git -C /home/lexa/DevProjects/_GameDev/MuraBito add Experiments/exp-01/src/render.py
git -C /home/lexa/DevProjects/_GameDev/MuraBito commit -m "exp-01: render zone tints, moving objects and slots, heading and pause markers" -m "<your Co-Authored-By trailer>"
```
