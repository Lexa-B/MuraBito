# exp-00 — StateTree visualizer: design

**Date:** 2026-09-17
**Location:** `experiments/exp-00/`
**Stack:** Python 3.13, pygame 2.6.1, pytest; uv-managed (`uv add`, `uv run`)

## Purpose

A throwaway-scale mockup, built outside UE5, of pathing and object use driven by
StateTree-style AI, so what the AI systems will be like is visible before there's
UE to write it in. The objects are **Smart Objects** (UE5) — Sims-style interactables
that advertise what can be done with them, which the actor keeps finding, claiming,
walking to, and interacting with.

## Screen

A single pygame window, split into two parts:

- **World view (left):** isometric 12×12 tile grid.
  - Two zones: West (columns 0–5) and East (columns 6–11), drawn with different floor tints.
  - A handful of blocking tiles, drawn as raised iso blocks.
  - Three Smart Objects, **A**, **B**, **C**: colored iso blocks, each labeled with its letter. Objects block movement.
  - Each object's slots are drawn as small floor markers. A claimed slot is highlighted.
  - One actor: a small iso figure that moves smoothly between tiles at a fixed speed.
  - The current A\* path is drawn as dots from the actor to its goal.
  - While the actor is interacting, a progress ring fills, labeled with the interaction name.
- **Brain panel (right):** a live view of the actor's decision state.
  - **State tree:** every state, indented by depth. The active path is highlighted. Each enter condition shows ✓/✗ from its most recent evaluation, or no mark if it hasn't been evaluated.
  - **Context:** `Zone`, `LastUsed`, `Target`, `Claim` (e.g. `A / slot 0`), `Interaction` (e.g. `A.Long 1.2 / 3.0s`), path length, and the active task's status.
  - **Transition log:** the last ~12 entries, each with a sim timestamp, e.g. `12.4s Interact → Completed`, `12.4s select → GoUse(B)/FindAndClaim`, `12.4s release A / slot 0`.
- **Controls:** `Space` pause/resume · `N` advance one fixed tick while paused · `+`/`-` sim speed (0.25×–8×) · `R` reset world and tree · `Esc` quit.

The sim runs on a fixed timestep (dt = 1/60 s) and is scaled by sim speed. Rendering is decoupled from it.

## World and pathing (`src/world.py`, `src/ai/pathing.py`)

- `World` holds:
  - the grid size;
  - the blocked-tile set, which includes object tiles;
  - the `SmartObjectSubsystem`;
  - `zone_of(tile) → "West" | "East"`.
- `astar(world, start, goals) → list[tile] | None`
  - 4-directional, Manhattan heuristic to the nearest goal.
  - `goals` is a set of tiles: the path ends at whichever goal is cheapest to reach.
  - Returns `None` if no goal can be reached.
- `world.py` and `pathing.py` do not import pygame.
- Isometric projection helpers (`tile_to_screen`, used for drawing) live in `render.py`.

## Smart Objects (`src/smartobjects.py`)

No pygame imports. A small model of UE5 Smart Objects, reduced to the Sims-style core: the object advertises interactions, and the actor claims a slot, walks to it, and performs one.

- **`Slot`:** `tile`, `facing` (one of N/E/S/W, pointing at the object), `index`. Slot tiles must be walkable.
- **`Interaction`:**
  - `name`, e.g. `A.Short`;
  - `duration` in seconds;
  - `effects`: a list of `fn(ctx)`.
- **`SmartObject`:**
  - `name` (`A` / `B` / `C`);
  - `tile`;
  - `tags: set[str]`, e.g. `{"Object.A"}`;
  - `slots: list[Slot]`, 1–2 per object;
  - `interactions: list[Interaction]`.
- **`ClaimHandle`:** `object`, `slot`, `actor`.
- **`SmartObjectSubsystem`:**
  - `register(obj)`.
  - `find(tag_query, near) → list[(SmartObject, Slot)]`
    - Returns only unclaimed slots, sorted by Manhattan distance from `near`.
    - `tag_query` is a set of tags that must all be present; an empty set matches any object.
  - `claim(obj, slot, actor) → ClaimHandle | None`: returns `None` if the slot is already claimed.
  - `release(handle)`: releasing an already-released handle does nothing.
  - `is_claimed(obj, slot) → bool`, for the renderer.

