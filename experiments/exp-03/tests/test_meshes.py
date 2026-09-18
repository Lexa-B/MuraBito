import numpy as np

from gfx.meshes import LEAVES, MESHES
from chunkgen import TREE, TUFT
from terrain import GRASS, GROUND_COLOURS


def extent(mesh):
    pos = mesh[:, :3]
    return pos.max(axis=0) - pos.min(axis=0)


def test_tuft_is_a_low_splayed_clump_not_a_tiny_tree():
    tuft = MESHES[TUFT]()
    width_x, height, width_z = extent(tuft)
    assert 0.06 <= height <= 0.12
    # splayed: wider than it is tall, so it does not read as a cone
    assert min(width_x, width_z) >= height
    # at least five blades, each a two-sided triangle
    assert len(tuft) >= 5 * 2 * 3


def test_tuft_colour_is_near_the_grass_not_the_foliage():
    colour = MESHES[TUFT]()[:, 6:9].mean(axis=0)
    grass = GROUND_COLOURS[GRASS]
    assert np.abs(colour - grass).max() < 0.15
    assert np.linalg.norm(colour - grass) < np.linalg.norm(np.array(LEAVES) - grass) / 2


def test_tuft_shades_like_the_ground():
    # upward normals: the clump is lit like the grass under it, not dark on its shaded side
    normals = MESHES[TUFT]()[:, 3:6]
    assert (normals[:, 1] > 0.99).all()


def test_trees_stay_full_size():
    assert 7.0 < extent(MESHES[TREE]())[1] < 8.0
