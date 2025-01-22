########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import time
from math import radians, inf, sin, cos, pi
from mathutils import geometry, Vector, Matrix
from mathutils.geometry import distance_point_to_plane, intersect_line_plane, intersect_line_sphere, intersect_point_line, convex_hull_2d, intersect_point_quad_2d
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d, region_2d_to_location_3d
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from .math3 import sphere_from_obj_bounds
from .object import get_visible_mesh_obj_by_name
from .screen import screen_factor, units_per_pixel_at_depth
from .vec_fade import init as init_vec_fade

########################•########################
"""                 CONTSTANTS                """
########################•########################

VEC3_ZERO = Vector((0,0,0))
EPSILON = 0.0001

########################•########################
"""                   UTILS                   """
########################•########################

def mouse_ray(context, event):
    mouse = Vector((event.mouse_region_x, event.mouse_region_y))
    ray_org = region_2d_to_origin_3d(context.region, context.region_data, mouse)
    ray_nor = region_2d_to_vector_3d(context.region, context.region_data, mouse)
    ray_end = ray_org + (ray_nor * context.space_data.clip_end)
    return mouse, ray_org, ray_nor, ray_end


def is_mouse_over_bounding_box(context, event, obj=None):
    perp_mat = context.region_data.perspective_matrix
    mat_ws = obj.matrix_world
    bb_corners = [perp_mat @ mat_ws @ Vector((x, y, z, 1)) for x,y,z in obj.bound_box]
    points = []
    wh = context.area.width / 2
    hh = context.area.height / 2
    for corner in bb_corners:
        if corner.w > 0.0:
            points.append(Vector((wh + wh * (corner.x / corner.w), hh + hh * (corner.y / corner.w))))
    if not points:
        return False
    indices = convex_hull_2d(points)
    if not indices:
        return False
    corners = [points[index] for index in indices]
    x_coords = [point.x for point in corners]
    y_coords = [point.y for point in corners]
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)
    p1 = Vector((min_x, min_y)) # BL
    p2 = Vector((max_x, min_y)) # BR
    p3 = Vector((max_x, max_y)) # TR
    p4 = Vector((min_x, max_y)) # TL
    mouse = Vector((event.mouse_region_x, event.mouse_region_y))
    if intersect_point_quad_2d(mouse, p1, p2, p3, p4) > 0:
        return True
    return False


def bounding_box_radius(obj):
    bb = obj.bound_box
    x_min = min([vec[0] for vec in bb])
    x_max = max([vec[0] for vec in bb])
    y_min = min([vec[1] for vec in bb])
    y_max = max([vec[1] for vec in bb])
    z_min = min([vec[2] for vec in bb])
    z_max = max([vec[2] for vec in bb])
    vec_min = obj.matrix_world @ Vector((x_min, y_min, z_min))
    vec_max = obj.matrix_world @ Vector((x_max, y_max, z_max))
    radius = (vec_max - vec_min).length / 2
    return radius


def cast_points_to_ss(context, points=[]):
    hw = context.area.width / 2
    hh = context.area.height / 2
    perp_mat = context.region_data.perspective_matrix
    casted_points = []
    for point in points:
        prj = perp_mat @ Vector((point[0], point[1], point[2], 1.0))
        if prj.w > 0.0:
            casted_points.append(Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w))))
    return casted_points


def cast_point_to_ss(context, point=None):
    hw = context.area.width / 2
    hh = context.area.height / 2
    perp_mat = context.region_data.perspective_matrix
    prj = perp_mat @ Vector((point[0], point[1], point[2], 1.0))
    if prj.w > 0.0:
        return Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w)))
    return None


def point_on_obj_is_obstructed_from_view(context, event, obj, point, ray_org, deps=None):
    if not isinstance(obj, bpy.types.Object) or not isinstance(point, Vector):
        return True
    target_point = point.copy()
    ray_nor = (ray_org - target_point).normalized()
    if not deps:
        deps = context.evaluated_depsgraph_get()
    target_point += ray_nor * EPSILON
    hit_result, hit_location, hit_normal, hit_poly_index, hit_obj, hit_matrix = context.scene.ray_cast(deps, target_point, ray_nor, distance=(target_point - ray_org).length)
    if not hit_result:
        return False
    if isinstance(hit_obj, bpy.types.Object):
        if hit_obj.name != obj.name:
            return True
    return True


def screen_origin_center(context):
    screen_center = (round(context.area.width), round(context.area.height))
    view_origin = region_2d_to_origin_3d(context.region, context.region_data, screen_center)
    return view_origin

########################•########################
"""                PROXIMITIES                """
########################•########################

