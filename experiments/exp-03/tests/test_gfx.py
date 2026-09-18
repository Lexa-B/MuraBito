"""The shader's hex maths against hexaddr: top-down orthographic renders of the real loaded world.

Debug mode 1 writes, per pixel, the tier that drew it and the low bytes of its cell id at a chosen
level; debug mode 2 draws flat grey with the border lines. Skipped when no GL context is available.
"""

import random

import numpy as np
import pytest

moderngl = pytest.importorskip("moderngl")

from chunkgen import generate_chunk  # noqa: E402
from gfx.matrices import ortho  # noqa: E402
from gfx.renderer import VIEW_SIZE, WINDOW_SIZE, Renderer, View  # noqa: E402
from hexaddr import (  # noqa: E402
    CHO, KEN, RI, SHAKU, SQRT3, WIDTH_M, axial_to_metres, centre_shaku, hex_round, in_world, metres_to_axial,
    round_at, shaku_at, tier_cell,
)
from loading import ChunkStore, Loader  # noqa: E402

FOCUS = (centre_shaku((4, 0), RI)[0] + 40, 17)  # near the rail start, not on any centre

# Chosen by scanning shaku points along the ri (-4,0)/(-5,0) boundary, at ken resolution, for ones
# whose loader's shaku window (its ken cell plus 3 rings) contains both a cho border that is not a
# ri border (top level 2) and a ri border (top level 3), then picking, among nearby candidates, the
# one with the cleanest classification (fewest anti-aliased edge pixels landing off-colour). Its q
# is negative, which exercises split_origin's floor on negatives.
FOCUS2 = (-59658, 2657)

# Straddles the world's outer rim: the shaku point nearest the midpoint between ri (12, 0), the
# outermost in-world ri in that direction (hex distance 12), and ri (13, 0), its out-of-world
# neighbour.
FOCUS_EDGE = shaku_at(*((axial_to_metres(12, 0, RI)[i] + axial_to_metres(13, 0, RI)[i]) / 2 for i in (0, 1)))

W, H = VIEW_SIZE


def _make_world(focus):
    try:
        ctx = moderngl.create_standalone_context(backend="egl", require=330)
    except Exception as exc:  # no EGL / GPU here
        pytest.skip(f"no GL context: {exc}")
    target = ctx.framebuffer(color_attachments=[ctx.renderbuffer(WINDOW_SIZE)],
                             depth_attachment=ctx.depth_renderbuffer(WINDOW_SIZE))
    renderer = Renderer(ctx, target)
    store = ChunkStore(lambda level, parent: generate_chunk(level, parent, 0), renderer.load_chunk,
                       renderer.unload_chunk)
    store.drain([Loader("camera", focus)])
    return ctx, renderer, set(store.loaded)


@pytest.fixture(scope="module")
def world():
    ctx, renderer, loaded = _make_world(FOCUS)
    yield renderer, loaded
    ctx.release()


@pytest.fixture(scope="module")
def world2():
    """A second loader focus, near a ri corner, so cho and ri borders are both in view."""
    ctx, renderer, loaded = _make_world(FOCUS2)
    yield renderer, loaded
    ctx.release()


def top_down(renderer, half_height_m, mode, level=SHAKU, base=(0, 0), focus=FOCUS):
    ox, oz = axial_to_metres(*focus)
    aspect = W / H
    proj = ortho(-half_height_m * aspect, half_height_m * aspect, -half_height_m, half_height_m, 1.0, 20000.0)
    renderer.debug, renderer.debug_level, renderer.debug_base = mode, level, base
    renderer.draw(View(origin=focus, eye=(ox, 5000.0, oz), target=(ox, 0.0, oz), up=(0.0, 0.0, -1.0),
                       projection=proj), draw_panel=False)
    renderer.debug = 0
    return renderer.read_rgb((0, 0, W, H))


def pixel_to_world(i, j, half_height_m, focus=FOCUS):
    """Centre of pixel column i, row j (top row first) in world metres."""
    ox, oz = axial_to_metres(*focus)
    aspect = W / H
    x = -half_height_m * aspect + (i + 0.5) * 2 * half_height_m * aspect / W
    view_y = half_height_m - (j + 0.5) * 2 * half_height_m / H
    return ox + x, oz - view_y  # screen up is world -z


