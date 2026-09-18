import numpy as np
import pytest

from hexaddr import CHO, KEN, RI, SHAKU, WIDTH_M
from terrain import (
    COUNTRY_AMPS, COUNTRY_WAVELENGTHS, DIRT, GRASS, MOUNTAIN_WAVELENGTHS, ROCK, SNOW, _field, forest_density,
    ground_height, ground_type, height, keeps, mountain_mask, octave_count,
)


@pytest.fixture(scope="module")
def points():
    rng = np.random.default_rng(4)
    return rng.uniform(-40000, 40000, 20000), rng.uniform(-40000, 40000, 20000)


def test_octave_counts_per_tier():
    assert octave_count(RI) == (2, 2)
    assert octave_count(CHO) == (7, 4)
    assert octave_count(KEN) == (13, 4)
    assert octave_count(SHAKU) == (16, 4)
    assert COUNTRY_WAVELENGTHS[-1] == pytest.approx(0.61, abs=0.01)
    assert all(keeps(w, SHAKU) for w in COUNTRY_WAVELENGTHS + MOUNTAIN_WAVELENGTHS)


def test_height_is_deterministic(points):
    x, z = points
    assert np.array_equal(height(x, z, KEN, 3), height(x, z, KEN, 3))
    assert not np.array_equal(height(x, z, KEN, 3), height(x, z, KEN, 4))


def test_coarse_tier_is_fine_tier_minus_dropped_octaves(points):
    x, z = points
    fine = height(x, z, SHAKU, 0)
    coarse = height(x, z, CHO, 0)
    dropped = sum(a * _field(x, z, w, 0, 1, k)
                  for k, (w, a) in enumerate(zip(COUNTRY_WAVELENGTHS, COUNTRY_AMPS)) if not keeps(w, CHO))
    assert np.allclose(fine - coarse, dropped)


def test_detail_amplitudes(points):
    x, z = points
    # what the ken tier adds over the cho tier: bumps under about a metre
    assert np.abs(height(x, z, KEN, 0) - height(x, z, CHO, 0)).max() < 3.0
    # what the shaku tier adds over the ken tier: centimetres
    assert np.abs(height(x, z, SHAKU, 0) - height(x, z, KEN, 0)).max() < 0.15


def test_rim_rises_above_the_country():
    a = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    rail = height(4 * WIDTH_M[RI] * np.cos(a), 4 * WIDTH_M[RI] * np.sin(a), CHO, 0)
    rim = height(11 * WIDTH_M[RI] * np.cos(a), 11 * WIDTH_M[RI] * np.sin(a), CHO, 0)
    assert np.abs(rail).max() < 60
    assert rim.mean() > 500
    assert mountain_mask(0.0, 0.0) == 0.0
    assert mountain_mask(12 * WIDTH_M[RI], 0.0) == 1.0


def test_ground_height_matches_the_shaku_tier():
    assert ground_height(123.4, -567.8, 2) == pytest.approx(float(height(123.4, -567.8, SHAKU, 2)))


def test_ground_type_rules():
    x = np.zeros(4)
    z = np.zeros(4)
    kinds = ground_type(x, z, np.array([1500.0, 950.0, 10.0, 10.0]), np.array([0.0, 0.0, 40.0, 0.0]), 0)
    assert list(kinds[:3]) == [SNOW, ROCK, ROCK]
    assert kinds[3] in (GRASS, DIRT)


def test_dirt_covers_about_thirty_percent(points):
    x, z = points
    kinds = ground_type(x, z, np.zeros_like(x), np.zeros_like(x), 0)
    assert 0.25 < (kinds == DIRT).mean() < 0.35


def test_forest_density_has_woods_and_clearings(points):
    x, z = points
    f = forest_density(x, z, 0)
    assert f.min() == 0.0 and f.max() == 1.0
    assert 0.25 < (f > 0).mean() < 0.6
