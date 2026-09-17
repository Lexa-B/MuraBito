# exp-01 — Wandering Smart Objects: design

**Date:** 2026-09-17
**Location:** `experiments/exp-01/`
**Stack:** Python 3.13, pygame 2.6.1, pytest; uv-managed (`uv add`, `uv run`)
**Based on:** exp-00, as merged to `main` at `d7c0e2b`. The exp-00 spec is at `experiments/exp-00/docs/specs/2026-09-17-exp-00-statetree-visualizer-design.md`.

## Purpose

exp-01 is almost the same as exp-00, except the Smart Objects slowly wander around. Each object stays inside its own zone of a map now split into three, and moves with stochastic momentum. The actor has to chase moving slots, and where an object has drifted to feeds back into the actor's decisions.

## Relationship to exp-00

- **A self-contained copy.** `experiments/exp-01/` starts as a full copy of `experiments/exp-00/`: `src/`, `tests/`, `pyproject.toml`, `uv.lock` and `.python-version`. It excludes `.venv/`, `screenshots/` and `docs/`. The uv project name becomes `murabito-exp-01`.
- **exp-00 is frozen.** Nothing under `experiments/exp-00/` changes.
- **Unchanged from exp-00** unless a section below says otherwise:
  - the hex grid (radius 12, pointy-top, axial);
  - A\*;
  - the StateTree engine, including the unselectable-target fallback fix;
  - the camera;
  - the window and panel layout;
  - controls and headless flags;
  - the Wander branch.
- **Manifest.** `experiments/manifest.md` gets an exp-01 entry.

## Zones (`src/world.py`)

The map splits into **three 120° sectors** that meet at the center. Each sector is one of the three diamonds the hexagon divides into.

- **Assignment.** For a tile `(q, r)`, let `s = -q - r`:
  - if `q >= r` and `q >= s`, the zone is **NE**;
  - otherwise, if `r >= s`, it's **S**;
  - otherwise, **NW**.
- **Ties** are broken by the order in the rule (q, then r, then s). Every tile belongs to exactly one zone, and the center tile `(0, 0)` is NE.
- **Where the names come from.** The largest q points up-right on screen, the largest r points down, and the largest s points up-left.
- **Signature.** `World.zone_of(tile) -> "NE" | "S" | "NW"`.
- **Rendering.** Each zone gets its own floor tint.

## Wandering Smart Objects

### Data (`src/smartobjects.py`)

- **`SmartObject` fields.** The object gains:
  - `home_zone: str`;
  - `pauses_during_use: bool`;
  - mutable movement state: `heading: int` (an index into `hexgrid.DIRECTIONS`), `next_tile: Tile | None` and `progress: float` (0..1).

  `tile` becomes mutable. It is the object's logical tile, updated when a step completes.
- **`Slot` stores a direction, not a tile.** A slot has `index` and `direction`, an index into `DIRECTIONS` pointing from the object to the slot. The slot's tile is derived as `add(obj.tile, DIRECTIONS[direction])`, and its facing is `(direction + 3) % 6`. Helpers:
  - `slot_tile(obj, slot) -> Tile`
  - `slot_facing(slot) -> int`
- **`SmartObjectSubsystem` gains in-use tracking:**
  - `set_in_use(obj, bool)` and `is_in_use(obj) -> bool`.
  - `find(tag_query, near, blocked_fn)` skips slots where `blocked_fn(tile)` is true. It still returns unclaimed slots sorted by hex distance from `near`.
- **`ClaimHandle`** is unchanged. It holds the object and slot, so its tile is always derived live.

### Blocking (`src/world.py`)

- **Blocked tiles.** A tile is blocked for pathing and for slots if any of these hold:
  - it's out of bounds;
  - it's a wall;
  - it's any object's `tile`;
  - it's any object's `next_tile`, while that object is stepping.
- **Recomputed live.** `World.blocked` is recomputed from walls and object positions; there's no cached set that goes stale. `World.is_walkable(tile)` means in bounds and not blocked.
- **Object moves.** An object may step into `t` only if all of these hold:
  - `t` is walkable;
  - `t` is in the object's `home_zone`;
  - `t` is not the actor's `tile` or `next_tile`.
- **Slots may cross zone borders.** Only the object's own tile is confined to its zone, so a slot can sit across a border. That's the mechanism that changes the zone rules.

### Motion (`src/wander.py`, no pygame)

