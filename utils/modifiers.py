########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
from math import radians
from ..resources.blends import autosmooth_nodes
from .bmu import query_any_polygons_shaded_smooth, query_sel_vert_indices
from .context import object_mode_toggle_start, object_mode_toggle_end
from .collections import boolean_collection, link_object_to_collection, collection_path_settings, unlink_object_from_all_collections
from .data import capture_prop_maps, transfer_props
from .mesh import duplicate_mesh_in_place, create_vgroup, vgroup_data_map, shade_polygons
from .object import parent_object, wire_display, obj_has_flat_dim
from .addon import user_prefs
from .guards import except_guard

########################•########################
"""                 CONSTANTS                 """
########################•########################

DEG_60 = radians(60)
DEG_30 = radians(30)
DEG_01 = radians(1)

########################•########################
"""                  SHADING                  """
########################•########################

def last_auto_smooth_mod(obj):
    if isinstance(obj, bpy.types.Object) and obj.type in {'MESH', 'CURVE'}:
        for mod in reversed(obj.modifiers):
            if mod.type == TYPES.NODES:
                if is_auto_smooth_modifier(mod):
                    return mod
    return None


def last_weighted_normal_mod(obj):
    if isinstance(obj, bpy.types.Object) and isinstance(obj.data, bpy.types.Mesh):
        for mod in reversed(obj.modifiers):
            if mod.type == TYPES.WEIGHTED_NORMAL:
                return True
    return False


def is_auto_smooth_modifier(mod):
    if mod.type == 'NODES':
        if mod.node_group:
            if mod.node_group.is_modifier:
                if all(word in mod.name.lower() for word in {'smooth', 'by', 'angle'}):
                    if all([item.name.lower() in {'mesh', 'angle', 'ignore sharpness'} for item in mod.node_group.interface.items_tree]):
                        return True
    return False


def last_auto_smooth_angle(obj):
    mod = last_auto_smooth_mod(obj)
    if isinstance(mod, bpy.types.Modifier):
        if 'Input_1' in mod:
            return mod['Input_1']
    return None


def setup_shading(obj, use_smooth=True, auto_smooth=True, weighted_normal=True, angle=DEG_30):
    if not isinstance(obj, bpy.types.Object) or obj.type not in {'MESH', 'CURVE'}:
        return
    # Mesh Shading
    if obj.type == 'MESH':
        shade_polygons(obj, use_smooth=use_smooth)
    elif obj.type == 'CURVE':
        for spline in obj.data.splines:
            spline.use_smooth = use_smooth
    # Find the last Auto-Smooth and Weighted-Normal
    auto_smooth_mod = None
    weighted_normal_mod = None
    for mod in reversed(obj.modifiers):
        if (auto_smooth_mod and weighted_normal_mod) or (obj.type != 'MESH' and auto_smooth_mod):
            break
        if not auto_smooth_mod:
            if is_auto_smooth_modifier(mod):
                auto_smooth_mod = mod
        if not weighted_normal_mod:
            if obj.type == 'MESH':
                if mod.type == TYPES.WEIGHTED_NORMAL:
                    weighted_normal_mod = mod
    # Setup Auto-Smooth
    if auto_smooth:
        if not auto_smooth_mod:
            auto_smooth_mod = obj.modifiers.new("Smooth by Angle", 'NODES')
        auto_smooth_mod.node_group = autosmooth_nodes()
        auto_smooth_mod.show_expanded = False
        auto_smooth_mod["Input_1"] = angle if angle != None else DEG_30
    # Remove Auto-Smooth
    elif not auto_smooth and auto_smooth_mod:
        obj.modifiers.remove(auto_smooth_mod)
    # Setup Weighted-Normal
    if weighted_normal and obj.type == 'MESH':
        if not weighted_normal_mod:
            weighted_normal_mod = obj.modifiers.new("WeightedNormal", TYPES.WEIGHTED_NORMAL)
        weighted_normal_mod.show_expanded = False
        weighted_normal_mod.keep_sharp = True
    # Remove Weighted-Normal
    elif not weighted_normal and weighted_normal_mod:
        obj.modifiers.remove(weighted_normal_mod)

########################•########################
"""                  MANAGMENT                """
########################•########################

