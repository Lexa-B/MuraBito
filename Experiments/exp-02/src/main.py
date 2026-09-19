"""exp-02 entry point. Run from Experiments/exp-02: `uv run src/main.py`."""

import argparse
import random
from pathlib import Path

import pygame

from camera import Camera
from render import VIEW_SIZE, WINDOW_SIZE, Renderer, actor_world_px
from sim import build_sim

DT = 1 / 60
SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
MAX_FRAME_TIME = 0.25  # avoid a catch-up spiral after a stall
SEED_RANGE = 2**31


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="MuraBito exp-02: StateTree + fog of war visualizer")
    parser.add_argument("--frames", type=int, default=0,
                        help="exit after N frames (0 = run until quit); each frame advances one fixed tick x speed")
    parser.add_argument("--screenshot-dir", type=Path, default=None)
    parser.add_argument("--screenshot-every", type=int, default=60)
    parser.add_argument("--speed", type=float, default=1.0, choices=SPEEDS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--truth", action="store_true", help="start with the truth overlay on")
    return parser.parse_args(argv)


def reset_sim(sim, new_seed=False, seed_source=None):
    """Reset the tree (releasing claims) and rebuild: same seed, or a new random one."""
    sim.tree.reset(sim.ctx)
    seed = (seed_source or random.Random()).randrange(SEED_RANGE) if new_seed else sim.seed
    return build_sim(seed)


def main(argv=None):
    args = parse_args(argv)
    pygame.init()
    pygame.display.set_caption("MuraBito exp-02")
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    sim = build_sim(args.seed)
    camera = Camera(VIEW_SIZE)
    camera.snap(actor_world_px(sim.actor))
    speed_index = SPEEDS.index(args.speed)
    paused = False
    truth = args.truth
    accumulator = 0.0
    frame = 0
    if args.screenshot_dir is not None:
        args.screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_n and paused:
                    sim.step(DT)
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    speed_index = min(speed_index + 1, len(SPEEDS) - 1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    speed_index = max(speed_index - 1, 0)
                elif event.key == pygame.K_t:
                    truth = not truth
                elif event.key == pygame.K_r:
                    sim = reset_sim(sim, new_seed=bool(event.mod & pygame.KMOD_SHIFT))
                    camera.snap(actor_world_px(sim.actor))
                    accumulator = 0.0

            speed = SPEEDS[speed_index]
            # Headless runs are deterministic: one fixed frame time, no waiting on the clock.
            frame_time = DT if args.frames else min(clock.tick(60) / 1000, MAX_FRAME_TIME)
            if not paused:
                accumulator += frame_time * speed
                while accumulator >= DT:
                    sim.step(DT)
                    accumulator -= DT
            camera.follow(actor_world_px(sim.actor), frame_time)

            renderer.draw(sim, camera, paused, speed, truth)
            pygame.display.flip()
            frame += 1

            if args.screenshot_dir is not None and frame % args.screenshot_every == 0:
                pygame.image.save(screen, str(args.screenshot_dir / f"frame_{frame:05d}.png"))
            if args.frames and frame >= args.frames:
                return
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
