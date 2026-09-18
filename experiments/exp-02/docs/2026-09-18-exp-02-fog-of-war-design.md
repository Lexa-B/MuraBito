# exp-02 — Fog of war & the believed world (design brief, DRAFT)

- **Status:** draft for brainstorm — sections marked ⚑ carry open questions to settle before the plan is written
- **Started:** 2026-09-18
- **Stack:** Python 3.13 + pygame, managed with uv (unchanged)
- **Builds on:** exp-01 (wandering Smart Objects). Copy-forward like exp-01 did from exp-00.

---

## Why

exp-00/exp-01 proved the execution stack (StateTree, Smart Objects, A*, chase/replan) — but the actor is omniscient. `FindAndClaim` resolves tag queries against ground truth and chasing reads the target's true tile every tick. In the target architecture, the engine's world registry is *observable reality*, not *known reality*: every layer above reflexes must run on the actor's beliefs, which diverge from truth in a partially observable world.

exp-01 accidentally built the ideal stress test for this: the objects wander, so belief goes stale on its own. exp-02 makes the actor earn its knowledge.

**Thesis to demonstrate:** partial observability slots in *underneath* the decision layer. The tree's rules barely change; only what its predicates and goals *read* changes. If that holds, the same seam holds later between UE5 and the external brain.

## What (one paragraph)

Same world, map, objects, and wander logic as exp-01. The actor gains a **sense range**, a **belief store** (its private model of where objects are and how much it trusts that), and an **Observe → Orient → Decide → Act loop**: a perception evaluator is the only code allowed to read the world; it writes observations; belief update/decay happens between observation and selection; all tree conditions, target choices, and movement goals read beliefs only. When belief fails contact with reality — the object isn't where it "is" — the actor notices, retracts, and searches. The renderer gains fog of war and ghost markers; the brain panel gains a belief table.

## Non-goals (exp-02 explicitly does not include)