class TYPES:
    ARRAY = 'ARRAY'
    BEVEL = 'BEVEL'
    BOOLEAN = 'BOOLEAN'
    CLOTH = 'CLOTH'
    COLLISION = 'COLLISION'
    DYNAMIC_PAINT = 'DYNAMIC_PAINT'
    EDGE_SPLIT = 'EDGE_SPLIT'
    EXPLODE = 'EXPLODE'
    FLUID = 'FLUID'
    MIRROR = 'MIRROR'
    NODES = 'NODES'
    OCEAN = 'OCEAN'
    PARTICLE_INSTANCE = 'PARTICLE_INSTANCE'
    PARTICLE_SYSTEM = 'PARTICLE_SYSTEM'
    SIMPLE_DEFORM = 'SIMPLE_DEFORM'
    SOFT_BODY = 'SOFT_BODY'
    SOLIDIFY = 'SOLIDIFY'
    SUBSURF = 'SUBSURF'
    TRIANGULATE = 'TRIANGULATE'
    WEIGHTED_NORMAL = 'WEIGHTED_NORMAL'
    WELD = 'WELD'
    WIREFRAME = 'WIREFRAME'
    UNSORTABLE = {SOFT_BODY}
    SORTABLE_TOP = {MIRROR, BEVEL, SOLIDIFY, SIMPLE_DEFORM, EDGE_SPLIT, SUBSURF}
    SORTABLE_BOT = {MIRROR, WELD, NODES, WEIGHTED_NORMAL, ARRAY, SIMPLE_DEFORM, TRIANGULATE}


def sort_all_mods(obj):
    if not isinstance(obj, bpy.types.Object):
        return
    if len(obj.modifiers) < 2:
        return
    options = user_prefs().sort
    if not options.sort_enabled:
        return

    ignore_str = options.ignore_sort_str.replace(" ", "")
    ignored_mods_map = {mod.name: index for index, mod in enumerate(obj.modifiers) if ignore_str in mod.name}

    top_sorted_mods = set(sort_top_mods(obj))
    sort_mid_mods(obj, top_sorted_mods=top_sorted_mods)
    sort_bot_mods(obj, top_sorted_mods=top_sorted_mods)

    if ignored_mods_map:
        for mod_name, to_index in ignored_mods_map.items():
            from_index = obj.modifiers.find(mod_name)
            if from_index >= 0 and to_index < len(obj.modifiers) and from_index != to_index:
                obj.modifiers.move(from_index, to_index)


def sort_top_mods(obj, perform_move=True):
    if not isinstance(obj, bpy.types.Object):
        return []
    if len(obj.modifiers) < 2:
        return []
    options = user_prefs().sort
    if not options.sort_enabled:
        return []
    if not any([options.top_mirror, options.top_bevel, options.top_solidify, options.top_deform, options.top_edge_split, options.top_subsurf]):
        return []
    mods = [mod for mod in obj.modifiers if mod.type in TYPES.SORTABLE_TOP]
    if not mods:
        return []
    ignore_str = options.ignore_sort_str.replace(" ", "")
    sorted_mods = []
    top_counts = {TYPES.MIRROR:0, TYPES.BEVEL:0, TYPES.SOLIDIFY:0, TYPES.SIMPLE_DEFORM:0, TYPES.EDGE_SPLIT:0, TYPES.SUBSURF:0}
    for mod in mods:
        # Ignore
        if ignore_str and ignore_str in mod.name:
            continue
        # Types Check
        if mod.type == TYPES.MIRROR:
            if options.top_mirror:
                if options.top_mirror_check_no_bisect and any([mod.use_bisect_axis[i] for i in range(3)]):
                    continue
                if options.top_mirror_check_no_object and mod.mirror_object:
                    continue
                if top_counts[TYPES.MIRROR] < options.top_mirror_count:
                    top_counts[TYPES.MIRROR] += 1
                    sorted_mods.insert(0, mod)
        elif mod.type == TYPES.BEVEL:
            if options.top_bevel:
                if options.top_bevel_require_vgroup and (mod.limit_method != 'VGROUP' or not mod.vertex_group):
                    continue
                if top_counts[TYPES.BEVEL] < options.top_bevel_count:
                    top_counts[TYPES.BEVEL] += 1
                    sorted_mods.append(mod)
        elif mod.type == TYPES.SOLIDIFY:
            if options.top_solidify:
                if options.top_solidify_require_vgroup and not mod.vertex_group:
                    continue
                if top_counts[TYPES.SOLIDIFY] < options.top_solidify_count:
                    top_counts[TYPES.SOLIDIFY] += 1
                    sorted_mods.append(mod)
        elif mod.type == TYPES.SIMPLE_DEFORM:
            if options.top_deform:
                if options.top_deform_require_vgroup and not mod.vertex_group:
                    continue
                if top_counts[TYPES.SIMPLE_DEFORM] < options.top_deform_count:
                    top_counts[TYPES.SIMPLE_DEFORM] += 1
                    sorted_mods.append(mod)
        elif mod.type == TYPES.EDGE_SPLIT:
            if options.top_edge_split:
                if options.top_edge_split_require_sharp and not mod.use_edge_sharp:
                    continue
                if top_counts[TYPES.EDGE_SPLIT] < options.top_edge_split_count:
                    top_counts[TYPES.EDGE_SPLIT] += 1
                    sorted_mods.append(mod)
        elif mod.type == TYPES.SUBSURF:
            if options.top_subsurf:
                if top_counts[TYPES.SUBSURF] < options.top_subsurf_count:
                    top_counts[TYPES.SUBSURF] += 1
                    sorted_mods.append(mod)
    if perform_move:
        min_index = 1 if obj.modifiers[0].type in TYPES.UNSORTABLE else 0
        for index, mod in enumerate(sorted_mods):
            from_index = obj.modifiers.find(mod.name)
            to_index = min_index + index
            if from_index != to_index:
                obj.modifiers.move(from_index, to_index)
    return sorted_mods


