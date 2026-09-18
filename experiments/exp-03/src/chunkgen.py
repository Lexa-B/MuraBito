"""Generating one chunk: heights, colours, mesh and props. A pure function of (level, parent, seed)."""

import time
from dataclasses import dataclass, field

import numpy as np

from chunkgeom import DIRS_PLANAR, axial_to_metres_np, mesh_height, mesh_triangle, template
from hexaddr import CHO, KEN, PACKING, RI, SHAKU, WIDTH_M, Tile, axial_to_metres, centre_child, window
from noise import hash01, hash_ints
from terrain import DIRT, GRASS, forest_density, ground_colour, ground_type, height

TREE, ROCK_PROP, TUFT, PEBBLE = 0, 1, 2, 3
PROP_NAMES = ("tree", "rock", "tuft", "pebble")
TREE_MAX = 0.05                                  # per ken, in the thick of the woods
ROCK_CHANCE = np.array([0.02, 0.06, 0.10, 0.0])  # per ken, by ground type
TUFT_CHANCE = 0.30                               # per grass shaku
PEBBLE_CHANCE = 0.15                             # per dirt shaku
INNER_SHAKU = np.array(window((0, 0), 2), dtype=np.int64)  # the 19 shaku a ken always owns whole
PROP_FIELDS = 10  # x, z (rel. origin), h_full, h_mid, h_far, scale, yaw, tint, cell q, cell r
MORPH_START, MORPH_END = 1.3, 2.0  # in parent widths from the loader focus (see the window margin)


@dataclass
class ChunkData:
    level: int                     # level of the children (the tier this chunk draws)
    parent: Tile                   # parent cell at level + 1 (world chunk: (0, 0))
    origin: tuple[float, float]    # world metres of the parent's centre; vertices are relative to it
    cells: np.ndarray              # (M, 2) global cells of the owned children
    vertices: np.ndarray           # (V, 7) float32: x, z, h, h_coarse, r, g, b
    triangles: np.ndarray          # (T, 3) uint32
    props: dict = field(default_factory=dict)  # kind -> (K, PROP_FIELDS) float32
    gen_ms: float = 0.0

    @property
    def key(self) -> tuple[int, Tile]:
        return (self.level, self.parent)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)


def tier_height(seed: int):
    return lambda x, z, tier: height(x, z, tier, seed)


def morph_range(level: int) -> tuple[float, float]:
    """Metres from the loader focus over which a tier's heights blend into the coarser mesh."""
    if level == RI:
        return (0.0, 0.0)
    w = WIDTH_M[level + 1]
    return (MORPH_START * w, MORPH_END * w)


def generate_chunk(level: int, parent: Tile, seed: int) -> ChunkData:
    t0 = time.perf_counter()
    tpl = template(level)
    if level == RI:
        base = np.zeros(2, dtype=np.int64)
        origin = (0.0, 0.0)
    else:
        base = np.array(centre_child(parent, level + 1), dtype=np.int64)
        origin = axial_to_metres(*parent, level + 1)
    cells = tpl.cells + base
    x, z = axial_to_metres_np(cells[:, 0], cells[:, 1], level)
    h = height(x, z, level, seed)

    v = tpl.vertex_count
    xv, zv, hv = x[:v], z[:v], h[:v]
    diffs = h[tpl.neighbours] - hv[:, None]
    grad = diffs @ DIRS_PLANAR / (3 * WIDTH_M[level])
    slope = np.degrees(np.arctan(np.hypot(grad[:, 0], grad[:, 1])))
    kind = ground_type(xv, zv, hv, slope, seed)
    colour = ground_colour(xv, zv, kind, level, seed)
    if level == RI:
        coarse = hv
    else:
        n = PACKING[level + 1]
        coarse = mesh_height(cells[:v, 0] / n, cells[:v, 1] / n, level + 1, tier_height(seed))

    vertices = np.column_stack([xv - origin[0], zv - origin[1], hv, coarse, colour]).astype(np.float32)
    owned = cells[:tpl.owned]
    props = {}
    if level == KEN:
        props = _ken_props(owned, kind[:tpl.owned], h, tpl, base, origin, seed)
    elif level == SHAKU:
        m = tpl.owned
        props = _shaku_details(owned, kind[:m], hv[:m], coarse[:m], parent, origin, seed)
    return ChunkData(
        level=level, parent=tuple(parent), origin=origin, cells=owned, vertices=vertices,
        triangles=tpl.triangles, props=props, gen_ms=(time.perf_counter() - t0) * 1000,
    )


