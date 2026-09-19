# exp-02 handoff

> **Superseded.** exp-02 has since been designed and built on branch `exp-02-impl` (2026-09-18); this file records the state *before* that work and is kept for history. Current documents: the spec (`docs/specs/2026-09-18-exp-02-fog-of-war-design.md`), the plan (`docs/plans/2026-09-18-exp-02-fog-of-war-plan.md`) and the exp-02 entry in `Experiments/manifest.md`.

Written 2026-09-18 at the end of the session that built exp-00 and exp-01. This file holds the context a fresh session needs that **isn't** already in `AGENTS.md`, `Experiments/manifest.md`, or the experiment specs. Read those first; this file doesn't repeat them.

## What exp-02 is

**Not decided yet.** No goal, scope or design has been stated for exp-02; this file is the only thing in the folder. Start with brainstorming and ask. Don't assume it builds on exp-01, or on any of the exp-01 open questions below, unless the user says so.

## Read first

1. `AGENTS.md`: project overview, repo layout, doc locations.
2. `Experiments/manifest.md`: what exp-00 and exp-01 are and how to run them.
3. `Experiments/exp-01/docs/specs/2026-09-17-exp-01-wandering-objects-design.md`: the latest design. It relies on the exp-00 spec for the unchanged parts, and has an **Open questions** section.
4. `Experiments/exp-00/docs/specs/2026-09-17-exp-00-statetree-visualizer-design.md`: the StateTree engine, Smart Objects, and brain panel in full.

## Repo state at handoff

- **`main`** is at `5a072b1`, pushed to `github.com/Lexa-B/MuraBito` (public, MIT). The working tree is clean.
- **Test suites:** exp-00 passes 88 tests and exp-01 passes 150 (`uv run pytest` from each experiment dir).
- **`main` is the only branch,** locally and on GitHub. The merged `exp-00-impl` and `exp-01-impl` branches have been deleted.
- **`.superpowers/sdd/`** at the repo root is scratch space for subagent-driven development. It ignores itself through its own `.gitignore` and is empty now.

## How exp-00 and exp-01 were built

The user approved this workflow for both experiments. Treat it as the precedent, not a rule, and confirm before assuming it for exp-02.

1. **Brainstorming** (superpowers):
   - one question at a time, mostly multiple choice;
   - the design presented in sections, each approved;
   - the spec written to `exp-NN/docs/specs/` and committed.
2. **Plan** (superpowers writing-plans), saved to `exp-NN/docs/plans/`:
   - The plans contained **complete code**, and that code was **run in a scratchpad copy before dispatch**.
   - For exp-01 this was done cumulatively per task, so each task's end state had a known-green test count (88 → 92 → 114 → 140 → 149).
   - This made implementer work transcription-only and caught plan bugs early.
3. **Subagent-driven development:**
   - a fresh implementer per task, then a task review;
   - a final whole-branch review on the most capable model, followed by one fix wave and a scoped re-review;
   - progress ledger in `.superpowers/sdd/<plan>/progress.md`, deleted when done.
4. **Git:**
   - work on a feature branch `exp-NN-impl` in the main checkout;
   - no worktree, because the user never asked for one;
   - fast-forward merge to `main` and push only when the user asks.
5. **Rulings the user saw and approved at merge:**
   - commit `Co-Authored-By` trailers name whichever model wrote each commit, so the history mixes Haiku, Sonnet and Opus;
   - decisions that need user intent were parked as open questions instead of guessed.

## What the user said they wanted in exp-00 / exp-01

These were said in the context of those experiments; confirm whether they carry into exp-02.

- **Format:** a Python + pygame visualizer, managed with uv.
- **AI style:** UE5 **StateTree** (the user chose it over a plain decision tree, a Behavior Tree, or an FSM).
- **Objects:** UE5 **Smart Objects**, described by the user as "Sims 4 esque interactable things".
- **Brain panel:** the live side panel was welcome: "if that right side panel is a peek inside its brain while the sim shows, thats perfect".
- **World:** a hexagon-shaped hex map, 25 tiles across on each axis, with a camera that follows the actor.
- **Wandering (exp-01):** each tick an object may or may not move. It most likely keeps its heading, and bigger turns are less likely. Objects stay inside one of three zones.
- **Rules:** placeholder rules were fine.

## Technical notes that cost time or are easy to miss

- **Imports are relative to `src/`** (`pythonpath = ["src"]`). Run the app as `uv run src/main.py` from the experiment dir.
- **Python and pygame versions:** Python is pinned to 3.13 (`.python-version`), with pygame 2.6.1.
- **Headless runs** use `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run src/main.py --frames N --speed S --screenshot-dir <dir> --screenshot-every K`. The Read tool opens the PNGs for visual checks. Write screenshots to the scratchpad or a gitignored `screenshots/` folder.
- **pygame's default font lacks `→`, `✓` and `✗`,** so log and panel text is ASCII only. Pass/fail marks are drawn as colored circles.
- **Plan Markdown:** code blocks nested under list items carry two extra spaces of indentation. Plans should say so explicitly; implementers stumbled on it otherwise.
- **StateTree engine semantics** were settled during the exp-00 reviews and are covered by tests:
  - a transition to a state re-enters it, so everything at or below the target runs `on_exit`;
  - an unselectable target falls back to ROOT, and `on_exit` uses that *effective* target (this was a claim-leak bug, fixed);
  - a finished task with no matching transition goes to ROOT;
  - the `select ->` log line is written before the leaf task's `enter`.
- **Randomized sims (exp-01)** are tested with per-tick invariants over several seeds, not exact event sequences. To catch error lines the bounded log deque would drop, tests replace `tree.write_log` and `ctx["log"]` with a spy.

## Open items carried over from exp-01

The three open questions in the exp-01 spec are still unanswered:
- the slot marker during a mid-step pause;
- claims abandoned on brief blocks, and C's drift-failure rate;
- wall placement.

They belong to exp-01. Only take them up if the user brings them into exp-02.