def sort_mid_mods(obj, top_sorted_mods=set()):
    if not isinstance(obj, bpy.types.Object):
        return
    if len(obj.modifiers) < 2:
        return
    options = user_prefs().sort
    if not options.sort_enabled:
        return
    top_sorted_mods = top_sorted_mods if top_sorted_mods else set(sort_top_mods(obj, perform_move=False))
    mods = [mod for mod in obj.modifiers if mod not in top_sorted_mods]
    ignore_str = options.ignore_sort_str.replace(" ", "")
    mid_mods = []
    target_mod = None
    for mod in reversed(mods):
        # Ignore
        if ignore_str and ignore_str in mod.name:
            continue
        # Types
        if mod.type == TYPES.BEVEL:
            if options.boolean_to_bevel:
                target_mod = mod
                break
        elif mod.type == TYPES.SOLIDIFY:
            if options.boolean_to_solidify:
                target_mod = mod
                break
        elif mod.type == TYPES.SUBSURF:
            if options.boolean_to_subsurf:
                target_mod = mod
                break
        elif mod.type == TYPES.ARRAY:
            if options.boolean_to_array:
                target_mod = mod
                break
        elif mod.type == TYPES.BOOLEAN:
            mid_mods.append(mod)
    if target_mod and mid_mods:
        for mod in mid_mods:
            from_index = obj.modifiers.find(mod.name)
            to_index = obj.modifiers.find(target_mod.name)
            if from_index >= 0 and to_index >= 0:
                if from_index < len(obj.modifiers) and to_index < len(obj.modifiers):
                    if from_index != to_index:
                        obj.modifiers.move(from_index, to_index)


def sort_bot_mods(obj, top_sorted_mods=set()):
    if not isinstance(obj, bpy.types.Object):
        return
    if len(obj.modifiers) < 2:
        return
    options = user_prefs().sort
    if not options.sort_enabled:
        return
    top_sorted_mods = top_sorted_mods if top_sorted_mods else set(sort_top_mods(obj, perform_move=False))
    ignore_str = options.ignore_sort_str.replace(" ", "")
    mods = [mod for mod in obj.modifiers if (mod not in top_sorted_mods) and (ignore_str and ignore_str not in mod.name)]
    mods.reverse()
    mod_types = {mod.type for mod in mods}
    sorted_mods = []
    if TYPES.MIRROR in mod_types:
        for mod in mods:
            if mod.type == TYPES.MIRROR:
                sorted_mods.append(mod)
                break
    if TYPES.WELD in mod_types:
        for mod in mods:
            if mod.type == TYPES.WELD:
                sorted_mods.append(mod)
                break
    if TYPES.NODES in mod_types:
        for mod in mods:
            if mod.type == TYPES.NODES:
                if is_auto_smooth_modifier(mod):
                    sorted_mods.append(mod)
                    break
    if TYPES.WEIGHTED_NORMAL in mod_types:
        for mod in mods:
            if mod.type == TYPES.WEIGHTED_NORMAL:
                sorted_mods.append(mod)
                break
    if TYPES.ARRAY in mod_types:
        for mod in mods:
            if mod.type == TYPES.ARRAY:
                sorted_mods.append(mod)
                break
    if TYPES.SIMPLE_DEFORM in mod_types:
        for mod in mods:
            if mod.type == TYPES.SIMPLE_DEFORM:
                sorted_mods.append(mod)
                break
    if TYPES.TRIANGULATE in mod_types:
        for mod in mods:
            if mod.type == TYPES.TRIANGULATE:
                sorted_mods.append(mod)
                break
    to_index = len(obj.modifiers) - 1
    if to_index >= 0:
        for mod in sorted_mods:
            from_index = obj.modifiers.find(mod.name)
            if from_index != to_index:
                obj.modifiers.move(from_index, to_index)


def get_all_of_type(obj, mod_type=TYPES.MIRROR):
    return [mod for mod in obj.modifiers if mod.type == mod_type]


def add(obj, mod_type=TYPES.MIRROR):
    name = mod_type.replace("_", " ").title()
    mod = obj.modifiers.new(name=name, type=mod_type)
    mod.show_expanded = False    
    return mod


def vp_visibility_map(obj):
    return {mod : mod.show_viewport for mod in obj.modifiers}


def set_vp_visibility_from_map(obj, vis_map={}):
    for mod in obj.modifiers:
        if mod in vis_map:
            mod.show_viewport = vis_map[mod]


