#version 330 core

// One chunk of one tier. Heights blend into the coarser tier's mesh (in_hc) between u_morph.x and
// u_morph.y metres from the loader focus (the origin), so tiers meet without cracks.

in vec2 in_pos;     // metres, relative to the chunk's parent centre
in float in_h;      // this tier's height
in float in_hc;     // the coarser tier's mesh height here
in vec3 in_col;

uniform mat4 u_viewproj;
uniform vec2 u_offset;   // chunk parent centre, relative to the origin
uniform vec2 u_morph;    // start, end (end <= start: no morph)

out vec3 v_rel;
out vec3 v_col;

void main() {
    vec2 xz = in_pos + u_offset;
    float w = u_morph.y > u_morph.x ? smoothstep(u_morph.x, u_morph.y, length(xz)) : 0.0;
    v_rel = vec3(xz.x, mix(in_h, in_hc, w), xz.y);
    v_col = in_col;
    gl_Position = u_viewproj * vec4(v_rel, 1.0);
}
