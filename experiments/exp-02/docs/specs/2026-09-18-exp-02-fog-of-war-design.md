# exp-02 — Fog of war and the believed world: design

**Date:** 2026-09-18
**Location:** `experiments/exp-02/`
**Stack:** Python 3.13, pygame 2.6.1, pytest; uv-managed (`uv add`, `uv run`)
**Based on:** exp-01, copied at `cfa81eb` on branch `exp-02-impl`. The exp-01 spec is at `experiments/exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md`; it relies on the exp-00 spec for the parts it leaves unchanged.
**Source brief:** `experiments/exp-02/docs/2026-09-18-exp-02-fog-of-war-design.md` (draft brief with the brainstorm decisions recorded in place). This spec supersedes it where they differ.

## Purpose

In exp-00 and exp-01 the actor is omniscient: `FindAndClaim` queries ground truth, and chasing reads the target's true tile every tick. exp-02 makes the actor earn its knowledge. The world stays the same kind of world (hex map, zones, wandering Smart Objects), but the actor only knows what it has seen. It keeps a private belief store, paths on a believed map, dead-reckons objects it has lost sight of, notices when a belief is wrong, and searches or explores.

**Thesis to demonstrate:** partial observability slots in *underneath* the decision layer. The rule table does not change; only what the tree's conditions, target choices and movement goals *read* changes. The seam between truth and belief is drawn here as the future boundary between the engine and the brain.

The rules, layout parameters and tuning constants are **placeholders**.

## Relationship to exp-01

- **A self-contained copy.** `experiments/exp-02/` started as a copy of `experiments/exp-01/` (`src/`, `tests/`, `pyproject.toml`, `uv.lock`, `.python-version`), with the uv project renamed to `murabito-exp-02`. That copy is commit `cfa81eb`.
- **exp-01 is frozen.** Nothing under `experiments/exp-01/` changes.
- **Unchanged from exp-01** unless a section below says otherwise:
  - `hexgrid.py`, `wander.py`, `camera.py`, `ai/pathing.py`, `ai/statetree.py`;
  - `world.py` (except that `zone_of` and `ZONES` move to `zones.py` and are re-exported);
  - the window size, the fixed timestep, sim speeds, and the headless flags;
  - the three zones, object wandering, blocking, and the `RULES` table.
- **exp-01's three open questions** stay with exp-01.

## Module map

| Module | Status | Role |
|---|---|---|
| `src/zones.py` | new | `ZONES` and the pure `zone_of(tile)`, moved from `world.py`. `world.py` imports and re-exports both. |
| `src/ai/vision.py` | new | Pure geometry: `visible_tiles(...)` by hex shadowcasting. |
| `src/ai/beliefs.py` | new | `BeliefStore`: object beliefs, tile memory, the believed map, search areas, the frontier. |
| `src/ai/perception.py` | new | `PerceptionEvaluator(world)`: the only AI code holding the world. Writes the belief store. |
| `src/body.py` | new | `Body(world, actor, beliefs)`: the truth-side actuator (claim, release, in-use, interactions). |
| `src/mapgen.py` | new | Random walls, then random object and actor starts. |
| `src/smartobjects.py` | changed | `SmartObject` gains `casts_shadow: bool`. |
| `src/layout.py` | changed | Object definitions only; `build_world(rng)` calls mapgen. `WALLS` and `ACTOR_START` are removed. |
| `src/ai/tasks.py` | changed | `ChooseTarget`, belief-based `MoveTo`, `Search`, `Explore`, Body-based `Interact`. `FindAndClaim` is removed. |
| `src/ai/tree_def.py` | changed | New GoUse subtree. `RULES` unchanged. |
| `src/sim.py` | changed | Wires beliefs, perception and Body; ctx has no world. |
| `src/render.py` | changed | Fog, ghosts, cone, search area, truth overlay; panel belief table and collapsed branches. |
| `src/main.py` | changed | `T`, `Shift+R`, `--truth`; seed shown in the status text. |

No new module imports pygame except through `render.py` and `main.py`, as before.

## Tick order and the truth/belief boundary

Each `Sim.step(dt)`:

```
mover.tick(dt)                     objects wander (truth, unchanged from exp-01)
tree.tick(ctx, dt)
  ├─ PerceptionEvaluator           OBSERVE + ORIENT: reads the world, writes the BeliefStore
  ├─ ZoneEvaluator                 ctx["Zone"] = zone_of(actor.tile)   (pure; self-knowledge)
  └─ select / tick leaf task       DECIDE + ACT: reads ctx["beliefs"], acts through ctx["body"]
```