def apply_with_map(context, obj_mods_map={}):
    if not obj_mods_map: return
    original_active = context.view_layer.objects.active
    toggle = object_mode_toggle_start(context)
    for obj, mods in obj_mods_map.items():
        if isinstance(obj, bpy.types.Object) and isinstance(mods, list):
            if obj.name in context.scene.objects:
                context.view_layer.objects.active = obj
                for mod in mods:
                    if isinstance(mod, bpy.types.Modifier):
                        bpy.ops.object.modifier_apply(modifier=mod.name)
    if toggle: object_mode_toggle_end(context)
    context.view_layer.objects.active = original_active


def apply_mods_with_leave_opts(context, obj, leave_first_bevel=False, leave_last_auto_smooth=False, leave_last_weighted_normal=False):
    if not isinstance(obj, bpy.types.Object): return
    if obj.name not in context.scene.objects: return
    if obj.name not in context.view_layer.objects: return
    original_active = context.view_layer.objects.active
    toggle = object_mode_toggle_start(context)
    context.view_layer.objects.active = obj

    mods_to_skip = set()
    if leave_last_auto_smooth or leave_last_weighted_normal:
        for mod in reversed(obj.modifiers):
            if leave_last_auto_smooth and mod.type == TYPES.NODES and is_auto_smooth_modifier(mod):
                leave_last_auto_smooth = False
                mods_to_skip.add(mod)
            elif leave_last_weighted_normal and mod.type == TYPES.WEIGHTED_NORMAL:
                leave_last_weighted_normal = False
                mods_to_skip.add(mod)
            if not leave_last_auto_smooth and not leave_last_weighted_normal:
                break
    if leave_first_bevel:
        for mod in obj.modifiers:
            if mod.type == TYPES.BEVEL:
                mods_to_skip.add(mod)
                break

    for mod in obj.modifiers[:]:
        if mod not in mods_to_skip:
            bpy.ops.object.modifier_apply(modifier=mod.name)

    if toggle: object_mode_toggle_end(context)
    context.view_layer.objects.active = original_active


def apply_all_booleans(context, obj):
    if not isinstance(obj, bpy.types.Object): return
    if obj.name not in context.scene.objects: return
    if obj.name not in context.view_layer.objects: return
    original_active = context.view_layer.objects.active
    toggle = object_mode_toggle_start(context)
    context.view_layer.objects.active = obj

    for mod in obj.modifiers[:]:
        if mod.type == TYPES.BOOLEAN:
            bpy.ops.object.modifier_apply(modifier=mod.name)

    if toggle: object_mode_toggle_end(context)
    context.view_layer.objects.active = original_active


def apply_mods_with_vgroups(context, obj):
    if not isinstance(obj, bpy.types.Object): return
    if obj.name not in context.scene.objects: return
    if obj.name not in context.view_layer.objects: return
    original_active = context.view_layer.objects.active
    toggle = object_mode_toggle_start(context)
    context.view_layer.objects.active = obj

    for mod in obj.modifiers[:]:
        if hasattr(mod, 'vertex_group'):
            if mod.type == TYPES.BEVEL and mod.limit_method == 'VGROUP':
                bpy.ops.object.modifier_apply(modifier=mod.name)
            elif mod.vertex_group:
                bpy.ops.object.modifier_apply(modifier=mod.name)

    if toggle: object_mode_toggle_end(context)
    context.view_layer.objects.active = original_active


def apply_first_mirror(context, obj):
    if not isinstance(obj, bpy.types.Object): return
    if obj.name not in context.scene.objects: return
    if obj.name not in context.view_layer.objects: return
    original_active = context.view_layer.objects.active
    toggle = object_mode_toggle_start(context)
    context.view_layer.objects.active = obj

    for mod in obj.modifiers[:]:
        if mod.type == TYPES.MIRROR:
            bpy.ops.object.modifier_apply(modifier=mod.name)
            break

    if toggle: object_mode_toggle_end(context)
    context.view_layer.objects.active = original_active

########################•########################
"""                  CAPTURE                  """
########################•########################

def objects_from_node_tree(tree):
    
    def traverse(tree, objs, visited):
        if tree in visited:
            return        
        visited.add(tree)
        for node in tree.nodes:
            if type(node) == bpy.types.GeometryNodeGroup:
                if hasattr(node, 'node_tree'):
                    traverse(node.node_tree, objs, visited)
            for socket in node.inputs:
                if socket.bl_idname == 'NodeSocketObject':
                    if socket.is_linked:
                        for link in socket.links:
                            from_socket = link.from_socket
                            if from_socket.bl_idname == 'NodeSocketObject':
                                obj = from_socket.default_value
                                if obj:
                                    objs.add(obj)
                    else:
                        obj = socket.default_value
                        if obj:
                            objs.add(obj)
    objs = set()
    visited = set()
    traverse(tree, objs, visited)
    return list(objs)


