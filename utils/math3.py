########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import mathutils
import bmesh
import numpy as np
from math import cos, sin, radians, sqrt
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from mathutils.geometry import area_tri, convex_hull_2d, intersect_point_line
from bpy_extras.view3d_utils import region_2d_to_origin_3d
from .vec_fade import init as init_vec_fade

########################•########################
"""                   FLOAT                   """
########################•########################

def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


def remap_value(value, min_a, max_a, min_b, max_b):
    if min_a != max_a:
        return min_b + ((value - min_a) / (max_a - min_a)) * (max_b - min_b)
    return value


def round_to_increment(value, increment=15):
    return round(value / increment) * increment


def projected_point_line_factor(point=Vector((0,0,0)), line_p1=Vector((0,0,0)), line_p2=Vector((0,0,0)), clamp_factor=False):
    split_point, factor = intersect_point_line(point, line_p1, line_p2)
    if clamp_factor:
        return clamp(factor, 0, 1)
    return factor

########################•########################
"""                   MATRIX                  """
########################•########################

def loc_matrix(vec3=Vector((0,0,0))):
    loc = Matrix.Translation(vec3)
    return loc


def rot_matrix(quaternion):
    rot = quaternion.to_matrix()
    rot = rot.to_4x4()
    return rot


def sca_matrix(vec3=Vector((1,1,1))):
    sca_mat = Matrix.Diagonal(vec3).to_4x4()
    return sca_mat


def rot_matrix_from_vectors(dir_1=Vector((1,0,0)), dir_2=Vector((0,0,1))):
    return dir_1.rotation_difference(dir_2).to_matrix()


def plane_matrix(point=Vector((0,0,0)), normal=Vector((0,0,1))):
    loc = Matrix.Translation(point)
    rot_quat = normal.to_track_quat('Z', 'Y')
    rot = rot_quat.to_matrix().to_4x4()
    mat = loc @ rot
    return mat


def remove_rot_from_matrix(mat_4x4):
    loc, rot, sca = mat_4x4.decompose()
    mat_loc = Matrix.Translation(loc)
    mat_sca = Matrix.Diagonal(sca).to_4x4()
    return mat_loc @ mat_sca


def inverse_rot_matrix(mat_4x4):
    rot = mat_4x4.to_3x3()
    rot.transpose()
    rot.normalize()
    return rot.to_4x4()


def rotation_matrix_from_perp_vectors(v1=Vector((0,0,0)), v2=Vector((0,0,0)), v3=Vector((0,0,0)), v4=Vector((0,0,0))):
    vec1 = (v1 - v2).normalized()
    vec2 = (v3 - v4).normalized()
    normal = vec1.cross(vec2)
    normal.normalize()
    return Matrix((vec1, vec2, normal)).transposed().to_4x4()


def matrix_loc_rot(matrix):
    if len(matrix) != 4:
        matrix = matrix.to_4x4()
    loc, rot, sca = matrix.decompose()
    sca = Vector((1,1,1,))
    return Matrix.LocRotScale(loc, rot, sca)

########################•########################
"""                   VECTOR                  """
########################•########################

def normal_from_points(v1=Vector((0,0,0)), v2=Vector((0,0,0)), v3=Vector((0,0,0))):
    return geometry.normal((v1, v2, v3))


def center_of_coords(coords=[]):
    if not coords:
        return None
    summed = Vector((0,0,0))
    for coord in coords:
        summed += coord
    return summed / len(coords)


def obj_dimension(obj):
    if isinstance(obj, bpy.types.Object):
        return obj.dimensions
    return None


def rotate_point_around_center_from_view(context, angle=0, point=Vector((0,0,0)), center=Vector((0,0,0))):
    view_no = (context.region_data.view_rotation @ Vector((0,0,1))).normalized()
    return center + (Matrix.Rotation(angle, 3, Vector((0,-1,0))) @ (point - center))


