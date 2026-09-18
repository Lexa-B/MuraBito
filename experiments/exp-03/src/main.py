"""exp-03 entry point. Run from experiments/exp-03: `uv run src/main.py`."""

import argparse
import time
from pathlib import Path

import numpy as np
import pygame

from chunkgen import generate_chunk
from gfx import context
from gfx.panel import Panel, PanelInfo
from gfx.renderer import WINDOW_SIZE, Renderer, View
from hexaddr import SHAKU
from loading import ChunkStore, Loader
from rail import Rail
from terrain import ground_height, height

DT = 1 / 60
MAX_FRAME_TIME = 0.25  # avoid a catch-up spiral after a stall
PANEL_EVERY = 6        # frames between panel redraws


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="MuraBito exp-03: tiered hex world")
    parser.add_argument("--frames", type=int, default=0,
                        help="exit after N frames (0 = run until quit); each frame advances one fixed tick")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--start", type=float, default=0.0, help="begin S seconds along the rail")
    parser.add_argument("--no-preload", action="store_true", help="skip loading everything before the first frame")
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--screenshot-every", type=int, default=60)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    pygame.init()
    ctx, target = context.create(WINDOW_SIZE, "MuraBito exp-03")
    renderer = Renderer(ctx, target)
    panel = Panel()
    store = ChunkStore(lambda level, parent: generate_chunk(level, parent, args.seed),
                       on_load=renderer.load_chunk, on_unload=renderer.unload_chunk)
    ground_many = lambda xs, zs: height(np.asarray(xs), np.asarray(zs), SHAKU, args.seed)  # noqa: E731
    rail = Rail(lambda x, z: ground_height(x, z, args.seed), start=args.start, ground_many=ground_many)
    camera = Loader("camera", rail.focus_shaku)
    if not args.no_preload:
        store.drain([camera])
    clock = pygame.time.Clock()
    paused = False
    accumulator = 0.0
    frame = 0
    frame_ms = 0.0
    if args.screenshot_dir is not None:
        args.screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_SPACE:
                        paused = not paused

            started = time.perf_counter()
            # Headless runs are deterministic: one fixed frame time, no waiting on the clock.
            frame_time = DT if args.frames else min(clock.tick(60) / 1000, MAX_FRAME_TIME)
            if not paused:
                accumulator += frame_time
                while accumulator >= DT:
                    rail.advance(DT)
                    accumulator -= DT
            camera.focus = rail.focus_shaku
            store.update([camera])

            if frame % PANEL_EVERY == 0:
                renderer.upload_panel(panel.draw(PanelInfo(
                    focus=camera.focus, position=rail.focus, lap_fraction=rail.lap_fraction,
                    sim_seconds=rail.t - args.start, tiers=store.summary(), loaded=set(store.loaded),
                    queued=set(store.queue), loaders=[camera], fps=clock.get_fps(), frame_ms=frame_ms,
                    seed=args.seed, paused=paused,
                )))
            renderer.draw(View(origin=camera.focus, eye=rail.eye, target=rail.focus))
            if not context.headless():
                pygame.display.flip()
            frame_ms = (time.perf_counter() - started) * 1000
            frame += 1

            if args.screenshot_dir is not None and frame % args.screenshot_every == 0:
                save_screenshot(renderer, args.screenshot_dir / f"frame_{frame:05d}.png")
            if args.frames and frame >= args.frames:
                return
    finally:
        pygame.quit()


def save_screenshot(renderer: Renderer, path: Path) -> None:
    pixels = np.ascontiguousarray(renderer.read_rgb())
    pygame.image.save(pygame.image.frombuffer(pixels.tobytes(), WINDOW_SIZE, "RGB"), str(path))


if __name__ == "__main__":
    main()
