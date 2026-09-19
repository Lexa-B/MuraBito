import math
import random

import pytest

from hexaddr import (
    CHO, KEN, PACKING, RI, SCALE, SHAKU, SHAKU_M, WIDTH_M, address, axial_to_metres, centre_child,
    centre_shaku, child_offsets, children, d2, format_address, from_address, hex_round, in_world,
    local, metres_to_axial, owner, parent, round_at, shaku_at, tier_cell, up, window, world_ri,
)


def brute_owner(cell, n):
    """Nearest parent centre by exact integer distance, ties to the greatest (a, b), searched wide."""
    q, r = cell
    best = None
    for a in range(round(q / n) - 3, round(q / n) + 4):
        for b in range(round(r / n) - 3, round(r / n) + 4):
            key = (d2(q - n * a, r - n * b), -a, -b)
            if best is None or key < best[0]:
                best = (key, (a, b))
    return best[1]


def test_unit_lengths():
    assert SHAKU_M == pytest.approx(0.30303, abs=1e-5)
    assert WIDTH_M[KEN] == pytest.approx(6 * SHAKU_M)
    assert WIDTH_M[CHO] == pytest.approx(360 * SHAKU_M)
    assert WIDTH_M[RI] == pytest.approx(3927.27, abs=0.01)
    assert SCALE == (1, 6, 360, 12960)


@pytest.mark.parametrize("n", [6, 60, 36])
def test_owner_matches_brute_force(n):
    rng = random.Random(n)
    for _ in range(3000):
        cell = (rng.randint(-5 * n, 5 * n), rng.randint(-5 * n, 5 * n))
        assert owner(cell, n) == brute_owner(cell, n)


@pytest.mark.parametrize("level, expected", [(KEN, 36), (CHO, 3600), (RI, 1296)])
def test_every_parent_owns_exactly_n_squared(level, expected):
    assert len(child_offsets(level)) == expected
    n = PACKING[level]
    for p in [(0, 0), (1, 0), (-2, 3), (5, -7)]:
        for c in children(p, level):
            assert owner(c, n) == p


@pytest.mark.parametrize("level", [KEN, CHO, RI])
def test_split_children_have_one_owner_by_the_tie_rule(level):
    n = PACKING[level]
    offsets = set(child_offsets(level))
    # the six edge-midpoint children: (n/2) along each neighbour direction
    halved = [(n // 2, 0), (-n // 2, 0), (0, n // 2), (0, -n // 2), (n // 2, -n // 2), (-n // 2, n // 2)]
    owned_halved = [h for h in halved if h in offsets]
    assert len(owned_halved) == 3
    # the six corners: n/3 along each diagonal
    k = n // 3
    corners = [(k, k), (-k, -k), (2 * k, -k), (-2 * k, k), (k, -2 * k), (-k, 2 * k)]
    assert len([c for c in corners if c in offsets]) == 2
    # the owner of a split child is the greatest tied candidate
    for h in halved:
        assert owner(h, n) == brute_owner(h, n)


def test_children_tile_the_plane_without_overlap():
    seen = {}
    for p in window((0, 0), 2):
        for c in children(p, KEN):
            assert c not in seen
            seen[c] = p
    # every shaku near the middle is covered
    for q in range(-6, 7):
        for r in range(-6, 7):
            assert (q, r) in seen


def test_centres_nest():
    assert centre_child((2, -1), KEN) == (12, -6)
    assert centre_shaku((2, -1), CHO) == (720, -360)
    assert up(centre_shaku((3, -2), RI), SHAKU, RI) == (3, -2)
    assert up(centre_shaku((7, 4), CHO), SHAKU, CHO) == (7, 4)


def test_address_round_trip():
    rng = random.Random(1)
    for _ in range(2000):
        s = (rng.randint(-150000, 150000), rng.randint(-150000, 150000))
        addr = address(s)
        assert from_address(addr) == s
        ri, cho, ken, sh = addr
        assert sh in child_offsets(KEN)
        assert ken in child_offsets(CHO)
        assert cho in child_offsets(RI)
        assert up(s, SHAKU, RI) == ri


def test_address_of_the_world_centre():
    assert address((0, 0)) == ((0, 0), (0, 0), (0, 0), (0, 0))
    assert format_address(address((0, 0))) == "ri (0,0) / cho (0,0) / ken (0,0) / shaku (0,0)"


def test_local_offset():
    # shaku (13, -6) belongs to ken (2, -1), centred on shaku (12, -6)
    assert parent((13, -6), SHAKU) == (2, -1)
    assert local((13, -6), SHAKU) == (1, 0)
    # ken (61, 2) belongs to cho (1, 0), centred on ken (60, 0)
    assert local((61, 2), KEN) == (1, 2)


def test_neighbouring_addresses_across_borders():
    # walking east along r = 0 crosses ken, cho and ri borders; each step moves one shaku
    prev = address((0, 0))
    crossings = {"ken": 0, "cho": 0, "ri": 0}
    for q in range(1, 13000):
        cur = address((q, 0))
        assert from_address(cur) == (q, 0)
        if cur[0] != prev[0]:
            crossings["ri"] += 1
        if up((q, 0), SHAKU, CHO) != up((q - 1, 0), SHAKU, CHO):
            crossings["cho"] += 1
        if up((q, 0), SHAKU, KEN) != up((q - 1, 0), SHAKU, KEN):
            crossings["ken"] += 1
        prev = cur
    # a straight line along a neighbour axis crosses a ken every 6 shaku, a cho every 360, a ri every 12960
    assert crossings["ken"] == pytest.approx(13000 / 6, abs=2)
    assert crossings["cho"] == pytest.approx(13000 / 360, abs=2)
    assert crossings["ri"] == 1


def test_metres_round_trip_and_rounding():
    x, z = axial_to_metres(5, -3)
    q, r = metres_to_axial(x, z)
    assert (q, r) == (pytest.approx(5), pytest.approx(-3))
    assert shaku_at(x + 0.1 * SHAKU_M, z) == (5, -3)
    assert axial_to_metres(1, 0, RI) == (pytest.approx(WIDTH_M[RI]), 0.0)
    assert hex_round(0.4, 0.4) == (0, 1)
    assert hex_round(-0.2, 0.9) == (0, 1)
    assert round_at(*axial_to_metres(2, 3, CHO), CHO) == (2, 3)


def test_neighbour_spacing_is_one_width():
    x0, z0 = axial_to_metres(0, 0, KEN)
    for d in [(1, 0), (0, 1), (-1, 1)]:
        x, z = axial_to_metres(*d, KEN)
        assert math.hypot(x - x0, z - z0) == pytest.approx(WIDTH_M[KEN])


def test_tier_cell_agrees_with_address_at_shaku_tier():
    rng = random.Random(2)
    for _ in range(500):
        s = (rng.randint(-5000, 5000), rng.randint(-5000, 5000))
        x, z = axial_to_metres(*s)
        assert tier_cell(x, z, SHAKU, CHO) == up(s, SHAKU, CHO)
        assert tier_cell(x, z, KEN, KEN) == round_at(x, z, KEN)


def test_world_and_windows():
    assert len(world_ri()) == 469
    assert all(in_world(ri) for ri in world_ri())
    assert not in_world((13, 0))
    w = window((4, -1))
    assert len(w) == 37 and (4, -1) in w and (7, -1) in w and (8, -1) not in w
