#version 330 core

in vec2 v_ndc;
out vec4 f_color;

uniform mat4 u_inv_viewproj;
uniform vec3 u_eye;
uniform vec3 u_fog_col;      // the horizon
uniform vec3 u_zenith_col;

void main() {
    vec4 far = u_inv_viewproj * vec4(v_ndc, 1.0, 1.0);
    vec3 dir = normalize(far.xyz / far.w - u_eye);
    float up = clamp(dir.y, 0.0, 1.0);
    f_color = vec4(mix(u_fog_col, u_zenith_col, pow(up, 0.6)), 1.0);
}