def _pack(x, z, h_full, h_mid, h_far, scale, yaw, tint, cell_q, cell_r, origin):
    return np.column_stack([
        x - origin[0], z - origin[1], h_full, h_mid, h_far, scale, yaw, tint, cell_q, cell_r,
    ]).astype(np.float32)


def _ken_props(kens, kind, h, tpl, base, origin, seed) -> dict:
    q, r = kens[:, 0], kens[:, 1]
    kx, kz = axial_to_metres_np(q, r, KEN)
    forest = forest_density(kx, kz, seed)
    roll_tree = hash01(seed, q, r, 11)
    roll_rock = hash01(seed, q, r, 12)
    is_tree = ((kind == GRASS) | (kind == DIRT)) & (roll_tree < TREE_MAX * forest)
    is_rock = ~is_tree & (roll_rock < ROCK_CHANCE[kind])
    has_prop = is_tree | is_rock
    pick = (hash_ints(seed, q, r, 13) % np.uint64(len(INNER_SHAKU))).astype(np.intp)
    k = kens[has_prop]
    s = k * PACKING[KEN] + INNER_SHAKU[pick[has_prop]]
    px, pz = axial_to_metres_np(s[:, 0], s[:, 1], SHAKU)
    h_full = height(px, pz, SHAKU, seed)
    # the ken mesh at the prop: its triangle's corners are all cells of this chunk
    corners, weights = mesh_triangle(s[:, 0] / PACKING[KEN], s[:, 1] / PACKING[KEN])
    idx = tpl.index_of(corners.reshape(-1, 2) - base).reshape(corners.shape[:-1])
    h_mid = (h[idx] * weights).sum(axis=-1)
    n_cho = PACKING[KEN] * PACKING[CHO]
    h_far = mesh_height(s[:, 0] / n_cho, s[:, 1] / n_cho, CHO, tier_height(seed))
    tree = is_tree[has_prop]
    lo = np.where(tree, 0.8, 0.5)
    hi = np.where(tree, 1.3, 1.5)
    scale = lo + (hi - lo) * hash01(seed, k[:, 0], k[:, 1], 14)
    yaw = 2 * np.pi * hash01(seed, k[:, 0], k[:, 1], 15)
    tint = 0.85 + 0.3 * hash01(seed, k[:, 0], k[:, 1], 16)
    packed = _pack(px, pz, h_full, h_mid, h_far, scale, yaw, tint, k[:, 0], k[:, 1], origin)
    return {TREE: packed[tree], ROCK_PROP: packed[~tree]}


def _shaku_details(shaku, kind, h, h_ken, ken, origin, seed) -> dict:
    """Tufts and pebbles. A detail sits on its shaku's centre: the shaku vertex height, and the
    ken mesh there is the vertex's coarse height."""
    q, r = shaku[:, 0], shaku[:, 1]
    roll = hash01(seed, q, r, 21)
    props = {}
    for kind_id, mask in ((TUFT, (kind == GRASS) & (roll < TUFT_CHANCE)),
                          (PEBBLE, (kind == DIRT) & (roll < PEBBLE_CHANCE))):
        s = shaku[mask]
        px, pz = axial_to_metres_np(s[:, 0], s[:, 1], SHAKU)
        scale = 0.7 + 0.6 * hash01(seed, s[:, 0], s[:, 1], 22)
        yaw = 2 * np.pi * hash01(seed, s[:, 0], s[:, 1], 23)
        tint = 0.85 + 0.3 * hash01(seed, s[:, 0], s[:, 1], 24)
        cells = np.broadcast_to(np.array(ken, dtype=np.int64), s.shape)
        props[kind_id] = _pack(px, pz, h[mask], h_ken[mask], np.zeros(len(s)), scale, yaw, tint,
                               cells[:, 0], cells[:, 1], origin)
    return props
