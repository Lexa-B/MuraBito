# exp-04: UE5 hex terrain and camera — design

- **Date:** 2026-09-18
- **Stack:** Unreal Engine 5.8.2 (C++), Linux
- **Status:** approved design, not yet implemented

## Why

exp-00 to exp-03 mock up AI ideas in Python + pygame. exp-04 is a separate line of work: getting a basic Unreal Engine 5 project running. It isn't built on the earlier experiments.

## Goal

A UE5 project that opens and plays with:

- hilly procedural terrain,
- a hex grid defined on a flat 2D plane and projected down onto the terrain, so a 2D hex coordinate stands for a spot in the 3D world,
- an overhead camera that pans and zooms, and tilts as it zooms,
- a highlight on the hex tile under the mouse.

Nothing else. No actors, AI, buildings or gameplay.

## Constraints

- **Public MIT repo: no engine code gets copied in.** The project uses the local engine install by path and doesn't copy it. Nothing from the engine tree gets committed.
- **Everything is procedural: no binary assets.** No `.uasset` or `.umap` files, and no Git LFS. The terrain, grid, lights, sky, materials in use and input bindings are all made in C++ at runtime. Asset storage gets decided later, when there is something to author.
- **Only what's needed to build, run and develop the game.** Build outputs, caches and editor state stay out of git.
- **Naming:** plain names that say what each class does, like exp-00 to exp-03. UE's required type prefixes (`A` for actors, `F` for plain structs, `U` for UObjects) stay, but the names after them are ours: `ACameraRig`, not a "…Pawn". Code and docs don't name any game that inspired the project.

## Engine install

`UE_ROOT` defaults to `/home/lexa/DevProjects/_GameDev/_GameEngines/UnrealEngine/5.8.2` and can be overridden from the environment. It is an installed build (`InstalledBuild.txt`) with the bundled clang toolchain, so C++ modules build with `Engine/Build/BatchFiles/Linux/Build.sh`.

## Repository layout

```
experiments/exp-04/
├─ MuraBito.uproject          text JSON: one runtime module "MuraBito", EngineAssociation "5.8",
│                             plugins: ProceduralMeshComponent, EnhancedInput
├─ Config/
│  ├─ DefaultEngine.ini       GameDefaultMap and EditorStartupMap = /Engine/Maps/Entry,
│  │                          GlobalDefaultGameMode = /Script/MuraBito.WorldBuilder
│  ├─ DefaultGame.ini         project name, version
│  └─ DefaultInput.ini        Enhanced Input as the default input component/player input
├─ Source/
│  ├─ MuraBito.Target.cs
│  ├─ MuraBitoEditor.Target.cs
│  └─ MuraBito/
│     ├─ MuraBito.Build.cs
│     ├─ Public/, Private/    the classes below
│     └─ Private/Tests/       automation tests
├─ scripts/
│  ├─ env.sh                  sets UE_ROOT (default above) and the project path
│  ├─ build.sh                builds MuraBitoEditor (Development, Linux)
│  ├─ editor.sh               opens the project in UnrealEditor
│  ├─ game.sh                 runs standalone: UnrealEditor <uproject> -game [-Seed=N]
│  └─ test.sh                 runs the automation tests headless
├─ docs/specs/, docs/plans/
└─ .gitignore                 Binaries/ Intermediate/ Saved/ DerivedDataCache/ .vs/ *.code-workspace, etc.
```

`/Engine/Maps/Entry` is an empty map that ships with the engine. The project refers to it and doesn't copy it, so the repo has no level file of its own. exp-04 has no Python and no uv project.

## Components

All in the `MuraBito` module.

### `FHexGrid`: pure math

A plain struct with no UObject and no world access.

- Axial hex coordinates `FHex {Q, R}`. Pointy-top orientation, with a `TileSize` in cm (center to corner).
- `HexToXY(FHex) -> FVector2D` and `XYToHex(FVector2D) -> FHex` (cube rounding).
- `Neighbors(FHex)`, `Corners(FHex) -> 6 × FVector2D`.
- A hexagon-shaped map of radius `R` (default 12, so 25 tiles across the widest row, as in exp-00). `Contains(FHex)`, `Tiles()`, and XY bounds.

The grid only lives on the 2D plane. Projecting onto the terrain is done by the classes that use it.

### `FTerrainHeight`: the height function

A plain struct: `Height(X, Y) -> Z` in cm, from seeded layered noise (a few octaves of `FMath::PerlinNoise2D` over offset coordinates, scaled so there are rolling hills across the map). It is deterministic for a given seed. It also offers `Normal(X, Y)` by finite differences.

The terrain mesh and the grid overlay both call this one function, so the grid's projection matches the surface exactly, with no line traces needed.

### `ATerrain`: ground mesh

An actor with a `UProceduralMeshComponent`. It samples `FTerrainHeight` on a regular square grid covering the hex map's XY bounds plus a margin, and builds one mesh section with positions, normals, UVs and vertex colors graded by height (low grass green to high rocky grey-brown). It has collision enabled so mouse raycasts can hit it.

