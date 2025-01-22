########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import enum
import gc
from mathutils import Vector, Matrix

########################•########################
"""                  CAPTURE                  """
########################•########################

''' (NOTE : WIP)
    ID_TYPES = [item.identifier for item in bpy.types.ID.bl_rna.properties['id_type'].enum_items]
    OB_MODES = [item.identifier for item in bpy.types.Context.bl_rna.properties['mode'].enum_items]
'''

EDIT_MODES = {'EDIT_MESH', 'EDIT_CURVE', 'EDIT_SURFACE', 'EDIT_METABALL', 'EDIT_TEXT', 'EDIT_ARMATURE', 'EDIT_LATTICE'}
MESH_MODES = {'OBJECT', 'EDIT_MESH', 'SCULPT', 'PAINT_VERTEX', 'PAINT_WEIGHT', 'PAINT_TEXTURE'}

def get_single_object_from_mode(context):
    if context.mode == 'OBJECT':
        if context.active_object:
            return context.active_object
        if len(context.selected_objects) == 1:
            return context.selected_objects[0]
        return None
    elif context.mode in EDIT_MODES:
        return context.edit_object
    elif context.mode == 'SCULPT':
        return context.sculpt_object
    elif context.mode == 'PAINT_VERTEX':
        return context.vertex_paint_object
    elif context.mode == 'PAINT_WEIGHT':
        return context.weight_paint_object
    elif context.mode == 'PAINT_TEXTURE':
        return context.image_paint_object
    return None


def get_objects(context, single_resolve=False, types={'MESH'}, required_mode='', min_objs=0, active_required=False, selected_only=True, visible_only=True, exclude=[]):
    # Validate Mode
    if required_mode:
        if context.mode != required_mode:
            return None
    def validator(obj):
        if not obj or obj.type not in types:
            return None
        if visible_only and not obj.visible_get():
            return None
        if selected_only and not obj.select_get():
            return None
        return obj
    # Validate Active
    if active_required:
        if not validator(context.active_object):
            return None
    # Single resolvable object
    if single_resolve:
        obj = get_single_object_from_mode(context)
        return validator(obj)
    if required_mode and context.mode in EDIT_MODES:
        objs = [obj for obj in context.objects_in_mode if validator(obj)]
        if len(objs) < min_objs:
            return None
        if exclude:
            return [obj for obj in objs if obj not in exclude]
        return objs
    else:
        if selected_only:
            objs = [obj for obj in context.selected_objects if validator(obj)]
            if len(objs) < min_objs:
                return None
            if exclude:
                return [obj for obj in objs if obj not in exclude]
            return objs
        else:
            objs = [obj for obj in context.scene.objects if validator(obj)]
            if len(objs) < min_objs:
                return None
            if exclude:
                return [obj for obj in objs if obj not in exclude]
            return objs
    return None


def get_objects_selected_or_in_mode(context, types=set()):
    if context.mode in EDIT_MODES:
        if types:
            return [obj for obj in context.objects_in_mode if obj and obj.type in types]
        else:
            return [obj for obj in context.objects_in_mode if obj]
    if types:
        return [obj for obj in context.selected_objects if obj and obj.type in types]
    return [obj for obj in context.selected_objects if obj]


def get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False):
    if context.mode not in MESH_MODES:
        return []
    if context.mode == 'OBJECT':
        if object_mode_require_selection:
            return [obj for obj in context.selected_editable_objects if obj and obj.type == 'MESH' and obj.select_get()]
        else:
            return [obj for obj in context.selected_editable_objects if obj and obj.type == 'MESH']
    elif context.mode == 'EDIT_MESH':
        if edit_mesh_mode_require_selection:
            return [obj for obj in context.objects_in_mode if obj and obj.type == 'MESH' and obj.select_get()]
        else:
            return [obj for obj in context.objects_in_mode if obj and obj.type == 'MESH']
    elif context.mode in MESH_MODES:
        obj = get_single_object_from_mode(context)
        if obj and obj.type == 'MESH':
            if other_mesh_modes_require_selection and obj.select_get():
                return [obj]
            else:
                return [obj]
    return []


