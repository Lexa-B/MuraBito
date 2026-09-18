"""Drawing the loaded world with moderngl: sky, terrain chunks, instanced props, and the panel.

Everything is drawn relative to the origin shaku (the loader focus), so the GPU only sees small
numbers. The renderer hears about chunks through load_chunk / unload_chunk.
"""

from dataclasses import dataclass
from pathlib import Path

import moderngl
import numpy as np

from chunkgen import PEBBLE, TUFT, morph_range
from gfx.matrices import gl_bytes, look_at, perspective
from gfx.meshes import MESHES
from hexaddr import KEN, RI, SCALE, SHAKU, Tile, axial_to_metres, up

WINDOW_SIZE = (1600, 900)
VIEW_SIZE = (1180, 900)
PANEL_SIZE = (420, 900)
FOV_Y_DEG = 60.0
NEAR_M, FAR_M = 0.5, 120000.0
SUN = tuple(np.array((0.4, 0.8, 0.3)) / np.linalg.norm((0.4, 0.8, 0.3)))
FOG_COL = (0.72, 0.80, 0.88)
ZENITH_COL = (0.32, 0.52, 0.82)
FOG_DIST_M = 30000.0
LOOKUP_RADIUS = 4  # the loaded-children textures cover the camera's cell +- 4 at each level
SHADERS = Path(__file__).parent / "shaders"


def shader_source(name: str) -> str:
    text = (SHADERS / name).read_text()
    return text.replace('#include "hex.glsl"', (SHADERS / "hex.glsl").read_text())


