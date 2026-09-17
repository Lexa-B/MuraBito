def test_headless_run_saves_screenshots(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import main

    main.main(["--frames", "120", "--speed", "4", "--screenshot-dir", str(tmp_path), "--screenshot-every", "60"])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["frame_00060.png", "frame_00120.png"]


def test_parse_args_defaults():
    import main

    args = main.parse_args([])
    assert (args.frames, args.screenshot_dir, args.screenshot_every, args.speed, args.seed) == (0, None, 60, 1.0, 0)
