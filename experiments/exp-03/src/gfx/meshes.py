"""Low-poly prop meshes, in metres, as flat-shaded triangle lists: (N, 9) float32 rows of
position, face normal and colour. The base sits slightly below y = 0 so props never float."""

import math

import numpy as np

from chunkgen import PEBBLE, ROCK_PROP, TREE, TUFT

TRUNK = (0.40, 0.28, 0.17)
LEAVES = (0.17, 0.36, 0.16)
STONE = (0.55, 0.54, 0.51)
BLADE = (0.42, 0.62, 0.28)


def _faces(tris, colour) -> np.ndarray:
    rows = []
    for a, b, c in tris:
        a, b, c = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n) or 1.0
        rows += [(*p, *n, *colour) for p in (a, b, c)]
    return np.array(rows, dtype=np.float32)


def _ring(radius, y, sides=6, turn=0.0):
    return [(radius * math.cos(2 * math.pi * i / sides + turn), y, radius * math.sin(2 * math.pi * i / sides + turn))
            for i in range(sides)]


def _cone(radius, y0, y1, sides=6, turn=0.0):
    ring = _ring(radius, y0, sides, turn)
    tip = (0.0, y1, 0.0)
    return [(ring[i], tip, ring[(i + 1) % sides]) for i in range(sides)]


def tree() -> np.ndarray:
    lo, hi = _ring(0.18, -0.2), _ring(0.14, 2.0)
    trunk = []
    for i in range(6):
        j = (i + 1) % 6
        trunk += [(lo[i], hi[i], lo[j]), (lo[j], hi[i], hi[j])]
    leaves = _cone(1.7, 1.5, 5.2, 7) + _cone(1.2, 3.6, 7.2, 7, 0.4)
    return np.concatenate([_faces(trunk, TRUNK), _faces(leaves, LEAVES)])


def _icosahedron():
    t = (1 + math.sqrt(5)) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
         (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
         (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = np.array(v, dtype=float)
    return v / np.linalg.norm(v[0]), f


def rock(radius=0.6, squash=0.6, colour=STONE) -> np.ndarray:
    v, f = _icosahedron()
    jitter = 1 + 0.18 * np.sin(np.arange(len(v)) * 2.39996)  # fixed, so every rock mesh is the same
    v = v * jitter[:, None] * radius
    v[:, 1] = v[:, 1] * squash + radius * squash * 0.55
    return _faces([(v[a], v[b], v[c]) for a, b, c in f], colour)


def tuft() -> np.ndarray:
    tris = []
    for k in range(3):
        a = math.pi * k / 3
        dx, dz = 0.04 * math.cos(a), 0.04 * math.sin(a)
        p0, p1 = (-dx, -0.01, -dz), (dx, -0.01, dz)
        top = (0.01 * math.sin(a), 0.14, 0.01 * math.cos(a))
        tris += [(p0, top, p1), (p1, top, p0)]
    return _faces(tris, BLADE)


def pebble() -> np.ndarray:
    return rock(radius=0.05, squash=0.5)


MESHES = {TREE: tree, ROCK_PROP: rock, TUFT: tuft, PEBBLE: pebble}
