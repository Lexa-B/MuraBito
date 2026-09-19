import random

import pytest


@pytest.mark.parametrize("extra", [[], ["--truth"]])
def test_headless_run_saves_screenshots(tmp_path, monkeypatch, extra):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import main

    main.main(["--frames", "120", "--speed", "4", "--screenshot-dir", str(tmp_path), "--screenshot-every", "60", *extra])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frame_00060.png", "frame_00120.png"]


def test_parse_args_defaults():
    import main

    args = main.parse_args([])
    assert (args.frames, args.screenshot_dir, args.screenshot_every, args.speed, args.seed, args.truth) == (
        0, None, 60, 1.0, 0, False
    )
    assert main.parse_args(["--truth"]).truth is True


def test_reset_replays_the_seed_or_picks_a_new_one():
    import main
    from sim import build_sim

    sim = build_sim(5)
    for _ in range(60):
        sim.step(main.DT)
    same = main.reset_sim(sim)
    assert same.seed == 5 and same.actor.tile == build_sim(5).actor.tile
    expected = random.Random(99).randrange(main.SEED_RANGE)
    fresh = main.reset_sim(same, new_seed=True, seed_source=random.Random(99))
    assert fresh.seed == expected
