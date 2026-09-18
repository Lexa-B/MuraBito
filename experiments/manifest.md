# Experiments manifest

One entry per experiment: what it is, why it exists, how to run it.

---

## exp-00 — StateTree hello world

- **Started:** 2026-09-17
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd experiments/exp-00 && uv run src/main.py`
- **Test:** `cd experiments/exp-00 && uv run pytest`
- **Design:** [`exp-00/docs/specs/2026-09-17-exp-00-statetree-visualizer-design.md`](exp-00/docs/specs/2026-09-17-exp-00-statetree-visualizer-design.md)

### Why

A quick mockup, built outside Unreal Engine because UE5 is a very large download.
It's a hello world of pathing and object use that shows what the AI systems will
be like once there's UE to write AI for.

### What

An isometric pygame window showing a hexagon-shaped hex-tile world (25 tiles
across, with a camera that follows the actor) with three placeholder
objects (A, B, C) and a single actor. The objects are modeled on UE5's **Smart
Objects**: Sims-style interactables that advertise interactions and offer slots
the actor claims, walks to, uses, and releases. The actor's behavior is driven by a
small **StateTree-style** engine modeled on UE5's StateTree: hierarchical states,
enter conditions, tasks, transitions, and evaluators writing to a shared context.
The actor paths to object slots with **A\*** on the hex grid.

Which object the actor goes to next depends on **where it is** (West or East zone)
and **which object it used last**. These rules are placeholders, kept in one data
file (`src/ai/tree_def.py`) so they're easy to change.

A side panel shows what's going on in the actor's "brain" while the sim runs: the
state tree with the active branch highlighted and pass/fail marks on each enter
condition, the current context values, and a running transition log.

### Layout

- `src/` — game loop, hex grid, world model, Smart Objects, camera, rendering, starting layout (`layout.py`), sim wiring (`sim.py`)
- `src/ai/` — StateTree engine, tasks/evaluators, the example tree, A* pathing
- `tests/` — pytest for the hex grid, world zones, pathing, Smart Objects, the StateTree engine, the tasks, the starting layout, the tree definition, the sim cycle, and the headless main loop

### Controls

Space pause/resume · N step one tick while paused · +/- sim speed (0.25x-8x) · R reset · Esc quit.

### Headless

`cd experiments/exp-00 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --screenshot-dir screenshots --screenshot-every K` (screenshots/ is gitignored).

---

## exp-01 — Wandering Smart Objects

- **Started:** 2026-09-17
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd experiments/exp-01 && uv run src/main.py`
- **Test:** `cd experiments/exp-01 && uv run pytest`
- **Design:** [`exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md`](exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md)

### Why

Built on exp-00. It's almost the same, but the targets slowly wander around.

### What

Starts as a copy of exp-00: same hex map, camera, StateTree engine, Smart Objects, A\* pathing and brain panel.

**What changes:**
- **Three zones.** The map is split into three 120° sectors (NE, S, NW).
- **Wandering objects.** Each Smart Object wanders inside its own zone, with stochastic momentum. It usually keeps its heading, and sharper turns are less likely. Slots ride along with their object and can poke across a zone border.
- **Chasing.** The actor re-plans when its claimed slot moves or its path gets blocked.
- **Pausing.** A and B hold still while in use. C keeps moving, and the interaction fails if its slot drifts away.
- **Rules.** The placeholder rules still key on the last object used and the actor's zone. Finishing in that object's home zone moves forward (A→B→C), and finishing across a border moves backward.

### Layout

- `src/`: same as exp-00, plus `wander.py`, the stochastic object mover.
- `src/ai/`: same as exp-00. `tasks.py` gains chasing, re-planning and in-use tracking.
- `tests/`: same as exp-00, plus `test_wander.py`. The sim tests check invariants over seeded runs instead of a fixed cycle: claims, in-use, zones, overlaps and step order.

### Open questions

Three design and tuning questions from the final review are listed in the spec's "Open questions" section: the slot marker during a mid-step pause, claims abandoned on brief blocks and C's drift-failure rate, and wall placement.

### Controls

Same as exp-00: Space pause/resume · N step one tick while paused · +/- sim speed (0.25x-8x) · R reset · Esc quit.

### Headless

`cd experiments/exp-01 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --screenshot-dir screenshots --screenshot-every K` (screenshots/ is gitignored).

---

## exp-02 — Fog of war and the believed world

- **Started:** 2026-09-18
- **Stack:** Python 3.13 + pygame, managed with uv
- **Run:** `cd experiments/exp-02 && uv run src/main.py`
- **Test:** `cd experiments/exp-02 && uv run pytest`
- **Design:** [`exp-02/docs/specs/2026-09-18-exp-02-fog-of-war-design.md`](exp-02/docs/specs/2026-09-18-exp-02-fog-of-war-design.md)

### Why

In exp-00 and exp-01 the actor is omniscient: it finds and chases objects using their true positions. exp-02 makes the actor earn its knowledge, to show that partial observability slots in underneath the decision layer: the rule table stays the same, and only what the tree reads changes.

### What

Starts as a copy of exp-01: same hex map, three zones, wandering Smart Objects, StateTree engine, A\* and brain panel.

