# exp-03 — Tiered hex world: design

**Date:** 2026-09-18
**Location:** `experiments/exp-03/`
**Stack:** Python 3.13, pygame 2.6.1, moderngl (OpenGL 3.3), numpy, pytest; uv-managed (`uv add`, `uv run`)
**Based on:** exp-02, copied at `bcae346` on `main`. Most of the copy is removed in exp-03's first commit (see "Layout").

## Purpose

exp-03 builds a hierarchical hex coordinate system at real Japanese scale (shaku, ken, cho, ri) and a procedural 3D world that loads lazily in tiers of detail around whoever needs it. A camera travels a fixed rail over the terrain, and a side panel reports what is loaded at each tier and where the camera is in the coordinate system.

It is the groundwork for tiered pathfinding (fine A\* close in, coarser regions further out), which is **not** part of exp-03. A later experiment, exp-05, merges this system into the exp-00 to exp-02 line.

All terrain, biome, prop and colour parameters are **placeholders**, to be tuned by eye.

## Decisions from brainstorming (2026-09-18)

In the order they were made; each was the user's pick or in the user's words.

1. Tiered windows, as the user described them: fine detail only close in, coarser further out. A window is **cell-based, not radial**: the loader's own cell at that level plus 3 rings of neighbouring cells.
2. **Historical ratios:** 6 shaku per ken, 60 ken per cho, 36 cho per ri. Scale is part of the problem.
3. **Split:** exp-03 is the hex system alone; exp-05 merges it into the exp-00 to exp-02 line.
4. **Procedural world, lazily loaded** "like minecraft".
5. **Packing B:** a ken is 6 shaku wide **flat to flat**, like the shaku, with a true centre shaku and the edge shaku bisected. The same packing at every level.
6. **One owner per cell:** split cells belong wholly to one parent.
7. **No actor, no pathing yet.** The camera is a special actor; **any actor can require its tiered windows loaded**. The camera's focus point is its location in world coordinates. The camera is **on rails**, with no user control.
8. **3D:** a ground mesh from noise, coloured sub-biomes, low-poly rocks and trees. Hex coordinates are 2D locations in a 3D world, **projected onto the terrain**.
9. **Rendering:** pygame window + moderngl.
10. **The terrain mesh LoD follows the hex tiers** (one LoD system).
11. **Bounded world**, about the size of a Japanese prefecture: **radius 12 ri**.
12. **Camera low**, with the horizon visible; a **2.5 m/s jog**; a **circle of radius 4 ri centred on the world centre**.
13. Start from the exp-02 copy: **keep the scaffolding, remove the rest**.
14. **Relief:** gently rolling country with **mountains around the rim**.
15. **Props placed per ken**, visible out to the ken tier; small detail per shaku.
16. **Ground types:** grass and dirt, plus bare rock and snow from height and slope; a separate forest density field.
17. **Hex lines:** every tier's borders wherever that tier is loaded, nested.
18. **Panel** contents as listed under "Panel"; addresses as local `(q, r)` offsets from the parent's centre.
19. **Loading:** a per-frame time-budgeted queue, nearest first, with the parent drawn until its children load.
20. **Borders drawn are owned borders** (they follow actual child cell edges), not ideal hexagons.

## Coordinates and addresses (`src/hexaddr.py`)

### Units

| Unit | Contains | Flat-to-flat width |
|---|---|---|
| shaku | — | 10/33 m ≈ 0.303 m |
| ken | 36 shaku | 6 shaku = 60/33 m ≈ 1.818 m |
| cho | 3,600 ken | 60 ken = 3,600/33 m ≈ 109.09 m |
| ri | 1,296 cho | 36 cho = 129,600/33 m ≈ 3,927.27 m |

Every hex at every level is **pointy-top with the same orientation**. Axial `(q, r)` coordinates; the hex-plane position of axial `(q, r)` in units of the cell's flat-to-flat width is `(q + r/2, r·√3/2)`.

### Packing B

At each level, with `N` = 6 (shaku in ken), 60 (ken in cho) or 36 (cho in ri):

- Parent centres sit on the child lattice scaled by `N`: parent `(a, b)` is centred on child `(N·a, N·b)`. No rotation between levels.
- Each parent has a true centre child. Its ideal hexagon's edges run through the centres of a row of children, which are halved; its corners fall on child centres, split three ways. (This needs `N` divisible by 6; 6, 60 and 36 all are.)
- Measured in brainstorming (nearest-centre assignment):