def perp_norm_from_view_with_coord_and_object(context, event, obj, direction=Vector((1,0,0)), plane_co_ls=Vector((0,0,0))):
    screen_ori = Vector((0,0,0))
    if context.region_data.view_perspective == 'PERSP':
        screen_ori = region_2d_to_origin_3d(context.region, context.region_data, (context.area.width, context.area.height))
    else:
        screen_ori = region_2d_to_origin_3d(context.region, context.region_data, (event.mouse_region_x, event.mouse_region_y))
    mat_ws = obj.matrix_world
    ori_to_point = (screen_ori - (mat_ws @ plane_co_ls)).normalized()
    view_no_up = ori_to_point.cross(context.region_data.view_rotation @ direction.normalized())
    return (mat_ws.transposed() @ view_no_up).normalized()


def snap_point_to_vector(point, vector, origin, increment):
    direction = vector.normalized()
    point_vector = point - origin
    projection_length = point_vector.dot(direction)
    snapped_length = round(projection_length / increment) * increment
    snapped_point = origin + direction * snapped_length
    return snapped_point

########################•########################
"""                 QUATERNION                """
########################•########################

def rot_diff_to_z_axis(mat):
    quat = mat.to_quaternion()
    quat.normalize()
    up = Quaternion((0.0, 0.0, 1.0), 0)
    return quat.rotation_difference(up)

########################•########################
"""                 RECTANGLES                """
########################•########################

def rectangle_from_bounds_2d(points=[]):
    points = [point for point in points if isinstance(point, Vector) and len(point) == 2]
    indices = convex_hull_2d(points)
    if not indices:
        return None, None
    corners = [points[index] for index in indices]
    x_coords = [point.x for point in corners]
    y_coords = [point.y for point in corners]
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)
    top_left = Vector((min_x, max_y))
    bottom_right = Vector((max_x, min_y))
    return top_left, bottom_right

########################•########################
"""                 TRIANGLES                 """
########################•########################

def triangles_from_visible_obj_bounds(context, obj):
    if not isinstance(obj, bpy.types.Object):
        return None
    if not obj.visible_get(view_layer=context.view_layer):
        return None
    if not hasattr(context, 'region_data'):
        return None
    if not isinstance(context.region_data, bpy.types.RegionView3D):
        return None
    bb = obj.bound_box
    mat = obj.matrix_world
    p1 = mat @ Vector((bb[0][0], bb[0][1], bb[0][2]))
    p2 = mat @ Vector((bb[1][0], bb[1][1], bb[1][2]))
    p3 = mat @ Vector((bb[2][0], bb[2][1], bb[2][2]))
    p4 = mat @ Vector((bb[3][0], bb[3][1], bb[3][2]))
    p5 = mat @ Vector((bb[4][0], bb[4][1], bb[4][2]))
    p6 = mat @ Vector((bb[5][0], bb[5][1], bb[5][2]))
    p7 = mat @ Vector((bb[6][0], bb[6][1], bb[6][2]))
    p8 = mat @ Vector((bb[7][0], bb[7][1], bb[7][2]))    
    triangles = []
    tri_append = triangles.append
    view_dir = context.region_data.view_rotation @ Vector((0,0,1))
    get_norm = geometry.normal
    # Top
    if get_norm((p2, p6, p7)).dot(view_dir) < 0.0:
        tri_append((p2, p6, p7))
        tri_append((p2, p7, p3))
    # Bottom
    if get_norm((p1, p4, p8)).dot(view_dir) < 0.0:
        tri_append((p1, p4, p8))
        tri_append((p1, p8, p5))
    # Right
    if get_norm((p5, p8, p7)).dot(view_dir) < 0.0:
        tri_append((p5, p8, p7))
        tri_append((p5, p7, p6))
    # Left
    if get_norm((p4, p1, p2)).dot(view_dir) < 0.0:
        tri_append((p4, p1, p2))
        tri_append((p4, p2, p3))
    # Front
    if get_norm((p1, p5, p6)).dot(view_dir) < 0.0:
        tri_append((p1, p5, p6))
        tri_append((p1, p6, p2))
    # Back
    if get_norm((p8, p4, p3)).dot(view_dir) < 0.0:
        tri_append((p8, p4, p3))
        tri_append((p8, p3, p7))
    return triangles


