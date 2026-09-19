import pytest

from ai.vision import SENSE_HALF_ANGLE, SENSE_RANGE, normalize, visible_tiles
from hexgrid import neighbors


def rotate(tile):
    """Rotate an axial offset one direction index counter-clockwise (DIRECTIONS[i] -> DIRECTIONS[i + 1])."""
    q, r = tile
    return (q + r, -q)


@pytest.mark.parametrize("facing", range(6))
def test_origin_and_neighbors_are_always_visible(facing):
    seen = visible_tiles((0, 0), facing, set())
    assert {(0, 0), *neighbors((0, 0))} <= seen


@pytest.mark.parametrize("facing", range(6))
def test_open_map_cone_is_52_tiles(facing):
    assert len(visible_tiles((0, 0), facing, set())) == 52


def test_cone_edges_are_included_and_tiles_beyond_are_not():
    seen = visible_tiles((0, 0), 0, set())
    assert (3, -3) in seen  # exactly -60 degrees
    assert (0, 3) in seen  # exactly +60 degrees
    assert (-1, 4) not in seen  # about 74 degrees
    assert (-2, 0) not in seen  # straight behind, distance 2


def test_placeholder_sense_constants():
    assert (SENSE_RANGE, SENSE_HALF_ANGLE) == (6, 60.0)


def test_range_is_six():
    seen = visible_tiles((0, 0), 0, set())
    assert (6, 0) in seen
    assert (7, 0) not in seen


def test_a_wall_hides_the_tiles_behind_it_and_is_itself_visible():
    seen = visible_tiles((0, 0), 0, {(2, 0)})
    assert (2, 0) in seen
    assert not {(3, 0), (4, 0), (5, 0), (6, 0)} & seen
    assert (3, -1) in seen  # off to the side of the shadow


def test_a_center_exactly_on_a_shadow_edge_is_visible():
    seen = visible_tiles((0, 0), 0, {(1, 0)})
    assert (2, 0) not in seen
    assert (2, -1) in seen  # center at exactly -30 degrees, the shadow's edge
    assert (1, 1) in seen  # a neighbor, never shadowed


def test_neighbors_are_never_shadowed():
    ring = set(neighbors((0, 0)))
    seen = visible_tiles((0, 0), 0, ring)
    assert seen == {(0, 0)} | ring


def test_a_blocker_on_the_cone_edge_shadows_the_tile_behind_it():
    seen = visible_tiles((0, 0), 0, {(2, -2)})  # exactly -60 degrees
    assert (2, -2) in seen
    assert (3, -3) not in seen


def test_a_blocker_outside_the_cone_still_casts_a_shadow_into_it():
    # With a 45-degree half angle, the neighbor (1, -1) at -60 degrees is outside the cone by angle
    # (it is still seen, as a neighbor). Its shadow spans -90..-30 and hides (3, -2) at about -41.
    assert (3, -2) in visible_tiles((0, 0), 0, set(), half_angle=45)
    assert (3, -2) not in visible_tiles((0, 0), 0, {(1, -1)}, half_angle=45)


def test_touching_shadows_leave_no_gap():
    seen = visible_tiles((0, 0), 0, {(1, 0), (1, -1)})  # shadows -30..30 and -90..-30 meet at -30
    assert (2, -1) not in seen


def test_rotating_the_facing_rotates_the_visible_set():
    base = visible_tiles((0, 0), 0, {(2, 0)})
    rotated = visible_tiles((0, 0), 2, {rotate(rotate((2, 0)))})
    assert rotated == {rotate(rotate(t)) for t in base}


def test_out_of_bounds_tiles_are_never_returned():
    seen = visible_tiles((12, 0), 0, set())
    assert all(abs(q) <= 12 and abs(r) <= 12 and abs(q + r) <= 12 for q, r in seen)
    assert (13, 0) not in seen


def test_normalize_wraps_to_minus_180_exclusive():
    assert normalize(190.0) == -170.0
    assert normalize(-180.0) == 180.0
    assert normalize(180.0) == 180.0