**Placeholder content.** Each object advertises two generic interactions: `<X>.Short` (1.5s) and `<X>.Long` (3.0s). Each interaction has one effect: `LastUsed = <X>`. The interaction is picked at random (seeded RNG, so reset replays the same sequence). The names, durations and effects are placeholders.

## StateTree engine (`src/ai/statetree.py`)

No pygame imports. Concepts are named after UE5 StateTree:

- **Context:** a plain dict shared by everything: `Zone`, `LastUsed`, `Target`, `Claim`, `Interaction`, `Path`, plus `actor`, `world`, `rng`, and `log` references.
- **Condition:** `name: str` + `test(ctx) → bool`. The last result is stored for the panel.
- **Task:**
  - `enter(ctx)`, `tick(ctx, dt) → RUNNING | SUCCEEDED | FAILED`, `exit(ctx)`.
  - Only leaf states have tasks in this experiment.
- **Transition:**
  - `trigger`: `ON_COMPLETED`, `ON_FAILED`, or `ON_CONDITION(condition)`.
  - `target`: a state name, or `ROOT`.
- **State:**
  - name;
  - children (ordered);
  - enter conditions, with a mode of `ALL` or `ANY`;
  - optional `on_exit(ctx)` hook;
  - task (leaf only);
  - transitions.
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
     - exit the current leaf's task;
     - select starting from the target, which gives a new active path;
     - run `on_exit`, deepest first, for every old-path state that is either not on the new path or at/below the transition target. Targeting a state re-enters it: a transition to `ROOT` exits everything below root, even if selection picks the same branch again;
     - enter the new leaf's task;
     - log the transition.
- **Selection** — `select(state)`:
  - If the state's enter conditions fail, return failure.
  - If it's a leaf, it becomes active.
  - Otherwise try each child in order; the first child that selects successfully wins.
  - If no child selects, the state fails and control falls back to the parent's next child.
  - Selecting from `ROOT` tries root's children in order.
  - A transition that targets a sibling leaf (e.g. `FindAndClaim → MoveTo`) keeps the shared parent on the active path, so its `on_exit` does not run.
  - If nothing at all is selectable, the tree logs an error and stays idle. The example tree prevents this with an unconditioned fallback.
  - The panel reads every recorded result (condition ✓/✗, active path).
- **`reset(ctx)`:** runs `on_exit` for the whole active path, deepest first, then clears the active state. Used by `R`.

## Tasks and evaluators (`src/ai/tasks.py`)

- **`ZoneEvaluator`:** sets `ctx["Zone"] = world.zone_of(actor.tile)`.
- **`FindAndClaim(tag_query)`:**
  - On enter:
    - `world.smart_objects.find(tag_query, near=actor.tile)`;
    - claim the first result;
    - write `ctx["Target"] = obj.name` and `ctx["Claim"] = handle`, and log the claim.
  - Returns `SUCCEEDED` on its first tick, or `FAILED` if nothing was found or claimed.
- **`MoveTo(goal_fn)`:**
  - On enter:
    - resolve the goal tiles: `{claim.slot.tile}` for a claim, or a single tile when wandering;
    - run A\* and write `ctx["Path"]`.
  - `FAILED` if there's no path.
  - While ticking: moves the actor along the path; `SUCCEEDED` on arrival. At a slot, the actor turns to face `slot.facing`.
- **`Interact`:**
  - On enter:
    - pick one of the claimed object's interactions using `ctx["rng"]`;
    - write `ctx["Interaction"]`.
  - Counts up to the interaction's `duration`, exposing progress to the renderer.
  - When it finishes, it applies each effect to `ctx`, clears `ctx["Interaction"]`, and returns `SUCCEEDED`.
- **`Wait(duration)`:** returns `SUCCEEDED` after `duration`.
- **`release_claim(ctx)`:**
  - The `on_exit` hook on every `GoUse` state.
  - If `ctx["Claim"]` is set: release it, log the release, and clear `Claim` and `Target`.
  - Because it's attached to the parent, the claim is released however the state ends: finished, failed partway, or interrupted by reset.