The material is an engine-provided vertex-color material. Which one works best lit in 5.8 gets checked during planning. The fallback is `/Engine/BasicShapes/BasicShapeMaterial` with a dynamic material instance tint.

### `AHexOverlay`: the projected grid

An actor with a `UProceduralMeshComponent` and two sections:

- **Grid lines:** every unique hex edge, built once, as a thin ribbon of quads. Each edge is split into short segments. Every vertex takes its Z from `Height()` plus a small lift (a few cm) so the lines follow the hills without sinking in, and the ribbon faces up along the terrain normal.
- **Hover highlight:** the outline of one tile, drawn thicker and in a different color. It's rebuilt when the hovered tile changes and hidden when the mouse is off the map.

It has no collision. The materials are unlit, and the two sections get different colors.

### `ACameraRig`: overhead camera

Subclasses `APawn`, since the engine needs one for possession, but the name follows our convention. It holds a `USpringArmComponent` and a `UCameraComponent`.

- **Pan:** WASD or the arrow keys, screen-edge scrolling, and middle-mouse drag. Speed scales with zoom. The pivot is clamped to the map's XY bounds, and its Z follows the average terrain height, not each hill.
- **Zoom:** the mouse wheel moves the arm length between a near and a far limit, with smoothing.
- **Tilt with zoom:** the pitch is interpolated from zoom, from about 75° down at the far limit to about 45° at the near limit. There's no yaw rotation.

The ranges are `UPROPERTY` values, so they can be tuned in the editor's details panel during a session.

### `AInputController`: input and picking

Subclasses `APlayerController`. The input actions and mapping context are created in C++ at startup (`NewObject<UInputAction>`, `NewObject<UInputMappingContext>`), not as assets, and are sent on to `ACameraRig`. It shows the mouse cursor.

Each tick it:

1. deprojects the cursor and line-traces against `ATerrain`,
2. takes the hit's XY and calls `FHexGrid::XYToHex`,
3. passes the tile, or none if it's off the map, to `AHexOverlay`.

### `AWorldBuilder`: startup

Subclasses `AGameModeBase` and is the project's global default. It sets `ACameraRig` as the default pawn and `AInputController` as the player controller. On `BeginPlay` it reads `-Seed=N` from the command line (default 0) and spawns:

- `ATerrain` and `AHexOverlay`, sharing one `FHexGrid` and one `FTerrainHeight`,
- lighting: a directional light (sun, angled), a sky light (real-time capture), `ASkyAtmosphere` and exponential height fog,
- the camera rig, at the map center.

## Data flow

```
-Seed ─► FTerrainHeight ─┬─► ATerrain (mesh + collision)
                         └─► AHexOverlay (draped edges)
FHexGrid ────────────────┴─► both of the above; bounds ─► ACameraRig clamp

cursor ─► AInputController: deproject ─► trace ATerrain ─► hit XY ─► FHexGrid::XYToHex
                                                                  ─► AHexOverlay.SetHover(tile | none)
```

## Error handling

- **`UE_ROOT` missing or not an engine install:** the scripts exit with a message that names the path they checked.
- **`-Seed` missing or unparsable:** use 0 and log it.
- **Cursor ray misses the terrain, or lands off the map:** clear the hover. That's normal, not an error.
- **An engine material fails to load:** log a warning and fall back to the default material, so the world still shows.

## Testing

UE Automation tests (`IMPLEMENT_SIMPLE_AUTOMATION_TEST`, filter prefix `MuraBito.`), run headless by `scripts/test.sh`:

```
UnrealEditor-Cmd <uproject> -ExecCmds="Automation RunTests MuraBito; Quit" -unattended -nullrhi -nosplash -log
```

The script's exit code reflects whether the tests passed.

Covered:

- **`FHexGrid`:** `HexToXY` → `XYToHex` round-trips for every tile, points near but inside a tile's edge map to that tile, the six neighbors are correct, the tile count for radius R is `3R² + 3R + 1`, and `Contains` works at the edge.
- **`FTerrainHeight`:** the same seed gives identical heights, different seeds give different heights, and the height range stays within the configured limits.
- **Draping:** every overlay vertex has `Z == Height(X, Y) + lift`.
- **Picking math:** the hex center, and points just inside each corner, map back to the right tile via `XYToHex`.
- **Camera:** the pitch at the zoom limits and midpoint matches the formula, and the pan clamp holds at the bounds. This tests pure helper functions, not a running world.

Checked by hand (`scripts/game.sh`, or play in the editor): how the terrain and grid look, how the camera feels, and whether the hover tracks the cursor across slopes.

## Out of scope

Actors and characters, AI (StateTree and Smart Objects), buildings, tile data or tile types, water, foliage, saving, UI beyond the hover highlight, packaging builds, and any binary assets or LFS.

## Worktree

Developed in `.claude/worktrees/exp-04` on branch `worktree-exp-04`. The experiment gets an entry in `experiments/manifest.md` with Build, Editor, Game and Test commands in place of `uv run`.
