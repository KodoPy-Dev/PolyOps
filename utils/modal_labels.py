########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import time
import gpu
import blf
from gpu import state
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from .addon import user_prefs
from .graphics import text_dims, text_descender_height, max_text_height, draw_text, text_maps_from_entry, Label2D
from .screen import screen_factor

########################•########################
"""                 INFO PANEL                """
########################•########################

INFO_LABEL = None

def info_panel_init(context, messages=[]):
    global INFO_LABEL
    INFO_LABEL = Label2D()
    xy = round(user_prefs().drawing.screen_padding * screen_factor())
    INFO_LABEL.build_from_msgs(pos_x=xy, pos_y=xy, messages=messages, pos='BOTTOM_LEFT')


def draw_info_panel():
    if isinstance(INFO_LABEL, Label2D):
        INFO_LABEL.draw()

########################•########################
"""               STATUS PANEL                """
########################•########################

STATUS_LABELS = []

def status_panel_init(context, messages=[]):
    global STATUS_LABELS
    STATUS_LABELS.clear()
    prefs = user_prefs().drawing
    factor = screen_factor()
    pad = prefs.padding * factor
    font_size = prefs.font_size
    by = round(prefs.screen_padding * factor)

    entry_width_pairs = []
    for entry in messages:
        if isinstance(entry, tuple):
            entry_w = pad * (len(entry) + 1)
            for string in entry:
                entry_w += text_dims(string.replace("$", ""), font_size)[0]
            insert = (round(entry_w), entry)
            entry_width_pairs.append(insert)

    total_width = sum([entry[0] for entry in entry_width_pairs])
    total_width += pad * len(entry_width_pairs)

    lx = round((context.area.width - total_width) / 2)
    for entry_w, entry_msgs in entry_width_pairs:
        label = Label2D()
        label.build_from_msgs(pos_x=lx, pos_y=by, messages=[entry_msgs], pos='BOTTOM_LEFT')
        STATUS_LABELS.append(label)
        lx += entry_w + pad


def draw_status_panel():
    for label in STATUS_LABELS:
        if isinstance(label, Label2D):
            label.draw()

########################•########################
"""             LABEL FADE SYSTEM             """
########################•########################

INTERVAL = 0.03
HANDLE = None
DRAW_DATA = []

class Data:
    def __init__(self, duration=0, label=None):
        self.start_time = time.time()
        self.duration = duration
        self.label = label


def fade_label_init(context, text="", coord_ws=None, coord_ss=None, duration=2.0, remove_previous=False):
    global DRAW_DATA

    if remove_previous:
        DRAW_DATA.clear()

    if not text:
        return
    if isinstance(coord_ws, Vector):
        coord_ss = location_3d_to_region_2d(context.region, context.region_data, coord_ws)
        if not isinstance(coord_ss, Vector):
            return
    if not isinstance(coord_ss, Vector):
        return
    label = Label2D()
    label.build_from_single(pos_x=coord_ss.x, pos_y=coord_ss.y, message=text, orientation='CENTER', pos='CENTER')
    label.store_transparency()
    data = Data(duration=duration, label=label)
    DRAW_DATA.append(data)
    assign_label_fade_handle()

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_label_fade_handle(null=''):
    if bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.unregister(view3d_tag_redraw)
    global HANDLE, DRAW_DATA
    if HANDLE:
        try: bpy.types.SpaceView3D.draw_handler_remove(HANDLE, "WINDOW")
        except Exception as e: print("Label Fade: Did not remove draw handle", e)
    HANDLE = None
    DRAW_DATA.clear()


def assign_label_fade_handle():
    global HANDLE
    if HANDLE is None:
        try: HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", "POST_PIXEL")
        except Exception as e: print("Label Fade: Did not assign draw handle", e)
    if not bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.register(view3d_tag_redraw, first_interval=INTERVAL)

########################•########################
"""                 CALLBACKS                 """
########################•########################

def draw():
    if not HANDLE: return
    for data in DRAW_DATA:
        if data.label:
            data.label.draw()


def process_timer():
    global DRAW_DATA
    for data in DRAW_DATA[:]:
        delta = time.time() - data.start_time
        if delta >= data.duration or data.duration <= 0 or data.label is None:
            DRAW_DATA.remove(data)
        else:
            factor = min(max((1 - (delta / data.duration)), 0), 1)
            data.label.lerp_transparency(factor=1-factor)
    if len(DRAW_DATA) == 0:
        remove_label_fade_handle()


def view3d_tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    process_timer()
    if HANDLE: return INTERVAL
    return None