- Needs/utility scoring (the placeholder rule table stays; that's a later experiment)
- Multiple actors, social anything, memory persistence across resets
- Provenance, hearsay, confidence math beyond a single scalar (exception, decided 2026-09-18: the per-object velocity estimate and uncertainty radius in §3)
- Occupancy-map diffusion (search is geometric expansion, not probabilistic)
- Hearing or any second sense; LLM anything

---

## Design

### 1. The hard boundary: truth vs. belief

- `world.py` and `smartobjects.py` remain **ground truth**. Objects wander, slots ride along, claims and interactions are arbitrated by truth exactly as in exp-01.
- New module `src/ai/beliefs.py`: the actor's private store. New evaluator `PerceptionEvaluator`: the **only** component permitted to read world object state.
- Everything in `tasks.py` and `tree_def.py` reads `ctx` + beliefs. No task, condition, or goal function may take or touch a world/object reference for *state* (position, zone, availability). Interaction/claim *execution* still goes through the truth-side Smart Object API — but only for an object currently in perception (see §4).
- Enforcement is structural, not honor-system: goal functions receive `(ctx, beliefs)` instead of the world; the world handle is removed from the ctx dict that tasks see. A test constructs a world where truth and belief disagree and asserts the actor acts on belief (see Testing).

This seam is the future engine/brain boundary. Draw it cleanly here where it's cheap.

### 2. Perception ⚑

- **Sense cone (decided 2026-09-18):** the actor sees a cone in the direction it faces, out to R tiles of hex distance. Facing is the existing `actor.facing`, which exp-01's `MoveTo` already updates on every step (and sets to `slot_facing` at a slot), so no new heading bookkeeping is needed.
  - **Near tiles (decided 2026-09-18):** the actor's own tile and its 6 neighbors are always observed, whatever its facing (a one-tile sense bubble on top of the cone). Walls still block sight beyond them.
  - **Cone size (decided 2026-09-18, placeholder):** 120° (±60° either side of the facing direction), out to R = 6. On an open map that is 52 tiles including the near tiles, about 11% of the 469-tile map. Both are module constants, to be tuned by watching the running sim.
- **Walls block sight (decided 2026-09-18):** the map has walls, and a tile hidden behind a wall is not observed. Wall placement is random (see §3a).
  - **LOS method (decided 2026-09-18): hex shadowcasting.** Wall tiles cast shadows; a wall tile that is lit is itself observed, which is how walls get learned (§3a). Ties where a shadow edge passes exactly between hexes are broken by one fixed, deterministic rule.
  - **Object shadows (decided 2026-09-18): per object.** `SmartObject` gains a `casts_shadow: bool` field, set per object in the layout (like `pauses_during_use`). An object with it set blocks sight from its current logical `tile`, so it can hide tiles, walls and other objects behind it, and its shadow moves as it wanders. The object itself is still observed when lit.
    - Placeholder values (decided 2026-09-18): A and B cast shadows, C does not.
- Each tick, `PerceptionEvaluator` emits an observation for every object whose tile (or any slot tile) is observed (in the cone and in line of sight): `(object_name, tile, next_tile, tick, in_use: bool)`. `next_tile` is needed for obstacle beliefs (§3a).
- Observations also cover **tiles**: every observed tile is marked *currently observed* this tick. This is what makes negative evidence well-defined (§3) and drives fog rendering.

### 3. Belief store (`src/ai/beliefs.py`)

Per known object, a `Belief`:

| field | meaning |
|---|---|
| `name`, `tags` | identity as observed |
| `datum_tile`, `datum_time` | where and when the object was last seen |
| `datum_next_tile` | the object's `next_tile` when last seen, if it was mid-step (§3a) |
| `datum_zone` | the zone of `datum_tile`: the zone the object was last seen in |
| `slots` | slot layout as last observed (rides with the believed tile) |
| `velocity` | estimated mean velocity vector (course and speed), blended from the prior |
| `observed_seconds` | total time the object has been in view, which weights the blend |
| `radius` | uncertainty radius, from speed and time since the datum |
| `level` | `POINT` → `REGION` → `LOST`, set by `radius` |
| `confidence` | display value derived from `radius`, not a separate clock |

- **Tracking a moving target (decided 2026-09-18: dead reckoning plus an uncertainty radius, "like a submarine hunting another sub").**
  - **Datum:** the tile and time where the object was last seen.
  - **Estimated velocity:** a mean velocity vector (course and speed) per object, estimated from its observed movement while in view.
  - **Velocity prior (decided 2026-09-18):** every object starts with a prior speed of 0.3 tiles/s (a tunable constant, from the measured mean) and no course. The estimate blends from the prior toward the observed mean, weighted by how many seconds the object has been observed. So an object seen briefly while idle still gets a growing radius.
  - **Dead-reckoned ghost:** while unseen, the believed position moves from the datum along the estimated velocity, rounded to a hex tile.
  - **Uncertainty radius (decided 2026-09-18):** `radius = speed × RADIUS_FACTOR × time since datum`, with `RADIUS_FACTOR` a tunable constant starting at 2. The object is believed to be within this radius of the dead-reckoned tile, clipped to `datum_zone`. Search (§5) sweeps inside that area, starting at the predicted tile.
    - Measured exp-01 drift has 90% of objects within 2 tiles after 4 s and 4 tiles after 8 s; ×2 the mean speed (~0.3 tiles/s) gives 2.4 and 4.8. It overshoots real spread later, and the zone clip limits it.
    - Rejected: max speed (the textbook furthest-on circle, which covers a whole zone after about 8 s), and ×1 (which often leaves the object outside).
  - **Zone clip:** the actor is not told home zones (truth-side data). `datum_zone` is a belief, "I've only seen B in S". In exp-02 it is always right, because objects never leave their home zones.
  - This goes beyond the brief's original single-scalar confidence (see Non-goals).
- **Levels (decided 2026-09-18: set by the radius, one clock):**
  - `POINT` while `radius ≤ 5` tiles: the ghost tile is a usable goal.
  - `REGION` while `5 < radius ≤ 13`: the believed area can seed a search but not a move-to-slot.
  - `LOST` when `radius > 13`: known to exist, whereabouts unknown.
  - At the prior speed (0.3 tiles/s × 2) that is `POINT` for 8.3 s and `LOST` after 21.7 s, matching the earlier choice of an 8 s half-life. Faster-observed objects go stale sooner, slower ones later, so each object gets its own fade rate from its velocity estimate.
  - Both thresholds are tunable constants. They supersede the brief's confidence thresholds (0.5 / 0.15) and the 8 s half-life; `confidence` is shown in the panel but derived from `radius`.
  - One shared prior for all objects: they all wander identically while unseen, and C's only difference (not pausing during use) happens while it is in view.
- **Correction:** any observation of the object resets the datum to the observed tile and time (so `radius = 0`, `level = POINT`) and updates the velocity estimate.
- **Negative evidence:** if the believed `POINT` tile is *currently observed* and the object is not there, the belief immediately drops to `REGION` (not gradual — absence under expected visibility is information). Log it distinctly (`belief: B not at (q,r) — retracting`). This is the primitive that later becomes theft detection; get the log line right.
  - **Decided 2026-09-18:** the radius jumps to just past the `POINT` limit, so the level becomes `REGION` at once. The datum and the ghost's dead reckoning are unchanged, and the radius keeps growing from there.
  - **Cleared tiles (decided 2026-09-18):** Search skips tiles the actor observed empty recently, like a sub hunter's cleared area. A cleared tile expires once the object could have reached it at its estimated speed (× `RADIUS_FACTOR`), since it may wander back in. The per-tile last-observed time from the fog layer (§5) provides the data. The exact expiry rule is defined in the design section.
- **Cold start (decided 2026-09-18):** the actor begins with no object beliefs, so Explore does real work in the opening of the sim.
- **Random starts (decided 2026-09-18):** the actor and every object start at random tiles instead of exp-01's fixed starting tiles. (Motivation: with exp-01's fixed layout, A starts 4 tiles from the actor and would be seen on the first tick.)
  - Objects start inside their home zone, on walkable tiles.
  - No object (tile or slot tile) is visible to the actor at tick 0; the starts are re-rolled until this holds.
  - The starts come from the sim's `--seed`: the same seed gives the same starts, and `R` reset replays them.

