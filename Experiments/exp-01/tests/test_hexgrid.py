import pytest

from hexgrid import DIRECTIONS, add, all_tiles, direction_index, distance, in_bounds, neighbors


def test_map_has_469_tiles():
    tiles = all_tiles()
    assert len(tiles) == 469
    assert len(set(tiles)) == 469
    assert all(in_bounds(t) for t in tiles)


def test_interior_tile_has_six_neighbors_in_direction_order():
    assert neighbors((0, 0)) == [add((0, 0), d) for d in DIRECTIONS]


def test_corner_tile_has_three_neighbors():
    assert sorted(neighbors((12, 0))) == sorted([(12, -1), (11, 0), (11, 1)])


def test_edge_tile_has_four_neighbors():
    assert sorted(neighbors((12, -6))) == sorted([(12, -7), (11, -6), (11, -5), (12, -5)])


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ((0, 0), (5, 0), 5),    # q axis
        ((0, 0), (0, -4), 4),   # r axis
        ((0, 0), (-3, 3), 3),   # s axis
        ((0, 0), (2, 1), 3),    # off-axis
        ((1, -2), (-2, 3), 5),  # off-axis, neither at origin
    ],
)
def test_distance(a, b, expected):
    assert distance(a, b) == expected
    assert distance(b, a) == expected


def test_in_bounds_rejects_distance_13():
    assert in_bounds((12, 0))
    assert not in_bounds((13, 0))
    assert not in_bounds((0, -13))
    assert not in_bounds((7, 6))  # distance 13, off-axis


def test_direction_index():
    assert direction_index((0, 0), (1, 0)) == 0
    assert direction_index((2, 2), (2, 3)) == 5
    with pytest.raises(ValueError):
        direction_index((0, 0), (2, 0))