def get_mesh_objs_from_edit_mode_if_verts_selected(context):
    objs = []
    if context.mode == 'EDIT_MESH':
        for obj in context.objects_in_mode:
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                obj.update_from_editmode()
                for vert in obj.data.vertices:
                    if vert.select:
                        objs.append(obj)
                        break
    gc.collect()
    return objs


def get_mesh_objs_from_edit_mode_if_edges_selected(context):
    objs = []
    if context.mode == 'EDIT_MESH':
        for obj in context.objects_in_mode:
            bm = bmesh.from_edit_mesh(obj.data)
            for edge in bm.edges:
                if edge.select:
                    objs.append(obj)
                    bm.free()
                    bm = None
                    break
    gc.collect()
    return objs


def get_mesh_objs_from_edit_mode_if_polygons_selected(context):
    objs = []
    if context.mode == 'EDIT_MESH':
        for obj in context.objects_in_mode:
            if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
                obj.update_from_editmode()
                for polygon in obj.data.polygons:
                    if polygon.select:
                        objs.append(obj)
                        break
    gc.collect()
    return objs


def get_mesh_from_edit_or_mesh_from_active(context):
    if context.mode == 'EDIT_MESH':
        return context.edit_object
    if isinstance(context.active_object, bpy.types.Object) and isinstance(context.active_object.data, bpy.types.Mesh):
        return context.active_object
    return None


def get_meshes_from_edit_or_from_selected(context):
    if context.mode == 'EDIT_MESH':
        return context.objects_in_mode
    return [obj for obj in context.selected_editable_objects if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh)]

########################•########################
"""                    TOOLS                  """
########################•########################

VERT = False
EDGE = False
FACE = False

def save_current_select_mode(context):
    global VERT, EDGE, FACE
    VERT, EDGE, FACE = context.tool_settings.mesh_select_mode[:]


def restore_to_last_select_mode(context):
    global VERT, EDGE, FACE
    context.tool_settings.mesh_select_mode = (VERT, EDGE, FACE)


def append_vert_select_mode(context):
    if context.tool_settings.mesh_select_mode[0] == False:
        select_settings = context.tool_settings.mesh_select_mode
        context.tool_settings.mesh_select_mode = (True, select_settings[1], select_settings[2])


def append_edge_select_mode(context):
    if context.tool_settings.mesh_select_mode[1] == False:
        select_settings = context.tool_settings.mesh_select_mode
        context.tool_settings.mesh_select_mode = (select_settings[0], True, select_settings[2])


def append_face_select_mode(context):
    if context.tool_settings.mesh_select_mode[2] == False:
        select_settings = context.tool_settings.mesh_select_mode
        context.tool_settings.mesh_select_mode = (select_settings[0], select_settings[1], True)


def set_component_selection(context, values=(False, True, False)):
    context.tool_settings.mesh_select_mode = values

########################•########################
"""                3D VIEW PORT               """
########################•########################

def view_3d_redraw(interval=1.0):
    bpy.app.timers.register(view3d_tag_redraw, first_interval=interval)


def view3d_tag_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return None


def view3d_region():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        return region
    return None

REGION_HUD = True
REGION_TOOLBAR = True
REGION_UI = True

def hide_3d_panels(context):
    if context.space_data.type == 'VIEW_3D':
        if hasattr(context.space_data, 'show_region_hud') and hasattr(context.space_data, 'show_region_toolbar') and hasattr(context.space_data, 'show_region_ui'):
            global REGION_HUD, REGION_TOOLBAR, REGION_UI
            REGION_HUD = bool(context.space_data.show_region_hud)
            REGION_TOOLBAR = bool(context.space_data.show_region_toolbar)
            REGION_UI = bool(context.space_data.show_region_ui)
            if context.space_data.show_region_hud:
                context.space_data.show_region_hud = False
            if context.space_data.show_region_toolbar:
                context.space_data.show_region_toolbar = False
            if context.space_data.show_region_ui:
                context.space_data.show_region_ui = False


