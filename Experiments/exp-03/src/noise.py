"""Hashed-lattice gradient noise and integer hashing, vectorized with numpy.

Everything is a pure function of its inputs and a seed, so any chunk can be generated in any order.
"""

from functools import cache

import numpy as np

_M1 = np.uint64(0x9E3779B97F4A7C15)
_M2 = np.uint64(0xBF58476D1CE4E5B9)
_M3 = np.uint64(0x94D049BB133111EB)
_S30, _S27, _S31 = np.uint64(30), np.uint64(27), np.uint64(31)

# Eight unit gradients, evenly spaced.
_ANGLES = np.arange(8) * (np.pi / 4) + np.pi / 8
_GX = np.cos(_ANGLES)
_GY = np.sin(_ANGLES)


def _mix(h: np.ndarray) -> np.ndarray:
    h = (h ^ (h >> _S30)) * _M2
    h = (h ^ (h >> _S27)) * _M3
    return h ^ (h >> _S31)


def hash_ints(seed: int, *parts) -> np.ndarray:
    """A 64-bit hash of integer arrays (broadcast together) and a seed."""
    with np.errstate(over="ignore"):
        h = np.full(np.broadcast(*parts).shape, np.uint64(seed & 0xFFFFFFFFFFFFFFFF) * _M1, dtype=np.uint64)
        for p in parts:
            h = _mix(h ^ (np.asarray(p, dtype=np.int64).view(np.uint64) + _M1))
    return h


def hash01(seed: int, *parts) -> np.ndarray:
    """Uniform floats in [0, 1) from integer arrays and a seed."""
    return (hash_ints(seed, *parts) >> np.uint64(11)).astype(np.float64) * (1.0 / (1 << 53))


def gradient_noise(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """2D gradient noise with unit lattice spacing, roughly in [-1, 1], 0 on lattice points."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    fx0 = np.floor(x)
    fy0 = np.floor(y)
    ix = fx0.astype(np.int64)
    iy = fy0.astype(np.int64)
    fx = x - fx0
    fy = y - fy0

    with np.errstate(over="ignore"):
        s = np.uint64(seed & 0xFFFFFFFFFFFFFFFF) * _M1

    def corner(dx, dy):
        with np.errstate(over="ignore"):
            h = ((ix + dx).view(np.uint64) * _M2) ^ ((iy + dy).view(np.uint64) * _M3) ^ s
            g = (_mix(h) & np.uint64(7)).astype(np.intp)
        return _GX[g] * (fx - dx) + _GY[g] * (fy - dy)

    ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    uy = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    n00, n10 = corner(0, 0), corner(1, 0)
    n01, n11 = corner(0, 1), corner(1, 1)
    nx0 = n00 + ux * (n10 - n00)
    nx1 = n01 + ux * (n11 - n01)
    return (nx0 + uy * (nx1 - nx0)) * 1.41421356


@cache
def octave_offset(seed: int, k: int) -> tuple[float, float]:
    """A per-octave shift, so no two octaves share lattice points."""
    u = hash01(seed, k, 101)
    v = hash01(seed, k, 202)
    return float(u) * 1000.0, float(v) * 1000.0