def referenced_objects(obj):

    def recursive(obj, objs):
        if obj in objs:
            return
        if obj is None:
            return
        objs.add(obj)
        if not hasattr(obj, 'modifiers'):
            return
        for mod in obj.modifiers:
            if mod.type == 'NODES':
                tree_objs = objects_from_node_tree(mod.node_group)
                for tree_obj in tree_objs:
                    recursive(tree_obj, objs)
                continue
            for item in dir(mod):
                attr = getattr(mod, item)
                if type(attr) == bpy.types.Object:
                    recursive(attr, objs)
    objs = set()
    recursive(obj, objs)
    return list(objs)


def referenced_booleans(obj):

    def recursive(obj, objs):
        if obj in objs:
            return
        if obj is None:
            return
        if not hasattr(obj, 'modifiers'):
            return
        objs.add(obj)
        for mod in obj.modifiers:
            if mod.type == TYPES.BOOLEAN:
                for item in dir(mod):
                    attr = getattr(mod, item)
                    if type(attr) == bpy.types.Object:
                        if attr.type == 'MESH':
                            recursive(attr, objs)
    starting_obj = obj
    objs = set()
    recursive(obj, objs)
    if starting_obj in objs:
        objs.remove(starting_obj)
    return list(objs)


def boolean_objs_from_mods(obj):
    objs = []
    for mod in obj.modifiers:
        if mod.type == TYPES.BOOLEAN:
            for item in dir(mod):
                attr = getattr(mod, item)
                if type(attr) == bpy.types.Object:
                    if attr.type == 'MESH':
                        objs.append(attr)
                        break
    return objs

########################•########################
"""               MOD SETUP SYSTEMS           """
########################•########################

def mod_is_valid(mod, mod_type=''):
    if mod_type == TYPES.BEVEL:
        if isinstance(mod, bpy.types.BevelModifier):
            return True
    elif mod_type == TYPES.SOLIDIFY:
        if isinstance(mod, bpy.types.SolidifyModifier):
            return True
    elif mod_type == TYPES.SIMPLE_DEFORM:
        if isinstance(mod, bpy.types.SimpleDeformModifier):
            return True
    return False


def assign_vgroup_to_mod(obj, mod, vgroup, mod_type=''):
    if not mod_is_valid(mod, mod_type):
        return
    if mod_type == TYPES.BEVEL:
        mod.limit_method = 'VGROUP'
        mod.vertex_group = vgroup.name
    elif mod.type == TYPES.SOLIDIFY:
        mod.vertex_group = vgroup.name
    elif mod.type == TYPES.SIMPLE_DEFORM:
        mod.vertex_group = vgroup.name


def defualt_settings(mod, mod_type=''):
    if not mod_is_valid(mod, mod_type):
        return    
    mod.show_expanded = False
    if mod_type == TYPES.BEVEL:
        mod.affect = 'EDGES'
        mod.offset_type = 'OFFSET'
        mod.width = 0.1
        mod.segments = 3
        mod.limit_method = 'ANGLE'
        mod.angle_limit = 0.523599
        mod.profile_type = 'SUPERELLIPSE'
        mod.profile = 0.5
        mod.miter_outer = 'MITER_ARC'
        mod.miter_inner = 'MITER_SHARP'
        mod.vmesh_method = 'ADJ'
        mod.use_clamp_overlap = False
        mod.loop_slide = True
        mod.harden_normals = False
        mod.mark_seam = False
        mod.mark_sharp = False
        mod.material = -1
        mod.face_strength_mode = 'FSTR_NONE'
    elif mod_type == TYPES.SOLIDIFY:
        mod.solidify_mode = 'EXTRUDE'
        mod.thickness = 0.125
        mod.offset = 0
        mod.use_even_offset = True
        mod.use_rim = True
        mod.use_rim_only = False
        mod.use_flip_normals = False
        mod.use_quality_normals = True
        mod.material_offset = 0
        mod.material_offset_rim = 0
        mod.edge_crease_inner = 0
        mod.edge_crease_outer = 0
        mod.edge_crease_rim = 0
        mod.bevel_convex = 0
        mod.thickness_clamp = 0
    elif mod_type == TYPES.SIMPLE_DEFORM:
        mod.deform_method = 'TWIST'
        mod.angle = radians(45)
        mod.origin = None
        mod.deform_axis = 'X'
        mod.limits[0] = 0
        mod.limits[1] = 1
        mod.lock_x = False
        mod.lock_y = False
        mod.lock_z = False
        mod.vertex_group = ''


def mods_of_type_using_vgroups(obj, mod_type=''):
    if mod_type == TYPES.BEVEL:
        return [mod for mod in obj.modifiers if mod and mod.type == TYPES.BEVEL and mod.limit_method == 'VGROUP' and mod.vertex_group]
    elif mod_type == TYPES.SOLIDIFY:
        return [mod for mod in obj.modifiers if mod and mod.type == TYPES.SOLIDIFY and mod.vertex_group]
    elif mod_type == TYPES.SIMPLE_DEFORM:
        return [mod for mod in obj.modifiers if mod and mod.type == TYPES.SIMPLE_DEFORM and mod.vertex_group]
    return []