def closest_vert_to_mouse_from_polygon(context, event, obj, polygon_index=-1):
    result = False
    delta_dist_ss = inf
    hit_coord_ls = None
    hit_coord_ws = None
    hit_vert_index = None
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return result, delta_dist_ss, hit_coord_ls, hit_coord_ws, hit_vert_index
    if not (polygon_index < len(obj.data.polygons) and polygon_index >= 0):
        return result, delta_dist_ss, hit_coord_ls, hit_coord_ws, hit_vert_index
    hw = context.area.width / 2
    hh = context.area.height / 2
    perp_mat = context.region_data.perspective_matrix
    mouse = Vector((event.mouse_region_x, event.mouse_region_y))
    mat_ws = obj.matrix_world
    polygon = obj.data.polygons[polygon_index]
    poly_vert_indices = polygon.vertices
    verts = obj.data.vertices
    for poly_vert_index in poly_vert_indices:
        vert_co_ls = verts[poly_vert_index].co
        vert_co_ws = mat_ws @ vert_co_ls
        prj = perp_mat @ vert_co_ws.to_4d()
        if prj.w > 0.0:
            vert_co_ss = Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w)))
            distance = (mouse - vert_co_ss).length
            if distance < delta_dist_ss:
                result = True
                delta_dist_ss = distance
                hit_coord_ls = vert_co_ls.copy()
                hit_coord_ws = vert_co_ws
                hit_vert_index = poly_vert_index
    return result, delta_dist_ss, hit_coord_ls, hit_coord_ws, hit_vert_index


def closest_edge_to_point_from_polygon(context, obj, point_ws=Vector((0,0,0)), polygon_index=-1):
    result = False
    delta = inf
    hit_coord_ls = None
    hit_coord_ws = None
    hit_edge_index = None
    # CHECK : TYPE
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return result, delta, hit_coord_ls, hit_coord_ws, hit_edge_index
    mesh = obj.data
    polygons = mesh.polygons
    # CHECK : INDEX
    if polygon_index >= len(polygons) or polygon_index < 0:
        return result, delta, hit_coord_ls, hit_coord_ws, hit_edge_index
    perp_mat = context.region_data.perspective_matrix
    point_vs = perp_mat @ point_ws
    mat_ws = obj.matrix_world
    mat_ws_inv = mat_ws.inverted_safe()
    polygon = polygons[polygon_index]
    verts = mesh.vertices
    edges = mesh.edges
    loops = mesh.loops
    for loop_index in polygon.loop_indices:
        edge_index = loops[loop_index].edge_index
        vert_1_index = edges[edge_index].vertices[0]
        vert_2_index = edges[edge_index].vertices[1]
        vert_1_co_ws = mat_ws @ verts[vert_1_index].co
        vert_2_co_ws = mat_ws @ verts[vert_2_index].co
        vert_1_co_vs = perp_mat @ vert_1_co_ws
        vert_2_co_vs = perp_mat @ vert_2_co_ws
        # INTERSECTION
        intersection, factor = intersect_point_line(point_vs, vert_1_co_vs, vert_2_co_vs)
        if factor < 0:
            factor = 0
            intersection = vert_1_co_vs
        elif factor > 1:
            factor = 1
            intersection = vert_2_co_vs
        distance = (intersection - point_vs).length
        if distance < delta:
            result = True
            delta = distance
            hit_coord_ws = vert_1_co_ws.lerp(vert_2_co_ws, factor)
            hit_coord_ls = mat_ws_inv @ hit_coord_ws
            hit_edge_index = edge_index
    return result, hit_coord_ls, hit_coord_ws, hit_edge_index


