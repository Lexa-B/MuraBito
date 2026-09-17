# exp-00 — StateTree visualizer: design

**Date:** 2026-09-17
**Location:** `experiments/exp-00/`
**Stack:** Python 3.13, pygame 2.6.1, pytest; uv-managed (`uv add`, `uv run`)

## Purpose

A throwaway-scale mockup, built outside UE5, of pathing and object use driven by
StateTree-style AI, so what the AI systems will be like is visible before there's
UE to write it in.

## Screen

A single pygame window, split into two parts:

- **World view (left):** isometric 12×12 tile grid.
  - Two zones: West (columns 0–5) and East (columns 6–11), drawn with different floor tints.
  - A handful of blocking tiles, drawn as raised iso blocks.
  - Three objects, **A**, **B**, **C**: colored iso blocks, each labeled with its letter. Objects also block movement.
  - One actor: a small iso figure that moves smoothly between tiles at a fixed speed.
  - The current A\* path is drawn as dots from the actor to its goal.
  - While the actor is using an object, a progress ring fills.
- **Brain panel (right):** a live view of the actor's decision state.
  - **State tree:** every state, indented by depth. The active path is highlighted. Each enter condition shows ✓/✗ from its most recent evaluation, or no mark if it hasn't been evaluated.
  - **Context:** `Zone`, `LastUsed`, `Target`, path length, and the active task's status.
  - **Transition log:** the last ~12 entries, each with a sim timestamp, e.g. `12.4s Use(A) → Completed`, `12.4s select → GoUse(B)/MoveTo`.
- **Controls:** `Space` pause/resume · `N` advance one fixed tick while paused · `+`/`-` sim speed (0.25×–8×) · `R` reset world and tree · `Esc` quit.

The sim runs on a fixed timestep (dt = 1/60 s) and is scaled by sim speed. Rendering is decoupled from it.

## World and pathing (`src/world.py`, `src/ai/pathing.py`)

- `World` holds the grid size, a blocked-tile set, objects (`name → tile`), and `zone_of(tile) → "West" | "East"`.
- An object is used from any walkable 4-neighbor tile. `World.use_tiles(obj)` returns those tiles.
- `astar(world, start, goals) → list[tile] | None`
  - 4-directional, Manhattan heuristic to the nearest goal.
  - `goals` is a set: the path ends at whichever use-tile is cheapest to reach.
  - Returns `None` if no goal can be reached.
  - `world.py` and `pathing.py` do not import pygame.
- Isometric projection helpers (`tile_to_screen`, used for drawing) live in `render.py`.

## StateTree engine (`src/ai/statetree.py`)

No pygame imports. Concepts are named after UE5 StateTree:

- **Context:** a plain dict shared by everything (`Zone`, `LastUsed`, `Target`, `Path`, plus `actor` and `world` references).
- **Condition:** `name: str` + `test(ctx) → bool`. The last result is stored for the panel.
- **Task:**
  - `enter(ctx)`, `tick(ctx, dt) → RUNNING | SUCCEEDED | FAILED`, `exit(ctx)`.
  - Only leaf states have tasks in this experiment.
- **Transition:**
  - `trigger`: `ON_COMPLETED`, `ON_FAILED`, or `ON_CONDITION(condition)`.
  - `target`: a state name, or `ROOT`.
- **State:** name, children (ordered), enter conditions, conditions mode (`ALL` / `ANY`), optional `on_select(ctx)` hook (runs when the state becomes part of the active path), task (leaf only), transitions.
- **Evaluator:** `tick(ctx, dt)`, run every tick before anything else.
- **StateTree** — each tick runs:
  1. Every evaluator.
  2. If there's no active state, select from `ROOT`.
  3. Tick the active leaf's task.
  4. Check transitions:
     - `ON_CONDITION` is checked every tick.
     - On `SUCCEEDED`, the leaf's `ON_COMPLETED` transition fires; if the leaf has none, parents are checked upward.
     - On `FAILED`, the same happens with `ON_FAILED`.
  5. When a transition fires:
     - exit the current task;
     - select starting from the target;
     - log the transition.