def world_to_pixel(x, z, half_height_m, focus=FOCUS):
    ox, oz = axial_to_metres(*focus)
    aspect = W / H
    i = (x - ox + half_height_m * aspect) / (2 * half_height_m * aspect) * W - 0.5
    j = (half_height_m - (oz - z)) / (2 * half_height_m) * H - 0.5
    return int(round(i)), int(round(j))


def expected_tier(x, z, loaded):
    for t in (SHAKU, KEN, CHO):
        if (t, tier_cell(x, z, t, t + 1)) in loaded:
            return t
    return RI


def classify(x, z, loaded, level):
    t = expected_tier(x, z, loaded)
    return t, tier_cell(x, z, t, max(level, t))


def stable(x, z, loaded, level, px_m):
    """The classification, if it is the same across the pixel's footprint; else None."""
    c = classify(x, z, loaded, level)
    for dx, dz in ((0.45, 0), (-0.45, 0), (0, 0.45), (0, -0.45)):
        if classify(x + dx * px_m, z + dz * px_m, loaded, level) != c:
            return None
    return c


@pytest.mark.parametrize("half_height_m, level", [(8.0, KEN), (8.0, CHO), (400.0, CHO), (400.0, RI)])
def test_shader_tiers_and_owners_match_hexaddr(world, half_height_m, level):
    renderer, loaded = world
    base = (0, 0)
    img = top_down(renderer, half_height_m, 1, level, base)
    px_m = 2 * half_height_m / H
    rng = random.Random(level * 1000 + int(half_height_m))
    checked = 0
    mismatches = 0
    tiers_seen = set()
    for _ in range(1500):
        i, j = rng.randrange(W), rng.randrange(H)
        x, z = pixel_to_world(i, j, half_height_m)
        c = stable(x, z, loaded, level, px_m)
        if c is None:
            continue
        tier, cell = c
        r, g, b = (int(v) for v in img[j, i])
        got_tier = round(b / 255 * 3)
        want = ((cell[0] - base[0]) & 255, (cell[1] - base[1]) & 255)
        checked += 1
        tiers_seen.add(tier)
        if got_tier != tier or (r, g) != want:
            mismatches += 1
    assert checked > 1000
    assert mismatches <= checked * 0.002
    assert len(tiers_seen) >= 2  # each view straddles a tier handover


def edge_distance_px(x, z, tier, px_m):
    fq, fr = metres_to_axial(x, z, tier)
    c = hex_round(fq, fr)
    dq, dr = fq - c[0], fr - c[1]
    dx, dy = dq + dr / 2, dr * SQRT3 / 2
    dirs = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
    best = max(dx * (q + r / 2) + dy * (r * SQRT3 / 2) for q, r in dirs)
    return (0.5 - best) * WIDTH_M[tier] / px_m


def test_flat_grey_away_from_every_edge(world):
    renderer, loaded = world
    half = 4.0
    img = top_down(renderer, half, 2)
    px_m = 2 * half / H
    rng = random.Random(5)
    checked = 0
    for _ in range(3000):
        i, j = rng.randrange(W), rng.randrange(H)
        x, z = pixel_to_world(i, j, half)
        tier = expected_tier(x, z, loaded)
        if tier != SHAKU or edge_distance_px(x, z, SHAKU, px_m) < 3:
            continue
        checked += 1
        assert tuple(img[j, i]) == pytest.approx((127, 127, 127), abs=2)
    assert checked > 500


def border_points(loaded, level, count, rng, half, focus=FOCUS):
    """Midpoints of shaku edges inside the shaku window where the owners at `level` differ."""
    ox, oz = axial_to_metres(*focus)
    found = []
    tries = 0
    while len(found) < count and tries < 200000:
        tries += 1
        x = ox + rng.uniform(-half, half)
        z = oz + rng.uniform(-half * 0.9, half * 0.9)
        s = hex_round(*metres_to_axial(x, z))
        d = rng.choice(((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)))
        n = (s[0] + d[0], s[1] + d[1])
        (ax, az), (bx, bz) = axial_to_metres(*s), axial_to_metres(*n)
        mx, mz = (ax + bx) / 2, (az + bz) / 2
        if expected_tier(mx, mz, loaded) != SHAKU:
            continue
        top = max(L for L in (SHAKU, KEN, CHO, RI)
                  if L == SHAKU or tier_cell(ax, az, SHAKU, L) != tier_cell(bx, bz, SHAKU, L))
        if top == level:
            found.append((mx, mz))
    return found