### 3a. Believed map (decided 2026-09-18: the actor paths on a believed map)

exp-01's `astar` reads `world.is_walkable`, which is ground truth (walls plus every object's live tile). Under fog that would let the actor route around objects it cannot see. In exp-02, A\* runs over the actor's believed map instead.

- **Walls are learned on sight (decided 2026-09-18).** The actor starts knowing no walls. A tile it has never seen is assumed walkable, so a plan can run through an unseen wall; when the wall is seen, the believed map gains it and the actor re-plans. Exploring therefore reveals the map as well as the objects.
- **Walls are random (decided 2026-09-18),** replacing exp-01's fixed `WALLS`, and seeded from `--seed` like the starts.
  - They follow exp-01's wall rules (decided 2026-09-18): short straight segments, about 30–40 wall tiles in total, no wall tile on or next to a zone border, and every zone's non-wall tiles connected.
  - Walls are generated first; the random starts (§3) are rolled after them.
- **Step check (decided 2026-09-18):** before each step, `MoveTo` checks the next tile against the believed map, not the world. Because the actor always observes its 6 neighbors (§2), the believed state of the next tile is always current, so the actor never steps into a wall or object it hasn't seen. A blocked next tile triggers a re-plan, as in exp-01.
- **Objects as obstacles (decided 2026-09-18):** when planning, every object believed at `POINT` level blocks its believed tile, whether it is currently seen or not. As the belief decays below `POINT` (§3), or negative evidence retracts it, the tile stops blocking. A stale belief can leave a phantom obstacle until then, which may force a detour or a "no path" failure.
  - An observed object that is mid-step also blocks its `next_tile`, as in exp-01's truth-side blocking. So observations carry the object's `next_tile`; without it the step check could let the actor step into a tile an object is stepping into.

### 4. Claiming under fog (the one real semantics change)

**Decided 2026-09-18: claim on sight,** as proposed below. While holding only an intention, the actor's movement goal is the set of all believed slot tiles of the chosen object; once the object is in view and a slot is claimed, the goal narrows to that slot.

exp-01's `FindAndClaim` claims instantly and globally — impossible under fog. Proposal, mirroring the target architecture (claims are truth-side arbitration and require contact with reality):

- Split into **`ChooseTarget`** (belief-side: pick the best believed object matching the tag query — nearest `POINT`-level match; falls back per §5) and claiming as part of approach.
- **Claim on sight:** during `MoveTo`, the moment the chosen object enters perception, attempt the truth-side claim on its best free slot. If claiming fails (slot taken — moot with one actor, but the semantics should be right), re-choose or search.
- Consequence: between choosing and seeing, the actor holds an **intention**, not a claim. `release_claim` on state exit releases only a real claim; an intention just evaporates. The exp-01 claim-leak lesson applies: intentions must not leak either — clear on subtree exit.

Alternative (simpler, less honest): keep claim-at-decision but have it silently fail when the object isn't where believed. Rejected in this draft because it lets the actor manipulate truth it cannot see; flagging in case the brainstorm disagrees.

### 5. Tree changes (`tree_def.py`, `tasks.py`)

