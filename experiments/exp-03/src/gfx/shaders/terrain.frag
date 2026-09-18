#version 330 core

#include "hex.glsl"

// A chunk draws exactly the pixels its parent owns (as its tier sees them), minus the pixels a
// finer tier draws, and outlines every cell border at the resolution of its own tier.

in vec3 v_rel;
in vec3 v_col;
out vec4 f_color;

uniform int u_level;        // the tier: level of this chunk's cells
uniform ivec2 u_parent;     // the chunk's parent cell (level u_level + 1)
uniform ivec2 u_lc[4];      // centre cell of each loaded-children texture (levels 1..3)
uniform usampler2D u_loaded1;
uniform usampler2D u_loaded2;
uniform usampler2D u_loaded3;
uniform vec3 u_eye;
uniform vec3 u_sun;
uniform vec3 u_fog_col;
uniform float u_fog_dist;
uniform int u_debug;        // 0 normal, 1 owner id at u_debug_level, 2 flat grey with lines
uniform int u_debug_level;
uniform ivec2 u_debug_base;

const vec3 LINE_COL[4] = vec3[4](vec3(0.08, 0.08, 0.06), vec3(0.95, 0.95, 0.88), vec3(1.0, 0.82, 0.15), vec3(0.9, 0.12, 0.08));
const float LINE_ALPHA[4] = float[4](0.45, 0.55, 0.85, 1.0);
const float LINE_HALF_PX[4] = float[4](0.5, 0.6, 1.0, 1.6);

// Has this level-L cell got its children loaded (so a finer tier draws there)?
bool children_loaded(int L, ivec2 cell) {
    ivec2 o = cell - u_lc[L] + ivec2(4);
    if (any(lessThan(o, ivec2(0))) || any(greaterThan(o, ivec2(8)))) {
        return false;
    }
    uint v;
    if (L == 1) {
        v = texelFetch(u_loaded1, o, 0).r;
    } else if (L == 2) {
        v = texelFetch(u_loaded2, o, 0).r;
    } else {
        v = texelFetch(u_loaded3, o, 0).r;
    }
    return v != 0u;
}

void main() {
    vec2 p = v_rel.xz;
    int c = u_level;

    // Nearest edge of this tier's cell. Derivatives are taken here, before any discard, while
    // every pixel of the 2x2 quad is still running.
    vec2 f = level_frac(p, c);
    ivec2 cr = hex_round(f);
    vec2 d = f - vec2(cr);
    vec2 dp = vec2(d.x + 0.5 * d.y, SQ3 * 0.5 * d.y);
    int bi = 0;
    float bp = -1.0;
    vec2 normal = vec2(1.0, 0.0);  // unit normal of the nearest edge, in world x/z
    for (int i = 0; i < 6; ++i) {
        vec2 u = vec2(float(DIRS[i].x) + 0.5 * float(DIRS[i].y), SQ3 * 0.5 * float(DIRS[i].y));
        float pr = dot(dp, u);
        if (pr > bp) {
            bp = pr;
            bi = i;
            normal = u;
        }
    }
    float cell_m = SCALE[c] * SHAKU_M;
    float edge_m = (0.5 - bp) * cell_m;
    vec3 dx = dFdx(v_rel);
    vec3 dy = dFdy(v_rel);
    // metres per pixel across the edge: the pixel footprint projected on the edge normal
    float edge_fw = max(abs(dot(dx.xz, normal)) + abs(dot(dy.xz, normal)), 1e-6);
    float px_mean = max(sqrt(length(dx.xz) * length(dy.xz)), 1e-6);

    if (c < 3) {
        if (owner(round_at(p, c), PACK[c + 1]) != u_parent) discard;
    } else if (hex_len(round_at(p, 3)) > WORLD_RADIUS) {
        discard;
    }
    if (c > 0 && children_loaded(c, owner(round_at(p, c - 1), PACK[c]))) discard;

    if (u_debug == 1) {
        ivec2 id = up(round_at(p, c), c, u_debug_level) - u_debug_base;
        f_color = vec4(float(id.x & 255) / 255.0, float(id.y & 255) / 255.0, float(c) / 3.0, 1.0);
        return;
    }

    // the highest level whose border this edge is
    ivec2 a = cr + u_k[c];
    ivec2 b = a + DIRS[bi];
    int top = c;
    for (int L = c; L < 3; ++L) {
        a = owner(a, PACK[L + 1]);
        b = owner(b, PACK[L + 1]);
        if (a != b) top = L + 1;
    }
    float line = 1.0 - smoothstep(LINE_HALF_PX[top] - 0.5, LINE_HALF_PX[top] + 0.5, edge_m / edge_fw);
    if (top == c) {
        line *= smoothstep(4.0, 10.0, cell_m / px_mean);  // fade a tier's own grid when its cells get tiny
    }
    // no border lines where the bordered cells are only a few pixels deep on screen
    line *= smoothstep(6.0, 16.0, SCALE[top] * SHAKU_M / edge_fw);
    line *= LINE_ALPHA[top];

    if (u_debug == 2) {
        f_color = vec4(mix(vec3(0.5), LINE_COL[top], line), 1.0);
        return;
    }

    vec3 n = normalize(cross(dx, dy));
    if (n.y < 0.0) n = -n;
    float light = 0.45 + 0.55 * max(dot(n, u_sun), 0.0);
    vec3 col = mix(v_col * light, LINE_COL[top], line);
    float fog = 1.0 - exp(-length(v_rel - u_eye) / u_fog_dist);
    f_color = vec4(mix(col, u_fog_col, fog), 1.0);
}