`ObjectMover` ticks every object once per sim tick. Each object:

- **Paused.** If `pauses_during_use` and `subsystem.is_in_use(obj)`, it does nothing this tick: it doesn't start a step, and it freezes any step in progress where it is. Use can start while the object is mid-step, because slot tiles derive from the logical `tile`, which only updates when a step completes. Freezing mid-step keeps the slot where the actor is standing. The step resumes once use ends.
- **Mid-step** (`next_tile` is set). It advances `progress` by `step_speed * dt`. At `progress >= 1` it sets `tile = next_tile` and clears `next_tile` and `progress`.
- **Idle.** With probability `move_rate * dt` it tries to start a step. Otherwise it stays this tick.
- **Choosing a direction.** The weight of each of the 6 directions depends on its divergence from `heading`, measured in 60° increments (0–3):

  | Divergence | Weight |
  |---|---|
  | 0 | `1.0` |
  | 1 (each side) | `turn_falloff` |
  | 2 (each side) | `turn_falloff ** 2` |
  | 3 | `turn_falloff ** 3` |

  - Directions whose target tile isn't allowed (see Blocking) are removed and the rest renormalized.
  - If none remain, the object stays this tick.
  - Otherwise it samples a direction, sets `heading` to it, sets `next_tile`, and `progress = 0`.
- **Randomness.** All sampling uses the sim's seeded `rng`.
- **Placeholder parameters** (module constants, easy to edit):

  | Parameter | Value |
  |---|---|
  | `move_rate` | 0.5 steps/s while idle |
  | `step_speed` | 1.5 tiles/s |
  | `turn_falloff` | 0.3 |

## StateTree tasks (`src/ai/tasks.py`)

The engine is unchanged. Task changes:

- **`FindAndClaim`:** calls `find(..., blocked_fn=lambda t: not world.is_walkable(t))`. A slot the actor is standing on counts as walkable, since the actor isn't in the blocked set.
- **`MoveTo` chases a moving goal:**
  - `goal_fn` is re-evaluated each time the actor completes a step onto a tile, and on the first tick.
  - If the goal tiles changed since the last plan, it re-plans A\* from `actor.tile` and logs `replan: slot moved`.
  - Before starting each step, if the next path tile isn't walkable, it re-plans from `actor.tile` and logs `replan: path blocked`.
  - It returns `FAILED` if a (re-)plan finds no path or the goal is empty.
  - It returns `SUCCEEDED` when the actor is standing on a current goal tile with no step in progress. At a claimed slot it faces `slot_facing(slot)`.
- **`Interact`:**
  - On enter, calls `set_in_use(claim.object, True)`. On exit, calls `set_in_use(claim.object, False)`, on every exit route. It remembers the object it marked so exit clears the right one.
  - Each tick, before counting time, returns `FAILED` if `actor.tile != slot_tile(claim.object, claim.slot)`, meaning the slot drifted away. This can only happen with objects where `pauses_during_use` is false.
- **`ZoneEvaluator`:** unchanged. It now yields NE/S/NW.

## Example tree and rules (`src/ai/tree_def.py`)

The rules are **placeholders**. Home zones: **A = NW**, **B = S**, **C = NE**.

| LastUsed | Zone = NW | Zone = S | Zone = NE |
|---|---|---|---|
| None | nearest | nearest | nearest |
| A (home NW) | B | C | C |
| B (home S) | A | C | A |
| C (home NE) | B | B | A |

The pattern: finishing in the last object's home zone goes *forward* (A→B→C→A). Finishing across a border, because the slot drifted over, goes *backward* (A→C, B→A, C→B).

Tree: the same shape as exp-00. Each `GoUse(X)` uses ANY-mode conditions:

```
GoUse(A)  enter ANY: [LastUsed==C & Zone==NE], [LastUsed==B & Zone!=S]
GoUse(B)  enter ANY: [LastUsed==A & Zone==NW], [LastUsed==C & Zone!=NE]
GoUse(C)  enter ANY: [LastUsed==B & Zone==S],  [LastUsed==A & Zone!=NW]
GoUse(Nearest)  enter: LastUsed==None
Wander    (fallback)
```

Each GoUse keeps FindAndClaim → MoveTo → Interact with the exp-00 transitions, plus one addition on `Interact`: `ON_FAILED → ROOT`. It still has `on_exit: release_claim`.

## Starting layout (`src/layout.py`, placeholder)