def closest_vert_to_mouse_from_edit_mode(context, event, objs=[], update_obj=True, tolerance_PX=20):
    ''' SLOW : (Maybe make a kd tree from a new bmesh but transformed to the view plane) '''
    tolerance_PX *= screen_factor()
    if context.mode != 'EDIT_MESH':
        return None, None, None
    objs = [obj for obj in context.objects_in_mode if obj in objs]
    if not objs:
        return False, None, None, None
    wire_frame = context.space_data.shading.type == 'WIREFRAME'
    deps = context.evaluated_depsgraph_get() if wire_frame else None
    mouse, m_ray_org, m_ray_nor, m_ray_end = mouse_ray(context, event)
    region = context.region
    rv3d = context.region_data
    hw = context.area.width / 2
    hh = context.area.height / 2
    perp_mat = context.region_data.perspective_matrix
    # Hit Data
    delta_dist = inf
    hit_coord_ws = None
    hit_vert_index = None
    hit_obj = None
    for obj in objs:
        if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
            continue
        if update_obj and obj.data.is_editmode:
            obj.update_from_editmode()
        intercept_near, intercept_far = cast_to_bb_sphere(context, obj, m_ray_org, m_ray_end, tolerance_PX)
        if not intercept_near or not intercept_far:
            continue
        intersection_len = (intercept_far - intercept_near).length
        if round(intersection_len, 6) == 0:
            continue
        mat_ws = obj.matrix_world
        vertices = obj.data.vertices
        for vert in vertices:
            world_co = mat_ws @ vert.co
            prj = perp_mat @ Vector((world_co[0], world_co[1], world_co[2], 1.0))
            ss_co = Vector((0,0))
            if prj.w <= 0.0:
                continue
            ss_co = Vector((hw + hw * (prj.x / prj.w), hh + hh * (prj.y / prj.w)))
            dist_2d = (ss_co - mouse).length
            if (dist_2d > delta_dist) or (dist_2d > tolerance_PX):
                continue
            # Reject solid view interferences
            if not wire_frame:
                if point_on_obj_is_obstructed_from_view(context, event, obj, world_co, m_ray_org, deps=deps):
                    continue
            delta_dist = dist_2d
            hit_coord_ws = world_co.copy()
            hit_vert_index = vert.index
            hit_obj = obj
    result = False
    if isinstance(hit_coord_ws, Vector) and isinstance(hit_vert_index, int) and isinstance(hit_obj, bpy.types.Object) and isinstance(hit_obj.data, bpy.types.Mesh):
        if hit_vert_index < len(hit_obj.data.vertices) and hit_vert_index >= 0:
            result = True
    return result, hit_coord_ws, hit_vert_index, hit_obj

########################•########################
"""                   CAST                    """
########################•########################

def cast_onto_plane(context, event, plane_co=VEC3_ZERO, plane_no=VEC3_ZERO, fallback=None):
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    hit_point = intersect_line_plane(ray_org, ray_end, plane_co, plane_no)
    return hit_point if isinstance(hit_point, Vector) else fallback


def cast_onto_view_plane(context, event, fallback=None):
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    plane_co = context.region_data.view_location
    plane_no = context.region_data.view_rotation @ Vector((0,0,1))
    hit_point = intersect_line_plane(ray_org, ray_end, plane_co, plane_no)
    return hit_point if isinstance(hit_point, Vector) else fallback


def cast_onto_view_plane_at_depth(context, event, plane_co=VEC3_ZERO, fallback=None):
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    view_no = (context.region_data.view_rotation @ Vector((0,0,1))).normalized()
    hit_point = intersect_line_plane(ray_org, ray_end, plane_co, view_no)
    return hit_point if isinstance(hit_point, Vector) else fallback


def cast_onto_view_plane_with_angle_from_point(context, event, point=VEC3_ZERO, increment_angle=15):
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    view_nor = (context.region_data.view_rotation @ Vector((0,0,1))).normalized()
    view_rot = context.region_data.view_rotation
    view_inv = view_rot.inverted()
    hit_point = intersect_line_plane(ray_org, ray_end, point, view_nor, False)
    if not hit_point:
        return None, None
    # User ray flat
    user = (view_inv @ (hit_point - point)).normalized().to_2d()
    if user.length == 0:
        return None, None
    terminator = Vector((1,0))
    # Angle of ray
    angle = terminator.angle_signed(user)
    increment_angle = radians(increment_angle)
    snapped_angle = -(round(angle / increment_angle) * increment_angle)
    # Rotate to snapped angle
    snap_mat = Matrix.Rotation(snapped_angle, 4, 'Z')
    snapped_point = snap_mat @ Vector((1,0,0))
    snapped_point.normalize()
    snapped_point *= (hit_point - point).length
    # Rotate back into view plane
    snapped_point = view_rot @ snapped_point
    snapped_point += point
    return snapped_point, snapped_angle


def cast_to_view_plane_pick_side(context, event, line_p1=VEC3_ZERO, line_p2=VEC3_ZERO):
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    plane_co = (line_p1 + line_p2) / 2
    view_no = context.region_data.view_rotation @ Vector((0,0,1))
    if context.region_data.view_perspective == 'PERSP':
        screen_center = (round(context.area.width), round(context.area.height))
        view_origin = region_2d_to_origin_3d(context.region, context.region_data, screen_center)
        view_no = (view_origin - plane_co).normalized()
    point = intersect_line_plane(ray_org, ray_end, plane_co, view_no)
    if point == None:
        return Vector((0,0,0)), Vector((0,0,0))
    direction = (line_p2 - line_p1).normalized()
    normal = direction.cross(view_no)
    temp_a = (point - plane_co).normalized()
    if temp_a.dot(normal) < 0:
        direction = (line_p1 - line_p2).normalized()
        normal = direction.cross(view_no)
    normal.normalize()
    return plane_co, normal