| N | Whole | Halved | Corners (thirds) | Area |
|---|---|---|---|---|
| 6 | 31 | 6 (1 per edge) | 6 | 36 |
| 60 | 3,541 | 114 (19 per edge) | 6 | 3,600 |
| 36 | 1,261 | 66 (11 per edge) | 6 | 1,296 |

### Ownership

`owner(c, N)` for child `c = (q, r)`:

- For parent candidates `p = (a, b)` near `(q/N, r/N)`, compute the integer `d2 = dq² + dq·dr + dr²` with `(dq, dr) = (q − N·a, r − N·b)`.
- The owner is the candidate with the smallest `d2`; **ties go to the lexicographically greatest `(a, b)`**.
- All integer arithmetic, so ties are exact. The rule is translation-invariant, so every parent owns exactly `N²` children: its whole children, the halved children on 3 of its 6 edges, and 2 of its 6 corner children. (Verified in brainstorming for N = 6, 36, 60.)

A parent's **owned territory** is therefore its ideal hexagon with battlement edges: half a child out along 3 edges and half a child in along the other 3. The owned territory is what addresses describe, what windows count, and what border lines draw.

### Global grid and addresses

- Every position resolves to a shaku: an axial `(q, r)` on one **global shaku grid**. Its origin is the world centre, which is the centre of a ri, a cho, a ken and a shaku.
- **Address:** `ri (q,r) / cho (q,r) / ken (q,r) / shaku (q,r)`. The ri part is the ri's position in the world; each other part is the child's offset from its parent's centre in the child lattice.
- **Conversions, both ways:** address ↔ global shaku ↔ world metres `(x, z)`. Also `level_cell(global_shaku, level)`, which gives the owned cell containing a shaku at any level, and `cell_center(level, cell)`.
- Height `y` is not part of the address; it comes from the terrain.

### World bounds

The world is every ri `(a, b)` within hex distance 12 of `(0, 0)`: 469 ri, 25 ri (about 98 km) across, about 6,270 km² (a typical prefecture). Its edge is the owned border of the outer ri. Nothing outside it is generated.

### Implementation notes

- `hexaddr.py` is pure Python (ints; no numpy, no pygame) and builds on the kept `hexgrid.py`.
- A vectorized numpy twin of `owner` and the conversions lives in `loading.py` or `terrain.py` for whole chunks, and is tested against `hexaddr`.

## Loaders, chunks and the load queue (`src/loading.py`)

### Chunks

A chunk is **one parent cell's children**: the unit of generation, meshing, loading and unloading.

| Chunk | Children | Loaded when |
|---|---|---|
| world | 469 ri | always |
| ri → cho | 1,296 cho | its ri is in some loader's cho window |
| cho → ken | 3,600 ken | its cho is in some loader's ken window |
| ken → shaku | 36 shaku | its ken is in some loader's shaku window |

A chunk's contents are a pure function of `(seed, level, parent cell)`: load order, timing and which loader asked never change what is generated.

### Tiers and windows

A **tier** is named by the cell size it draws. A `Loader` has a focus position (a global shaku coordinate); its request is:

| Tier | Window | Chunks | Cells |
|---|---|---|---|
| shaku | the loader's ken + 3 rings (37 ken) | 37 ken → shaku | 1,332 shaku |
| ken | the loader's cho + 3 rings (37 cho) | 37 cho → ken | 133,200 ken |
| cho | the loader's ri + 3 rings (37 ri), clipped to the world | up to 37 ri → cho | up to 47,952 cho |
| ri | the whole world | world | 469 ri |

For one loader, each window lies inside the next coarser one, so a chunk's parent cell is always loaded. `ChunkStore` accepts any number of loaders; exp-03 runs with the camera as the only one, and tests use two.

### The queue

Each frame, `ChunkStore.update(loaders)`:

1. Computes the union of all loaders' requests.
2. Queues chunks that are requested but neither loaded nor queued, ordered **coarsest level first, then by distance from the nearest loader focus to the parent cell's centre**. Ties go by `(level, parent cell)`, for determinism.
3. Unloads loaded chunks that are no longer requested, immediately, and drops queued chunks that are no longer requested. No hysteresis.
4. Loads queued chunks in order until **8 ms** of the frame has been spent (always at least one chunk).

At startup the queue is drained before the first frame. `--no-preload` skips that, so the world fills in visibly.

The renderer is notified through `on_load(chunk)` and `on_unload(chunk)` callbacks, so loading is testable without a GPU.

### Stats

Per tier: cells and chunks loaded, loads and unloads in the last second, generation time (last chunk and a rolling mean), and queue length. The panel reads these.

