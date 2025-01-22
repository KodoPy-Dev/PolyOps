########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import time
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from .addon import user_prefs
from .context import view_3d_redraw
from .graphics import Label2D, max_text_height
from .screen import screen_factor

HANDLE = None
START_TIME = 0
LABEL = None

def init(context, messages=[]):
    prefs = user_prefs()
    if not prefs.settings.display_notify:
        return
    global START_TIME, LABEL
    START_TIME = time.time()
    LABEL = Label2D()
    prefs = user_prefs()
    factor = screen_factor()
    pad = round(prefs.drawing.padding * factor)
    h = max_text_height(prefs.drawing.font_size) * len(messages)
    h += pad * (len(messages) + 1)
    cx = round(context.area.width / 2)
    by = round((prefs.drawing.screen_padding + 40) * factor)
    cy = by + round(h / 2)
    LABEL.build_from_msgs(pos_x=cx, pos_y=cy, messages=messages, pos='CENTER', special="$")
    if not HANDLE:
        assign_notify_handles()
    view_3d_redraw(interval=prefs.settings.notify_duration)
    context.area.tag_redraw()

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_notify_handle(null=''):
    global HANDLE, LABEL
    if HANDLE:
        try: bpy.types.SpaceView3D.draw_handler_remove(HANDLE, "WINDOW")
        except Exception as e: print("Notify: Did not remove draw handle", e)
    HANDLE = None
    LABEL = None


def assign_notify_handles():
    global HANDLE
    try: HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", "POST_PIXEL")
    except Exception as e: print("Notify: Did not assign draw handle", e)

########################•########################
"""                  CALLBACK                 """
########################•########################

def draw():
    if not HANDLE or not LABEL:
        remove_notify_handle()
        return
    prefs = user_prefs()
    if (time.time() - START_TIME) > prefs.settings.notify_duration:
        remove_notify_handle()
    if isinstance(LABEL, Label2D):
        LABEL.draw()
