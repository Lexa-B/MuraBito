"""The side panel, drawn with pygame onto a 420 x 900 surface (ASCII text only)."""

import math
from dataclasses import dataclass

import pygame

from hexaddr import (
    CHO, KEN, LEVEL_NAMES, SHAKU, WINDOW_RINGS, Tile, address, axial_to_metres, format_address,
    metres_to_axial, up, window,
)

COLORS = {
    "panel": (24, 26, 32),
    "edge": (60, 64, 76),
    "title": (236, 238, 242),
    "head": (150, 190, 255),
    "text": (214, 218, 226),
    "dim": (130, 136, 150),
    "loaded": (86, 160, 98),
    "queued": (214, 170, 60),
    "missing": (54, 58, 68),
    "camera": (255, 255, 255),
}
LINE = 19


@dataclass
class PanelInfo:
    focus: Tile                              # the camera's global shaku
    position: tuple[float, float, float]     # focus point, world metres
    lap_fraction: float
    sim_seconds: float
    tiers: list                              # ChunkStore.summary()
    loaded: set                              # chunk keys loaded
    queued: set                              # chunk keys queued
    loaders: list                            # Loader objects
    fps: float
    frame_ms: float
    seed: int
    paused: bool


class Panel:
    def __init__(self, size=(420, 900)):
        self.surface = pygame.Surface(size)
        self.font = pygame.font.Font(None, 22)
        self.small = pygame.font.Font(None, 18)

    def draw(self, info: PanelInfo) -> pygame.Surface:
        s = self.surface
        s.fill(COLORS["panel"])
        pygame.draw.line(s, COLORS["edge"], (0, 0), (0, s.get_height()), 2)
        y = 12
        y = self._text("MURABITO EXP-03  tiered hex world", 14, y, "title", self.font) + 6

        y = self._head("CAMERA", y)
        addr = format_address(address(info.focus)).split(" / ")
        y = self._text(f"{addr[0]}   {addr[1]}", 14, y)
        y = self._text(f"{addr[2]}   {addr[3]}", 14, y)
        x, h, z = info.position
        y = self._text(f"x {x:10.1f} m   z {z:10.1f} m   h {h:7.1f} m", 14, y)
        t = int(info.sim_seconds)
        state = "   PAUSED" if info.paused else ""
        y = self._text(f"lap {100 * info.lap_fraction:6.3f} %   t {t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"
                       f"   seed {info.seed}{state}", 14, y) + 6

        y = self._head("TIERS", y)
        y = self._text("tier     chunks    cells     tris   +/s  -/s  gen ms last/mean  queue", 14, y, "dim",
                       self.small)
        for name, stats, loads, unloads in info.tiers:
            gen = f"{stats.gen_ms_last:5.1f}/{stats.gen_ms_mean:5.1f}"
            y = self._text(f"{name:<6} {stats.chunks:>6} {stats.cells:>8} {stats.triangles:>8} {loads:>5} {unloads:>4}"
                           f" {gen:>12} {stats.queued:>6}", 14, y, "text", self.small)
        y += 8

        y = self._head("NEIGHBOURHOOD", y)
        y = self._text("windows: loaded / queued / not loaded; white = camera's cell", 14, y, "dim", self.small)
        for i, level in enumerate((SHAKU, KEN, CHO)):
            self._window_diagram(info, level, 14 + i * 134, y + 4)
        y += 150

        y = self._head("LOADERS", y)
        for loader in info.loaders:
            y = self._text(f"{loader.name}: focus shaku {loader.focus}", 14, y)
            y = self._text("  37 ken -> shaku, 37 cho -> ken, 37 ri -> cho, world -> ri", 14, y, "dim", self.small)
        y += 6

        y = self._head("FRAME", y)
        self._text(f"{info.fps:5.1f} fps   {info.frame_ms:5.1f} ms", 14, y)
        return s

    def _window_diagram(self, info: PanelInfo, level: int, x0: int, y0: int) -> None:
        """The loader's window at one tier: the parent cells (level + 1) around the camera."""
        parent_level = level + 1
        centre = up(info.focus, SHAKU, parent_level)
        size = 9.5  # hex corner radius, px
        cx, cy = x0 + 60, y0 + 70
        s = self.surface
        for cell in window(centre, WINDOW_RINGS):
            dq, dr = cell[0] - centre[0], cell[1] - centre[1]
            px = cx + math.sqrt(3) * size * (dq + dr / 2)
            py = cy - 1.5 * size * dr
            key = (level, cell)
            state = "loaded" if key in info.loaded else "queued" if key in info.queued else "missing"
            colour = COLORS[state]
            pts = [(px + size * 0.95 * math.cos(math.radians(30 + 60 * i)),
                    py + size * 0.95 * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
            pygame.draw.polygon(s, colour, pts)
            if cell == centre:
                pygame.draw.polygon(s, COLORS["camera"], pts, 2)
        # the camera inside its cell
        fx, fz = axial_to_metres(*info.focus)
        fq, fr = metres_to_axial(fx, fz, parent_level)
        dq, dr = fq - centre[0], fr - centre[1]
        pygame.draw.circle(s, COLORS["camera"], (cx + math.sqrt(3) * size * (dq + dr / 2), cy - 1.5 * size * dr), 2)
        label = f"{LEVEL_NAMES[parent_level]} -> {LEVEL_NAMES[level]}"
        s.blit(self.small.render(label, True, COLORS["dim"]), (x0 + 22, y0 + 130))

    def _head(self, text: str, y: int) -> int:
        return self._text(text, 14, y, "head", self.font)

    def _text(self, text: str, x: int, y: int, colour: str = "text", font=None) -> int:
        self.surface.blit((font or self.font).render(text, True, COLORS[colour]), (x, y))
        return y + LINE
