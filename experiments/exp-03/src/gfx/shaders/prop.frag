#version 330 core

in vec3 v_rel;
in vec3 v_n;
in vec3 v_col;
out vec4 f_color;

uniform vec3 u_eye;
uniform vec3 u_sun;
uniform vec3 u_fog_col;
uniform float u_fog_dist;

void main() {
    float light = 0.45 + 0.55 * max(dot(normalize(v_n), u_sun), 0.0);
    float fog = 1.0 - exp(-length(v_rel - u_eye) / u_fog_dist);
    f_color = vec4(mix(v_col * light, u_fog_col, fog), 1.0);
}
