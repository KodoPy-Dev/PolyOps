########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, Quaternion
from .collections import link_object_to_collection, collection_path_settings, scence_collections, ensure_object_collections_visible
from .math3 import loc_matrix, rot_matrix, sca_matrix

########################•########################
"""       TRANSFORM | DATA | PARENT           """
########################•########################

def apply_scale(obj):
    if not (isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh)):
        return
    if all([n == 1 for n in obj.scale]):
        return
    mat =  Matrix.Diagonal(obj.scale).to_4x4()
    if obj.data.is_editmode:
        bm = bmesh.from_edit_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    else:
        obj.data.transform(mat)
    for child in obj.children:
        child.matrix_local = mat @ child.matrix_local
    obj.scale = Vector((1,1,1))


def scale_obj(obj, scale=Vector((1,1,1))):
    if not (isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh)):
        return
    mat = sca_matrix(scale).inverted_safe()
    if obj.data.is_editmode:
        bm = bmesh.from_edit_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)
    else:
        obj.data.transform(mat)
    for child in obj.children:
        child.matrix_local = mat @ child.matrix_local
    obj.scale = scale


def apply_location(obj):
    obj.data.transform(loc_matrix(obj.location))
    obj.location = Vector((0,0,0))


def apply_rotation(obj):
    obj.data.transform(rot_matrix(obj.rotation_quaternion))
    obj.rotation_euler = Euler()


def obj_has_flat_dim(obj):
    return isinstance(obj, bpy.types.Object) and any([abs(dim) == 0 for dim in obj.dimensions[:]])


def parent_object(child, parent):
    if isinstance(child, bpy.types.Object) and isinstance(parent, bpy.types.Object):
        if child.parent:
            unparent_object(child)
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted_safe()


def unparent_object(obj):
    if isinstance(obj, bpy.types.Object) and obj.parent:
        mat = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = mat

########################•########################
"""              CREATE | DELETE              """
########################•########################

def create_obj(context, data_type='MESH', obj_name="Obj", data_name="Data", loc=Vector((0,0,0)), rot=Quaternion(), sca=Vector((1,1,1,)), collection=None, ensure_visible=True):
    data = None
    if data_type == 'MESH':
        data = bpy.data.meshes.new(name=data_name)
    elif data_type == 'LATTICE':
        data = bpy.data.lattices.new(name=data_name)

    obj = bpy.data.objects.new(name=obj_name, object_data=data)

    if collection is None:
        context.collection.objects.link(obj)
    else:
        link_object_to_collection(collection, obj)

    if ensure_visible:
        ensure_object_collections_visible(context, obj)

    obj.matrix_world = Matrix.LocRotScale(loc, rot, sca)
    return obj


def delete_obj(obj):
    if not isinstance(obj, bpy.types.Object): return
    if obj.name not in bpy.data.objects: return
    obj_type = obj.type
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
    if obj_type == 'EMPTY':
        return
    elif obj_type == 'MESH':
        if data.name in bpy.data.meshes:
            bpy.data.meshes.remove(data, do_unlink=True, do_id_user=True, do_ui_user=True)
    elif obj_type == 'LATTICE':
        if data.name in bpy.data.lattices:
            bpy.data.lattices.remove(data, do_unlink=True, do_id_user=True, do_ui_user=True)


def swap_mesh_delete(obj, new_mesh):
    if isinstance(obj, bpy.types.Object) and isinstance(new_mesh, bpy.types.Mesh):
        old_mesh = obj.data
        old_name = old_mesh.name
        old_mesh.name = "X"
        new_mesh.name = old_name
        obj.data = new_mesh
        if old_mesh.name in bpy.data.meshes:
            bpy.data.meshes.remove(old_mesh, do_unlink=True, do_id_user=True, do_ui_user=True)

########################•########################
"""                  SELECT                   """
########################•########################

def select_none(context):
    for obj in context.selected_objects:
        obj.select_set(False, view_layer=context.view_layer)
    context.view_layer.objects.active = None


def select_obj(context, obj, make_active=False):
    if isinstance(obj, bpy.types.Object):
        def select_set(context, obj):
            obj.hide_set(False, view_layer=context.view_layer)
            obj.select_set(True, view_layer=context.view_layer)
            if make_active:
                context.view_layer.objects.active = obj
        # Object Not in a Collection
        if obj.name not in context.scene.objects:
            context.scene.collection.objects.link(obj)
            select_set(context, obj)
        # Object Visible
        elif obj.visible_get(view_layer=context.view_layer):
            select_set(context, obj)
        # Object Not Visible
        else:
            ensure_object_collections_visible(context, obj)
            select_set(context, obj)

########################•########################
"""                  CAPTURE                  """
########################•########################

def obj_children(obj):
    if isinstance(obj, bpy.types.Object):
        return obj.children_recursive
    return []


def obj_parents(obj):
    if not isinstance(obj, bpy.types.Object) or obj.parent is None:
        return []
    stack = set([obj.parent])
    visited = set()
    while stack:
        current = stack.pop()
        visited.add(current)
        parent = current.parent
        if parent:
            if parent not in visited:
                stack.add(parent)
    return list(visited)


def objs_parents_and_children(obj):
    if (not isinstance(obj, bpy.types.Object)) or (not obj.parent and not obj.children):
        return []
    stack = set()
    if obj.parent:
        stack.add(obj.parent)
    if obj.children:
        stack.update([obj for obj in obj.children])
    visited = set()
    while stack:
        current = stack.pop()
        visited.add(current)
        parent = current.parent
        if parent:
            if parent not in visited:
                stack.add(parent)
        for child in current.children_recursive:
            if child not in visited:
                stack.add(child)
    return list(visited)


def get_visible_mesh_obj_by_name(context, obj_name="", update=True):
    view_layer = context.view_layer
    if obj_name in view_layer.objects:
        obj = view_layer.objects[obj_name]
        if obj.visible_get(view_layer=view_layer):
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                if update and obj.data.is_editmode:
                    obj.update_from_editmode()
                return obj
    return None


def get_ID_obj_from_data(context, obj_name='', mesh_name='', require_visible=True):
    if obj_name not in bpy.data.objects: return None
    obj = bpy.data.objects[obj_name]
    if mesh_name not in bpy.data.meshes: return None
    mesh = bpy.data.meshes[mesh_name]
    if obj.data != mesh: return None
    if require_visible:
        view_layer = context.view_layer
        space = context.space_data
        if obj.name not in view_layer.objects: return None
        if space.type != 'VIEW_3D': return None
        if not obj.visible_get(view_layer=view_layer, viewport=space): return None
    return obj

########################•########################
"""                  DISPLAY                  """
########################•########################

def wire_display(obj):
    if isinstance(obj, bpy.types.Object):
        obj.display_type = 'WIRE'


def retopo_display(show=True):
    bpy.context.space_data.overlay.show_retopology = show


def unhide(context, obj):
    if isinstance(obj, bpy.types.Object):
        if obj.name in context.scene.objects:
            if not obj.visible_get(view_layer=context.view_layer):
                ensure_object_collections_visible(context, obj)
                obj.hide_set(False)


