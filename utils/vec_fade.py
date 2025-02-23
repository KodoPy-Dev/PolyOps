########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import time
import gpu
import numpy as np
from random import choice
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from mathutils import Vector, Matrix
from .addon import user_prefs
from .graphics import draw_matrix, gen_line_batches_for_wire_sphere, gen_triangles_from_sphere, gen_tri_batch_from_triangles


UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')
INTERVAL = 0.03
DURATION = 2.5
HANDLE = None
# List of Data Instances
DRAW_DATA = []

class Data:
    def __init__(self):
        # TIME
        self.start_time = time.time()
        self.duration = None
        # DRAW
        self.alpha = 1.0
        self.point_size = 1
        self.line_width = 1
        self.color_a = None
        self.color_b = None
        self.use_half_alpha = False
        # BATCH
        self.point_batch = None
        self.line_batch = None
        self.tri_batch = None
        self.plane_batch = None
        self.sphere_batch = None
        self.matrix = None

COLORS = [
    (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
    (1.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0), (1.0, 0.2, 0.0), (1.0, 0.0, 0.2),
    (0.2, 0.0, 0.0), (1.0, 0.2, 0.2), (0.0, 0.2, 0.0), (0.2, 1.0, 0.2), (0.0, 0.0, 0.2), (0.4, 0.4, 1.0)
]

def init(
    points=[], lines=[], tris=[],
    plane_origin=None, plane_normal=None,
    sphere_center=None, sphere_radius=None, sphere_as_wire=True, sphere_res=32,
    matrix=None,
    point_size=6, line_width=1,
    color_a=None, color_b=None, use_half_alpha=False, random_color=False,
    duration=DURATION,
    handle_type="POST_VIEW",
    clear_all_handles=False):

    if clear_all_handles:
        remove_vec_fade_handle()

    global DRAW_DATA

    data = Data()

    data.duration = duration
    data.use_half_alpha = use_half_alpha

    if random_color:
        data.color_a = Vector(choice(COLORS))
        data.color_b = Vector(choice(COLORS))
    else:
        if color_a is None:
            color_a = (0,1,0)

        if color_b is None:
            if color_a is not None:
                color_b = color_a
            else:
                color_b = (1,1,1)
        data.color_a = Vector((color_a[0], color_a[1], color_a[2]))
        data.color_b = Vector((color_b[0], color_b[1], color_b[2]))

    data.matrix = matrix
    data.point_size = point_size

    if points:
        data.point_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": points})

    if lines:
        data.line_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": lines})
    
    if tris:
        points = [vec for tri in tris for vec in tri]
        indices = [(i, i+1, i+2) for i in range(0, len(points), 3)]
        data.tri_batch = batch_for_shader(UNIFORM_COLOR, 'TRIS', {"pos": points}, indices=indices)

    if plane_origin is not None and plane_normal is not None:

        loc = Matrix.Translation(plane_origin)
        rot_quat = plane_normal.to_track_quat('Z', 'Y')
        rot = rot_quat.to_matrix().to_4x4()
        mat = loc @ rot

        bot_L = mat @ Vector((-0.5, -0.5, 0))
        bot_R = mat @ Vector(( 0.5, -0.5, 0))
        top_L = mat @ Vector((-0.5,  0.5, 0))
        top_R = mat @ Vector(( 0.5,  0.5, 0))
        data.plane_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": (bot_L, top_L, top_L, top_R, top_R, bot_R, bot_R, bot_L, plane_origin, plane_origin + plane_normal)})

    if sphere_center and sphere_radius:
        if sphere_as_wire:
            data.sphere_batch = gen_line_batches_for_wire_sphere(sphere_center, sphere_radius, sphere_res)
        else:
            triangles = gen_triangles_from_sphere(sphere_center, sphere_radius, sphere_res, int(sphere_res/2))
            data.sphere_batch = gen_tri_batch_from_triangles(triangles)

    DRAW_DATA.append(data)
    assign_v_fade_handle(handle_type)

########################•########################
"""                   TIMER                   """
########################•########################

def process_timer():
    global DRAW_DATA
    for data in DRAW_DATA[:]:
        delta = time.time() - data.start_time
        if delta >= data.duration or data.duration <= 0:
            DRAW_DATA.remove(data)
        elif data.use_half_alpha:
            data.alpha = min(max((1 - (delta / data.duration)), 0), 1) / 6
        else:
            data.alpha = min(max((1 - (delta / data.duration)), 0), 1)
    if len(DRAW_DATA) == 0:
        remove_vec_fade_handle()

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_vec_fade_handle(null=''):
    if bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.unregister(view3d_tag_redraw)
    global HANDLE, DRAW_DATA
    if HANDLE:
        try: bpy.types.SpaceView3D.draw_handler_remove(HANDLE, "WINDOW")
        except Exception as e: print("Poly Fade: Did not remove draw handle", e)
    HANDLE = None
    DRAW_DATA.clear()


def assign_v_fade_handle(handle_type="POST_VIEW"):
    global HANDLE
    if HANDLE is None:
        try: HANDLE = bpy.types.SpaceView3D.draw_handler_add(draw, tuple(), "WINDOW", handle_type)
        except Exception as e: print("Poly Fade: Did not assign draw handle", e)
    if not bpy.app.timers.is_registered(view3d_tag_redraw):
        bpy.app.timers.register(view3d_tag_redraw, first_interval=INTERVAL)

########################•########################
"""                 CALLBACKS                 """
########################•########################

def draw():
    if not HANDLE:
        return
    gpu.state.depth_mask_set(False)
    gpu.state.blend_set('ALPHA')
    for data in DRAW_DATA:
        color = data.color_b.lerp(data.color_a, data.alpha)
        color = (color[0], color[1], color[2], data.alpha)
        UNIFORM_COLOR.uniform_float("color", color)
        if data.line_batch:
            gpu.state.line_width_set(data.line_width)
            data.line_batch.draw(UNIFORM_COLOR)
            gpu.state.line_width_set(1)
        if data.point_batch:
            gpu.state.point_size_set(data.point_size)
            data.point_batch.draw(UNIFORM_COLOR)
        if data.tri_batch:
            data.tri_batch.draw(UNIFORM_COLOR)
        if data.matrix:
            draw_matrix(matrix=data.matrix)
        if data.plane_batch:
            gpu.state.line_width_set(data.line_width)
            data.plane_batch.draw(UNIFORM_COLOR)
            gpu.state.line_width_set(1)
        if data.sphere_batch:
            if type(data.sphere_batch) == tuple:
                for batch in data.sphere_batch:
                    batch.draw(UNIFORM_COLOR)
            else:
                data.sphere_batch.draw(UNIFORM_COLOR)
    gpu.state.blend_set('NONE')


def view3d_tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    process_timer()
    if HANDLE: return INTERVAL
    return None
