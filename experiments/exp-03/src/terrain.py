"""The procedural world: height, ground type and props, per tier. Placeholder numbers throughout.

A tier is named by the cell size it draws (SHAKU..RI) and keeps only the noise octaves whose
wavelength is at least twice its cell spacing, so a coarse sample is the fine terrain minus the
detail it cannot show.
"""

import numpy as np

from hexaddr import RI, SHAKU, WIDTH_M
from noise import gradient_noise, hash01, octave_offset

# Country: 16 octaves, 20 km down to 0.61 m.
COUNTRY_WAVELENGTHS = tuple(20000.0 / 2**k for k in range(16))
COUNTRY_AMPS = (25.0, 20.0, 15.0, 10.0, 6.0, 3.5, 2.0, 1.0, 0.5, 0.3, 0.2, 0.12, 0.08, 0.04, 0.025, 0.015)
# Rim mountains: ridged noise, 20 km down to 2.5 km, masked by distance from the centre.
MOUNTAIN_WAVELENGTHS = (20000.0, 10000.0, 5000.0, 2500.0)
MOUNTAIN_AMPS = (700.0, 450.0, 250.0, 100.0)
MOUNTAIN_INNER_M = 6 * WIDTH_M[RI]
MOUNTAIN_OUTER_M = 11 * WIDTH_M[RI]

GRASS, DIRT, ROCK, SNOW = 0, 1, 2, 3
GROUND_NAMES = ("grass", "dirt", "rock", "snow")
GROUND_COLOURS = np.array([
    (0.36, 0.55, 0.25),
    (0.52, 0.40, 0.26),
    (0.48, 0.47, 0.45),
    (0.92, 0.94, 0.96),
])
SNOW_LINE_M = 1200.0
ROCK_LINE_M = 900.0
ROCK_SLOPE_DEG = 35.0
DIRT_WAVELENGTH_M = 300.0
DIRT_THRESHOLD = -0.17          # about 30% of the dirt field lies below this
FOREST_WAVELENGTH_M = 800.0

# Salts keep the separate noise fields independent.
_COUNTRY, _MOUNTAIN, _SNOW, _DIRT, _FOREST, _SHADE = 1, 2, 3, 4, 5, 6


def keeps(wavelength: float, tier: int) -> bool:
    return wavelength >= 2 * WIDTH_M[tier]


def octave_count(tier: int) -> tuple[int, int]:
    """(country octaves, mountain octaves) kept at a tier."""
    return (sum(keeps(w, tier) for w in COUNTRY_WAVELENGTHS), sum(keeps(w, tier) for w in MOUNTAIN_WAVELENGTHS))


def _field(x, z, wavelength, seed, salt, k=0):
    ox, oz = octave_offset(seed * 16 + salt, k)
    return gradient_noise(x / wavelength + ox, z / wavelength + oz, seed * 64 + salt * 16 + k)


def mountain_mask(x, z):
    d = np.hypot(x, z)
    t = np.clip((d - MOUNTAIN_INNER_M) / (MOUNTAIN_OUTER_M - MOUNTAIN_INNER_M), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def height(x, z, tier: int, seed: int) -> np.ndarray:
    """Terrain height in metres at world points, with the octaves a tier keeps."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    h = np.zeros(np.broadcast(x, z).shape)
    for k, (w, a) in enumerate(zip(COUNTRY_WAVELENGTHS, COUNTRY_AMPS)):
        if keeps(w, tier):
            h += a * _field(x, z, w, seed, _COUNTRY, k)
    ridges = np.zeros_like(h)
    for k, (w, a) in enumerate(zip(MOUNTAIN_WAVELENGTHS, MOUNTAIN_AMPS)):
        if keeps(w, tier):
            n = 1.0 - np.abs(_field(x, z, w, seed, _MOUNTAIN, k))
            ridges += a * n * n
    return h + mountain_mask(x, z) * ridges


def ground_height(x: float, z: float, seed: int) -> float:
    """Full-detail height at one point."""
    return float(height(np.array([x]), np.array([z]), SHAKU, seed)[0])


def ground_type(x, z, h, slope_deg, seed: int) -> np.ndarray:
    snow_line = SNOW_LINE_M + 80.0 * _field(x, z, 2000.0, seed, _SNOW)
    dirt = _field(x, z, DIRT_WAVELENGTH_M, seed, _DIRT) < DIRT_THRESHOLD
    kind = np.where(dirt, DIRT, GRASS)
    kind = np.where((slope_deg > ROCK_SLOPE_DEG) | (h > ROCK_LINE_M), ROCK, kind)
    return np.where(h > snow_line, SNOW, kind)


def ground_colour(x, z, kind, tier: int, seed: int) -> np.ndarray:
    shade_wavelength = max(7.0, 4 * WIDTH_M[tier])
    shade = 1.0 + 0.08 * _field(x, z, shade_wavelength, seed, _SHADE)
    return GROUND_COLOURS[kind] * shade[..., None]


def forest_density(x, z, seed: int) -> np.ndarray:
    """0 in clearings, up to 1 in the thick of the woods."""
    return np.clip(_field(x, z, FOREST_WAVELENGTH_M, seed, _FOREST) * 1.8 - 0.1, 0.0, 1.0)


def prop_roll(seed: int, q, r, salt: int) -> np.ndarray:
    return hash01(seed, q, r, salt)