- **Selection** — `select(state)`:
  - If the state's enter conditions fail, return failure.
  - If it's a leaf, it becomes active.
  - Otherwise try each child in order; the first child that selects successfully wins.
  - If no child selects, the state fails and control falls back to the parent's next child.
  - Selecting from `ROOT` tries root's children in order.
  - If nothing at all is selectable, the tree logs an error and stays idle. The example tree prevents this with an unconditioned fallback.
  - The panel reads every recorded result (condition ✓/✗, active path).

## Tasks and evaluators (`src/ai/tasks.py`)

- **`ZoneEvaluator`:** sets `ctx["Zone"] = world.zone_of(actor.tile)`.
- **`MoveTo(target_fn)`:**
  - On enter: resolves the goal tiles (an object's use-tiles or one tile), runs A\*, and writes `ctx["Path"]`.
  - `FAILED` if there's no path.
  - While ticking: moves the actor along the path; `SUCCEEDED` on arrival.
- **`UseObject(duration)`:** counts up to `duration`, exposing progress to the renderer. On success it sets `ctx["LastUsed"] = ctx["Target"]`.
- **`Wait(duration)`:** returns `SUCCEEDED` after `duration`.
- **Setting the target:** each `GoUse(X)` state's `on_select` hook writes `ctx["Target"]`. `GoUse(Nearest)` picks the object with the shortest A\* path. Because this happens at selection, the panel shows the target before movement starts.

## Example tree (`src/ai/tree_def.py`)

The rules are **placeholders**. They exist to show that the decision depends on both
zone and history, and they are expected to be rewritten.

| LastUsed | Zone = West | Zone = East |
|----------|-------------|-------------|
| None     | nearest object | nearest object |
| A        | B | C |
| B        | C | A |
| C        | A | B |

```
Root
├─ GoUse(A)        enter ANY: [LastUsed==C & Zone==West], [LastUsed==B & Zone==East]
│   ├─ MoveTo(A)   ON_COMPLETED→GoUse(A)/Use   ON_FAILED→Wander
│   └─ Use(A, 2s)  ON_COMPLETED→ROOT
├─ GoUse(B)        enter ANY: [LastUsed==A & Zone==West], [LastUsed==C & Zone==East]
├─ GoUse(C)        enter ANY: [LastUsed==B & Zone==West], [LastUsed==A & Zone==East]
├─ GoUse(Nearest)  enter: LastUsed==None   (Target = object with shortest A* path)
└─ Wander          (no conditions — fallback)
    ├─ MoveTo(random walkable tile)  ON_COMPLETED→Wander/Wait  ON_FAILED→ROOT
    └─ Wait(1s)                      ON_COMPLETED→ROOT
```

`GoUse(B)`, `GoUse(C)` and `GoUse(Nearest)` have the same MoveTo / Use children as `GoUse(A)`.
Each rule row is one compound condition, so the table maps directly onto the tree.

**Starting layout:** A is in the West zone, C is in the East zone, B is on the East side near the boundary. A few obstacles sit between them so paths visibly bend. The actor starts in the West zone.

## Testing

TDD. Unit tests in `experiments/exp-00/tests/` (pytest, `pythonpath = ["src"]`):

- **`test_pathing.py`**
  - straight path on an open grid;
  - path routes around obstacles;
  - an unreachable goal returns `None`;
  - with several goals, the path ends at the nearest one.
- **`test_statetree.py`**
  - selection picks the first child whose conditions pass;
  - if a subtree fails, selection falls back to the next sibling;
  - the `ANY`/`ALL` condition modes;
  - `ON_COMPLETED` / `ON_FAILED` go to the right states;
  - a transition with no match on the leaf is resolved by a parent;
  - evaluators run before tasks;
  - condition results are recorded.
- **`test_tree_def.py`:** for every LastUsed × Zone pair, selecting from ROOT reaches the expected `GoUse(X)`.

**Visual check:** a headless run (`SDL_VIDEODRIVER=dummy`, `--frames N --screenshot-dir …` flags on `main.py`). It runs a few hundred ticks and saves screenshots, which get inspected before the experiment is called working.

## Out of scope

Needs/utility scoring, multiple actors, editing the world while it runs, save/load, UE-style tasks on parent states, sound.
