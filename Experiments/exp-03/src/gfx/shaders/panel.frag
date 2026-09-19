#version 330 core

in vec2 v_uv;
out vec4 f_color;

uniform sampler2D u_panel;

void main() {
    f_color = texture(u_panel, v_uv);
}
