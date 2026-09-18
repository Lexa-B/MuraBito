# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository. `CLAUDE.md` at the repo root is a one-line import shim (`@AGENTS.md`) kept for Claude Code's file-discovery convention.

## Project Overview

MuraBito is a new project, described by its author as halfway between a game and a fun AI experiment / population-dynamics simulator. It's being built in Unreal Engine 5, starting with exp-04.

Ideas are tried out as small, self-contained **experiments**. They come in two kinds:

- **Unreal Engine 5 (C++)**: where most of the code is headed. exp-04 is the first: a UE 5.8 project with procedural hilly terrain, a hex grid draped over it, an overhead camera, and hover highlighting.
- **Python + pygame**: mostly for quick testing of ideas.
  - **exp-00** is a "hello world" of pathing and object use, meant to show what the AI systems will be like in UE.
  - **exp-01** builds on it with objects that wander.
  - **exp-02** adds fog of war and a believed world.
  - **exp-03** is a tiered hex world: hierarchical hex addresses at historical Japanese scale, loaded in tiers of detail (moderngl).

Don't assume goals beyond what `experiments/manifest.md` and each experiment's spec state.


## Repository Organization

```
MuraBito/
├─ AGENTS.md, CLAUDE.md, LICENSE, .gitignore
└─ experiments/
   ├─ manifest.md          one entry per experiment: what, why, how to run
   ├─ exp-NN/              a Python + pygame experiment
   │  ├─ pyproject.toml    its own uv project (Python deps managed with `uv add`)
   │  ├─ src/              code
   │  │  └─ ai/            AI code (decision logic, pathing, etc.)
   │  ├─ tests/            pytest; run with `uv run pytest` from the experiment dir
   │  └─ docs/             specs/ and plans/, as below
   └─ exp-NN/              an Unreal Engine 5 (C++) experiment
      ├─ MuraBito.uproject, Config/       project file and text config
      ├─ Source/MuraBito/                 the C++ module; Private/Tests/ holds automation tests
      ├─ scripts/                         build.sh, editor.sh, game.sh, test.sh (wrap the local engine)
      ├─ .gitignore                       Binaries/ Intermediate/ Saved/ DerivedDataCache/ …
      └─ docs/
         ├─ specs/         design specs    (YYYY-MM-DD-<topic>-design.md)
         └─ plans/         implementation plans (YYYY-MM-DD-<topic>-plan.md)
```

- **Experiments are self-contained.** Code, tests, dependencies and docs live inside `experiments/exp-NN/`. Nothing experiment-specific goes at the repo root.
- **A new experiment can start as a copy of an earlier one.** exp-01 started as a copy of exp-00. The copy gets its own project name (uv project, or UE project/module), and the earlier experiment is left unchanged.
- **Every new experiment gets an entry in `experiments/manifest.md`.** Update the entry when the experiment's design changes.
- **Specs go in the experiment's `docs/specs/` and plans in its `docs/plans/`.** This replaces the superpowers default of `docs/superpowers/specs/` and `docs/superpowers/plans/`. Don't create a `superpowers/` folder or a root-level `docs/`. Name specs `YYYY-MM-DD-<topic>-design.md` and plans `YYYY-MM-DD-<topic>-plan.md`.


## Unreal Engine experiments

- **Public MIT repo: never copy engine code or assets in.** Projects use the local engine install by path (`UE_ROOT`, default `/home/lexa/DevProjects/_GameDev/_GameEngines/UnrealEngine/5.8.2`). Reading engine headers and source to check an API is fine; pasting them, or Epic copyright headers, into the repo is not.
- **No binary assets yet.** No `.uasset`/`.umap` files and no Git LFS; the world is built in C++ at runtime. How assets get stored is decided when there is something to author.
- **Naming:** keep UE's type prefixes (`A`, `F`, `U`), but the names after them are plain and say what the class does (`ACameraRig`, not a "…Pawn"). Code and docs don't name games that inspired the project.
- **Build and test with the scripts**, from the experiment dir: `scripts/build.sh`, `scripts/test.sh [TestPathPrefix]` (headless automation tests; pass/fail comes from the log, since the editor's exit code is always 1 under `-TestExit`).
- **Never kill, signal or otherwise touch an Unreal Editor (or any process) you didn't start.**
- **The user may have the editor open on the same checkout while you work.** `build.sh` then does a hot-reload build, and the open editor loads it by itself within about a second. While the user is in Play, the reload waits until they stop. Changes to class layout (new or changed `UPROPERTY`/`UCLASS`, header changes) don't hot-reload reliably: tell the user to restart the editor after those.
- **`test.sh` is safe with an editor open.** It copies the project into a private mirror (`~/.cache/murabito/exp-04-test-mirror`) and builds that with `-NoHotReloadFromIDE`, so the tests run the code on disk and never touch the editor's modules.
- **Windowed runs need the desktop display.** Shells in the user's terminal may have no `DISPLAY`/`WAYLAND_DISPLAY`; `game.sh` and `editor.sh` take them from the systemd user session.