def vgroup_mods_map_from_obj(obj, mod_type=''):
    '''
    RET : {vgroup_name : [mods using this vgroup]}
    '''

    mods = mods_of_type_using_vgroups(obj, mod_type)
    if not mods:
        return {}

    if mod_type == TYPES.BEVEL:
        vgroup_mods_map = {mod.vertex_group : [] for mod in mods}
        for mod in mods:
            vgroup_mods_map[mod.vertex_group].append(mod)
        return vgroup_mods_map

    elif mod_type == TYPES.SOLIDIFY:
        vgroup_mods_map = {mod.vertex_group : [] for mod in mods}
        for mod in mods:
            vgroup_mods_map[mod.vertex_group].append(mod)
        return vgroup_mods_map

    elif mod_type == TYPES.SIMPLE_DEFORM:
        vgroup_mods_map = {mod.vertex_group : [] for mod in mods}
        for mod in mods:
            vgroup_mods_map[mod.vertex_group].append(mod)
        return vgroup_mods_map

    return {}


def mod_from_edit_mode(context, obj, mod_type='', sort_when_new=True, only_new=False):
    '''
    RET : vgroup, boolean, modifier, boolean
    IFO : Booleans indicate if the vgroup or modifier was created new or not
    '''

    if obj is None:
        return None, False, None, False

    if mod_type not in {TYPES.BEVEL, TYPES.SOLIDIFY, TYPES.SIMPLE_DEFORM}:
        return None, False, None, False

    def create_new_with_vgroup(sel_indices):
        mod = add(obj, mod_type=mod_type)
        defualt_settings(mod, mod_type)
        name = mod.name.replace('_', ' ').title()
        vgroup = create_vgroup(context, obj, name=name, vertex_indices=sel_indices)
        assign_vgroup_to_mod(obj, mod, vgroup, mod_type=mod_type)
        if sort_when_new:
            sort_all_mods(obj)
        return vgroup, True, mod, True

    def create_new_standard():
        mod = add(obj, mod_type=mod_type)
        defualt_settings(mod, mod_type)
        if sort_when_new:
            sort_all_mods(obj)
        return None, False, mod, True

    # Only New
    if only_new:
        sel_indices = query_sel_vert_indices(obj)
        if sel_indices:
            return create_new_with_vgroup(sel_indices)
        # New
        return create_new_standard()

    # Selected Vertex Indices
    sel_indices = query_sel_vert_indices(obj)
    # Last (OR) New Without V-Group
    if not sel_indices:
        # Last created
        for mod in reversed(obj.modifiers):
            if mod.type == mod_type:
                return None, False, mod, False
        # New
        return create_new_standard()

    # Vertex Groups from Object
    obj_vgroups = obj.vertex_groups[:]
    # Create New
    if not obj_vgroups:
        return create_new_with_vgroup(sel_indices)

    # KEY -> V-Group Name || VAL -> [Mods]
    vgroup_mods_map = vgroup_mods_map_from_obj(obj, mod_type)
    # Create New
    if not vgroup_mods_map:
        return create_new_with_vgroup(sel_indices)

    # KEY -> V-Group || VAL -> {'VG_VERTS_ALL' : [], 'VG_VERTS_SEL' : [], 'VG_VERTS_VG_REFS' : [], 'VG_MODS' : []}
    vgroup_map = vgroup_data_map(obj)

    for vgroup, vgroup_data in vgroup_map.items():
        if vgroup.name not in vgroup_mods_map:
            continue

        sel_vg_verts = set([v.index for v in vgroup_data['VG_VERTS_SEL']])
        all_vg_verts = set([v.index for v in vgroup_data['VG_VERTS_ALL']])

        # Only one Vertex Group
        if len(vgroup_data['VG_VERTS_VG_REFS']) == 1:

            # Matching all selected vertices
            if set(sel_indices) == sel_vg_verts:

                # (PRIORITY 1) Only 1 V-Group & All Selected Verts in V-Group & Only 1 Mod Ref
                if len(vgroup_data['VG_MODS']) == 1:
                    return vgroup, False, vgroup_data['VG-MODS'][0], False

                # (PRIORITY 2) Only 1 V-Group & All Selected Verts in V-Group & Any Mod Refs
                elif len(vgroup_data['VG_MODS']) > 1:
                    for mod in reversed(obj.modifiers):
                        if mod in vgroup_data['VG-MODS']:
                            return vgroup, False, mod, False

            # Matching some selected vertices
            if set(sel_indices).issubset(all_vg_verts):

                # (PRIORITY 3) Only 1 V-Group & Any Selected Verts in V-Group & Only 1 Mod Ref
                if len(vgroup_data['VG_MODS']) == 1:
                    return vgroup, False, vgroup_data['VG-MODS'][0], False

                # (PRIORITY 4) Only 1 V-Group & Any Selected Verts in V-Group & Any Mod Refs
                if len(vgroup_data['VG_MODS']) > 1:
                    for mod in reversed(obj.modifiers):
                        if mod in vgroup_data['VG_MODS']:
                            return vgroup, False, mod, False

        # More than one Vertex Group
        if len(vgroup_data['VG_VERTS_VG_REFS']) > 1:

            # Matching some selected vertices
            if set(sel_indices).issubset(all_vg_verts):

                # (PRIORITY 5) More than 1 V-Group & Any Selected Verts in V-Group & Only 1 Mod Ref
                if len(vgroup_data['VG_MODS']) == 1:
                    return vgroup, False, vgroup_data['VG_MODS'][0], False

                # (PRIORITY 6) More than 1 V-Group & Any Selected Verts in V-Group & Any Mod Refs
                if len(vgroup_data['VG_MODS']) > 1:
                    for mod in reversed(obj.modifiers):
                        if mod in vgroup_data['VG_MODS']:
                            return vgroup, False, mod, False

    # Create New
    return create_new_with_vgroup(sel_indices)