@pytest.mark.parametrize("level, check", [
    (SHAKU, lambda rgb: max(rgb) < 100),                    # dark shaku lines
    (KEN, lambda rgb: min(rgb) > 160),                      # light ken borders
])
def test_border_pixels_carry_their_levels_colour(world, level, check):
    renderer, loaded = world
    half = 3.0
    img = top_down(renderer, half, 2)
    points = border_points(loaded, level, 60, random.Random(level), half)
    assert len(points) >= 30
    good = 0
    for x, z in points:
        i, j = world_to_pixel(x, z, half)
        if 0 <= i < W and 0 <= j < H and check(tuple(int(v) for v in img[j, i])):
            good += 1
    assert good >= 0.9 * len(points)


def test_parent_pixels_are_discarded_where_children_are_loaded(world):
    renderer, loaded = world
    # with every child chunk hidden from the lookup, the coarse tiers draw everywhere they own
    img_all = top_down(renderer, 400.0, 1, CHO)
    saved = dict(renderer.chunks)
    try:
        for key in [k for k in renderer.chunks if k[0] == SHAKU]:
            del renderer.chunks[key]
        img = top_down(renderer, 400.0, 1, CHO)
    finally:
        renderer.chunks.update(saved)
    tier_all = np.rint(img_all[:, :, 2] / 255 * 3)
    tier = np.rint(img[:, :, 2] / 255 * 3)
    # where the shaku tier drew, the ken tier now draws instead; nothing is left empty
    assert (tier_all == SHAKU).sum() > 0
    assert ((tier_all == SHAKU) & (tier != KEN)).sum() <= 0.01 * (tier_all == SHAKU).sum()
    assert (tier == SHAKU).sum() == 0


def test_no_terrain_beyond_the_world_edge(world):
    """An orthographic top-down view straddling the world's rim (radius 12 ri): terrain draws
    where hexaddr says the point is in the world, and nothing (bare sky) where it is not."""
    renderer, _ = world
    half = 1200.0
    aspect = W / H
    ox, oz = axial_to_metres(*FOCUS_EDGE)
    proj = ortho(-half * aspect, half * aspect, -half, half, 1.0, 40000.0)
    renderer.draw(View(origin=FOCUS_EDGE, eye=(ox, 20000.0, oz), target=(ox, 0.0, oz), up=(0.0, 0.0, -1.0),
                       projection=proj), draw_panel=False)
    img = renderer.read_rgb((0, 0, W, H))

    rng = random.Random(7)
    sky = None
    inside_checked = outside_checked = 0
    outside_mismatches = 0
    inside_matches_sky = 0
    for _ in range(4000):
        i, j = rng.randrange(W), rng.randrange(H)
        x, z = pixel_to_world(i, j, half, focus=FOCUS_EDGE)
        rgb = tuple(int(v) for v in img[j, i])
        if in_world(round_at(x, z, RI)):
            inside_checked += 1
            if sky is not None and sum(abs(a - b) for a, b in zip(rgb, sky)) < 30:
                inside_matches_sky += 1
        else:
            outside_checked += 1
            if sky is None:
                sky = rgb
            elif rgb != sky:
                outside_mismatches += 1

    assert inside_checked > 500 and outside_checked > 500
    assert outside_mismatches == 0  # nothing is drawn past the rim: bare sky, uniformly
    assert inside_matches_sky <= 0.02 * inside_checked  # terrain is drawn just inside it


# world2 opens a second GL context; keep its tests last so no test after it touches `world`'s
# renderer (a standalone context's handles are only valid while it is the current context).
@pytest.mark.parametrize("level, check", [
    (CHO, lambda rgb: rgb[0] > rgb[1] > rgb[2] and rgb[0] > 200 and rgb[2] < 100),   # yellow
    (RI, lambda rgb: rgb[0] > 200 and rgb[1] < 100 and rgb[2] < 100),                # red
])
def test_cho_and_ri_border_pixels_carry_their_levels_colour(world2, level, check):
    renderer, loaded = world2
    half = 6.0
    img = top_down(renderer, half, 2, focus=FOCUS2)
    points = border_points(loaded, level, 60, random.Random(level), half, focus=FOCUS2)
    assert len(points) >= 30
    good = 0
    for x, z in points:
        i, j = world_to_pixel(x, z, half, focus=FOCUS2)
        if 0 <= i < W and 0 <= j < H and check(tuple(int(v) for v in img[j, i])):
            good += 1
    assert good >= 0.9 * len(points)
