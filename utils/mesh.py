########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import bmesh
import numpy as np
from math import cos, sin, radians
from bpy.app.handlers import persistent
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from .addon import user_prefs
from .collections import link_object_to_collection, visible_scene_collections
from .context import object_mode_toggle_start, object_mode_toggle_end
from .object import select_obj

########################•########################
"""                 VALIDATORS                """
########################•########################

def mesh_obj_is_valid(context, obj, check_visible=True, check_select=False, check_has_polys=False):
    if not isinstance(obj, bpy.types.Object): return False
    if not isinstance(obj.data, bpy.types.Mesh): return False
    if obj.is_evaluated: return False
    if obj.is_runtime_data: return False
    if obj.data.is_runtime_data: return False
    if obj.name not in bpy.data.objects: return False
    if obj.data.name not in bpy.data.meshes: return False
    view_layer = context.view_layer
    if obj.name not in view_layer.objects: return False
    if check_visible:
        space = context.space_data
        if space.type != 'VIEW_3D': return False
        if not obj.visible_get(view_layer=view_layer, viewport=space): return False
    if check_select:
        if not obj.select_get(view_layer=view_layer): return False
    if check_has_polys:
        if obj.data.is_editmode:
            obj.update_from_editmode()
        if len(obj.data.polygons) == 0: return False
    return True

########################•########################
"""                 MESH COPY                 """
########################•########################

def duplicate_mesh_in_place(context, target_obj, ensure_updated=True):
    if not (isinstance(target_obj, bpy.types.Object) and isinstance(target_obj.data, bpy.types.Mesh)):
        return
    if ensure_updated:
        if target_obj.data.is_editmode:
            target_obj.update_from_editmode()
    obj = target_obj.copy()
    obj.data = target_obj.data.copy()
    obj.animation_data_clear()
    collection = None
    # Place directly into the same collection
    if len(target_obj.users_collection) == 1:
        collection = target_obj.users_collection[0]
    # Attempt to put in best collection
    if collection is None:
        visible_collections = visible_scene_collections(context)            
        for user_collection in target_obj.users_collection:
            if user_collection in visible_collections:
                collection = user_collection
                break
    # Link to active collection
    if collection is None:
        context.collection.objects.link(obj)
    # Link to found collection
    else:
        link_object_to_collection(collection, obj)
    return obj

########################•########################
"""                  V-GROUPS                 """
########################•########################

def create_vgroup(context, obj, name="VGroup", vertex_indices=[]):
    mode = context.mode
    if mode != 'OBJECT':
        object_mode_toggle_start(context)
    vgroup = obj.vertex_groups.new(name=name)
    vgroup.add(vertex_indices, 1, 'ADD')
    if mode != 'OBJECT':
        object_mode_toggle_end(context)
    return vgroup


def vert_index_to_vgroups_map(obj):
    '''
    RET : {Vert Index : [V-Groups]}
    '''

    vert_index_groups_map = {vert.index: [] for vert in obj.data.vertices}
    # KEY -> V-Group Index || VAL -> V-Group
    obj_vgroups_map = {vgroup.index : vgroup for vgroup in obj.vertex_groups}
    if not obj_vgroups_map:
        return vert_index_groups_map
    for vert in obj.data.vertices:
        for group_elem in vert.groups:
            vgroup = obj_vgroups_map[group_elem.group]
            vert_index_groups_map[vert.index].append(vgroup)
    return vert_index_groups_map