def cast_into_scene(context, event):
    mouse, m_ray_org, m_ray_nor, m_ray_end = mouse_ray(context, event)
    result, hit_location, hit_normal, hit_index, hit_obj, hit_matrix = context.scene.ray_cast(context.view_layer.depsgraph, m_ray_org, m_ray_nor)
    return result, hit_location, hit_normal, hit_index, hit_obj, hit_matrix


def cast_into_scene_uneval_objs(context, event, objs):
    objects_turned_off = []
    mods_turned_off = []
    mouse, m_ray_org, m_ray_nor, m_ray_end = mouse_ray(context, event)
    deps = context.evaluated_depsgraph_get()
    last_hit_obj = None
    result = True
    while result:
        result, hit_coord_ws, hit_normal, hit_face_index, hit_obj, hit_matrix = context.scene.ray_cast(deps, m_ray_org, m_ray_nor)
        if result:
            if hit_obj in objs:
                for mod in hit_obj.modifiers:
                    if mod.show_viewport:
                        mods_turned_off.append(mod)
                        mod.show_viewport = False
                context.view_layer.update()
                deps.update()
                if last_hit_obj == hit_obj:
                    break
                else:
                    last_hit_obj = hit_obj
            else:
                last_hit_obj = None
                hit_obj.hide_viewport = True
                objects_turned_off.append(hit_obj)
                context.view_layer.update()
                deps.update()
    for obj in objects_turned_off:
        obj.hide_viewport = False
    for mod in mods_turned_off:
        mod.show_viewport = True
    context.view_layer.update()
    return result, hit_coord_ws, hit_normal, hit_face_index, hit_matrix, hit_obj


def cast_to_uneval_object_nearest_vert(context, event, obj):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return False, None, None, None
    mouse, m_ray_org, m_ray_nor, m_ray_end = mouse_ray(context, event)
    mat_ws = obj.matrix_world.copy()
    mat_ws_inv = mat_ws.inverted_safe()
    # Temp Object
    temp_obj = bpy.data.objects.new(name="TempObj", object_data=obj.data)
    temp_obj.matrix_world = mat_ws
    context.collection.objects.link(temp_obj)
    # Ray
    origin = mat_ws_inv @ m_ray_org
    direction = ((mat_ws_inv @ m_ray_end) - origin).normalized()
    result, hit_coord_ws, hit_normal, hit_poly_index = temp_obj.ray_cast(origin, direction)
    hit_vert_index = None
    if result:
        polygons = temp_obj.data.polygons
        vertices = temp_obj.data.vertices
        delta_dist = inf
        asdf = None
        for vert_index in polygons[hit_poly_index].vertices:
            vert = vertices[vert_index]
            vert_world_co = mat_ws @ vert.co
            vert_ss_co = cast_point_to_ss(context, vert_world_co)
            if vert_ss_co:
                distance = (mouse - vert_ss_co).length
                if distance < delta_dist:
                    delta_dist = distance
                    hit_vert_index = vert_index
                    hit_coord_ws = vert_world_co
    bpy.data.objects.remove(temp_obj)
    return result, hit_coord_ws, hit_normal, hit_vert_index


def cast_to_uneval_object(context, event, obj):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return False, None, None, None
    mouse, ray_org, ray_nor, ray_end = mouse_ray(context, event)
    if obj.original != obj:
        obj = obj.original
    mat_ws = obj.matrix_world.copy()
    mat_ws_inv = mat_ws.inverted_safe()
    origin = mat_ws_inv @ ray_org
    direction = ((mat_ws_inv @ ray_end) - origin).normalized()
    mods_turned_off = [mod for mod in obj.modifiers if mod.show_viewport]
    for mod in reversed(mods_turned_off):
        mod.show_viewport = False
    result, hit_coord_ls, hit_normal, hit_poly_index = obj.ray_cast(origin, direction)
    for mod in reversed(mods_turned_off):
        mod.show_viewport = True
    hit_coord_ws = mat_ws @ hit_coord_ls
    return result, hit_coord_ls, hit_coord_ws, hit_normal, hit_poly_index


def cast_to_bb_sphere(context, obj, m_ray_org, m_ray_end, tolerance_PX=20):
    bb_center, bb_radius = sphere_from_obj_bounds(obj)
    if bb_radius == 0:
        bb_radius = .125
    if round(tolerance_PX, 6) != 0:
        bb_radius += (units_per_pixel_at_depth(context, bb_center) * tolerance_PX) / 2
    intercept_far, intercept_near = intersect_line_sphere(m_ray_org, m_ray_end, bb_center, bb_radius)
    if not intercept_far:
        return None, None
    if not intercept_near:
        intercept_near = m_ray_org
    return intercept_near, intercept_far
