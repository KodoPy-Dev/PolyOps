########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from .data import DB
from ....utils import debug_print
from ....utils.graphics import COLORS
from .... import utils

########################•########################
"""                   MODAL                   """
########################•########################

def update_SS():
    context = DB.runtime.context
    event   = DB.runtime.event


def update_WS():
    context = DB.runtime.context
    event   = DB.runtime.event

    # Reset
    if event.type == 'R' and event.value == 'PRESS':
        utils.notifications.init(context, messages=[("Entity", "Reset")])
        DB.graph.reset_active_entity_CON()
        DB.ops.reset()

    # Undo
    elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
        DB.graph.undo()

    # Ensure Sketch CON
    sketch_CON = DB.graph.get_active_sketch_CON(allow_create=True)
    if sketch_CON is None:
        DB.razor.ops.status = 'ERROR'
        debug_print("Error : Invalid Sketch Con")
        return

    # Ensure Entity CON
    entity_CON = sketch_CON.get_active_entity_CON(allow_create=True)
    if entity_CON is None:
        DB.razor.ops.status = 'ERROR'
        debug_print("Error : Invalid Sketch Con")
        return

    # Ray
    snap = False if event.ctrl else True
    hit_point = ray_to_surface_WS(context, event, snap=snap)
    if hit_point is None:
        return

    # Ops
    points_ws = DB.ops.points_ws
    if DB.runtime.LMB_pressed:
        points_ws.append(hit_point)

    # Entity
    entity = entity_CON.entity

    # Points
    current_count = len(points_ws)
    required_count = entity.point_count_needed()
    points_needed = required_count - current_count
    points_needed = 0 if points_needed < 0 else points_needed

    # Tess & Save
    tess = False
    save = False
    shape = entity.shape
    graphics = DB.ops.graphics

    # 1 Points Required
    if shape == 'POINT':
        # Tess & Save
        if points_needed == 0:
            tess, save = True, True
        # Add One & Tess
        elif points_needed == 1:
            tess = True
            graphics.gen_point_batch(space='3D', clear=True, points=[hit_point], color=COLORS.ACT_ONE, size=6)

    # 2 Points Required
    elif shape in {'LINE', 'CIRCLE', 'RECTANGLE'}:
        # Tess & Save
        if points_needed == 0:
            tess, save = True, True
        # Add One & Tess
        elif points_needed == 1:
            tess = True
            points_ws = points_ws[:]
            points_ws.append(hit_point)
            graphics.gen_point_batch(space='3D', clear=True, points=points_ws, color=COLORS.ACT_ONE, size=6)
        # Only Hit
        elif points_needed == 2:
            graphics.gen_point_batch(space='3D', clear=True, points=[hit_point], color=COLORS.ACT_ONE, size=6)

    # 3 Points Required
    if shape == 'NGON':
        pass

    # 3 Points Required
    elif shape == 'ELLIPSE':
        pass

    # 4 Points Required
    elif shape == 'ARC':
        pass

    if tess:
        if not entity_CON.build(points_ws=points_ws):
            debug_print("Error : Failed to build entity data")
            return

    if save:
        if not entity_CON.save():
            debug_print("Error : Failed to register data to entity")
            return
        sketch_CON.new_entity_CON()
        DB.graph.evaluate()
        DB.ops.reset()

########################•########################
"""                   UTILS                   """
########################•########################

def ray_to_surface_WS(context, event, snap=False):
    # Ray
    surface = DB.surface
    point = utils.ray.cast_onto_plane(context, event, plane_co=surface.loc_ws, plane_no=surface.normal, fallback=None)
    # Error
    if not isinstance(point, Vector): return None
    if len(point) != 3: return None
    # Snap
    if snap and isinstance(surface.kd_tree, KDTree):
        results = surface.kd_tree.find_n(point, 1)
        if len(results) > 0:
            position, index, distance = results[0]
            if isinstance(position, Vector):
                point = position
    # Casted
    return point