def triangles_from_obj_bounds(obj, transform=True):
    if not isinstance(obj, bpy.types.Object):
        return None
    bb = obj.bound_box
    mat = obj.matrix_world if transform else Matrix.Identity(3)
    p1 = mat @ Vector((bb[0][0], bb[0][1], bb[0][2]))
    p2 = mat @ Vector((bb[1][0], bb[1][1], bb[1][2]))
    p3 = mat @ Vector((bb[2][0], bb[2][1], bb[2][2]))
    p4 = mat @ Vector((bb[3][0], bb[3][1], bb[3][2]))
    p5 = mat @ Vector((bb[4][0], bb[4][1], bb[4][2]))
    p6 = mat @ Vector((bb[5][0], bb[5][1], bb[5][2]))
    p7 = mat @ Vector((bb[6][0], bb[6][1], bb[6][2]))
    p8 = mat @ Vector((bb[7][0], bb[7][1], bb[7][2]))
    return [
    # Top
    (p2, p6, p7), (p2, p7, p3),
    # Bottom
    (p1, p4, p8), (p1, p8, p5),
    # Right
    (p5, p8, p7), (p5, p7, p6),
    # Left
    (p4, p1, p2), (p4, p2, p3),
    # Front
    (p1, p5, p6), (p1, p6, p2),
    # Back
    (p8, p4, p3), (p8, p3, p7)]


def triangle_scale_from_center(v1, v2, v3, factor=2):
    center = (v1 + v2 + v3) / 3
    scale_factor = sqrt(factor)
    v1_offset = ((v1 - center) * scale_factor) + center
    v2_offset = ((v2 - center) * scale_factor) + center
    v3_offset = ((v3 - center) * scale_factor) + center
    return v1_offset, v2_offset, v3_offset

########################•########################
"""                   SPHERES                 """
########################•########################

def sphere_from_obj_bounds(obj):
    bb = obj.bound_box
    mat = obj.matrix_world
    center = Vector((0,0,0))
    for x, y, z in bb:
        center += mat @ Vector((x, y, z))
    center *= .125
    x_min = min([vec[0] for vec in bb])
    x_max = max([vec[0] for vec in bb])
    y_min = min([vec[1] for vec in bb])
    y_max = max([vec[1] for vec in bb])
    z_min = min([vec[2] for vec in bb])
    z_max = max([vec[2] for vec in bb])
    vec_min = mat @ Vector((x_min, y_min, z_min))
    vec_max = mat @ Vector((x_max, y_max, z_max))
    radius = (vec_max - vec_min).length / 2
    return center, radius

########################•########################
"""                   BVHTree                 """
########################•########################

def bvh_tree_from_obj_bounds(obj, tolerance=0.125):
    if not isinstance(obj, bpy.types.Object):
        return None
    bb = obj.bound_box
    norm = 0.5773502588272095
    mat_ws = obj.matrix_world
    verts = [
        (mat_ws @ Vector((bb[0][0], bb[0][1], bb[0][2]))) + Vector((-norm, -norm, -norm)) * tolerance,
        (mat_ws @ Vector((bb[1][0], bb[1][1], bb[1][2]))) + Vector((-norm, -norm,  norm)) * tolerance,
        (mat_ws @ Vector((bb[2][0], bb[2][1], bb[2][2]))) + Vector((-norm,  norm,  norm)) * tolerance,
        (mat_ws @ Vector((bb[3][0], bb[3][1], bb[3][2]))) + Vector((-norm,  norm, -norm)) * tolerance,
        (mat_ws @ Vector((bb[4][0], bb[4][1], bb[4][2]))) + Vector(( norm, -norm, -norm)) * tolerance,
        (mat_ws @ Vector((bb[5][0], bb[5][1], bb[5][2]))) + Vector(( norm, -norm,  norm)) * tolerance,
        (mat_ws @ Vector((bb[6][0], bb[6][1], bb[6][2]))) + Vector(( norm,  norm,  norm)) * tolerance,
        (mat_ws @ Vector((bb[7][0], bb[7][1], bb[7][2]))) + Vector(( norm,  norm, -norm)) * tolerance
    ]
    polys = ((1, 5, 6), (1, 6, 2), (0, 3, 7), (0, 7, 4), (4, 7, 6), (4, 6, 5), (3, 0, 1), (3, 1, 2), (0, 4, 5), (0, 5, 1), (7, 3, 2), (7, 2, 6))
    return BVHTree.FromPolygons(verts, polys, all_triangles=True, epsilon=0.0)


