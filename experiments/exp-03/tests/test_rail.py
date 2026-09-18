import math

import pytest

from hexaddr import RI, WIDTH_M, axial_to_metres
from rail import (
    EYE_BACK_M, EYE_MIN_CLEARANCE_M, FOV_Y_DEG, RAIL_RADIUS_M, SPEED_M_S, Rail, focus_xz, heading, lap_seconds,
)
from terrain import ground_height


def test_radius_speed_and_lap():
    assert RAIL_RADIUS_M == pytest.approx(4 * WIDTH_M[RI])
    assert SPEED_M_S == 2.5
    assert lap_seconds() == pytest.approx(2 * math.pi * RAIL_RADIUS_M / 2.5)
    for t in (0.0, 1000.0, 20000.0):
        x, z = focus_xz(t)
        assert math.hypot(x, z) == pytest.approx(RAIL_RADIUS_M)
    x0, z0 = focus_xz(100.0)
    x1, z1 = focus_xz(101.0)
    assert math.hypot(x1 - x0, z1 - z0) == pytest.approx(2.5, rel=1e-6)


def test_anticlockwise_from_due_east():
    assert focus_xz(0.0) == (pytest.approx(RAIL_RADIUS_M), pytest.approx(0.0))
    x, z = focus_xz(1000.0)
    assert z > 0  # heading north first, i.e. anticlockwise seen from above (x east, z north)
    assert heading(0.0) == (pytest.approx(0.0), pytest.approx(1.0))


def test_start_offsets_the_rail():
    a = Rail(lambda x, z: 0.0, start=500.0)
    b = Rail(lambda x, z: 0.0)
    for _ in range(500):
        b.advance(1.0)
    assert a.focus == pytest.approx(b.focus)


def test_focus_shaku_is_where_the_focus_is():
    rail = Rail(lambda x, z: 0.0, start=123.0)
    x, _, z = rail.focus
    sx, sz = axial_to_metres(*rail.focus_shaku)
    assert math.hypot(sx - x, sz - z) < WIDTH_M[0]


def test_eye_trails_and_clears_the_ground():
    ground = lambda x, z: ground_height(x, z, 0)  # noqa: E731
    rail = Rail(ground, start=0.0)
    for _ in range(600):
        rail.advance(1 / 30)
        ex, ey, ez = rail.eye
        fx, fy, fz = rail.focus
        assert math.hypot(ex - fx, ez - fz) == pytest.approx(EYE_BACK_M)
        assert ey >= ground(ex, ez) + EYE_MIN_CLEARANCE_M - 1e-9


def test_horizon_stays_in_view():
    rail = Rail(lambda x, z: ground_height(x, z, 0), start=0.0)
    for _ in range(300):
        rail.advance(0.2)
        ex, ey, ez = rail.eye
        fx, fy, fz = rail.focus
        pitch = math.degrees(math.atan2(ey - fy, math.hypot(fx - ex, fz - ez)))
        assert 0 < pitch < FOV_Y_DEG / 2  # looking down, with the horizon still above the bottom edge


def test_lap_fraction():
    rail = Rail(lambda x, z: 0.0, start=lap_seconds() * 1.25)
    assert rail.lap_fraction == pytest.approx(0.25)