### Measured cost (brainstorming, rough numpy prototype)

About 3 ms for 1,300 cells, 57 ms for 25,000 and 245 ms for 133,000 (generation plus a triangle mesh). A cho → ken chunk is about 8 ms. These figures assume chunk-level numpy arrays, not a Python object per cell.

## Terrain (`src/noise.py`, `src/terrain.py`)

Everything is a pure numpy function of `(seed, world position)`. Noise is a hashed-lattice gradient noise implemented in `noise.py` (no new dependency).

### Height

`height(x, z, tier)` in metres:

- **Country:** fBm with 16 octaves, wavelengths `20 km / 2^k` for `k = 0..15` (20 km down to 0.61 m). Target amplitudes: hills of about 30 m at cho scale, bumps of about 0.5 m at ken scale, about 5 cm at shaku scale. The exact amplitude table is set in the plan.
- **Rim mountains:** ridged noise with wavelengths from 2 km to 20 km and heights up to about 1,500 m. It is multiplied by a mask of distance from the world centre: 0 inside 6 ri, smoothstep to 1 at 11 ri. The rail (radius 4 ri) runs through country, 2 ri or more from the mountains.
- **Octave cut per tier:** a tier keeps only octaves (of both terms) whose wavelength is at least **twice its cell spacing**. That leaves ri 2 octaves of country, cho 7, ken 13 and shaku 16. A coarse sample is therefore exactly the fine sample minus the dropped octaves.

### Ground type

Per cell, from its tier's height and slope (slope from neighbouring cell heights in the chunk plus its border ring):

| Type | Rule (placeholder) |
|---|---|
| snow | height above about 1,200 m (the line perturbed by noise) |
| bare rock | slope above about 35°, or height above about 900 m |
| dirt | otherwise, where a 300 m-wavelength noise field is in its lowest ~30% |
| grass | otherwise |

Each type has a base colour with slight noise shading. Coarse cells use the same rules on their tier's terrain.

### Props (with each cho → ken chunk)

- A **forest density** field (800 m wavelength) makes woods and clearings.
- Per ken, a hash of `(seed, global ken)` decides:
  - **tree:** probability up to 0.15 (scaled by forest density) on grass or dirt; never on rock or snow;
  - **rock:** about 0.02 on grass, 0.06 on dirt, 0.10 on bare rock;
  - at most one prop per ken.
- The same hash picks the prop's shaku among the ken's **inner 19** (hex distance ≤ 2 from the centre), which are always owned whole, so a prop never straddles a border. It also picks scale and yaw.
- The prop's base height is the **full-detail (shaku-tier) height** at that shaku, computed directly. It stands correctly once the shaku tier loads and sinks a few centimetres into the ken-tier mesh.

### Small detail (with each ken → shaku chunk)

Grass tufts on grass shaku (about 30%) and pebbles on dirt shaku (about 15%), hashed per global shaku.

### Prop meshes

Low-poly, instanced:
- **tree:** a 6-sided trunk plus 2 stacked cones;
- **rock:** a squashed, jittered icosahedron;
- **tuft:** 3 crossed blades;
- **pebble:** a tiny rock.

## Camera (`src/rail.py`)

- **Focus point:** it travels **anticlockwise** round a circle of **radius 4 ri** (≈ 15,709 m) centred on the world origin, at **2.5 m/s**. A lap is about 98.7 km, about 11 h. The focus height is the full-detail terrain height. At this speed a new ken comes every ~0.73 s, a new cho every ~44 s, a new ri every ~26 min.
- `--start S` begins the rail S seconds in.
- **Eye:** 8 m behind the focus point along the direction of travel, and 3 m above it, looking at it. That's about 20° of downward pitch; with a 60° vertical field of view the horizon stays in frame. The eye height is smoothed and kept at least 1.5 m above the terrain beneath it.
- The camera is the only `Loader`; its focus point is its location.

## Rendering (`src/gfx/`)

- **Window:** 1600 × 900, with the 3D view in the left 1180 × 900 and the panel in the right 420.
- **Precision:** positions are float64 in Python. Each chunk's mesh is stored relative to its parent cell's centre, and its per-frame offset is computed relative to the camera in float64, so the GPU only sees small float32 values.
- **Chunk meshes:**
  - a vertex at each child cell's centre, with the tier's height and ground colour;
  - triangles join each 3 mutually adjacent centres;
  - a chunk samples a one-cell ring of neighbours, so chunks on the same tier meet without seams;
  - each triangle is assigned to exactly one chunk by a fixed rule, so none is drawn twice.