def vgroup_data_map(obj):
    '''
    RET : {vgroup : {'VG_VERTS_ALL' : [], 'VG_VERTS_SEL' : [], 'VG_VERTS_VG_REFS' : [], 'VG_MODS' : []}}
    '''

    vgroup_map = {vgroup : {'VG_VERTS_ALL' : [], 'VG_VERTS_SEL' : [], 'VG_VERTS_VG_REFS' : [], 'VG_MODS' : []} for vgroup in obj.vertex_groups}

    if (not isinstance(obj, bpy.types.Object)) or (not isinstance(obj.data, bpy.types.Mesh)) or (not obj.vertex_groups):
        return vgroup_map

    if obj.data.is_editmode:
        obj.update_from_editmode()

    vgroup_index_map = {vgroup.index : vgroup for vgroup in obj.vertex_groups}
    verts_to_groups_map = {vert : [vgroup_index_map[vgroup_elem.group] for vgroup_elem in vert.groups] for vert in obj.data.vertices}

    for vert in obj.data.vertices:
        for vgroup_elem in vert.groups:
            vgroup_index = vgroup_elem.group
            vgroup = vgroup_index_map[vgroup_index]
            
            vgroup_map[vgroup]['VG_VERTS_ALL'].append(vert)
            if vert.select:
                vgroup_map[vgroup]['VG_VERTS_SEL'].append(vert)
            for vgroup in verts_to_groups_map[vert]:
                vgroup_map[vgroup]['VG_VERTS_VG_REFS'].append(vgroup)

    for mod in obj.modifiers:
        if mod.type == 'BEVEL':
            if mod.limit_method == 'VGROUP':
                if mod.vertex_group in obj.vertex_groups:
                    vgroup = obj.vertex_groups[mod.vertex_group]
                    vgroup_map[vgroup]['VG_MODS'].append(mod)
        elif mod.type == 'SOLIDIFY':
            if mod.vertex_group in obj.vertex_groups:
                vgroup = obj.vertex_groups[mod.vertex_group]
                vgroup_map[vgroup]['VG_MODS'].append(mod)
        elif mod.type == 'SIMPLE_DEFORM':
            if mod.vertex_group in obj.vertex_groups:
                vgroup = obj.vertex_groups[mod.vertex_group]
                vgroup_map[vgroup]['VG_MODS'].append(mod)
    
    return vgroup_map

########################•########################
"""                  SHADING                  """
########################•########################

def shade_polygons(obj, use_smooth=True):
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        mesh = obj.data
        if mesh.is_editmode:
            bm = bmesh.from_edit_mesh(mesh)
            for face in bm.faces:
                face.smooth = use_smooth
            bmesh.update_edit_mesh(mesh)
            obj.update_from_editmode()
        else:
            for polygon in obj.data.polygons:
                polygon.use_smooth = use_smooth


def any_polygons_smooth(obj, ensure_updated=True):
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        if ensure_updated:
            if obj.data.is_editmode:
                obj.update_from_editmode()
        for polygon in obj.data.polygons:
            if polygon.use_smooth:
                return True
    return False

########################•########################
"""                    GEO                    """
########################•########################

def edge_indices_from_polygon(obj, polygon_index=0):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    if not (polygon_index < len(obj.data.polygons) and polygon_index >= 0):
        return []
    polygon = obj.data.polygons[polygon_index]
    loops = obj.data.loops
    return [loops[loop_index].edge_index for loop_index in polygon.loop_indices]


def neighboring_polygons_from_polygon_index(obj, polygon_index=0):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    if not (polygon_index < len(obj.data.polygons) and polygon_index >= 0):
        return []
    polygons = obj.data.polygons
    poly_verts = {vert_index for vert_index in polygons[polygon_index].vertices}
    return [neighbor.index for neighbor in polygons if neighbor.index != polygon_index and any([vert_index in neighbor.vertices for vert_index in poly_verts])]


def connected_polygons_from_vert_index(obj, vert_index=0):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    if not (vert_index < len(obj.data.vertices) and vert_index >= 0):
        return []
    polys = obj.data.polygons
    return [poly.index for poly in polys if vert_index in poly.vertices]


def connected_polygons_from_vert_indices(obj, vert_indices=[]):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    vert_indices_set = set(vert_indices)
    if not vert_indices_set:
        return
    polys = obj.data.polygons
    return [poly.index for poly in polys for vert_index in poly.vertices if vert_index in vert_indices_set]


def edge_coords_from_polygon_indices(obj, polygon_indices=[], matrix=None, normals_scalar=1.0, uptdate_mesh=True):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    poly_indices_set = set(polygon_indices)
    if not poly_indices_set:
        return []
    if uptdate_mesh and obj.data.is_editmode:
        obj.update_from_editmode()
    mesh = obj.data
    verts = mesh.vertices
    polys = mesh.polygons
    if matrix:
        if normals_scalar != 1.0:
            return [(matrix @ verts[vert_index].co) + (polys[poly_index].normal * normals_scalar) for poly_index in poly_indices_set for vert_index in polys[poly_index].vertices]
        else:
            return [matrix @ verts[vert_index].co for poly_index in poly_indices_set for vert_index in polys[poly_index].vertices]
    if normals_scalar != 1.0:
        return [verts[vert_index].co + (polys[poly_index].normal * normals_scalar) for poly_index in poly_indices_set for vert_index in polys[poly_index].vertices]
    return [verts[vert_index].co.copy() for poly_index in poly_indices_set for vert_index in polys[poly_index].vertices]