- **Objects.** Each starts inside its home zone, near the zone's middle, with 2 slots:

  | Object | Home zone | `pauses_during_use` |
  |---|---|---|
  | A | NW | true |
  | B | S | true |
  | C | NE | false |

  Initial headings are arbitrary.
- **Interactions.** The `<X>.Short` (1.5 s) and `<X>.Long` (3.0 s) placeholders are kept, with the effect `LastUsed = <X>`.
- **Walls.** A few short segments inside each zone, about 30–40 tiles total.
  - No wall tile lies on or next to a zone border, so objects can reach borders and push slots across.
  - Every zone's non-wall tiles stay connected, so an object can reach any part of its zone.
- **Actor.** Starts in NW, on a walkable tile that isn't a slot.

## Rendering (`src/render.py`)

The window, camera, panel layout, controls and headless flags are unchanged. Changes:

- **Floor:** three zone tints.
- **Objects:**
  - drawn at interpolated positions (`tile` → `next_tile` by `progress`), still as lettered raised hex columns;
  - a small heading tick on the column top points along `heading`;
  - while a pausing object is in use, a pause marker (two short bars) shows on its column.
- **Slot markers:**
  - drawn at the slot tile, interpolated with the object's movement;
  - a claimed slot is filled as before;
  - a blocked slot (its tile isn't walkable) is drawn dimmed.
- **Path dots:** from `ctx["Path"]`, as before. They change as the actor re-plans.
- **Panel:** same sections and layout. The condition names reflect the new rules, and the log includes `replan: ...` lines.

## Sim wiring (`src/sim.py`)

`Sim.step(dt)` first ticks `ObjectMover` over all objects, then ticks the StateTree. The context keys are unchanged from exp-00.

## Testing

TDD with pytest (`pythonpath = ["src"]`). The copied exp-00 tests are kept and updated where behaviour changed. New or updated tests:

- **Zones** (`test_world.py`):
  - every tile of the map maps to exactly one of NE/S/NW;
  - sample tiles in each sector are correct;
  - center and border ties follow the q, r, s order.
- **Blocking** (`test_world.py`):
  - object `tile` and `next_tile` are blocked;
  - walls are blocked;
  - moving an object updates blocking without stale state.
- **Smart Objects** (`test_smartobjects.py`):
  - slot tiles and facings derive from the object's position and move with it;
  - `find` skips blocked slots;
  - in-use set/clear.
- **Wander** (`test_wander.py`):
  - the weight table for a heading: 1, 0.3, 0.09, 0.027 by divergence;
  - disallowed directions are removed and the rest renormalized, with none allowed meaning no step;
  - the observed step-start frequency with a seeded RNG is within tolerance of `move_rate`;
  - a step completes after `1 / step_speed` seconds and updates `tile` and `heading`;
  - a pausing object in use doesn't move, and a non-pausing one does;
  - long seeded runs never put an object outside its home zone, on a wall, on another object, or on the actor.
- **Tasks** (`test_tasks.py`):
  - `MoveTo` re-plans when the claimed slot moves and still arrives;
  - `MoveTo` re-plans when an object blocks the path;
  - `MoveTo` fails when no path exists;
  - `Interact` fails when the slot drifts away from the actor;
  - `Interact` clears in-use on success, failure, and interruption by reset.
- **Rules** (`test_tree_def.py`): parametrized over the full LastUsed × Zone table above.
- **Sim** (`test_sim.py`). Randomness replaces exp-00's fixed cycle. Long runs over seeds 0–4 check every tick that:
  - there's at most one live claim;
  - `ctx["Claim"]` is that claim, or None;
  - no `error` log lines appear;
  - every object is in its home zone;
  - no object's `tile` or `next_tile` equals the actor's `tile` or `next_tile`.

  On seed 0, all of A, B and C get used at least once within a bounded number of sim-seconds, fixed in the plan once measured.
- **Visual check:** a headless screenshot run, as in exp-00, confirming:
  - three zone tints;
  - objects moving between screenshots and staying in their zones;
  - slot markers following objects, with blocked slots dimmed;
  - path dots changing after re-plans;
  - `replan:` log lines;
  - a pause marker on A or B while in use.

## Out of scope

- Multiple actors.
- Per-object movement parameters beyond the placeholder module constants.
- Object–object interaction beyond mutual blocking.
- Changes to the panel layout or controls.
- Changing exp-00.
