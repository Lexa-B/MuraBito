# Experiments manifest

One entry per experiment: what it is, why it exists, how to run it.

---

## exp-00 — StateTree hello world

- **Started:** 2026-09-17
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd experiments/exp-00 && uv run src/main.py`
- **Test:** `cd experiments/exp-00 && uv run pytest`
- **Design:** [`docs/superpowers/specs/2026-09-17-exp-00-statetree-visualizer-design.md`](../docs/superpowers/specs/2026-09-17-exp-00-statetree-visualizer-design.md)

### Why

A quick mockup, built outside Unreal Engine because UE5 is a very large download.
It's a hello world of pathing and object use that shows what the AI systems will
be like once there's UE to write AI for.

### What

An isometric pygame window showing a small tile world with three placeholder
objects (A, B, C) and a single actor. The actor's behavior is driven by a small
**StateTree-style** engine modeled on UE5's StateTree: hierarchical states,
enter conditions, tasks, transitions, and evaluators writing to a shared context.
The actor paths to objects with **A\*** on the tile grid.

Which object the actor goes to next depends on **where it is** (West or East zone)
and **which object it used last**. These rules are placeholders, kept in one data
file (`src/ai/tree_def.py`) so they're easy to change.

A side panel shows what's going on in the actor's "brain" while the sim runs: the
state tree with the active branch highlighted and pass/fail marks on each enter
condition, the current context values, and a running transition log.

### Layout

- `src/` — game loop, world model, rendering
- `src/ai/` — StateTree engine, tasks/evaluators, the example tree, A* pathing
- `tests/` — pytest for pathing and the StateTree engine