**What changes:**
- **Random maps.** Walls, object starts and the actor's start are random, seeded from `--seed`. Nothing is in view at the start.
- **Sight.** The actor sees a 120° cone out to 6 tiles, plus its neighboring tiles. Walls, and objects set to cast shadows, block sight.
- **Beliefs.** The actor keeps a private belief store. It learns walls on sight and paths on a believed map. It dead-reckons objects it has lost sight of, with an uncertainty radius that grows with each object's observed speed and sets how sure it is.
- **Behaviour.** The actor chooses targets from beliefs, claims a slot only once the object is in view, searches when a belief turns out wrong, and explores when it knows nothing.
- **Rendering.** Fog of war, ghost markers for believed positions, a sense cone, and a truth overlay (`T`). The brain panel gains a belief table.

### Layout

- `src/`: same as exp-01, plus `zones.py` (zone geometry), `mapgen.py` (random walls and starts), `body.py` (the truth-side actuator).
- `src/ai/`: same as exp-01, plus `vision.py` (sense cone and shadowcasting), `beliefs.py` (belief store, believed map, search area, frontier), `perception.py` (the only AI code that reads the world). `tasks.py` gains `ChooseTarget`, `Search` and `Explore` and reads beliefs.
- `tests/`: same as exp-01 minus `test_layout.py`, plus `test_vision.py`, `test_mapgen.py`, `test_beliefs.py`, `test_believed_map.py`, `test_perception.py`, `test_body.py`, `test_boundary.py`.

### Open questions

Tuning and polish left open after the final review (2026-09-18); none is a bug.

- **Explore churn.** `EXPLORE_MIN_DISTANCE = 3` often picks a frontier tile the actor sees within a fraction of a second, so Explore re-enters and logs a lot in the opening: about 35 `explore ->` lines per 120 s, against about 20 at a value of 9, with no measured change in how fast objects are found.
- **Believed-map cost.** `BeliefStore.is_walkable` recomputes `object_blocked()` on every call, so a failed A\* costs about 10 ms. Fine at 1x; a per-tick cache would remove possible hitches at 8x.
- **Stale target in the panel.** After Search gives up, `Target` keeps the abandoned name while Explore runs, and the CONTEXT panel shows it. Display only: no condition reads it there.

### Controls

Space pause/resume · N step one tick while paused · +/- sim speed (0.25x-8x) · R reset (same seed) · Shift+R reset with a new seed · T truth overlay · Esc quit.

### Headless

`cd experiments/exp-02 && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --seed K --truth --screenshot-dir screenshots --screenshot-every M` (screenshots/ is gitignored; `--truth` is optional).

---

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

---

## exp-04 — UE5 hex terrain and camera

- **Started:** 2026-09-18
- **Stack:** Unreal Engine 5.8.2, C++ (Linux). Set `UE_ROOT` to use another engine install.
- **Build:** `experiments/exp-04/scripts/build.sh`
- **Run:** `experiments/exp-04/scripts/game.sh [-Seed=N]`, or `experiments/exp-04/scripts/editor.sh` and press Play
- **Test:** `experiments/exp-04/scripts/test.sh [TestPathPrefix]` (headless UE automation tests)
- **Design:** [`exp-04/docs/specs/2026-09-18-exp-04-ue5-hex-terrain-design.md`](exp-04/docs/specs/2026-09-18-exp-04-ue5-hex-terrain-design.md)
- `build.sh` (and so `test.sh`, which calls it) refuses to run while any Unreal Editor is running. Close the editor first; the scripts never stop it for you. The check looks for an editor process launched by its path, not by window title.
- `test.sh` needs `rg` (ripgrep) on PATH to parse the automation log.

### Why

A separate line from exp-00–03. Instead of mocking AI in pygame, this gets a basic Unreal Engine 5 world running.

### What

A C++ UE5 project with no binary assets. At startup the game mode builds everything into the engine's empty `/Engine/Maps/Entry` map:

- **Terrain.** Hilly ground made from seeded layered noise (`-Seed=N`).
- **Hex grid.** A pointy-top hex grid, radius 12, defined on a flat 2D plane and draped onto the terrain as thin lines. A 2D hex coordinate stands for a spot in the 3D world.
- **Camera.** An overhead camera that pans (WASD/arrows, screen edges, middle-drag) and zooms (wheel). It tilts from about 75° down far out to about 45° close in.
- **Hover.** An outline on the tile under the mouse.

The repo holds only what's needed to build and run: no engine code, and no `.uasset`/`.umap` files. Don't save the Entry map from the editor.

### Layout

- `MuraBito.uproject`, `Config/`: project file and settings (default map, game mode, Enhanced Input)
- `Source/MuraBito/`: `HexGrid`, `TerrainHeight`, `MeshBuilders`, `CameraMath` (pure math); `Terrain`, `HexOverlay`, `CameraRig`, `InputController`, `WorldBuilder` (actors); `Materials` (runtime materials)
- `Source/MuraBito/Private/Tests/`: automation tests for the hex grid, height function, mesh builders and camera math
- `scripts/`: build, editor, game and test wrappers around the local engine install

### Controls

WASD/arrows or screen edges pan · middle-drag pans · wheel zooms · mouse hover highlights a tile.