def bvh_tree_from_bmesh_bounds(bm, mat_ws=Matrix.Identity(3), tolerance=0.125):
    if not isinstance(bm, bmesh.types.BMesh):
        return
    if not bm.is_valid:
        return
    min_vec = Vector((float('inf'), float('inf'), float('inf')))
    max_vec = Vector((float('-inf'), float('-inf'), float('-inf')))
    for vert in bm.verts:
        if vert.is_valid:
            min_vec.x = min(min_vec.x, vert.co.x)
            min_vec.y = min(min_vec.y, vert.co.y)
            min_vec.z = min(min_vec.z, vert.co.z)
            max_vec.x = max(max_vec.x, vert.co.x)
            max_vec.y = max(max_vec.y, vert.co.y)
            max_vec.z = max(max_vec.z, vert.co.z)
    norm = 0.5773502588272095
    verts = [
        (mat_ws @ Vector((min_vec.x, min_vec.y, min_vec.z))) + Vector((-norm, -norm, -norm)) * tolerance,
        (mat_ws @ Vector((min_vec.x, min_vec.y, max_vec.z))) + Vector((-norm, -norm,  norm)) * tolerance,
        (mat_ws @ Vector((min_vec.x, max_vec.y, max_vec.z))) + Vector((-norm,  norm,  norm)) * tolerance,
        (mat_ws @ Vector((min_vec.x, max_vec.y, min_vec.z))) + Vector((-norm,  norm, -norm)) * tolerance,
        (mat_ws @ Vector((max_vec.x, min_vec.y, min_vec.z))) + Vector(( norm, -norm, -norm)) * tolerance,
        (mat_ws @ Vector((max_vec.x, min_vec.y, max_vec.z))) + Vector(( norm, -norm,  norm)) * tolerance,
        (mat_ws @ Vector((max_vec.x, max_vec.y, max_vec.z))) + Vector(( norm,  norm,  norm)) * tolerance,
        (mat_ws @ Vector((max_vec.x, max_vec.y, min_vec.z))) + Vector(( norm,  norm, -norm)) * tolerance
    ]
    polys = ((1, 5, 6), (1, 6, 2), (0, 3, 7), (0, 7, 4), (4, 7, 6), (4, 6, 5), (3, 0, 1), (3, 1, 2), (0, 4, 5), (0, 5, 1), (7, 3, 2), (7, 2, 6))
    return BVHTree.FromPolygons(verts, polys, all_triangles=True, epsilon=0.0)

########################•########################
"""                   KDTree                  """
########################•########################

def kd_tree_from_points(points=[]):
    points = [p for p in points if isinstance(p, Vector) and len(p) == 3]
    kd_tree = KDTree(len(points))
    for index, point in enumerate(points):
        if isinstance(point, Vector):
            kd_tree.insert(point, index)
    kd_tree.balance()
    return kd_tree

########################•########################
"""                    MISC                   """
########################•########################

def bounding_box_wires_and_corners(obj, tolerance=0.125):
    mat_ws = obj.matrix_world
    bb = obj.bound_box
    norm = 0.5773502588272095
    p1 = (mat_ws @ Vector((bb[0][0], bb[0][1], bb[0][2]))) + Vector((-norm, -norm, -norm)) * tolerance
    p2 = (mat_ws @ Vector((bb[1][0], bb[1][1], bb[1][2]))) + Vector((-norm, -norm,  norm)) * tolerance
    p3 = (mat_ws @ Vector((bb[2][0], bb[2][1], bb[2][2]))) + Vector((-norm,  norm,  norm)) * tolerance
    p4 = (mat_ws @ Vector((bb[3][0], bb[3][1], bb[3][2]))) + Vector((-norm,  norm, -norm)) * tolerance
    p5 = (mat_ws @ Vector((bb[4][0], bb[4][1], bb[4][2]))) + Vector(( norm, -norm, -norm)) * tolerance
    p6 = (mat_ws @ Vector((bb[5][0], bb[5][1], bb[5][2]))) + Vector(( norm, -norm,  norm)) * tolerance
    p7 = (mat_ws @ Vector((bb[6][0], bb[6][1], bb[6][2]))) + Vector(( norm,  norm,  norm)) * tolerance
    p8 = (mat_ws @ Vector((bb[7][0], bb[7][1], bb[7][2]))) + Vector(( norm,  norm, -norm)) * tolerance
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
    return points, lines
