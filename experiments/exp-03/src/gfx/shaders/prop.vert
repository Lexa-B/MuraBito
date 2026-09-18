#version 330 core

// Instanced props. A prop stands on whichever ground is drawn under it: the shaku tier if its ken
// has shaku loaded (or it is a shaku detail), else the ken tier; each blends like the terrain.

in vec3 in_vert;
in vec3 in_normal;
in vec3 in_vcol;
in vec4 i_a;    // x, z (relative to the chunk parent centre), h_full, h_mid
in vec4 i_b;    // h_far, scale, yaw, tint
in vec2 i_cell; // the prop's ken

uniform mat4 u_viewproj;
uniform vec2 u_offset;
uniform vec2 u_morph_fine;   // the shaku tier's morph range
uniform vec2 u_morph_mid;    // the ken tier's morph range
uniform int u_detail;        // 1: a shaku detail (always on the shaku tier)
uniform usampler2D u_loaded1;
uniform ivec2 u_lc1;

out vec3 v_rel;
out vec3 v_n;
out vec3 v_col;

float morph(vec2 range, float d) {
    return range.y > range.x ? smoothstep(range.x, range.y, d) : 0.0;
}

bool shaku_loaded(ivec2 ken) {
    ivec2 o = ken - u_lc1 + ivec2(4);
    if (any(lessThan(o, ivec2(0))) || any(greaterThan(o, ivec2(8)))) {
        return false;
    }
    return texelFetch(u_loaded1, o, 0).r != 0u;
}

void main() {
    vec2 xz = i_a.xy + u_offset;
    float d = length(xz);
    float ground;
    if (u_detail == 1 || shaku_loaded(ivec2(round(i_cell)))) {
        ground = mix(i_a.z, i_a.w, morph(u_morph_fine, d));
    } else {
        ground = mix(i_a.w, i_b.x, morph(u_morph_mid, d));
    }
    float c = cos(i_b.z);
    float s = sin(i_b.z);
    vec3 v = in_vert * i_b.y;
    v = vec3(c * v.x - s * v.z, v.y, s * v.x + c * v.z);
    v_n = vec3(c * in_normal.x - s * in_normal.z, in_normal.y, s * in_normal.x + c * in_normal.z);
    v_col = in_vcol * i_b.w;
    v_rel = vec3(xz.x, ground, xz.y) + v;
    gl_Position = u_viewproj * vec4(v_rel, 1.0);
}