########################•########################
"""                  BOOLEAN                  """
########################•########################

class BOOLEAN_OPS:
    DIFFERENCE = 'DIFFERENCE'
    INTERSECT = 'INTERSECT'
    UNION = 'UNION'
    SLICE = 'SLICE'


def boolean_operations(context, target_obj, boolean_objs=[], boolean_ops=BOOLEAN_OPS.DIFFERENCE):
    settings = user_prefs().settings
    if boolean_ops == BOOLEAN_OPS.SLICE:
        set_shading = query_any_polygons_shaded_smooth(target_obj)
        boolean_mod_map = {}
        sub_objs = set()
        for boolean_obj in boolean_objs:
            sub_obj = duplicate_mesh_in_place(context, target_obj)
            sub_objs.add(sub_obj)
            shade_polygons(boolean_obj, use_smooth=set_shading)
            shade_polygons(sub_obj, use_smooth=set_shading)
            parent_object(child=sub_obj, parent=target_obj)
            mod = setup_boolean(context, target_obj, boolean_obj, 'DIFFERENCE')
            if target_obj in boolean_mod_map:
                boolean_mod_map[target_obj].append(mod)
            else:
                boolean_mod_map[target_obj] = [mod]
            mod = sub_obj.modifiers.new("Boolean", type='BOOLEAN')
            mod.show_expanded = False
            mod.operation = 'INTERSECT'
            mod.object = boolean_obj
            mod.solver = settings.boolean_solver_mode
            mod.show_in_editmode = True
            sort_all_mods(sub_obj)
        insert_booleans_into_collecion(context, boolean_objs)
        sort_all_mods(target_obj)
        if settings.destructive_mode:
            apply_with_map(context, obj_mods_map=boolean_mod_map)
            for sub_obj in sub_objs:
                apply_all_booleans(context, sub_obj)
        target_obj.hide_set(False)
    else:
        boolean_mod_map = {}
        for boolean_obj in boolean_objs:
            if boolean_obj in boolean_objs_from_mods(target_obj):
                continue
            mod = setup_boolean(context, target_obj, boolean_obj, boolean_ops)
            if target_obj in boolean_mod_map:
                boolean_mod_map[target_obj].append(mod)
            else:
                boolean_mod_map[target_obj] = [mod]
        insert_booleans_into_collecion(context, boolean_objs)
        sort_all_mods(target_obj)
        if settings.destructive_mode:
            apply_with_map(context, obj_mods_map=boolean_mod_map)
        target_obj.hide_set(False)


def setup_boolean(context, target_obj, boolean_obj, operation):
    shade_polygons(boolean_obj, use_smooth=query_any_polygons_shaded_smooth(target_obj))
    mod = target_obj.modifiers.new("Boolean", type='BOOLEAN')
    mod.show_expanded = False
    mod.operation = operation
    mod.object = boolean_obj
    mod.solver = user_prefs().settings.boolean_solver_mode
    mod.show_in_editmode = True
    parent_object(child=boolean_obj, parent=target_obj)
    wire_display(boolean_obj)
    boolean_obj.ps.use_for_boolean = True
    return mod


def insert_booleans_into_collecion(context, boolean_objs):
    collection = boolean_collection(context)
    for obj in boolean_objs:
        unlink_object_from_all_collections(context, obj)
        link_object_to_collection(collection, obj)
    collection_path_settings(context, collection, exclude=False, hide_viewport=False, hide_render=True)
    for obj in collection.objects:
        if obj not in boolean_objs:
            if obj.ps.use_for_boolean:
                obj.hide_set(True)
                obj.hide_render = True


def delete_booleans_if_valid(boolean_objs=[]):
    settings = user_prefs().settings
    removed = False
    boolean_objs = list(set(boolean_objs))
    if settings.destructive_mode:
        if settings.del_booleans_if_destructive:
            for boolean_obj in boolean_objs[:]:
                if boolean_obj.name in bpy.data.objects:
                    if boolean_obj.data.name in bpy.data.meshes:
                        boolean_mesh = boolean_obj.data
                        bpy.data.objects.remove(boolean_obj)
                        bpy.data.meshes.remove(boolean_mesh)
                        removed = True
    return removed

