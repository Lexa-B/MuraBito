import pytest


def test_parse_args_defaults():
    import main

    args = main.parse_args([])
    assert (args.frames, args.seed, args.start, args.no_preload, args.screenshot_dir, args.screenshot_every) == (
        0, 0, 0.0, False, None, 60
    )
    assert main.parse_args(["--start", "90.5", "--no-preload"]).start == 90.5


@pytest.mark.parametrize("extra", [[], ["--no-preload", "--start", "600"]])
def test_headless_run_saves_screenshots(tmp_path, monkeypatch, extra):
    pytest.importorskip("moderngl")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import main

    try:
        main.main(["--frames", "120", "--screenshot-dir", str(tmp_path), "--screenshot-every", "60", *extra])
    except Exception as exc:  # no EGL / GPU here
        if "EGL" in str(exc) or "context" in str(exc).lower():
            pytest.skip(f"no GL context: {exc}")
        raise
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frame_00060.png", "frame_00120.png"]