Perception runs after the mover, so beliefs reflect this tick's positions.

**The boundary is structural:**
- `ctx` has no `"world"` key. The world is passed only to `PerceptionEvaluator`, `Body`, the mover, and the renderer.
- `ai/tasks.py`, `ai/tree_def.py` and `ai/beliefs.py` import none of `world`, `smartobjects`, `wander` or `body`.
- Tasks read `ctx["beliefs"]` (the belief store) and `ctx["actor"]` (the actor's own tile, facing and motion, which is self-knowledge). They affect other objects only through `ctx["body"]`.
- `ai/pathing.astar(world, start, goals)` is unchanged: tasks pass it the belief store, which provides `radius` and `is_walkable`.

**Context keys** (built in `sim.py`):

| Key | Meaning |
|---|---|
| `Zone` | the actor's zone |
| `LastUsed` | name of the last object used, or `None` |
| `Target` | the intention: name of the chosen object, or `None` |
| `Claim` | `(name, slot_index)` once a claim is held, or `None` |
| `Interaction`, `InteractionElapsed` | as in exp-01 |
| `Path` | as in exp-01 |
| `actor`, `rng`, `log` | as in exp-01 |
| `beliefs` | the `BeliefStore` |
| `body` | the `Body` |

## Vision (`src/ai/vision.py`)

`visible_tiles(origin, facing, blockers, radius=SENSE_RANGE, half_angle=SENSE_HALF_ANGLE, map_radius=MAP_RADIUS) -> set[Tile]`

- **Geometry.** Angles use unsquashed pointy-top hex centers: `px(q, r) = (sqrt(3) * (q + r/2), 1.5 * r)`. The facing direction is `px(DIRECTIONS[facing])`. Each angle is measured relative to the facing direction and normalized to `(-180°, 180°]`.
- **Candidates.**
  - The origin tile and its in-bounds neighbors (distance 1) are always candidates, whatever the facing.
  - A tile at distance 2..`radius` is a candidate if its center's relative angle is within `[-half_angle, +half_angle]`, edges included.
- **Shadowcasting, ring by ring.** Rings are processed outward from distance 1 to `radius`.
  - A candidate is **visible** unless its center angle lies *strictly inside* a shadow interval cast by a blocker in a closer ring. A center exactly on an interval edge counts as visible.
  - A visible tile that is in `blockers` adds a shadow interval: the angular span of its 6 corners (`px(tile) + (cos(30° + 60°·i), sin(30° + 60°·i))`) as seen from the origin. Intervals that cross ±180° are split in two.
  - A blocker hidden by a closer shadow casts nothing more (it is already inside a shadow).
  - Distance-1 tiles can never be shadowed.
- **Blockers passed by perception:** the true walls, plus the logical `tile` of every object with `casts_shadow`. A lit blocker is itself visible.
- Out-of-bounds tiles are never returned.

**Constants** (module-level, in `ai/perception.py`): `SENSE_RANGE = 6`, `SENSE_HALF_ANGLE = 60` degrees. On an open map, the cone plus near tiles is 52 tiles (about 11% of the 469-tile map).

## Perception (`src/ai/perception.py`)

`PerceptionEvaluator(world)`, an `Evaluator`, runs first each tick:

1. `vis = visible_tiles(actor.tile, actor.facing, walls ∪ {obj.tile for obj with casts_shadow})`.
2. `beliefs.advance(dt)` advances the belief store's clock (`beliefs.now`).
3. `beliefs.observe_tiles(vis)`: every tile in `vis` gets `last_seen = now`; every true wall in `vis` joins `known_walls`. `beliefs.visible_now = vis`.
4. For each object, it is **seen** if its `tile` or any of its slot tiles is in `vis`. Each seen object yields an `Observation(name, tags, tile, next_tile, slot_directions, in_use)` passed to `beliefs.observe_object(...)`. `beliefs.seen_now` is the set of names seen this tick.
5. `beliefs.apply_negative_evidence()` (see Beliefs).
6. Log lines (ASCII only), written only when something changes:
   - `see B at (q,r)`: first sighting, or seen again after not being seen the previous tick;
   - `lose sight of B`: seen the previous tick, not this tick;
   - `belief: B not at (q,r) - retracting`: negative evidence;
   - `belief: B -> REGION`, `belief: B -> LOST`: a level change caused by radius growth.
   Learning a wall is not logged; walls appear in the fog view.

Perception reads truth, which is its job. Nothing it writes describes a tile or object outside `vis`.

## Beliefs (`src/ai/beliefs.py`)

### Object beliefs

Per known object, a `Belief`:

| Field | Meaning |
|---|---|
| `name`, `tags` | identity, as observed |
| `slot_directions` | slot directions, as observed |
| `datum_tile`, `datum_time` | where and when the object was last seen |
| `datum_next_tile` | its `next_tile` when last seen (`None` if not mid-step) |
| `datum_zone` | `zone_of(datum_tile)`: the zone it was last seen in |
| `observed_seconds`, `steps` | watching time and observed steps, excluding in-use time |
| `course` | direction index of the most recent observed step, or `None` |
| `radius_floor` | 0, or just above `POINT_RADIUS` after negative evidence |

**On observation** (`observe_object`):
- If there is no belief yet, create one with `observed_seconds = 0`, `steps = 0`, `course = None`.
- If the object was also seen the previous tick **and** is not `in_use` this tick:
  - `observed_seconds += dt`;
  - if `tile != datum_tile`: `steps += 1` and `course = direction_index(datum_tile, tile)`.

  (Time and steps while in use are excluded, because A and B freeze while in use. A step seen after a gap in visibility is not counted, since the path taken is unknown.)
- Then reset the datum: `datum_tile = tile`, `datum_time = now`, `datum_next_tile = next_tile`, `datum_zone = zone_of(tile)`, `slot_directions` as observed, `radius_floor = 0`.

**Derived values** (computed on read, with `t = now - datum_time`):
- **Speed:** `w = observed_seconds / (observed_seconds + PRIOR_SECONDS)`; `speed = (1 - w) * PRIOR_SPEED + w * (steps / observed_seconds)` (the second term is 0 when `observed_seconds == 0`).
  - Course and speed are tracked separately rather than as one mean velocity vector: a random wander's lifetime mean displacement is near zero, which would predict no motion at all.
- **Radius:** `max(speed * RADIUS_FACTOR * t, radius_floor)`.
- **Ghost tile:** if `course` is `None`, `datum_tile`. Otherwise, walk from `datum_tile` in direction `course` for `floor(speed * t)` steps, stopping at the last tile that is in bounds, in `datum_zone`, and not in `known_walls`.
- **Level:** `POINT` if `radius <= POINT_RADIUS`; `REGION` if `radius <= LOST_RADIUS`; otherwise `LOST`.
- **Confidence** (display only): `max(0, 1 - radius / LOST_RADIUS)`.
- **Believed slot tiles:** `add(ghost_tile, DIRECTIONS[d])` for each slot direction; the facing at a slot is `(d + 3) % 6`.

A belief for an object seen this tick has `t = 0`: radius 0 (unless `radius_floor`, which is reset on observation), ghost tile = datum tile, level `POINT`.

**Negative evidence** (`apply_negative_evidence`): for each belief whose name is not in `seen_now`, whose level is `POINT`, and whose ghost tile is in `visible_now`: set `radius_floor = POINT_RADIUS + 0.01` (so the level becomes `REGION` at once) and log the retraction. The datum and dead reckoning are unchanged. Absence of an object from a tile *outside* `visible_now` never retracts anything.

**Constants** (module-level, tunable):

| Constant | Value | Notes |
|---|---|---|
| `PRIOR_SPEED` | 0.3 tiles/s | measured mean drift of an unused exp-01 object |
| `PRIOR_SECONDS` | 10 s | weight of the prior in the speed blend |
| `RADIUS_FACTOR` | 2 | the radius grows at speed × 2 |
| `POINT_RADIUS` | 5 tiles | at the prior speed: `POINT` for about 8.3 s |
| `LOST_RADIUS` | 13 tiles | at the prior speed: `LOST` after about 21.7 s |
| `CLEAR_DISTANCE` | 2 tiles | cleared-tile expiry |
| `EXPLORE_MIN_DISTANCE` | 3 tiles | frontier preference |

Reference measurements from exp-01's wander (120 object runs): mean drift 1.3 tiles after 4 s, 2.3 after 8 s, 3.7 after 15 s, 4.7 after 30 s; 90% of objects within 2, 4, 6 and 8 tiles at those times.

### Tile memory and the believed map

- `last_seen: dict[Tile, float]` (absent means never seen) and `known_walls: set[Tile]`.
- `radius`: the map radius (12), for `astar`.
- `is_walkable(t)`: true when `t` is in bounds, not in `known_walls`, not the ghost tile of any `POINT` belief, and not the `datum_next_tile` of any object in `seen_now`. (A `next_tile` for an object not seen this tick is stale and ignored.) Tiles never seen count as walkable.
- `walkable_tiles()`: every in-bounds tile for which `is_walkable` holds.

Phantom obstacles are expected: a stale `POINT` ghost blocks planning until it decays below `POINT` or is retracted.

### Search area

`search_area(name) -> list[Tile]` for a belief:

1. All tiles within `radius` (hex distance, `<=`) of the ghost tile;
2. that are in bounds, in `datum_zone`, and not in `known_walls`;
3. minus **cleared** tiles;
4. ordered by distance from the ghost tile, ties by `(q, r)`.

A tile `t` is **cleared** when both hold:
- `last_seen[t] > datum_time` (it was seen after the object was last seen, and the object was not on it, or the belief would have been corrected); and
- `(now - last_seen[t]) * speed * RADIUS_FACTOR < CLEAR_DISTANCE` (seen recently enough that the object is unlikely to have wandered back in; about 3.3 s at the prior speed).

This is a simplification of "until the object could have reached it", which would need each tile's distance from the edge of the checked region.

### Frontier

`frontier(actor_tile) -> Tile | None`, over `walkable_tiles()` excluding `visible_now`:

1. If any never-seen tile is at hex distance `>= EXPLORE_MIN_DISTANCE` from the actor, the nearest such tile.
2. Otherwise, if any never-seen tile exists, the nearest one.
3. Otherwise, the tile with the smallest `last_seen`, ties by distance, then `(q, r)`.
4. `None` if there are no candidates.

The minimum distance avoids one-tile trips to never-seen tiles just behind the actor's cone.

## Body (`src/body.py`)

`Body(world, actor, beliefs)` is the truth-side actuator. It is engine-side, outside `ai/`. It keeps the real `ClaimHandle` private.

- `claim(name) -> int | None`
  - If `name` is not in `beliefs.seen_now`: log `body: claim B refused (not in view)` and return `None`.
  - Otherwise, from the object's unclaimed slots whose true tile is walkable (exp-01's `find` with its `blocked_fn`), claim the one nearest the actor. Return its slot index, or log `body: claim B failed (no free slot)` and return `None`.
  - MoveTo retries at every tile boundary, so a failure line is logged only when it differs from the previous failure logged for that object; a success resets this.