########################•########################
"""                CONTROLLER                 """
########################•########################

class ModController:
    def __init__(self, obj, mod_type=''):
        self.obj = obj
        self.mod_type = mod_type
        self.mods = [mod for mod in obj.modifiers if mod.type == mod_type]
        self.mod_names_map = {mod : mod.name for mod in obj.modifiers if mod.type == mod_type}
        self.prop_maps = {}
        self.mod = None
        self.created_mods = []
        self.original_stack_order = [(index, mod.name) for index, mod in enumerate(obj.modifiers)]
        # Quick Setup
        if self.mods:
            # Set to active
            if self.obj.modifiers.active in self.mods:
                self.mod = self.obj.modifiers.active
            # Set to last
            else:
                self.mod = self.mods[-1]
            # Revert prop maps
            for mod in self.mods:
                self.__capture_props(mod)


    def status(self):
        if not isinstance(self.obj, bpy.types.Object):
            return 'INVALID_OBJECT'
        if len(self.obj.modifiers) == 0:
            return 'NO_MODIFIERS'
        if not isinstance(self.mod, bpy.types.Modifier):
            return 'INVALID_CURRENT_MOD'
        if self.mod.type != self.mod_type:
            return 'INVALID_TYPE_MATCH'
        if self.mod not in self.mods:
            return 'MOD_NOT_TRACKED'
        if self.mod.name not in self.obj.modifiers:
            return 'MOD_NOT_FOUND'
        return 'OK'


    def new_mod(self, name=''):
        name = name if name else self.mod_type.title()
        self.mod = self.obj.modifiers.new(name, self.mod_type)
        defualt_settings(self.mod, self.mod_type)
        self.mods.append(self.mod)
        self.created_mods.append(self.mod)
        self.__capture_props(self.mod)
        return self.mod


    def add_mod(self, mod):
        if not mod:
            return
        elif mod.type != self.mod_type:
            return
        elif mod in self.mods:
            self.mod = mod
            self.mod.show_expanded = False
        elif mod.name in self.obj.modifiers:
            self.mod = mod
            self.mod.show_expanded = False
            self.mods.append(self.mod)
            self.created_mods.append(self.mod)
            self.__capture_props(self.mod)


    def sort(self):
        if isinstance(self.obj, bpy.types.Object):
            sort_all_mods(self.obj)


    def set_current_mod(self, mod):
        for existing_mod in self.mods:
            if existing_mod == mod:
                self.mod = existing_mod
                return True
        return False


    def move_curent_mod(self, move_up=True, flag_to_ignore_sort=True):
        if isinstance(self.obj, bpy.types.Object) and isinstance(self.mod, bpy.types.Modifier) and len(self.obj.modifiers) > 1:
            from_index = self.obj.modifiers.find(self.mod.name)
            if from_index >= 0:
                to_index = from_index - 1 if move_up else from_index + 1
                if to_index < len(self.obj.modifiers) and to_index >= 0:
                    self.obj.modifiers.move(from_index, to_index)
                    # Ignore
                    if flag_to_ignore_sort:
                        options = user_prefs().sort
                        ignore_str = options.ignore_sort_str.replace(" ", "")
                        if ignore_str and ignore_str not in self.mod.name:
                            self.mod.name = f"{self.mod.name} {ignore_str}"


    def reset(self, revert_props=True, remove_created=True, reset_stack_order=True):
        def reset_names():
            for mod, name in self.mod_names_map.items():
                if isinstance(mod, bpy.types.Modifier) and name:
                    if mod.name != name:
                        mod.name = name
        except_guard(try_func=reset_names)

        def revert():
            for mod in self.mods:
                if remove_created and mod in self.created_mods:
                    continue
                if mod.name in self.prop_maps:
                    prop_map = self.prop_maps[mod.name]
                    transfer_props(prop_map, mod)
        def remove():
            mods = list(set(self.created_mods))
            for mod in mods[:]:
                if mod in self.mods:
                    self.mods.remove(mod)
                self.obj.modifiers.remove(mod)
            self.created_mods.clear()
        def restack():
            if not self.obj.modifiers:
                return
            max_index = len(self.obj.modifiers) - 1
            for to_index, mod_name in self.original_stack_order:
                from_index = self.obj.modifiers.find(mod_name)
                if from_index < 0:
                    continue
                if to_index > max_index:
                    to_index = max_index
                if from_index != to_index:
                    self.obj.modifiers.move(from_index, to_index)
        if revert_props:
            except_guard(try_func=revert)
        if remove_created:
            except_guard(try_func=remove)
        if reset_stack_order:
            except_guard(try_func=restack)


    def __capture_props(self, mod):
        prop_map = capture_prop_maps(mod)
        self.prop_maps[mod.name] = prop_map
