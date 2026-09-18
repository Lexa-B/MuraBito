# exp-03 handoff

Written 2026-09-18 at the end of the session that built exp-02. This file holds the context a fresh session needs that **isn't** already in `AGENTS.md`, `experiments/manifest.md`, or the experiment specs. Read those first; this file doesn't repeat them.

## What exp-03 is

**Not decided yet.** No goal, scope or design has been stated for exp-03; this file is the only thing in the folder. Start with brainstorming and ask. Don't assume it builds on exp-02, or on any of the open questions below, unless the user says so.

## Read first

1. `AGENTS.md`: project overview, repo layout, doc locations.
2. `experiments/manifest.md`: what exp-00, exp-01 and exp-02 are, how to run them, and each one's open questions.
3. `experiments/exp-02/docs/specs/2026-09-18-exp-02-fog-of-war-design.md`: the latest design (fog of war and the believed world). It relies on the exp-01 and exp-00 specs for the unchanged parts, and ends with two amendment sections recording what changed while the plan was built and after the final review.
4. `experiments/exp-02/docs/plans/2026-09-18-exp-02-fog-of-war-plan.md`: the implementation plan, useful as a worked example of the plan format the user has approved twice.

## Repo state at handoff

- **`main` is at `fabd682`,** pushed to `github.com/Lexa-B/MuraBito` (public, MIT).
- **`exp-02-impl` is 14 commits ahead of `main`, at `085c031`, and has not been merged or pushed.** The user was offered merge / PR / keep and had not chosen when this file was written. **Check this first:** `git -C <repo> log --oneline main..exp-02-impl`. If exp-02 is still unmerged, ask before starting anything that assumes it landed.
- The branch lives in the main checkout; no worktree was used.
- **Test suites:** exp-00 passes 88, exp-01 passes 150, exp-02 passes 401 (`uv run pytest` from each experiment dir).
- **`.superpowers/sdd/`** at the repo root is git-ignored scratch space for subagent-driven development. It is empty; each plan's workspace is deleted when its plan finishes.

## How exp-02 was built

The user approved this workflow for exp-00, exp-01 and exp-02. Treat it as the precedent, not a rule, and confirm before assuming it for exp-03.

1. **Brainstorming** (superpowers), one question at a time, mostly multiple choice, with the design presented in sections and each section approved. For exp-02 the user supplied a draft brief first (`experiments/exp-02/docs/2026-09-18-exp-02-fog-of-war-design.md`); decisions were recorded into it as they were made, and the spec was written afterwards to `docs/specs/`.
2. **Measure before offering options.** Several exp-02 choices were settled by running a quick experiment against exp-01's code first (how far objects drift when unseen, how many tiles a cone of each size sees, how often Explore restarts). The numbers went into the question, and the user picked from them. This worked well and is worth repeating.
3. **Plan** (superpowers writing-plans), saved to `exp-NN/docs/plans/`:
   - the plan contains **complete code**, and that code was **written and run in a scratchpad copy before the plan was written**;
   - then the plan was **replayed** task by task onto a fresh copy of the experiment, recording the test count after each task, so every task's expected count in the plan is real (exp-02: 150 → 174 → 323 → 344 → 356 → 366 → 374 → 397 → 399);
   - this caught two real bugs before any implementer saw the plan, and made the implementers' work transcription plus testing.
4. **Subagent-driven development:**
   - a fresh implementer per task, then a task review; Haiku for transcription tasks, Sonnet for the big integration and rendering tasks, Opus for the riskiest review and the final whole-branch review;
   - the controller diffed each commit against the scratchpad code, so transcription drift would have been caught immediately (there was none);
   - one fix round was needed (a claim outliving its target), plus one final fix wave (docs and two stronger tests);
   - progress ledger in `.superpowers/sdd/<plan>/progress.md`, deleted when done.
5. **Git:** feature branch `exp-NN-impl` in the main checkout, `git -C <abs path>` for every command, no push until the user asks.
6. **Rulings the user saw at the end:** commit `Co-Authored-By` trailers name whichever model wrote each commit, so the history mixes Haiku, Sonnet and Opus; decisions the controller had to make during execution were collected and reported in one list at the end.

## What the user said they wanted in exp-00 / exp-01 / exp-02

These were said in the context of those experiments; confirm whether they carry into exp-03.

- **Format:** a Python + pygame visualizer, managed with uv.
- **AI style:** UE5 **StateTree**; objects are UE5 **Smart Objects**.
- **Brain panel:** the live "peek inside its brain" side panel is wanted.
- **World:** a hexagon-shaped hex map, 25 tiles across, camera following the actor.
- **exp-02 choices, in the user's words or their picks:** cold start with random starts and random walls; walls block sight and are learned on sight; a facing cone rather than a radius; hex shadowcasting; per-object `casts_shadow`; tracking a target "like a submarine hunting another sub" (dead reckoning plus an uncertainty circle); claim on sight; Explore inside each GoUse branch; truth overlay off by default.
- **Rules:** placeholder rules are fine, and the exp-01 `RULES` table went through exp-02 unchanged on purpose.

## Technical notes that cost time or are easy to miss

- **Imports are relative to `src/`** (`pythonpath = ["src"]`). Run the app as `uv run src/main.py` from the experiment dir. Python is pinned to 3.13, pygame 2.6.1.
- **Headless runs:** `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --seed K [--truth] --screenshot-dir <dir> --screenshot-every M`. The Read tool opens the PNGs for visual checks. Write screenshots to the scratchpad or the gitignored `screenshots/`.
- **pygame's default font lacks `→`, `✓` and `✗`,** so log and panel text is ASCII only.
- **Plan Markdown:** keep code blocks at column 0 and say so in the plan; indented blocks under list items tripped implementers in exp-01.
- **exp-02's truth/belief boundary is enforced by tests,** not convention: `tests/test_boundary.py` fails if `ai/tasks.py`, `ai/tree_def.py` or `ai/beliefs.py` import a truth-side module or read a `.world` / `._handle` / `.smart_objects` attribute, and there is a fixture where belief and truth disagree. If exp-03 copies exp-02, keep that test honest or drop it deliberately.
- **Two engine-level gotchas found in exp-02 review, both now covered by tests:**
  - shadows from two touching blockers must be merged, or sight leaks through the zero-width crack between them;
  - an object counts as seen when its `next_tile` is in view, or an object stepping in from out of view can collide with the actor.
- **Long-run sim tests** (5 seeds × 120 s) check per-tick invariants, including that every belief's datum matches where the object really was at that moment. They are the cheapest place to catch this kind of bug; the collision above was found there.
- **Determinism:** everything (map, wander, interaction choice, wander goals) comes from one `random.Random(seed)`, drawn in a fixed order. Tests rely on it; keep new randomness on the same rng.

## Open items carried over from exp-02

- The three tuning questions in the exp-02 manifest entry: Explore churn (`EXPLORE_MIN_DISTANCE`), the believed-map recompute cost at high sim speeds, and the stale `Target` shown in the panel while exploring.
- exp-01's three open questions (slot marker during a mid-step pause, claims abandoned on brief blocks and C's drift-failure rate, wall placement) are still parked with exp-01. exp-02 replaced the fixed walls with random ones, so the wall-placement question now reads differently.

They belong to exp-01 and exp-02. Only take them up if the user brings them into exp-03.