- **Parent vs children.** A parent chunk draws its whole mesh; the fragment shader computes the pixel's owner cells with the same integer maths as `hexaddr`. It **discards** the pixel if that parent cell's child chunk is loaded. The handover therefore follows the owned border exactly.
  - Which cells have their children loaded comes from a camera-centred lookup texture per tier, large enough to cover the camera's windows.
- **Cracks between tiers:** the finer tier has extra octaves, so its edge is not on the parent's surface. Skirts cover the step. The exact skirt method is settled in the plan's scratchpad run and recorded in the plan.
- **Lighting:** one directional sun plus ambient, low-poly shading.
- **Sky:** a gradient, plus distance fog that fades the far ri tier into the horizon.
- **Props:** instanced, one draw per prop type, with an instance buffer per chunk.

### Hex lines

Drawn in the terrain fragment shader:

- For each pixel, the shader finds its owner cell at each level. It checks the neighbour across the nearest edge **of the finest tier loaded at that point**; if the two differ in owner at level L, the pixel is on an L border.
- So a border is drawn at the resolution of the finest tier loaded there: up close a ri border battlements along shaku edges, far out along cho edges.
- Each tier's lines are drawn only where that tier is loaded.
- Styles, heaviest drawn on top:

| Border | Style (placeholder) |
|---|---|
| shaku | thin, dark, low contrast |
| ken | light |
| cho | yellow |
| ri | red, heaviest |

- Widths are in screen pixels (via `fwidth`).

## Panel

A 420 × 900 pygame surface, styled like the exp-02 panel, uploaded to a texture about 10 times a second. ASCII text only, because pygame's default font lacks arrows and check marks.

- **CAMERA:**
  - the address `ri (q,r) / cho (q,r) / ken (q,r) / shaku (q,r)`;
  - world position in metres, height, lap progress, elapsed sim time.
- **TIERS:** a row per tier (shaku, ken, cho, ri) with cells loaded, chunks loaded, loads and unloads in the last second, generation time, triangle count, and queue length.
- **NEIGHBOURHOOD:** a small top-down 2D diagram of the nested windows. The camera's cell is highlighted at each level, with its 3-ring window.
- **LOADERS:** each loader and its request (for now, the camera).
- **FPS / frame time.**

## Main loop (`src/main.py`)

- A fixed 60 Hz timestep, as in the earlier experiments.
- **Flags:** `--seed`, `--frames N`, `--start S`, `--no-preload`, `--screenshot-dir DIR`, `--screenshot-every M`.
- **Controls:** `Space` pause/resume, `Esc` quit. The camera cannot be steered.
- **Headless:** `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`, with a moderngl EGL standalone context rendering to an offscreen framebuffer, read back and saved as PNG. A brainstorming probe confirmed that EGL and a pygame OpenGL window both work on the development machine (NVIDIA RTX 5090, OpenGL 3.3+).

## Layout

The first commit removes what exp-03 does not use:

- **Kept:** `pyproject.toml`, `uv.lock`, `.python-version`, `src/hexgrid.py` and `tests/test_hexgrid.py`. The shape of `main.py`'s loop and headless screenshot flags is kept, but the file is rewritten.
- **Deleted:**
  - `src/ai/`, and `body.py`, `smartobjects.py`, `wander.py`, `world.py`, `zones.py`, `mapgen.py`, `layout.py`, `sim.py`, `render.py`, `camera.py`;
  - their tests (everything except `test_hexgrid.py`; `test_main.py` is rewritten).

  exp-02 still has all of it.

```
src/
  hexgrid.py      kept: axial hex maths
  hexaddr.py      units, packing, ownership, addresses, conversions
  noise.py        hashed gradient noise, numpy
  terrain.py      height, ground type, props per chunk
  loading.py      Loader, windows, ChunkStore, the load queue
  rail.py         camera rail and eye
  gfx/            moderngl context, shaders (.glsl), chunk meshes, props, panel
  main.py         loop, flags, headless screenshots
```

**Dependencies:** `uv add moderngl numpy`. The matrices are done in numpy.

The manifest's exp-03 entry is filled in with this design.

## Testing

TDD with pytest (`pythonpath = ["src"]`).

- **`test_hexaddr.py`**
  - address ↔ global shaku ↔ metres round trips at every level;
  - every parent owns exactly 36, 3,600 or 1,296 children;
  - each split cell has exactly one owner, and the owner matches the rule;
  - neighbouring addresses across ken, cho and ri borders are correct;
  - unit lengths are exact;
  - world bounds give 469 ri;
  - the numpy twin agrees with `hexaddr`.