def restore_3d_panels(context):
    if context.space_data.type == 'VIEW_3D':
        if hasattr(context.space_data, 'show_region_hud') and hasattr(context.space_data, 'show_region_toolbar') and hasattr(context.space_data, 'show_region_ui'):
            if REGION_HUD:
                context.space_data.show_region_hud = True
            if REGION_TOOLBAR:
                context.space_data.show_region_toolbar = True
            if REGION_UI:
                context.space_data.show_region_ui = True


def rv3d_view_direction(context, direction='Z'):
    if direction == 'Z':
        return context.region_data.view_rotation @ Vector((0,0,1))
    if direction == 'X':
        return context.region_data.view_rotation @ Vector((1,0,0))
    if direction == 'Y':
        return context.region_data.view_rotation @ Vector((0,1,0))


def rv3d_view_rotation(context):
    return context.region_data.view_rotation


def rv3d_view_location(context):
    return context.region_data.view_location

########################•########################
"""                    MODE                   """
########################•########################

def set_mode(target_mode='OBJECT'):
    if target_mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    elif bpy.context.view_layer.objects.active is not None:
        if target_mode in {'EDIT', 'EDIT_MESH', 'EDIT_CURVE'}:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        elif target_mode in {'SCULPT'}:
            bpy.ops.object.mode_set(mode='SCULPT', toggle=False)
        elif target_mode in {'PAINT_VERTEX', 'VERTEX_PAINT'}:
            bpy.ops.object.mode_set(mode='VERTEX_PAINT', toggle=False)
        elif target_mode in {'PAINT_WEIGHT', 'WEIGHT_PAINT'}:
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT', toggle=False)
        elif target_mode in {'PAINT_TEXTURE', 'TEXTURE_PAINT'}:
            bpy.ops.object.mode_set(mode='TEXTURE_PAINT', toggle=False)

ORIGINAL_MODE = None
ORIGINAL_ACTIVE = None
ORIGINAL_SELECTION = None
ORIGINAL_IN_MODE = None

def object_mode_toggle_reset():
    global ORIGINAL_MODE, ORIGINAL_ACTIVE, ORIGINAL_SELECTION, ORIGINAL_IN_MODE
    ORIGINAL_MODE = None
    ORIGINAL_ACTIVE = None
    ORIGINAL_SELECTION = None
    ORIGINAL_IN_MODE = None


def object_mode_toggle_start(context):
    if context.mode == 'OBJECT':
        return False
    global ORIGINAL_MODE, ORIGINAL_ACTIVE, ORIGINAL_SELECTION, ORIGINAL_IN_MODE
    ORIGINAL_MODE = context.mode
    ORIGINAL_ACTIVE = context.view_layer.objects.active
    ORIGINAL_SELECTION = context.selected_objects[:]
    ORIGINAL_IN_MODE = context.objects_in_mode[:]
    set_mode(target_mode='OBJECT')
    return True


def object_mode_toggle_end(context):
    global ORIGINAL_MODE, ORIGINAL_ACTIVE, ORIGINAL_SELECTION, ORIGINAL_IN_MODE
    if ORIGINAL_MODE is None or context.mode == ORIGINAL_MODE:
        return
    try:
        bpy.ops.object.select_all(action='DESELECT')
        if isinstance(ORIGINAL_ACTIVE, bpy.types.Object):
            context.view_layer.objects.active = ORIGINAL_ACTIVE
        if isinstance(ORIGINAL_IN_MODE, list):
            for obj in ORIGINAL_IN_MODE:
                if isinstance(obj, bpy.types.Object):
                    obj.select_set(True)
        set_mode(target_mode=ORIGINAL_MODE)
        if isinstance(ORIGINAL_SELECTION, list):
            for obj in ORIGINAL_SELECTION:
                if isinstance(obj, bpy.types.Object):
                    obj.select_set(True)
    except: pass
    object_mode_toggle_reset()

