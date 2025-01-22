########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gpu
import math
from gpu import state
from gpu_extras.batch import batch_for_shader
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from .data import DB
from .interface import draw_menus
from .... import utils

########################•########################
"""                  HANDLES                  """
########################•########################

POST_PIXEL_HANDLE = None
POST_VIEW_HANDLE = None

def register_shader_handles():
    unregister_shader_handles()
    global POST_PIXEL_HANDLE, POST_VIEW_HANDLE
    context = DB.runtime.context
    guard = utils.guards.except_guard_callback
    args  = (draw_post_pixel, (context,), unregister_shader_handles)
    POST_PIXEL_HANDLE = bpy.types.SpaceView3D.draw_handler_add(guard, args, 'WINDOW', 'POST_PIXEL')
    args  = (draw_post_view, (context,), unregister_shader_handles)
    POST_VIEW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(guard, args, 'WINDOW', 'POST_VIEW')


def unregister_shader_handles():
    global POST_PIXEL_HANDLE, POST_VIEW_HANDLE
    if POST_PIXEL_HANDLE:
        bpy.types.SpaceView3D.draw_handler_remove(POST_PIXEL_HANDLE, "WINDOW")
    if POST_VIEW_HANDLE:
        bpy.types.SpaceView3D.draw_handler_remove(POST_VIEW_HANDLE, "WINDOW")
    POST_PIXEL_HANDLE = None
    POST_VIEW_HANDLE = None

########################•########################
"""                   LABELS                  """
########################•########################

def setup_help_panel():
    context = DB.runtime.context
    prefs = utils.addon.user_prefs()
    razor = context.scene.razor

    help_msgs = [("H", "Toggle Help")]
    append = help_msgs.append
    if prefs.settings.show_modal_help:
        append(("ESC" , "Cancel"))
        append(("CTRL", "Snap"))
    utils.modal_labels.info_panel_init(context, messages=help_msgs)


def setup_status_panel():
    context = DB.runtime.context
    prefs = utils.addon.user_prefs()
    razor = context.scene.razor

    status_msgs = [
        ("Razor"  , ""),
        ("Surface", razor.ops.surface.title()),
        ("Tool"   , razor.ops.tool.title()),
        ("Shape"  , razor.ops.shape.title()),
    ]
    utils.modal_labels.status_panel_init(context, messages=status_msgs)

########################•########################
"""                    DRAW                   """
########################•########################

draw_info_panel = utils.modal_labels.draw_info_panel
draw_status_panel = utils.modal_labels.draw_status_panel

def draw_post_pixel(context):
    if DB.ops.graphics:
        DB.ops.graphics.draw_2D()
    draw_info_panel()
    draw_status_panel()
    draw_menus()


def draw_post_view(context):
    DB.graph.draw_3D()
    if DB.ops.graphics:
        DB.ops.graphics.draw_3D()
