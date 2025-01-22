########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import time
import gpu
import bmesh
import numpy as np
from gpu import state
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix
from .addon import user_prefs
from .graphics import COLORS

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
INTERVAL = 0.03
DURATION = 1.0
HANDLE = None
# List of Data Instances
DRAW_DATA = []

class Data:
    def __init__(self, line_batch=None, point_batch=None):
        self.start_time = time.time()
        self.alpha = 1.0
        self.color_a = None
        self.color_b = None
        self.line_batch = line_batch
        self.point_batch = point_batch


def init(obj=None, points=[], lines=[], bounding_box_only=False, color_a=COLORS.WHITE, color_b=COLORS.BLACK):
    if not isinstance(obj, bpy.types.Object):
        return
    prefs = user_prefs()
    if not bounding_box_only:
        if len(points) + len(lines) > prefs.settings.mesh_fade_geo_limit:
            bounding_box_only = True
        elif isinstance(obj.data, bpy.types.Mesh):
            if len(obj.data.vertices) > prefs.settings.mesh_fade_geo_limit:
                bounding_box_only = True
    global DURATION, DRAW_DATA
    DURATION = prefs.settings.mesh_fade_duration
    data = Data()
    data.color_b = Vector((color_a[0], color_a[1], color_a[2]))
    data.color_a = Vector((color_b[0], color_b[1], color_b[2]))
    # Bounding Box
    if bounding_box_only:
        mat_ws = obj.matrix_world
        bb = obj.bound_box
        p1 = mat_ws @ Vector((bb[0][0], bb[0][1], bb[0][2]))
        p2 = mat_ws @ Vector((bb[1][0], bb[1][1], bb[1][2]))
        p3 = mat_ws @ Vector((bb[2][0], bb[2][1], bb[2][2]))
        p4 = mat_ws @ Vector((bb[3][0], bb[3][1], bb[3][2]))
        p5 = mat_ws @ Vector((bb[4][0], bb[4][1], bb[4][2]))
        p6 = mat_ws @ Vector((bb[5][0], bb[5][1], bb[5][2]))
        p7 = mat_ws @ Vector((bb[6][0], bb[6][1], bb[6][2]))
        p8 = mat_ws @ Vector((bb[7][0], bb[7][1], bb[7][2]))
        points = [p1, p2, p3, p4, p5, p6, p7, p8]
        lines = [
            # Top
            p2, p3, p3, p7, p7, p6, p6, p2,
            # Bottom
            p1, p4, p4, p8, p8, p5, p5, p1,
            # Right
            p5, p6, p6, p7, p7, p8, p8, p5,
            # Left
            p1, p2, p2, p3, p3, p4, p4, p1,
            # Front
            p1, p2, p2, p6, p6, p5, p5, p1,
            # Back
            p4, p3, p3, p7, p7, p8, p8, p4]
    # Mesh
    elif not lines and not points and isinstance(obj.data, bpy.types.Mesh):
        mat_ws = obj.matrix_world
        bm = bmesh.new(use_operators=False)
        bm.from_mesh(obj.data)
        bm.transform(mat_ws)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        lines = [vert.co for edge in bm.edges for vert in edge.verts]
    # Batches
    if points or lines:
        if points:
            data.point_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [coord for coord in points if isinstance(coord, Vector)]})
        if lines:
            data.line_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": [coord for coord in lines if isinstance(coord, Vector)]})
        DRAW_DATA.append(data)
        assign_poly_fade_handle()

########################•########################
"""                  HANDLES                  """
########################•########################

def process_timer():
    global DRAW_DATA
    for data in DRAW_DATA[:]:
        delta = time.time() - data.start_time
        if delta >= DURATION:
            DRAW_DATA.remove(data)
        else:
            data.alpha = min(max((1 - (delta / DURATION)), 0), 1)
    if len(DRAW_DATA) == 0:
        remove_poly_fade_handle()


@persistent
def remove_poly_fade_handle(null=''):
    if bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.unregister(view3d_tag_redraw)
    global HANDLE, DRAW_DATA
    if HANDLE:
        try: bpy.types.SpaceView3D.draw_handler_remove(HANDLE, "WINDOW")
        except Exception as e: print("Poly Fade: Did not remove draw handle", e)
    HANDLE = None
    DRAW_DATA.clear()


def assign_poly_fade_handle():
    global HANDLE
    if HANDLE is None:
        try: HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", "POST_VIEW")
        except Exception as e: print("Poly Fade: Did not assign draw handle", e)
    if not bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.register(view3d_tag_redraw, first_interval=INTERVAL, persistent=False)

########################•########################
"""                 CALLBACKS                 """
########################•########################

def draw():
    if not HANDLE:
        return
    state.blend_set('ALPHA')
    state.line_width_set(1)
    state.point_size_set(1)
    for data in DRAW_DATA:
        color = data.color_a.lerp(data.color_b, data.alpha)
        color = (color[0], color[1], color[2], data.alpha)
        UNIFORM_COLOR.uniform_float("color", color)
        if data.line_batch:
            data.line_batch.draw(UNIFORM_COLOR)
        if data.point_batch:
            data.point_batch.draw(UNIFORM_COLOR)
    state.blend_set('NONE')


def view3d_tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    process_timer()
    if HANDLE:
        return INTERVAL
    return None


