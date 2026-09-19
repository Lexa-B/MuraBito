"""Creating the GL context: a pygame OpenGL window, or an offscreen EGL context when headless."""

import os

import moderngl
import pygame


def headless() -> bool:
    return os.environ.get("SDL_VIDEODRIVER") == "dummy"


def create(size: tuple[int, int], title: str):
    """Returns (ctx, target framebuffer). Call after pygame.init()."""
    if headless():
        ctx = moderngl.create_standalone_context(backend="egl", require=330)
        target = ctx.framebuffer(
            color_attachments=[ctx.renderbuffer(size)],
            depth_attachment=ctx.depth_renderbuffer(size),
        )
        return ctx, target
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption(title)
    ctx = moderngl.create_context(require=330)
    return ctx, ctx.screen
