########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from mathutils import Vector
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, region_2d_to_location_3d, location_3d_to_region_2d
from mathutils.geometry import distance_point_to_plane

########################•########################
"""                   SCALE                   """
########################•########################

def screen_factor():
    prefs = bpy.context.preferences.system
    dpi = prefs.dpi
    ui_scale = prefs.ui_scale
    pixel_size = prefs.pixel_size
    ui_line_width = prefs.ui_line_width
    scale_factor = (dpi * ui_scale / 72) * pixel_size
    return scale_factor / ui_line_width


def depth_factor_from_clip_extents(context, point_3d):
    region = context.region
    rv3d = context.region_data
    clip_dist = context.space_data.clip_end - context.space_data.clip_start
    cx = context.area.width / 2
    cy = context.area.height / 2
    ray_org = region_2d_to_origin_3d(region, rv3d, (cx, cy))
    ray_nor = region_2d_to_vector_3d(region, rv3d, (cx, cy))
    point_dist = distance_point_to_plane(ray_org, point_3d, -ray_nor)
    factor = 1 / (clip_dist / point_dist)
    if factor < 0:
        return 1
    if factor > 1:
        return 0
    return factor


def pixels_per_unit_at_depth(context, point_3d, fallback=0):
    rv3d = context.region_data
    tangent = rv3d.view_rotation @ Vector((1,1,0))
    tangent.normalize()
    tangent *= .5
    v3d_p1 = point_3d + tangent
    v3d_p2 = point_3d - tangent
    region = context.region
    ss_p1 = location_3d_to_region_2d(region, rv3d, v3d_p1)
    ss_p2 = location_3d_to_region_2d(region, rv3d, v3d_p2)
    if ss_p1 and ss_p2:
        return (ss_p1 - ss_p2).length
    return fallback


def units_per_pixel_at_depth(context, point_3d, fallback=0):
    pixels_per_unit = pixels_per_unit_at_depth(context, point_3d, fallback=0)
    if pixels_per_unit != 0:
        return 1 / pixels_per_unit
    return fallback


def object_location_to_screen_coords(context, obj):
    if not isinstance(obj, bpy.types.Object):
        return None
    region = context.region
    rv3d = context.region_data
    return location_3d_to_region_2d(region, rv3d, obj.matrix_world.translation)


def rv3d_frustrum_planes(context):
    # --- CONTEXT --- #
    clip_end = context.space_data.clip_end
    clip_start = context.space_data.clip_start
    region = context.region
    rv3d = context.region_data
    width = context.area.width
    height = context.area.height
    center_x = context.area.width / 2
    center_y = context.area.height / 2
    # --- VIEW RAY --- #
    v_ray_org = region_2d_to_origin_3d(region, rv3d, (center_x, center_y))
    v_ray_nor = region_2d_to_vector_3d(region, rv3d, (center_x, center_y))
    # --- Near --- #
    v_ray_clip_org = v_ray_org + (v_ray_nor * clip_start)
    # Bottom Left
    p1 = region_2d_to_location_3d(region, rv3d, (0, 0), v_ray_clip_org)
    # Bottom Right
    p2 = region_2d_to_location_3d(region, rv3d, (width, 0), v_ray_clip_org)
    # Top Right
    p3 = region_2d_to_location_3d(region, rv3d, (width, height), v_ray_clip_org)
    # Top Left
    p4 = region_2d_to_location_3d(region, rv3d, (0, height), v_ray_clip_org)
    # --- Far --- #
    # Bottom Left
    v_ray_clip_end = v_ray_org + (v_ray_nor * clip_end)
    p5 = region_2d_to_location_3d(region, rv3d, (0, 0), v_ray_clip_end)
    # Bottom Right
    p6 = region_2d_to_location_3d(region, rv3d, (width, 0), v_ray_clip_end)
    # Top Right
    p7 = region_2d_to_location_3d(region, rv3d, (width, height), v_ray_clip_end)
    # Top Left
    p8 = region_2d_to_location_3d(region, rv3d, (0, height), v_ray_clip_end)
    # --- VIEW PLANES --- #
    frustrum_planes = []
    # Left Plane
    temp_a = (p8 - p1).normalized()
    temp_b = (p5 - p4).normalized()
    left_co = (p1 + p4 + p8 + p5) / 4
    left_no = temp_b.cross(temp_a)
    frustrum_planes.append((left_co, left_no))
    # Right Plane
    temp_a = (p7 - p2).normalized()
    temp_b = (p6 - p3).normalized()
    right_co = (p2 + p3 + p7 + p6) / 4
    right_no = temp_a.cross(temp_b)
    frustrum_planes.append((right_co, right_no))
    # Top Plane
    temp_a = (p7 - p4).normalized()
    temp_b = (p8 - p3).normalized()
    top_co = (p4 + p3 + p7 + p8) / 4
    top_no = temp_b.cross(temp_a)
    frustrum_planes.append((top_co, top_no))
    # Bottom Plane
    temp_a = (p6 - p1).normalized()
    temp_b = (p5 - p2).normalized()
    bottom_co = (p1 + p2 + p5 + p6) / 4
    bottom_no = temp_a.cross(temp_b)
    frustrum_planes.append((bottom_co, bottom_no))
    return frustrum_planes