The rule table (`RULES`) is untouched. The `GoUse` subtree becomes:

```
GoUse(X)  [conditions unchanged — but Zone now = believed self-zone (self-knowledge, free), LastUsed = memory (already belief)]
├─ ChooseTarget(tag)      — belief-side; SUCCEEDED → MoveTo | FAILED (no usable belief) → Search or Explore (see below)
├─ MoveTo(believed slot, chase-by-belief)
│     · chase updates only when perception refreshes the belief (no truth-tracking)
│     · claim on sight (§4)
│     · ON_CONDITION TargetBeliefDegraded (level < POINT) → Search
│     · arrival at believed tile + object absent → negative evidence fires → Search
├─ Search(target)          — NEW leaf task
│     · sweeps the search area: the uncertainty circle around the dead-reckoned tile, clipped to
│       datum_zone, minus recently cleared tiles (§3); starts at the predicted tile
│     · found (perception refresh) → MoveTo
│     · give up (decided 2026-09-18) when the belief turns LOST (radius > 13) or no uncleared tile
│       is left in the area → GoUse(X)/Explore
└─ Interact                — unchanged (truth-arbitrated; C's drift-failure now reads as
                             "it slipped away," which is the same event under an honest camera)
```

Plus Explore, **a child of each `GoUse(X)`** (decided 2026-09-18), not a top-level branch. A top-level Explore can't be selected by an enter condition: selection takes the first child of Root whose enter conditions pass, and `GoUse(Nearest)`'s `LastUsed==None` always passes at startup. Inside each GoUse it is reached by transition, the same pattern exp-01 uses for failures:

```
GoUse(X)
├─ ChooseTarget            ON_FAILED → GoUse(X)/Explore  (when there is no usable belief to search from)
├─ ...
└─ Explore(tag)            — built per GoUse, so it knows what it is looking for
      · MoveTo(frontier): nearest never-observed or longest-unobserved tile (a "last observed tick"
        per tile, i.e. the fog layer itself, doubles as the exploration map)
      · ON_CONDITION "a matching object is observed" → GoUse(X)/ChooseTarget
```

- `RULES` and the GoUse enter conditions are unchanged.
- On cold start, `GoUse(Nearest)` (tag query `{}`) explores until any object is seen.

