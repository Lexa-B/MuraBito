import numpy as np
import pytest

from chunkgen import (
    INNER_SHAKU, MORPH_END, MORPH_START, PEBBLE, ROCK_PROP, TREE, TUFT, generate_chunk, morph_range, tier_height,
)
from chunkgeom import mesh_height, template
from hexaddr import CHO, KEN, PACKING, RI, SHAKU, WIDTH_M, axial_to_metres, parent, shaku_at, up
from terrain import height

SEED = 0


@pytest.fixture(scope="module")
def ken_chunk():
    return generate_chunk(KEN, (144, 0), SEED)


def test_chunk_contents_match_the_template():
    for level, parent_cell in ((SHAKU, (8640, 0)), (KEN, (144, 0)), (CHO, (4, 0)), (RI, (0, 0))):
        c = generate_chunk(level, parent_cell, SEED)
        tpl = template(level)
        assert c.key == (level, parent_cell)
        assert len(c.cells) == tpl.owned
        assert c.vertices.shape == (tpl.vertex_count, 7) and c.vertices.dtype == np.float32
        assert c.triangle_count == len(tpl.triangles)
        if level != RI:
            assert all(up(tuple(cell), level, level + 1) == parent_cell for cell in c.cells[:50])


def test_generation_is_deterministic():
    a = generate_chunk(KEN, (5, -3), SEED)
    b = generate_chunk(KEN, (5, -3), SEED)
    assert np.array_equal(a.vertices, b.vertices)
    for kind in a.props:
        assert np.array_equal(a.props[kind], b.props[kind])
    assert not np.array_equal(a.vertices, generate_chunk(KEN, (5, -3), SEED + 1).vertices)


def test_vertices_are_relative_to_the_parent_centre(ken_chunk):
    ox, oz = axial_to_metres(144, 0, CHO)
    assert ken_chunk.origin == (pytest.approx(ox), pytest.approx(oz))
    x = ken_chunk.vertices[:, 0] + ox
    z = ken_chunk.vertices[:, 1] + oz
    assert np.allclose(ken_chunk.vertices[:, 2], height(x, z, KEN, SEED), atol=1e-3)
    assert np.abs(ken_chunk.vertices[:, :2]).max() < 0.7 * WIDTH_M[CHO]


def test_coarse_height_is_the_coarser_mesh(ken_chunk):
    tpl = template(KEN)
    cells = tpl.cells[:tpl.vertex_count] + np.array((144 * 60, 0))
    n = PACKING[CHO]
    expected = mesh_height(cells[:, 0] / n, cells[:, 1] / n, CHO, tier_height(SEED))
    assert np.allclose(ken_chunk.vertices[:, 3], expected, atol=1e-3)
    world = generate_chunk(RI, (0, 0), SEED)
    assert np.array_equal(world.vertices[:, 2], world.vertices[:, 3])


def test_same_tier_neighbours_agree_on_shared_vertices():
    a = generate_chunk(SHAKU, (0, 0), SEED)
    b = generate_chunk(SHAKU, (1, 0), SEED)
    tpl = template(SHAKU)
    ca = {tuple(c): i for i, c in enumerate(tpl.cells[:tpl.vertex_count] + np.array((0, 0)))}
    cb = {tuple(c): i for i, c in enumerate(tpl.cells[:tpl.vertex_count] + np.array((6, 0)))}
    shared = set(ca) & set(cb)
    assert shared
    for cell in shared:
        va = a.vertices[ca[cell]]
        vb = b.vertices[cb[cell]]
        assert va[2:].tolist() == pytest.approx(vb[2:].tolist(), abs=1e-4)


def test_ken_props(ken_chunk):
    trees, rocks = ken_chunk.props[TREE], ken_chunk.props[ROCK_PROP]
    assert len(trees) + len(rocks) > 0
    ox, oz = ken_chunk.origin
    for rows in (trees, rocks):
        for row in rows[:40]:
            ken = (int(row[8]), int(row[9]))
            assert parent(ken, KEN) == (144, 0)
            # the prop stands on one of its ken's inner 19 shaku
            px, pz = row[0] + ox, row[1] + oz
            s = shaku_at(px, pz)
            offset = (s[0] - 6 * ken[0], s[1] - 6 * ken[1])
            assert offset in {tuple(o) for o in INNER_SHAKU}
            assert row[2] == pytest.approx(float(height(px, pz, SHAKU, SEED)), abs=1e-3)


def test_prop_rates_over_many_ken():
    counts = {TREE: 0, ROCK_PROP: 0}
    kens = 0
    for q in range(-3, 3):
        c = generate_chunk(KEN, (q * 7, q * 3), SEED)
        kens += len(c.cells)
        for kind in counts:
            counts[kind] += len(c.props[kind])
    assert 0.0 < counts[TREE] / kens < 0.05
    assert 0.01 < counts[ROCK_PROP] / kens < 0.10


def test_a_prop_stands_on_the_shaku_tier_ground(ken_chunk):
    # the prop's full-detail and ken-mesh heights are exactly the shaku chunk's vertex heights there
    ox, oz = ken_chunk.origin
    rows = np.concatenate([ken_chunk.props[TREE], ken_chunk.props[ROCK_PROP]])[:10]
    for row in rows:
        ken = (int(row[8]), int(row[9]))
        shaku_chunk = generate_chunk(SHAKU, ken, SEED)
        s = shaku_at(row[0] + ox, row[1] + oz)
        i = [tuple(c) for c in shaku_chunk.cells].index(s)
        assert row[2] == pytest.approx(float(shaku_chunk.vertices[i, 2]), abs=1e-3)
        assert row[3] == pytest.approx(float(shaku_chunk.vertices[i, 3]), abs=1e-3)


def test_shaku_details_sit_on_their_shaku():
    c = generate_chunk(SHAKU, (8640, 3), SEED)
    rows = np.concatenate([c.props[TUFT], c.props[PEBBLE]])
    ox, oz = c.origin
    for row in rows:
        assert row[2] == pytest.approx(float(height(row[0] + ox, row[1] + oz, SHAKU, SEED)), abs=1e-3)
        assert (int(row[8]), int(row[9])) == (8640, 3)


def test_morph_ranges():
    assert morph_range(SHAKU) == (pytest.approx(MORPH_START * WIDTH_M[KEN]), pytest.approx(MORPH_END * WIDTH_M[KEN]))
    assert morph_range(CHO) == (pytest.approx(MORPH_START * WIDTH_M[RI]), pytest.approx(MORPH_END * WIDTH_M[RI]))
    assert morph_range(RI) == (0.0, 0.0)
    # the blend ends before the nearest possible window edge (2.26 parent widths, measured)
    assert MORPH_END < 2.26
