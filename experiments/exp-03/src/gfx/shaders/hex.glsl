// Hex addressing in the shader: the same integer maths as hexaddr.py.
// Positions are metres relative to the origin shaku O (the loader focus). For each level L the
// origin is split as O = SCALE[L] * u_k[L] + u_m[L], so rounding stays in small numbers.

const int PACK[4] = int[4](1, 6, 60, 36);
const float SCALE[4] = float[4](1.0, 6.0, 360.0, 12960.0);
const float SHAKU_M = 10.0 / 33.0;
const float SQ3 = 1.7320508075688772;
const ivec2 DIRS[6] = ivec2[6](ivec2(1, 0), ivec2(1, -1), ivec2(0, -1), ivec2(-1, 0), ivec2(-1, 1), ivec2(0, 1));
const int WORLD_RADIUS = 12;

uniform ivec2 u_k[4];
uniform ivec2 u_m[4];

vec2 shaku_axial(vec2 xz) {
    float r = xz.y / (SQ3 * 0.5 * SHAKU_M);
    return vec2(xz.x / SHAKU_M - r * 0.5, r);
}

ivec2 hex_round(vec2 f) {
    float fs = -f.x - f.y;
    float q = floor(f.x + 0.5);
    float r = floor(f.y + 0.5);
    float s = floor(fs + 0.5);
    float dq = abs(q - f.x);
    float dr = abs(r - f.y);
    float ds = abs(s - fs);
    if (dq > dr && dq > ds) {
        q = -r - s;
    } else if (dr > ds) {
        r = -q - s;
    }
    return ivec2(int(q), int(r));
}

// Fractional axial position at level L, relative to the level-L cell u_k[L].
vec2 level_frac(vec2 xz, int L) {
    return (vec2(u_m[L]) + shaku_axial(xz)) / SCALE[L];
}

ivec2 round_at(vec2 xz, int L) {
    return hex_round(level_frac(xz, L)) + u_k[L];
}

int d2(ivec2 d) {
    return d.x * d.x + d.x * d.y + d.y * d.y;
}

// The parent (on the lattice scaled by n) that owns a child: nearest centre, ties to the
// lexicographically greatest parent.
ivec2 owner(ivec2 c, int n) {
    ivec2 a0 = ivec2(floor(vec2(c) / float(n) + 0.5));
    ivec2 best = a0;
    int best_d = 2147483647;
    for (int i = -1; i <= 1; ++i) {
        for (int j = -1; j <= 1; ++j) {
            ivec2 a = a0 + ivec2(i, j);
            int d = d2(c - n * a);
            if (d < best_d || (d == best_d && (a.x > best.x || (a.x == best.x && a.y > best.y)))) {
                best = a;
                best_d = d;
            }
        }
    }
    return best;
}

ivec2 up(ivec2 c, int from_level, int to_level) {
    for (int L = from_level; L < to_level; ++L) {
        c = owner(c, PACK[L + 1]);
    }
    return c;
}

int hex_len(ivec2 c) {
    return (abs(c.x) + abs(c.y) + abs(c.x + c.y)) / 2;
}