- `release()`: releases the held claim, if any. Idempotent.
- `set_in_use(in_use: bool)`: sets or clears in-use on the claimed object only. Clearing remembers the object it set, so it clears the right one even after release (as exp-01's `Interact` did).
- `interactions() -> list[Interaction]`: the claimed object's advertised interactions, or `[]`.
- `claimed_slot() -> tuple[str, int] | None`.

Truth-side arbitration (a slot on a real wall, a slot already claimed) is the Body's call, as the Smart Object subsystem's would be in UE5.

## Tasks (`src/ai/tasks.py`)

**`ZoneEvaluator`:** `ctx["Zone"] = zone_of(ctx["actor"].tile)`, using `zones.zone_of`.

**`ChooseTarget(tag_query)`**, on enter:
- Candidates: beliefs whose tags include every tag in the query, with level not `LOST`.
- Pick the nearest `POINT` candidate by hex distance from the actor to its ghost tile (ties by name). Failing that, the nearest `REGION` candidate.
- On success: `ctx["Target"] = name`, log `target B (POINT)` or `target B (REGION)`, return `SUCCEEDED` on its tick. Otherwise `FAILED`.

**`MoveTo(goal_fn, chase=False)`** keeps exp-01's stepping loop with these changes:
- Planning is `astar(ctx["beliefs"], actor.tile, goals)`; the step check is `beliefs.is_walkable(next_tile)` (log `replan: path blocked` and re-plan when it fails).
- **`target_goal(ctx)`**, used by the GoUse `MoveTo`:
  - with `ctx["Claim"] = (name, i)`: `{believed slot tile of slot i}`;
  - otherwise: the believed slot tiles of `ctx["Target"]` for which `beliefs.is_walkable` holds.
- **Claim on sight.** At each tile boundary (no step in progress), if `ctx["Claim"]` is `None` and `ctx["Target"]` is in `beliefs.seen_now`: `i = body.claim(name)`; on success set `ctx["Claim"] = (name, i)` and log `claim B / slot i`.
- **Chase.** With `chase=True`, goals are re-read at each tile boundary; a change re-plans and logs `replan: target moved`. (For an unseen target this happens when the dead-reckoned ghost moves; claiming narrows the goal.)
- **Finishing.**
  - With a claim: `SUCCEEDED` when standing on the claimed slot's believed tile with no step in progress; the actor faces `(direction + 3) % 6`.
  - Without a claim, standing on a goal tile: try `body.claim` once more; if it still fails, `FAILED`.
  - `FAILED` if a (re-)plan finds no path or the goal set is empty.
- `random_tile_goal(ctx)` for Wander draws from `beliefs.walkable_tiles()`.

**`Search`** (target = `ctx["Target"]`):
- Each tick, first: if the belief is `LOST` or `search_area` is empty, log `search: give up on B` and return `FAILED`.
- It walks, using an internal MoveTo-style stepper (chase off), toward the first tile of `search_area`. It picks a new tile when the current one is reached, becomes cleared, or leaves the area, and re-plans then.
- Otherwise `RUNNING`. Finding the target is handled by the tree's `TargetIsPoint` transition.

**`Explore(tag_query)`**:
- On enter: `beliefs.frontier(actor.tile)`; plan to it. Log `explore -> (q,r)`.
- Steps like MoveTo with `chase=False`.
- `SUCCEEDED` when the actor reaches the frontier tile **or** the tile's `last_seen` is later than the time Explore entered (seen from a distance).
- `FAILED` if there is no frontier tile or no path.

**`Interact`**:
- On enter: `body.set_in_use(True)`; pick from `body.interactions()` with `ctx["rng"]`; set `Interaction` and `InteractionElapsed` as in exp-01.
- Each tick, before counting time: `FAILED` (log `interact: slot drifted away`) if there is no claim or `actor.tile` is not the claimed slot's believed tile. (The object is adjacent, and neighbors are always observed, so this belief is current.)
- Completion and effects as in exp-01.
- On exit (every route): `body.set_in_use(False)`; clear `Interaction` and `InteractionElapsed`.

**`Wait(duration)`:** unchanged.

**`release_claim(ctx)`**, the `on_exit` of every GoUse state:
- If `ctx["Claim"]`: `body.release()`, log `release B / slot i`, clear `Claim`.
- Always clear `Target` (an intention must not outlive its GoUse branch).

**Conditions** (in `tree_def.py`, reading only `ctx["Target"]` and the belief store):
- `TargetIsRegion`: the target's level is `REGION`.
- `TargetNotPoint`: the target's level is `REGION` or `LOST`.
- `TargetIsPoint`: the target's level is `POINT`.
- `MatchSeen(tag_query)`: some name in `seen_now` has a belief matching the tag query.

## Tree (`src/ai/tree_def.py`)

`RULES`, `rule_condition`, the GoUse enter conditions, `GoUse(Nearest)`'s `LastUsed==None` condition, and the Wander branch are unchanged from exp-01. Each `go_use_state(name, tag_query, ...)` builds:

```
GoUse(X)                                   on_exit: release_claim
├─ ChooseTarget(tag)
│     ON_CONDITION TargetIsRegion -> GoUse(X)/Search      (listed first)
│     ON_COMPLETED               -> GoUse(X)/MoveTo
│     ON_FAILED                  -> GoUse(X)/Explore
├─ MoveTo(target_goal, chase=True)
│     ON_CONDITION TargetNotPoint -> GoUse(X)/Search
│     ON_COMPLETED                -> GoUse(X)/Interact
│     ON_FAILED                   -> Wander
├─ Search
│     ON_CONDITION TargetIsPoint  -> GoUse(X)/MoveTo
│     ON_FAILED                   -> GoUse(X)/Explore
├─ Explore(tag)
│     ON_CONDITION MatchSeen(tag) -> GoUse(X)/ChooseTarget
│     ON_COMPLETED                -> GoUse(X)/Explore
│     ON_FAILED                   -> Wander
└─ Interact
      ON_COMPLETED -> ROOT
      ON_FAILED    -> ROOT
```

How this relies on the existing engine:
- A state's transitions are checked in order and the first match wins, so a `REGION` choice goes straight to Search.
- Transitions between siblings keep `GoUse(X)` on the active path, so `release_claim` does not run and a claim or intention survives a short search. Leaving the branch (Wander, ROOT, reset) releases it.
- `Explore -> GoUse(X)/Explore` targets the state itself, so the engine re-enters it and a new frontier is chosen.
- These `ON_CONDITION` transitions are checked every tick, so re-deciding happens as soon as perception updates the beliefs (the brief's OODA "plan monitor").

**Decided policies:**
- **Never substitute.** Once a target is chosen, the actor does not switch to another matching object mid-search, even if one becomes `POINT`. This only affects `GoUse(Nearest)`.
- **Cold start.** The actor starts with no beliefs. `LastUsed` is `None`, so `GoUse(Nearest)` is selected, `ChooseTarget` fails, and the actor explores until any object is seen.

## Map generation (`src/mapgen.py`)

`generate(rng, objects) -> (walls, placements, actor_tile, actor_facing)`, all drawn from the sim's `random.Random(seed)` in this fixed order:

**1. Walls**
- Target count: `rng.randint(30, 40)`.
- Repeat: choose a start tile uniformly from all tiles, a direction `rng.randrange(6)`, and a length `rng.randint(2, 5)`. Truncate the segment so the total never exceeds 40. Accept it only if every tile in it:
  - is in bounds and not already a wall;
  - has all 6 of its in-bounds neighbors in its own zone (as exp-01's `test_walls_are_in_range_in_bounds_and_away_from_zone_borders` checks);
  - keeps its zone's non-wall tiles connected (flood fill).
- Stop once the total reaches the target.

**2. Objects**, in `OBJECTS` order:
- A random tile in the object's home zone that is not a wall and not another object's tile, with at least one slot tile in bounds, not a wall, and not an object tile.
- `heading = rng.randrange(6)`.

**3. Actor**
- A random tile that is not a wall, not an object tile and not any slot tile, with `facing = rng.randrange(6)`.
- Re-rolled (tile and facing only) until:
  - `visible_tiles(...)` from there, with the true blockers, contains no object tile and no slot tile; and
  - every walkable slot tile is reachable from it by `astar` on the true world.

**Guard:** each of steps 1–3 gives up after 2000 attempts with a `RuntimeError` naming the step and seed. Tests over seeds 0–49 show it is not hit.

**`layout.py`** keeps the placeholder interactions and `OBJECTS`, now `(name, slot directions, home zone, pauses_during_use, casts_shadow)`:

| Object | Home zone | Slot directions | `pauses_during_use` | `casts_shadow` |
|---|---|---|---|---|
| A | NW | (0, 5) | true | true |
| B | S | (2, 1) | true | true |
| C | NE | (3, 4) | false | false |

`build_world(rng) -> (World, Actor)` runs `mapgen.generate`, builds the world, and places the objects and actor.

## Sim wiring (`src/sim.py`)

`build_sim(seed)`:
1. `rng = random.Random(seed)`; `world, actor = build_world(rng)`.
2. `beliefs = BeliefStore()`; `body = Body(world, actor, beliefs)`.
3. `tree = build_tree()`, with evaluators `[PerceptionEvaluator(world), ZoneEvaluator()]` in that order.
4. `ctx` as in the context table; `mover = ObjectMover(world, actor, rng)`.

`Sim` gains `beliefs`, `body` and `seed` fields. `Sim.step(dt)` is unchanged: mover, then tree.

## Rendering (`src/render.py`)

The window, world view and panel sizes are unchanged. The renderer reads truth from `sim.world` only for objects in view and for the truth overlay; everything else comes from `ctx["beliefs"]`.

**World view:**
- **Floor fog:** zone tint, shaded ×1.0 for tiles in `visible_now`, ×0.55 for tiles seen before, ×0.2 with no grid lines for tiles never seen.
- **Walls:** only `known_walls` are drawn as columns; dimmed when not in `visible_now`.
- **Objects in `seen_now`:** drawn as in exp-01 (interpolated column, heading tick, pause marker, slot markers with claimed and blocked styling).
- **Ghosts:** every other belief that is not `LOST` is drawn as a translucent lettered column at its ghost tile, with alpha scaled by confidence, plus a small confidence bar.
- **Search area:** while the active leaf is Search, the target's `search_area` tiles get a faint outline in the object's color.
- **Sense cone:** two faint rays at ±`SENSE_HALF_ANGLE` from the actor's facing, and an arc at `SENSE_RANGE`.
- **Path dots:** from `ctx["Path"]`, as before.
- **Truth overlay** (toggled by `T`, or `--truth`): faint outline columns for true objects not in `seen_now` and for true walls not in `known_walls`.
- **Status text:** `<speed>x`, `PAUSED` when paused, `TRUTH` when the overlay is on, and `seed N`.
- **Hint line:** `Space pause | N step | +/- speed | R reset | Shift+R new seed | T truth | Esc quit`.
- Translucent drawing uses one reusable `SRCALPHA` overlay surface.

**Brain panel:**
- **STATE TREE:** inactive GoUse branches are collapsed: their name and enter conditions (with pass/fail marks) are shown, but not their children. The active GoUse branch, Root and Wander are shown in full.
- **CONTEXT:** as in exp-01; `Claim` shows `B / slot i` from the `(name, slot)` tuple.
- **BELIEFS** (new): one row per known object, e.g. `B  (3,-4)  12.3s  0.42  REGION  0.31t/s` (ghost tile, age since last sighting, confidence, level, speed). A row shows `seen` in place of the age while the object is in `seen_now`.
- **TRANSITION LOG:** 12 lines, as before, including the new log lines.

Estimated panel height with collapsing is about 790 px of the 900 available (exp-01 used about 830 px; without collapsing, exp-02 would need about 1,040).

## Controls (`src/main.py`)

- Unchanged: `Space`, `N`, `+`/`-`, `Esc`.
- `R`: reset and rebuild from the current seed.
- `Shift+R`: pick a new random seed (from an unseeded `random.Random()`), then reset and rebuild from it.
- `T`: toggle the truth overlay.
- `--truth` flag: start with the overlay on (for headless screenshots).
- `--seed` sets the starting seed, as before.

## Testing

TDD with pytest (`pythonpath = ["src"]`). The copied exp-01 tests are kept and updated where behavior changed; `test_layout.py` is replaced by `test_mapgen.py`. Randomized runs are tested with invariants over seeds, and the exp-01 log-spy pattern (replacing `tree.write_log` and `ctx["log"]`) is kept.

- **`test_vision.py`**
  - the origin and its neighbors are visible for every facing;
  - a tile at exactly ±60° is a candidate, and one beyond is not; distance 7 is never visible;
  - a wall hides the tile directly behind it, and the wall itself is visible;
  - the tie rule: a center exactly on a shadow edge is visible;
  - a neighbor is never shadowed;
  - rotating the facing rotates the visible set;
  - out-of-bounds tiles are never returned.
- **`test_beliefs.py`**
  - first sighting creates a belief at radius 0, level `POINT`;
  - speed blending matches the formula (prior only; after observed steps);
  - in-use ticks add neither seconds nor steps; a step seen after a visibility gap is not counted; `course` is the last observed step;
  - radius growth over time; `radius_floor` after negative evidence, reset by the next observation;
  - the ghost dead-reckons along `course` and stops at the zone edge, a known wall, and the map edge; with no course it stays at the datum;
  - level thresholds at exactly 5 and 13; confidence display;
  - negative evidence only when the ghost tile is in `visible_now` and the object is not in `seen_now`;
  - `is_walkable`: known walls, `POINT` ghosts (not `REGION` ones), `next_tile` of objects seen this tick only; never-seen tiles are walkable;
  - `search_area`: radius, zone clip, both cleared-tile conditions (including expiry), ordering;
  - `frontier`: prefers never-seen tiles at distance ≥ 3, then nearer never-seen tiles, then the oldest-seen tile; excludes visible tiles.
- **`test_perception.py`**
  - only objects whose tile or slot tile is visible create or update beliefs;
  - walls join `known_walls` only when visible;
  - an object's absence from a tile outside view never retracts a belief;
  - `see`, `lose sight`, retraction and level-change log lines each fire once per change.
- **`test_body.py`**
  - `claim` is refused for an object not in `seen_now`;
  - `claim` picks the nearest unclaimed slot with a truly walkable tile, and fails when none is free;
  - `release` is idempotent; `set_in_use` affects only the claimed object and clears the right one;
  - the `ClaimHandle` is never placed in `ctx`.
- **`test_mapgen.py`** (seeds 0–49)
  - wall count in 30–40; every wall's neighbors in its zone; each zone's non-wall tiles connected;
  - each object in its home zone, not on a wall or another object, with at least one walkable slot tile;
  - the actor not on a wall, object or slot tile; nothing (object or slot tile) visible at tick 0; every walkable slot reachable;
  - the same seed gives an identical map; seeds 0 and 1 differ.
- **No-cheating** (`test_boundary.py`)
  - structural: `build_sim(...).ctx` has no `"world"` key; the source of `ai/tasks.py`, `ai/tree_def.py` and `ai/beliefs.py` imports none of `world`, `smartobjects`, `wander`, `body`;
  - behavioral: with a belief placing B at X while the true B is at Y outside the actor's view, `ChooseTarget`, `MoveTo`'s goals and re-plans, and `search_area` all derive from X.
- **`test_tasks.py`** (updated)
  - `ChooseTarget`: `POINT` before `REGION`, nearest first, `LOST` excluded, fails with no candidates;
  - `MoveTo`: claims only when the target is in `seen_now`; the goal narrows after the claim; `replan: target moved` when the ghost moves; `replan: path blocked` from the believed map; fails with no path; fails on arriving without a claim;
  - `Search`: walks toward the first area tile; gives up on `LOST` and on an empty area;
  - `Explore`: succeeds on arrival and on seeing the tile from a distance; fails with no frontier;
  - `Interact`: fails when the believed slot tile is not the actor's tile; in-use is cleared on success, failure, and reset;
  - `release_claim` clears `Target` even without a claim.
- **`test_tree_def.py`** (updated): the full `RULES` × Zone table, as in exp-01; each GoUse's transitions and their order match the tree above.
- **`test_statetree.py`, `test_hexgrid.py`, `test_pathing.py`, `test_wander.py`, `test_world.py`, `test_smartobjects.py`:** kept; updated only for moved imports and the new `casts_shadow` field.
- **`test_sim.py`** (updated). Long runs over seeds 0–4 check every tick that:
  - there is at most one live claim, and `ctx["Claim"]` matches the Body's claim;
  - every successful `Body.claim` call was for an object in `seen_now` that tick (spy);
  - no `error` log lines appear;
  - every object is in its home zone, and no object's `tile` or `next_tile` equals the actor's `tile` or `next_tile`;
  - while the active leaf is `Interact` with a claim, exactly the claimed object is in use; otherwise none is;
  - no `interact: slot drifted away` line for an object with `pauses_during_use`;
  - **every belief's datum matches the true object position at `datum_time`** (checked against a recorded truth history).

  Also: `Sim.step` ticks the mover before the tree, and perception before the zone evaluator; two runs with the same seed produce identical logs; for each seed, all three objects are seen within a time bound, and on seed 0 each of A, B and C is used within a time bound. The two time bounds are measured in the plan's scratchpad run and written into the plan with margin.
- **`test_main.py`** (updated): the headless run still works, with and without `--truth`.
- **Visual check:** headless screenshot runs with and without `--truth`, confirming: the three fog levels; walls appearing as they are seen; the sense cone; a ghost drifting from the true object (truth overlay); a retraction log line followed by a visible search area; claim on sight; collapsed inactive branches; the belief table filling in during the opening.

## Success criteria

1. **The screenshot:** the actor walking toward ghost-B while true-B sits a couple of tiles away (visible with the truth overlay), fog dimmed and the ghost translucent.
2. The actor arrives, the retraction line fires, a search follows, then a sighting, claim on sight, and an interaction.
3. Cold start: the opening is legible as *explore → see objects → begin the rule loop*, with the belief table filling in live.
4. `uv run pytest` passes, including the no-cheating tests.
5. The `RULES` table is identical between exp-01 and exp-02 (`git diff` shows no change to it).

## Out of scope

- Needs or utility scoring; the placeholder rule table stays.
- Multiple actors; social behavior; memory that persists across resets.
- Provenance or hearsay; probabilistic occupancy maps (search is geometric).
- Senses other than sight; any LLM integration.
- Changes to exp-01, or to exp-01's open questions.
- Manual camera control, sound, save/load.
