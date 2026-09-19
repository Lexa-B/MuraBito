import numpy as np

from noise import gradient_noise, hash01, hash_ints, octave_offset


def test_hash_is_deterministic_and_seed_dependent():
    q = np.arange(-50, 50)
    assert np.array_equal(hash_ints(7, q, 3), hash_ints(7, q, 3))
    assert not np.array_equal(hash_ints(7, q, 3), hash_ints(8, q, 3))
    assert not np.array_equal(hash_ints(7, q, 3), hash_ints(7, q, 4))


def test_hash01_is_uniform_in_unit_interval():
    u = hash01(1, np.arange(200000), 5)
    assert u.min() >= 0.0 and u.max() < 1.0
    assert abs(u.mean() - 0.5) < 0.005
    hist, _ = np.histogram(u, bins=10, range=(0, 1))
    assert hist.min() > 19000


def test_gradient_noise_range_and_lattice_zeros():
    rng = np.random.default_rng(0)
    x = rng.uniform(-1000, 1000, 100000)
    y = rng.uniform(-1000, 1000, 100000)
    n = gradient_noise(x, y, 3)
    assert -1.0 <= n.min() and n.max() <= 1.0
    assert 0.25 < n.std() < 0.35
    assert abs(n.mean()) < 0.01
    ints = np.arange(-20, 20, dtype=float)
    assert np.allclose(gradient_noise(ints, ints, 3), 0.0)


def test_gradient_noise_is_continuous():
    x = np.linspace(0, 10, 100001)
    n = gradient_noise(x, np.full_like(x, 0.37), 9)
    assert np.abs(np.diff(n)).max() < 0.001


def test_gradient_noise_is_deterministic_and_order_free():
    x = np.array([3.2, -7.9, 100.5])
    y = np.array([0.1, 4.4, -2.2])
    a = gradient_noise(x, y, 11)
    b = gradient_noise(x[::-1], y[::-1], 11)[::-1]
    assert np.array_equal(a, b)
    assert gradient_noise(x[1], y[1], 11) == a[1]


def test_octave_offsets_differ():
    assert octave_offset(1, 0) != octave_offset(1, 1)
    assert octave_offset(1, 0) == octave_offset(1, 0)