## Example tree (`src/ai/tree_def.py`)

The rules are **placeholders**. They exist to show that the decision depends on both
zone and history, and they are expected to be rewritten.

| LastUsed | Zone = West | Zone = East |
|----------|-------------|-------------|
| None     | nearest free slot, any object | nearest free slot, any object |
| A        | B | C |
| B        | C | A |
| C        | A | B |

```
Root
├─ GoUse(A)        enter ANY: [LastUsed==C & Zone==West], [LastUsed==B & Zone==East]
│   │              on_exit: release_claim
│   ├─ FindAndClaim(tags={Object.A})  ON_COMPLETED→GoUse(A)/MoveTo    ON_FAILED→Wander
│   ├─ MoveTo(claimed slot)           ON_COMPLETED→GoUse(A)/Interact  ON_FAILED→Wander
│   └─ Interact                       ON_COMPLETED→ROOT
├─ GoUse(B)        enter ANY: [LastUsed==A & Zone==West], [LastUsed==C & Zone==East]
├─ GoUse(C)        enter ANY: [LastUsed==B & Zone==West], [LastUsed==A & Zone==East]
├─ GoUse(Nearest)  enter: LastUsed==None   (FindAndClaim(tags={}) → any object)
└─ Wander          (no conditions — fallback)
    ├─ MoveTo(random walkable tile)  ON_COMPLETED→Wander/Wait  ON_FAILED→ROOT
    └─ Wait(1s)                      ON_COMPLETED→ROOT
```

`GoUse(B)`, `GoUse(C)` and `GoUse(Nearest)` have the same FindAndClaim / MoveTo / Interact children and `on_exit` as `GoUse(A)`; only the tag query differs.
Each rule row is one compound condition, so the table maps directly onto the tree.
Leaving `GoUse` for `Wander` releases the claim.

**Starting layout:**
- A is in the West zone with 2 slots.
- C is in the East zone with 2 slots.
- B is on the East side near the boundary, with 1 slot.
- A few obstacles sit between them so paths visibly bend.
- The actor starts in the West zone.

## Testing

TDD. Unit tests in `experiments/exp-00/tests/` (pytest, `pythonpath = ["src"]`):

- **`test_pathing.py`**
  - straight path on an open grid;
  - path routes around obstacles;
  - an unreachable goal returns `None`;
  - with several goals, the path ends at the nearest one.
- **`test_smartobjects.py`**
  - `find` filters by tag, and an empty query matches everything;
  - `find` returns results sorted by distance;
  - claimed slots are excluded from `find`;
  - `claim` on a claimed slot returns `None`;
  - `release` frees the slot and is idempotent.
- **`test_statetree.py`**
  - selection picks the first child whose conditions pass;
  - if a subtree fails, selection falls back to the next sibling;
  - the `ANY`/`ALL` condition modes;
  - `ON_COMPLETED` / `ON_FAILED` go to the right states;
  - a transition with no match on the leaf is resolved by a parent;
  - evaluators run before tasks;
  - condition results are recorded;
  - `on_exit` runs for states leaving the active path, deepest first;
  - `on_exit` doesn't run on a sibling-leaf transition;
  - `reset` runs `on_exit` for the whole active path.
- **`test_tasks.py`**
  - `FindAndClaim` success and failure;
  - `Interact` applies effects after its duration;
  - the claim is released when `GoUse` completes;
  - the claim is released when `MoveTo` fails partway (with the path blocked).
- **`test_tree_def.py`:** for every LastUsed × Zone pair, selecting from ROOT reaches the expected `GoUse(X)`.

**Visual check:** a headless run (`SDL_VIDEODRIVER=dummy`, `--frames N --screenshot-dir …` flags on `main.py`). It runs a few hundred ticks and saves screenshots, which get inspected before the experiment is called working.

## Out of scope

- Multiple actors, so claims are never contested in practice.
- Sims-style motives or advertisement scoring for choosing interactions.
- Editing the world while it runs.
- Save/load.
- UE-style tasks on parent states.
- Sound.