def split_origin(origin: Tile) -> tuple[list, list]:
    """origin = SCALE[L] * k[L] + m[L] per level, with 0 <= m < SCALE[L]."""
    ks, ms = [], []
    for s in SCALE:
        k = (origin[0] // s, origin[1] // s)
        ks.append(k)
        ms.append((origin[0] - s * k[0], origin[1] - s * k[1]))
    return ks, ms


@dataclass
class View:
    origin: Tile                         # the loader focus (global shaku)
    eye: tuple[float, float, float]      # world metres
    target: tuple[float, float, float]   # world metres
    up: tuple[float, float, float] = (0.0, 1.0, 0.0)
    projection: np.ndarray | None = None  # default: the perspective camera


@dataclass
class ChunkGPU:
    level: int
    parent: Tile
    origin: tuple[float, float]
    vao: moderngl.VertexArray
    buffers: list
    props: list  # (kind, vao, instance count)


class Renderer:
    def __init__(self, ctx: moderngl.Context, target: moderngl.Framebuffer):
        self.ctx = ctx
        self.target = target
        self.terrain = ctx.program(vertex_shader=shader_source("terrain.vert"),
                                   fragment_shader=shader_source("terrain.frag"))
        self.prop = ctx.program(vertex_shader=shader_source("prop.vert"), fragment_shader=shader_source("prop.frag"))
        self.sky = ctx.program(vertex_shader=shader_source("sky.vert"), fragment_shader=shader_source("sky.frag"))
        self.panel = ctx.program(vertex_shader=shader_source("panel.vert"), fragment_shader=shader_source("panel.frag"))
        self.empty = ctx.vertex_array(self.sky, [])
        self.panel_vao = ctx.vertex_array(self.panel, [])
        self.mesh_vbos = {kind: ctx.buffer(make().tobytes()) for kind, make in MESHES.items()}
        size = 2 * LOOKUP_RADIUS + 1
        self.lookup = {level: ctx.texture((size, size), 1, dtype="u1") for level in (1, 2, 3)}
        for tex in self.lookup.values():
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.panel_tex = ctx.texture(PANEL_SIZE, 4)
        self.chunks: dict = {}
        self.debug = 0          # 0 normal, 1 owner ids, 2 flat grey with lines
        self.debug_level = 0
        self.debug_base = (0, 0)
        self.terrain["u_loaded1"] = 1
        self.terrain["u_loaded2"] = 2
        self.terrain["u_loaded3"] = 3
        self.prop["u_loaded1"] = 1

    # --- chunks -------------------------------------------------------------------------------

    def load_chunk(self, chunk) -> None:
        vbo = self.ctx.buffer(chunk.vertices.tobytes())
        ibo = self.ctx.buffer(chunk.triangles.tobytes())
        vao = self.ctx.vertex_array(self.terrain, [(vbo, "2f 1f 1f 3f", "in_pos", "in_h", "in_hc", "in_col")],
                                    index_buffer=ibo, index_element_size=4)
        buffers = [vbo, ibo]
        props = []
        for kind, rows in chunk.props.items():
            if len(rows) == 0:
                continue
            inst = self.ctx.buffer(np.ascontiguousarray(rows).tobytes())
            buffers.append(inst)
            pvao = self.ctx.vertex_array(self.prop, [
                (self.mesh_vbos[kind], "3f 3f 3f", "in_vert", "in_normal", "in_vcol"),
                (inst, "4f 4f 2f/i", "i_a", "i_b", "i_cell"),
            ])
            props.append((kind, pvao, len(rows)))
        self.chunks[chunk.key] = ChunkGPU(chunk.level, chunk.parent, chunk.origin, vao, buffers, props)

    def unload_chunk(self, chunk) -> None:
        gpu = self.chunks.pop(chunk.key, None)
        if gpu is None:
            return
        gpu.vao.release()
        for _, pvao, _ in gpu.props:
            pvao.release()
        for b in gpu.buffers:
            b.release()

    # --- frame --------------------------------------------------------------------------------

    def upload_panel(self, surface) -> None:
        import pygame
        self.panel_tex.write(pygame.image.tobytes(surface, "RGBA", True))

    def draw(self, view: View, draw_panel: bool = True) -> None:
        ctx = self.ctx
        ox, oz = axial_to_metres(*view.origin)
        eye = (view.eye[0] - ox, view.eye[1], view.eye[2] - oz)
        target = (view.target[0] - ox, view.target[1], view.target[2] - oz)
        proj = view.projection
        if proj is None:
            proj = perspective(FOV_Y_DEG, VIEW_SIZE[0] / VIEW_SIZE[1], NEAR_M, FAR_M)
        viewproj = proj @ look_at(eye, target, view.up)
        ks, ms = split_origin(view.origin)
        centres = [up(view.origin, SHAKU, level) for level in range(RI + 1)]
        self._write_lookups(centres)

        self.target.use()
        ctx.viewport = (0, 0, *VIEW_SIZE)
        ctx.clear(*FOG_COL, 1.0, depth=1.0)

        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.sky["u_inv_viewproj"].write(gl_bytes(np.linalg.inv(viewproj)))
        self.sky["u_eye"] = eye
        self.sky["u_fog_col"] = FOG_COL
        self.sky["u_zenith_col"] = ZENITH_COL
        self.empty.render(moderngl.TRIANGLES, vertices=3)

        ctx.enable(moderngl.DEPTH_TEST)
        t = self.terrain
        t["u_viewproj"].write(gl_bytes(viewproj))
        t["u_k"].write(np.array(ks, dtype="i4").tobytes())
        t["u_m"].write(np.array(ms, dtype="i4").tobytes())
        t["u_lc"].write(np.array(centres, dtype="i4").tobytes())
        t["u_eye"] = eye
        t["u_sun"] = SUN
        t["u_fog_col"] = FOG_COL
        t["u_fog_dist"] = FOG_DIST_M
        t["u_debug"] = self.debug
        t["u_debug_level"] = self.debug_level
        t["u_debug_base"] = self.debug_base
        for level, tex in self.lookup.items():
            tex.use(location=level)
        for gpu in self.chunks.values():
            t["u_level"] = gpu.level
            t["u_parent"] = gpu.parent
            t["u_offset"] = (gpu.origin[0] - ox, gpu.origin[1] - oz)
            t["u_morph"] = morph_range(gpu.level)
            gpu.vao.render()

        if self.debug == 0:
            p = self.prop
            p["u_viewproj"].write(gl_bytes(viewproj))
            p["u_morph_fine"] = morph_range(SHAKU)
            p["u_morph_mid"] = morph_range(KEN)
            p["u_lc1"] = centres[1]
            p["u_eye"] = eye
            p["u_sun"] = SUN
            p["u_fog_col"] = FOG_COL
            p["u_fog_dist"] = FOG_DIST_M
            for gpu in self.chunks.values():
                if not gpu.props:
                    continue
                p["u_offset"] = (gpu.origin[0] - ox, gpu.origin[1] - oz)
                for kind, pvao, count in gpu.props:
                    p["u_detail"] = 1 if kind in (TUFT, PEBBLE) else 0
                    pvao.render(instances=count)

        if draw_panel:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.viewport = (VIEW_SIZE[0], 0, *PANEL_SIZE)
            self.panel_tex.use(location=0)
            self.panel["u_panel"] = 0
            self.panel_vao.render(moderngl.TRIANGLES, vertices=3)

    def _write_lookups(self, centres) -> None:
        size = 2 * LOOKUP_RADIUS + 1
        grids = {level: np.zeros((size, size), dtype="u1") for level in self.lookup}
        for level, parent in self.chunks:
            cell_level = level + 1  # the chunk is the children of this cell
            if cell_level not in grids:
                continue
            c = centres[cell_level]
            dq, dr = parent[0] - c[0], parent[1] - c[1]
            if abs(dq) <= LOOKUP_RADIUS and abs(dr) <= LOOKUP_RADIUS:
                grids[cell_level][dr + LOOKUP_RADIUS, dq + LOOKUP_RADIUS] = 1
        for level, grid in grids.items():
            self.lookup[level].write(grid.tobytes())

    def read_rgb(self, viewport=None) -> np.ndarray:
        """The target's pixels as an (H, W, 3) uint8 array, top row first."""
        viewport = viewport or (0, 0, *WINDOW_SIZE)
        data = self.target.read(viewport=viewport, components=3)
        w, h = viewport[2], viewport[3]
        return np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)[::-1]