- **`test_noise.py`, `test_terrain.py`**
  - determinism;
  - a coarse-tier sample equals the fine sample minus exactly the dropped octaves;
  - the rim is higher than the centre;
  - the ground-type rules;
  - prop rates within tolerance over many ken;
  - props lie in the inner 19 shaku, and a prop is identical whether generated for the ken tier or looked up from the shaku tier.
- **`test_loading.py`**
  - window membership and sizes (1,332 / 133,200 / 47,952 / 469), including clipping at the world edge;
  - the union of two loaders;
  - parents always load before their children;
  - chunk contents are identical whatever the load order;
  - the time budget is respected (at least one chunk per frame);
  - unloads are immediate;
  - a simulated camera run keeps every window fully loaded once the queue drains.
- **`test_rail.py`**
  - speed is 2.5 m/s and the radius is 4 ri;
  - the direction is anticlockwise;
  - `--start` offsets the rail;
  - the eye stays at least 1.5 m above the terrain;
  - the horizon is inside the view frustum.
- **`test_gfx.py`** (skipped if no GL context is available)
  - render a top-down orthographic view of a patch containing ken, cho and ri borders, and check that pixels on the drawn borders match `hexaddr`'s owned borders;
  - check that parent-pixel discarding matches the loaded chunks.
- **`test_main.py`**
  - a headless run with `--frames` works and writes a screenshot.
- **Visual checks** (headless screenshots):
  - nested lines at a ken/cho/ri junction;
  - the tier handover in the distance, with no holes or cracks;
  - the rim mountains on the horizon;
  - woods and clearings;
  - the panel.

## Success criteria

1. **The screenshot:** a jogging-height view with shaku, ken, cho and ri borders nested on the ground, woods and clearings, and the rim mountains on the horizon.
2. **No holes and no cracks,** including during a cho crossing while the queue works through its chunks. Tier handovers show only as a change in line density.
3. **Panel counts with the queue idle:** 1,332 shaku, 133,200 ken, 47,952 cho and 469 ri.
4. **Smooth frames:** 60 fps on the development machine, with no frame over 33 ms at a cho crossing.
5. **`uv run pytest` passes,** including the shader-vs-Python border tests.

## Out of scope

- Pathfinding of any kind (tiered A\* is a later experiment).
- Actors other than the camera; manual camera control; time-scale controls.
- Water, rivers, paddies; weather; sound; save/load.
- Merging with exp-00 to exp-02 (exp-05).

## Amendments from planning (2026-09-18)

Found while running the implementation plan's code in a scratchpad. The plan (`docs/plans/2026-09-18-exp-03-tiered-hex-world-plan.md`, "Differences from the spec") has the full list. The behavioural ones:

- **Cracks between tiers: geomorphing, not skirts.** Each vertex also stores the coarser tier's mesh height at its position, and the vertex shader blends toward it between 1.3 and 2.0 parent widths from the loader focus. A loader's window edge is never nearer than 2.26 parent widths (measured at every level), so at every window edge the finer tier matches the coarser mesh exactly. Props blend the same way.
- **The tier partition.** Where tier *t* is drawn, a point belongs to the level-*L* cell `tier_cell(x, z, t, L)`: round to the nearest tier-*t* cell, then take owners upward. At the shaku tier this is exactly the address. Both sides of every handover use the same test, so tiers meet without gaps or overlaps.
- **Chunk meshes** draw every triangle that touches one of the chunk's owned cells; the fragment shader clips them to the owned territory.
- **The load queue** stops before a chunk whose level's mean generation time would take the frame past 8 ms, but always loads at least one. Measured: a median frame of 7.7 ms, and a worst frame of 24 ms at a cho crossing (one ken chunk).
- **Hex lines** get their width from the pixel footprint across the edge. They fade out where the bordered cells are only a few pixels deep, and a tier's own grid fades where its cells get small, so distant borders do not wash over the horizon.
- **Placeholder tuning:** at most 0.05 trees per ken (0.15 made a closed canopy that hid the horizon), forest density `1.8 n - 0.1`, and a dirt threshold of -0.17 (measured 30%).
- **Modules:** `chunkgeom.py` (chunk templates, built once per level) and `chunkgen.py` (chunk contents) are split out of `terrain.py`. `owner` has no numpy twin: templates are computed once from `hexaddr`, because ownership is the same for every parent at a level.
- **Rail start:** the rail starts on the centre of ri (4, 0), heading due north along a column of ken edges, so the shaku window changes many times a second for the first stretch. This is correct behaviour for that alignment, not a bug.