- **OODA mapping, explicitly:** *Observe* = `PerceptionEvaluator` (evaluators already tick before selection — the engine loop is already OODA-shaped, exp-02 just gives each phase real content). *Orient* = belief decay + correction + negative evidence, run inside the same evaluator pass. *Decide* = selection + `ON_CONDITION` transitions over belief predicates (`TargetBeliefDegraded` is the plan-monitor: the plan's standing assumption, "target is where I think," made checkable). *Act* = tasks, which feed reality's answers back in as observations. Reeval is therefore continuous and free — no new machinery, only new predicates.
- **Target choice and substitution (decided 2026-09-18: never substitute).** `ChooseTarget` picks the nearest matching `POINT` belief; failing that, the nearest matching `REGION` belief, which is searched; failing that, it fails to Explore. Once a target is chosen, the actor does not switch to another matching object mid-search, even if one becomes `POINT`; it keeps searching until Search gives up, then explores. This only matters for `GoUse(Nearest)`, since the other GoUse queries match exactly one object.
- **Give-up (decided 2026-09-18):** Search gives up when the belief turns `LOST` or every tile in the search area is cleared, and transitions to `GoUse(X)/Explore`, not Wander. There is no separate time budget; the level thresholds are the budget.

### 6. Rendering & brain panel

- **Fog of war:** three tile tints — currently observed (full), previously observed (dimmed, with age-darkening optional), never observed (dark). The per-tile last-observed-tick layer from §5 drives this directly.
- **Ghost markers:** believed object positions drawn semi-transparent at the believed tile with confidence shown (alpha or a small bar). Truth positions drawn as faint outlines **only when the truth overlay is toggled on** (new key: `T`).
- **Truth overlay (decided 2026-09-18): off by default.** `T` toggles it. It shows faint outlines of true object positions **and of walls the actor has not learned yet** (walls are learned on sight, §3a). Headless runs get a `--truth` flag so screenshots can show either view. Hiding truth by default shows only what the actor knows.
- **Sense cone outline** from the actor.
- **Brain panel additions:** a belief table (object · believed tile · age in ticks · confidence · level), and log lines for the new event classes: `observe`, `belief-decay→REGION/LOST`, `negative-evidence`, `claim-on-sight`, `search-give-up`. ASCII only (known pygame font limitation).
- The panel remains the "machinery confesses" surface: every belief transition that changes behavior must have a log line.

### 7. Testing

Invariant style over seeded runs, as in exp-01, plus targeted unit tests:

- **No-cheating (the load-bearing test):** run tasks against a fixture where truth and belief deliberately disagree; assert movement targets, chase updates, and `ChooseTarget` results derive from belief. Structurally: assert task/goal code paths never receive the world handle.
- Belief store: correction resets, decay curve, level thresholds, negative evidence requires the tile to be currently observed (absence outside perception must NOT retract).
- Claim on sight: no truth-side claim exists for any object never yet perceived (invariant over full runs); intentions cleared on subtree exit (claim-leak regression, belief edition).
- Search: ring expansion is monotone; finding the target transitions to MoveTo; give-up marks LOST.
- Explore: frontier selection prefers never-observed tiles; cold-start runs eventually observe all three objects (bounded-tick liveness check per seed).
- Determinism: seeded runs reproduce belief tables exactly.
- Log-spy pattern from exp-01 carries over for asserting dropped log lines.

### 8. Migration notes from exp-01

- Copy-forward per precedent. `wander.py`, `hexgrid.py`, `world.py`, `statetree.py` engine: unchanged.
- `tasks.py`: `FindAndClaim` → `ChooseTarget` + claim-on-sight inside `MoveTo`; new `Search`; goal functions re-signatured to `(ctx, beliefs)`.
- `sim.py`: wire `PerceptionEvaluator` first in the evaluator list; remove the world handle from task-visible ctx.
- `render.py`: fog layer, ghosts, range ring, truth toggle; panel belief table.
- exp-01's three open questions stay parked with exp-01 (walls intersect §2 only if resolved independently).

---

## Success criteria (what "done" demos)

1. **The screenshot:** actor walking confidently toward a ghost-B while true-B sits two tiles away — fog dimmed, ghost translucent, truth overlay off.
2. The actor arrives, the negative-evidence log line fires, and a visible expanding ring search follows — then correction, claim-on-sight, interact.
3. Cold start: the opening minute is legible as *explore → learn the map → begin the exp-01 loop*, with the belief table filling in live.
4. `uv run pytest` green, including the no-cheating fixture.
5. The `RULES` table diff between exp-01 and exp-02 is ~zero — the thesis, proven by `git diff`.

## Open questions rollup (for the brainstorm, in proposed order)

Decided 2026-09-18:
- Cold start, with random starts for the actor and every object (§3)
- Random starts: nothing visible at tick 0 (re-roll), seeded from `--seed` (§3)
- Facing cone, not radius (§2)
- Walls stay and block sight (§2)
- The actor paths on a believed map (§3a)
- Walls are learned on sight; unseen tiles are assumed walkable (§3a)
- Walls are random, seeded from `--seed`, following exp-01's wall rules (§3a)
- The actor always observes its own tile and its 6 neighbors, whatever its facing (§2)
- The step check reads the believed map (§3a)
- POINT-level object beliefs block planning until they decay or are retracted; seen mid-step objects also block their next tile (§3a)
- Claim on sight; the goal is all believed slots until a claim narrows it (§4)
- Explore is a child of each GoUse, reached when ChooseTarget fails, and returns to ChooseTarget when a match is seen (§5)
- Cone: 120°, R = 6, as tunable constants (§2)
- LOS by hex shadowcasting (§2)
- Objects cast shadows per object, via a `casts_shadow` field; A and B do, C doesn't (§2)
- ~~Confidence halves every 8 s~~ (superseded by radius-driven levels, below; the 8 s holds at the prior speed) (§3)
- Tracking: dead-reckoned ghost from a datum and a mean observed velocity, with a growing uncertainty radius that Search sweeps (§3)
- Radius grows at mean observed speed × 2, a tunable factor (§3)
- Speed prior 0.3 tiles/s, blended toward observed by seconds watched (§3)
- The radius sets the level: POINT ≤ 5 tiles, REGION ≤ 13, LOST beyond; confidence is derived for display; the search area is clipped to the zone last seen in (§3)
- Negative evidence bumps the radius just past POINT; Search skips recently cleared tiles, which expire (§3)
- Search gives up on LOST or when the area is fully cleared, and goes to Explore (§5)
- Truth overlay off by default; `T` toggles true objects and unlearned walls; `--truth` for headless (§6)
- Never substitute targets mid-search (§5)

Still open:
