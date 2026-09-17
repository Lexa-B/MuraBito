# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository. `CLAUDE.md` at the repo root is a one-line import shim (`@AGENTS.md`) kept for Claude Code's file-discovery convention.

## Project Overview

MuraBito is a new project, described by its author as halfway between a game and a fun AI experiment / population-dynamics simulator. It is planned to be built in Unreal Engine 5 eventually.

Until then, ideas are mocked up as small **experiments** outside UE5, because the UE5 download is very large. Each one is a Python + pygame sim.
- **exp-00** is a "hello world" of pathing and object use, meant to show what the AI systems will be like once there's UE to write AI for.
- **exp-01** builds on it with objects that wander.

Don't assume goals beyond what `experiments/manifest.md` and each experiment's spec state.


## Repository Organization

```
MuraBito/
├─ AGENTS.md, CLAUDE.md, LICENSE, .gitignore
└─ experiments/
   ├─ manifest.md          one entry per experiment: what, why, how to run
   └─ exp-NN/              a self-contained experiment
      ├─ pyproject.toml    its own uv project (Python deps managed with `uv add`)
      ├─ src/              code
      │  └─ ai/            AI code (decision logic, pathing, etc.)
      ├─ tests/            pytest; run with `uv run pytest` from the experiment dir
      └─ docs/
         ├─ specs/         design specs    (YYYY-MM-DD-<topic>-design.md)
         └─ plans/         implementation plans (YYYY-MM-DD-<topic>-plan.md)
```

- **Experiments are self-contained.** Code, tests, dependencies and docs live inside `experiments/exp-NN/`. Nothing experiment-specific goes at the repo root.
- **A new experiment can start as a copy of an earlier one.** exp-01 started as a copy of exp-00. The copy gets its own uv project name, and the earlier experiment is left unchanged.
- **Every new experiment gets an entry in `experiments/manifest.md`.** Update the entry when the experiment's design changes.
- **Specs go in the experiment's `docs/specs/` and plans in its `docs/plans/`.** This replaces the superpowers default of `docs/superpowers/specs/` and `docs/superpowers/plans/`. Don't create a `superpowers/` folder or a root-level `docs/`. Name specs `YYYY-MM-DD-<topic>-design.md` and plans `YYYY-MM-DD-<topic>-plan.md`.
