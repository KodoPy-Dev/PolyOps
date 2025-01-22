########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import time
import gpu
import inspect
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from .addon import user_prefs
from .context import view_3d_redraw
from .graphics import Label2D, max_text_height
from .notifications import remove_notify_handle
from .screen import screen_factor


class FCOLS:
    BLACK   = "\033[30m"
    WHITE   = "\033[37m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    BLUE    = "\033[34m"
    YELLOW  = "\033[33m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"


class FMODS:
    RESET     = "\033[0m"
    BOLD      = "\033[1m"
    UNDERLINE = "\033[4m"


def debug_print(msg=""):
    if not user_prefs().dev.debug_mode: return
    stack = inspect.stack()
    caller_frame = stack[1]
    module = inspect.getmodule(caller_frame[0])
    module_name = module.__name__ if module else "<unknown>"
    function_name = caller_frame.function
    line_number = caller_frame.lineno
    traced = []
    for frame in stack[1:]:
        mod = inspect.getmodule(frame[0])
        mod_name = mod.__name__ if mod else "<unknown>"
        traced.append(f"{mod_name}.{frame.function}")
    print(f"{FCOLS.RED}{'-' * 120}", FMODS.RESET)
    print(f"• {time.ctime()}")
    for i, trace in enumerate(reversed(traced)):
        print(f"{i+1}) {trace}")
    print(f"• {FCOLS.GREEN}{function_name}{FMODS.RESET} • {FCOLS.CYAN}{line_number}{FMODS.RESET}")
    print(f"• {FMODS.BOLD}{msg}{FMODS.RESET}")
    print(f"{FCOLS.RED}{'-' * 120}{FMODS.RESET}")
    print(FMODS.RESET)


HANDLE = None
START_TIME = 0
LABEL = None


def debug_notify(context, messages=[]):
    prefs = user_prefs()
    if not prefs.settings.debug_mode: return
    remove_notify_handle()
    global START_TIME, LABEL
    START_TIME = time.time()
    if not isinstance(LABEL, Label2D):
        LABEL = Label2D()
    else:
        messages.extend(LABEL.messages)
    factor = screen_factor()
    pad = round(prefs.drawing.padding * factor)
    h = max_text_height(prefs.drawing.font_size) * len(messages)
    h += pad * (len(messages) + 1)
    cx = round(context.area.width / 2)
    by = round(context.area.height / 2)
    cy = by + round(h / 2)
    LABEL.build_from_msgs(pos_x=cx, pos_y=cy, messages=messages, pos='CENTER', special="$")
    if not HANDLE:
        assign_debug_handles()
    view_3d_redraw(interval=prefs.settings.notify_duration)
    context.area.tag_redraw()

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_debug_handle(null=''):
    global HANDLE, LABEL
    if HANDLE:
        try: bpy.types.SpaceView3D.draw_handler_remove(HANDLE, "WINDOW")
        except Exception as e: print("Debug: Did not remove draw handle", e)
    HANDLE = None
    LABEL = None


def assign_debug_handles():
    global HANDLE
    try: HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", "POST_PIXEL")
    except Exception as e: print("Debug: Did not assign draw handle", e)

########################•########################
"""                  CALLBACK                 """
########################•########################

def draw():
    if not HANDLE or not LABEL:
        remove_debug_handle()
        return
    prefs = user_prefs()
    if (time.time() - START_TIME) > prefs.settings.notify_duration:
        remove_debug_handle()
    if isinstance(LABEL, Label2D):
        LABEL.draw()