def edge_key_coords_from_polygon_indices(obj, polygon_indices=[], matrix=None, normals_scalar=1.0, uptdate_mesh=True):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    poly_indices_set = set(polygon_indices)
    if not poly_indices_set:
        return []
    if uptdate_mesh and obj.data.is_editmode:
        obj.update_from_editmode()
    mesh = obj.data
    verts = mesh.vertices
    polys = mesh.polygons
    if matrix:
        if normals_scalar != 1.0:
            return [(matrix @ verts[vert_index].co) + (polys[poly_index].normal * normals_scalar) for poly_index in poly_indices_set for edge_verts in polys[poly_index].edge_keys for vert_index in edge_verts]
        else:
            return [matrix @ verts[vert_index].co for poly_index in poly_indices_set for edge_verts in polys[poly_index].edge_keys for vert_index in edge_verts]
    if normals_scalar != 1.0:
        return [verts[vert_index].co + (polys[poly_index].normal * normals_scalar) for poly_index in poly_indices_set for edge_verts in polys[poly_index].edge_keys for vert_index in edge_verts]
    return [verts[vert_index].co.copy() for poly_index in poly_indices_set for edge_verts in polys[poly_index].edge_keys for vert_index in edge_verts]


def triangle_coords_from_polygon_indices(obj, polygon_indices=[], matrix=None, normals_scalar=1.0, uptdate_mesh=True):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return []
    poly_indices_set = set(polygon_indices)
    if not poly_indices_set:
        return []
    if uptdate_mesh and obj.data.is_editmode:
        obj.update_from_editmode()
    mesh = obj.data
    mesh.calc_loop_triangles()
    loop_triangles = mesh.loop_triangles
    verts = mesh.vertices
    if matrix:
        if normals_scalar != 1.0:
            return [(matrix @ verts[vert_index].co) + (triangle.normal * normals_scalar) for triangle in loop_triangles if triangle.polygon_index in poly_indices_set for vert_index in triangle.vertices]
        else:
            return [matrix @ verts[vert_index].co for triangle in loop_triangles if triangle.polygon_index in poly_indices_set for vert_index in triangle.vertices]
    if normals_scalar != 1.0:
        return [verts[vert_index].co + (triangle.normal * normals_scalar) for triangle in loop_triangles if triangle.polygon_index in poly_indices_set for vert_index in triangle.vertices]
    return [verts[vert_index].co.copy() for triangle in loop_triangles if triangle.polygon_index in poly_indices_set for vert_index in triangle.vertices]


def face_triangle_coords_map_from_polygon_indices(obj, polygon_indices=[], matrix=None, uptdate_mesh=True):
    if not isinstance(obj, bpy.types.Object) or not isinstance(obj.data, bpy.types.Mesh):
        return {}
    poly_indices_set = set(polygon_indices)
    if not poly_indices_set:
        return {}
    if uptdate_mesh and obj.data.is_editmode:
        obj.update_from_editmode()
    mesh = obj.data
    mesh.calc_loop_triangles()
    loop_triangles = mesh.loop_triangles
    verts = mesh.vertices
    face_tri_map = {face_index : [] for face_index in poly_indices_set}
    if matrix:
        for loop_triangle in loop_triangles:
            if loop_triangle.polygon_index in poly_indices_set:
                face_tri_map[loop_triangle.polygon_index].extend([matrix @ verts[vert_index].co for vert_index in loop_triangle.vertices])
    else:
        for loop_triangle in loop_triangles:
            if loop_triangle.polygon_index in poly_indices_set:
                face_tri_map[loop_triangle.polygon_index].extend([verts[vert_index].co.copy() for vert_index in loop_triangle.vertices])
    return face_tri_map

########################•########################
"""                  HANDLES                  """
########################•########################

@persistent
def remove_backup_meshes(dummy):
    for mesh in bpy.data.meshes[:]:
        if mesh.ps.is_backup:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
