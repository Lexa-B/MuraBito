import numpy as np
import pytest

from chunkgeom import axial_to_metres_np, mesh_height, mesh_triangle, template
from hexaddr import CHO, KEN, RI, SHAKU, axial_to_metres, child_offsets, neighbours


@pytest.mark.parametrize("level, owned", [(SHAKU, 36), (KEN, 3600), (CHO, 1296), (RI, 469)])
def test_template_owns_the_parents_children(level, owned):
    tpl = template(level)
    assert tpl.owned == owned
    cells = [tuple(c) for c in tpl.cells]
    assert len(set(cells)) == len(cells)
    if level != RI:
        assert set(cells[:owned]) == set(child_offsets(level + 1))


def test_template_rings_and_neighbours():
    tpl = template(KEN)
    cells = [tuple(c) for c in tpl.cells]
    vertices = set(cells[:tpl.vertex_count])
    for i, c in enumerate(cells[:tpl.vertex_count]):
        assert [cells[j] for j in tpl.neighbours[i]] == neighbours(c)
    # every owned cell's neighbours are vertices (ring 1)
    for c in cells[:tpl.owned]:
        assert set(neighbours(c)) <= vertices


def test_triangles_are_adjacent_and_cover_every_owned_vertex():
    tpl = template(KEN)
    cells = tpl.cells
    tri = tpl.triangles
    assert tri.max() < tpl.vertex_count
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d = cells[tri[:, a]] - cells[tri[:, b]]
        dist = (np.abs(d[:, 0]) + np.abs(d[:, 1]) + np.abs(d[:, 0] + d[:, 1])) // 2
        assert (dist == 1).all()
    # six triangles around every owned vertex
    counts = np.bincount(tri.ravel(), minlength=tpl.vertex_count)
    assert (counts[:tpl.owned] == 6).all()
    # every triangle touches an owned cell
    assert (tri.min(axis=1) < tpl.owned).all()


def test_neighbouring_chunks_share_their_border_triangles():
    tpl = template(SHAKU)
    base_a = np.array((0, 0))
    base_b = np.array((6, 0))  # the next ken east
    tris = lambda base: {tuple(sorted(map(tuple, tpl.cells[t] + base))) for t in tpl.triangles}  # noqa: E731
    shared = tris(base_a) & tris(base_b)
    assert shared  # triangles straddling the border are drawn by both, clipped by ownership


def test_index_of_finds_template_cells():
    tpl = template(KEN)
    idx = tpl.index_of(tpl.cells[:50])
    assert list(idx) == list(range(50))
    assert tpl.index_of(np.array([[1000, 1000]]))[0] == -1


def test_mesh_triangle_weights():
    corners, weights = mesh_triangle(np.array([0.0, 0.25, 0.75, 2.0]), np.array([0.0, 0.25, 0.75, -1.0]))
    assert np.allclose(weights.sum(axis=-1), 1.0)
    assert (weights >= -1e-12).all()
    # a lattice point is its own corner with weight 1
    assert np.allclose(weights[0], [1, 0, 0]) and tuple(corners[0][0]) == (0, 0)
    assert np.allclose(weights[3], [1, 0, 0]) and tuple(corners[3][0]) == (2, -1)
    # the weighted corners reproduce the point
    p = (corners * weights[..., None]).sum(axis=-2)
    assert np.allclose(p, [[0, 0], [0.25, 0.25], [0.75, 0.75], [2, -1]])


def test_mesh_height_is_exact_at_vertices_and_linear_between():
    plane = lambda x, z, tier: 2.0 * x - 3.0 * z + 5.0  # noqa: E731
    fq = np.array([0.0, 1.3, -4.7, 10.5])
    fr = np.array([0.0, 2.2, 0.4, -3.9])
    x, z = axial_to_metres_np(fq, fr, CHO)
    assert np.allclose(mesh_height(fq, fr, CHO, plane), plane(x, z, CHO))
    bumpy = lambda x, z, tier: np.sin(x) + np.cos(z)  # noqa: E731
    cx, cz = axial_to_metres(3, -2, KEN)
    assert mesh_height(np.array([3.0]), np.array([-2.0]), KEN, bumpy)[0] == pytest.approx(bumpy(cx, cz, KEN))
