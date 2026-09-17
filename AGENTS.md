# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository. `CLAUDE.md` at the repo root is a one-line import shim (`@AGENTS.md`) kept for Claude Code's file-discovery convention.

## Project Overview


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
- **Every new experiment gets an entry in `experiments/manifest.md`.** Update the entry when the experiment's design changes.
- **Specs go in the experiment's `docs/specs/` and plans in its `docs/plans/`.** This replaces the superpowers default of `docs/superpowers/specs/` and `docs/superpowers/plans/`. Don't create a `superpowers/` folder or a root-level `docs/`. Name specs `YYYY-MM-DD-<topic>-design.md` and plans `YYYY-MM-DD-<topic>-plan.md`.
