"""Chunk geometry: which cells a chunk holds, its triangles, and heights on a tier's mesh.

A chunk is one parent cell's children. Its template (offsets, neighbour table, triangles) is the
same for every parent at a level, so it is built once. Cells are ordered: owned children first,
then ring 1 (together, the mesh vertices), then ring 2 (only for slopes at ring-1 vertices).
"""

from dataclasses import dataclass
from functools import cache

import numpy as np

from hexaddr import RI, SQRT3, WIDTH_M, child_offsets, world_ri
from hexgrid import DIRECTIONS

# The triangulation of every level: each cell anchors two triangles of mutually adjacent cells,
# the two halves of the parallelogram (c, c+(1,0), c+(1,1), c+(0,1)).
TRI_A = ((0, 0), (1, 0), (0, 1))
TRI_B = ((1, 0), (1, 1), (0, 1))

# Unit vectors of the six neighbour directions in the plane (in cell widths).
DIRS_PLANAR = np.array([(q + r / 2, r * SQRT3 / 2) for q, r in DIRECTIONS])


@dataclass(frozen=True)
class Template:
    level: int                # level of the cells (the chunk's children)
    owned: int                # the first `owned` cells are the chunk's own children
    vertex_count: int         # the first `vertex_count` cells are mesh vertices (owned + ring 1)
    cells: np.ndarray         # (H, 2) int64 offsets from the parent's centre child (world: absolute ri)
    neighbours: np.ndarray    # (vertex_count, 6) indices into cells, in DIRECTIONS order
    triangles: np.ndarray     # (T, 3) uint32 indices into the vertices
    grid: np.ndarray          # dense lookup: grid[q - lo, r - lo] = index into cells, or -1
    grid_lo: int

    def index_of(self, offsets: np.ndarray) -> np.ndarray:
        """Indices into cells of (N, 2) template offsets (-1 where the template has no such cell)."""
        i = offsets[:, 0] - self.grid_lo
        j = offsets[:, 1] - self.grid_lo
        n = len(self.grid)
        inside = (i >= 0) & (i < n) & (j >= 0) & (j < n)
        found = self.grid[np.clip(i, 0, n - 1), np.clip(j, 0, n - 1)]
        return np.where(inside, found, -1)


def _neighbours(c):
    return [(c[0] + dq, c[1] + dr) for dq, dr in DIRECTIONS]


def _build(level: int, owned: list) -> Template:
    owned_set = set(owned)
    ring1 = sorted({n for c in owned for n in _neighbours(c)} - owned_set)
    ring1_set = set(ring1)
    ring2 = sorted({n for c in ring1 for n in _neighbours(c)} - owned_set - ring1_set)
    cells = list(owned) + ring1 + ring2
    index = {c: i for i, c in enumerate(cells)}
    vertex_count = len(owned) + len(ring1)
    neighbours = [[index[n] for n in _neighbours(c)] for c in cells[:vertex_count]]
    triangles = set()
    for v in owned:
        for tri in (TRI_A, TRI_B):
            for corner in tri:
                anchor = (v[0] - corner[0], v[1] - corner[1])
                triangles.add(tuple((anchor[0] + a, anchor[1] + b) for a, b in tri))
    tri_idx = sorted([index[a], index[b], index[c]] for a, b, c in triangles)
    arr = np.array(cells, dtype=np.int64)
    lo = int(arr.min()) - 1
    size = int(arr.max()) - lo + 2
    grid = np.full((size, size), -1, dtype=np.int64)
    grid[arr[:, 0] - lo, arr[:, 1] - lo] = np.arange(len(cells))
    return Template(
        level=level,
        owned=len(owned),
        vertex_count=vertex_count,
        cells=arr,
        neighbours=np.array(neighbours, dtype=np.int64),
        triangles=np.array(tri_idx, dtype=np.uint32),
        grid=grid,
        grid_lo=lo,
    )


@cache
def template(level: int) -> Template:
    """The template for chunks whose children are at `level` (RI: the world chunk)."""
    if level == RI:
        return _build(RI, world_ri())
    return _build(level, list(child_offsets(level + 1)))


def axial_to_metres_np(q, r, level: int):
    w = WIDTH_M[level]
    q = np.asarray(q, dtype=np.float64)
    r = np.asarray(r, dtype=np.float64)
    return (q + r / 2) * w, r * (SQRT3 / 2) * w


def mesh_triangle(fq, fr):
    """The mesh triangle containing fractional axial points: three corner cells and their weights."""
    fq = np.asarray(fq, dtype=np.float64)
    fr = np.asarray(fr, dtype=np.float64)
    i = np.floor(fq)
    j = np.floor(fr)
    u = fq - i
    v = fr - j
    upper = u + v >= 1.0
    i = i.astype(np.int64)
    j = j.astype(np.int64)
    # lower half: (i,j), (i+1,j), (i,j+1); upper half: (i+1,j), (i+1,j+1), (i,j+1)
    ax = np.where(upper, i + 1, i)
    bx = np.where(upper, i + 1, i + 1)
    by = np.where(upper, j + 1, j)
    corners = np.stack([
        np.stack([ax, j], -1),
        np.stack([bx, by], -1),
        np.stack([i, j + 1], -1),
    ], axis=-2)
    weights = np.stack([
        np.where(upper, 1.0 - v, 1.0 - u - v),
        np.where(upper, u + v - 1.0, u),
        np.where(upper, 1.0 - u, v),
    ], axis=-1)
    return corners, weights


def mesh_height(fq, fr, level: int, height_fn) -> np.ndarray:
    """Height of the tier-`level` mesh at fractional axial points on the `level` lattice.

    height_fn(x, z, tier) gives heights at world points; the mesh is the linear interpolation of
    its values at the three corner cells.
    """
    corners, weights = mesh_triangle(fq, fr)
    flat = corners.reshape(-1, 2)
    # unique on a packed 1-D key is much faster than np.unique(axis=0)
    key = (flat[:, 0] << 32) + (flat[:, 1] & 0xFFFFFFFF)
    _, first, inverse = np.unique(key, return_index=True, return_inverse=True)
    unique = flat[first]
    x, z = axial_to_metres_np(unique[:, 0], unique[:, 1], level)
    h = height_fn(x, z, level)[inverse.reshape(-1)].reshape(corners.shape[:-1])
    return (h * weights).sum(axis=-1)
