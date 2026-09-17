"""Pygame drawing: the isometric hex world view and the brain panel."""

import math

import pygame

from hexgrid import DIRECTIONS, all_tiles

WINDOW_SIZE = (1600, 900)
VIEW_SIZE = (1180, 900)
PANEL_RECT = pygame.Rect(1180, 0, 420, 900)
LINE = 17

HEX_SIZE = 64 / math.sqrt(3)  # corner radius; a pointy-top hex is sqrt(3) * size = 64px across
SQUASH = 0.6  # vertical squash for the tilted look
WALL_HEIGHT = 20
OBJECT_HEIGHT = 30
CULL_MARGIN = 80

COLORS = {
    "void": (18, 20, 26),
    "west": (70, 96, 78),
    "east": (104, 94, 70),
    "grid": (40, 46, 44),
    "path": (240, 220, 120),
    "claimed": (250, 240, 170),
    "wall": (120, 118, 128),
    "outline": (30, 30, 36),
    "actor": (236, 236, 240),
    "shadow": (12, 14, 16),
    "ring_bg": (60, 60, 70),
    "ring": (250, 210, 90),
    "text": (230, 230, 235),
    "text_dim": (150, 154, 165),
    "text_active": (255, 255, 255),
    "panel": (26, 28, 36),
    "panel_edge": (60, 64, 80),
    "active_row": (52, 70, 110),
    "header": (140, 180, 255),
    "pass": (110, 200, 120),
    "fail": (220, 90, 90),
    "unknown": (110, 110, 120),
}
OBJECT_COLORS = {"A": (214, 96, 77), "B": (110, 180, 100), "C": (90, 140, 215)}


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def tile_to_world_px(tile):
    q, r = tile
    return (math.sqrt(3) * HEX_SIZE * (q + r / 2), 1.5 * HEX_SIZE * r * SQUASH)


def actor_world_px(actor):
    x0, y0 = tile_to_world_px(actor.tile)
    if actor.next_tile is None:
        return (x0, y0)
    x1, y1 = tile_to_world_px(actor.next_tile)
    t = actor.progress
    return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)


def hex_corners(center, scale=1.0, lift=0.0):
    """Corners of a squashed pointy-top hex; corner 1 is the bottom point, corner 4 the top."""
    cx, cy = center
    return [
        (
            cx + HEX_SIZE * scale * math.cos(math.radians(30 + 60 * i)),
            cy - lift + HEX_SIZE * scale * math.sin(math.radians(30 + 60 * i)) * SQUASH,
        )
        for i in range(6)
    ]


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.view = screen.subsurface(pygame.Rect((0, 0), VIEW_SIZE))  # clips world drawing
        self.font = pygame.font.Font(None, 20)
        self.small = pygame.font.Font(None, 18)
        self.big = pygame.font.Font(None, 28)
        self.floor_tiles = sorted(all_tiles(), key=lambda t: (tile_to_world_px(t)[1], tile_to_world_px(t)[0]))

    def draw(self, sim, camera, paused, speed):
        self.draw_world(sim, camera, paused, speed)
        self.draw_panel(sim)

    # --- world view -------------------------------------------------------

    def draw_world(self, sim, camera, paused, speed):
        view = self.view
        world, ctx = sim.world, sim.ctx
        to_screen = camera.world_to_screen
        view.fill(COLORS["void"])

        for tile in self.floor_tiles:
            center = to_screen(tile_to_world_px(tile))
            if not self._visible(center):
                continue
            base = COLORS["west"] if world.zone_of(tile) == "West" else COLORS["east"]
            corners = hex_corners(center)
            pygame.draw.polygon(view, shade(base, 1.0 - 0.05 * ((tile[0] - tile[1]) % 3)), corners)
            pygame.draw.polygon(view, COLORS["grid"], corners, 1)

        for tile in (ctx.get("Path") or [])[1:]:
            pygame.draw.circle(view, COLORS["path"], to_screen(tile_to_world_px(tile)), 4)

        for obj in world.smart_objects.objects:
            color = OBJECT_COLORS.get(obj.name, COLORS["wall"])
            object_center = to_screen(tile_to_world_px(obj.tile))
            for slot in obj.slots:
                center = to_screen(tile_to_world_px(slot.tile))
                corners = hex_corners(center, scale=0.45)
                if world.smart_objects.is_claimed(obj, slot):
                    pygame.draw.polygon(view, COLORS["claimed"], corners)
                pygame.draw.polygon(view, color, corners, 2)
                tip = (center[0] + (object_center[0] - center[0]) * 0.35, center[1] + (object_center[1] - center[1]) * 0.35)
                pygame.draw.line(view, color, center, tip, 2)

        # Raised things and the actor, back to front.
        drawables = [(tile_to_world_px(t)[1], "wall", t) for t in world.walls]
        drawables += [(tile_to_world_px(o.tile)[1], "object", o) for o in world.smart_objects.objects]
        actor_px = actor_world_px(sim.actor)
        drawables.append((actor_px[1] + 0.1, "actor", actor_px))
        for _, kind, item in sorted(drawables, key=lambda d: d[0]):
            if kind == "wall":
                center = to_screen(tile_to_world_px(item))
                if self._visible(center):
                    self._draw_column(center, WALL_HEIGHT, COLORS["wall"])
            elif kind == "object":
                center = to_screen(tile_to_world_px(item.tile))
                if self._visible(center):
                    self._draw_column(center, OBJECT_HEIGHT, OBJECT_COLORS.get(item.name, COLORS["wall"]))
                    label = self.big.render(item.name, True, COLORS["text_active"])
                    view.blit(label, label.get_rect(center=(center[0], center[1] - OBJECT_HEIGHT)))
            else:
                self._draw_actor(sim, to_screen(item))

        status = f"{speed:g}x" + ("   PAUSED" if paused else "")
        view.blit(self.big.render(status, True, COLORS["text"]), (12, 10))
        hint = "Space pause  |  N step  |  +/- speed  |  R reset  |  Esc quit"
        view.blit(self.small.render(hint, True, COLORS["text_dim"]), (12, VIEW_SIZE[1] - 24))

    def _visible(self, point):
        x, y = point
        return -CULL_MARGIN <= x <= VIEW_SIZE[0] + CULL_MARGIN and -CULL_MARGIN <= y <= VIEW_SIZE[1] + CULL_MARGIN

    def _draw_column(self, center, height, color):
        ground = hex_corners(center)
        top = hex_corners(center, lift=height)
        # Visible side faces: right (5-0), lower-right (0-1), lower-left (1-2), left (2-3).
        for (a, b), factor in zip(((5, 0), (0, 1), (1, 2), (2, 3)), (0.75, 0.6, 0.5, 0.65)):
            pygame.draw.polygon(self.view, shade(color, factor), [ground[a], ground[b], top[b], top[a]])
        pygame.draw.polygon(self.view, color, top)
        pygame.draw.polygon(self.view, COLORS["outline"], top, 1)

    def _draw_actor(self, sim, center):
        view = self.view
        x, y = center
        pygame.draw.ellipse(view, COLORS["shadow"], pygame.Rect(x - 10, y - 4, 20, 8))
        pygame.draw.circle(view, COLORS["actor"], (x, y - 12), 8)
        head = (x, y - 26)
        pygame.draw.circle(view, COLORS["actor"], head, 6)
        fx, fy = tile_to_world_px(DIRECTIONS[sim.actor.facing])
        length = math.hypot(fx, fy)
        pygame.draw.circle(view, COLORS["outline"], (head[0] + fx / length * 4, head[1] + fy / length * 4), 2)

        interaction = sim.ctx.get("Interaction")
        if interaction is not None:
            fraction = min(sim.ctx.get("InteractionElapsed", 0.0) / interaction.duration, 1.0)
            ring = pygame.Rect(0, 0, 36, 36)
            ring.center = (round(head[0]), round(head[1]))
            pygame.draw.circle(view, COLORS["ring_bg"], ring.center, 18, 3)
            if fraction > 0:
                pygame.draw.arc(view, COLORS["ring"], ring, math.pi / 2, math.pi / 2 + 2 * math.pi * fraction, 3)
            label = self.small.render(interaction.name, True, COLORS["text"])
            view.blit(label, label.get_rect(midbottom=(head[0], head[1] - 22)))

    # --- brain panel (completed in Task 8) --------------------------------

    def draw_panel(self, sim):
        pygame.draw.rect(self.screen, COLORS["panel"], PANEL_RECT)
        pygame.draw.line(self.screen, COLORS["panel_edge"], PANEL_RECT.topleft, PANEL_RECT.bottomleft, 2)
