########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.utils import register_class, unregister_class
from bpy.props import PointerProperty
from . import utils

########################•########################
"""                   PROPS                   """
########################•########################

from .props.settings import PS_PROPS_Settings
from .props.sort import PS_PROPS_Sort
from .props.dev import PS_PROPS_Dev
from .props.drawing import PS_PROPS_Drawing
from .props.operator import PS_PROPS_EEVEE
from .props.operator import PS_PROPS_Cycles
from .props.operator import PS_PROPS_Workbench
from .props.operator import PS_PROPS_SliceAndKnife
from .props.operator import PS_PROPS_MirrorAndWeld
from .props.operator import PS_PROPS_LoopSelect
from .props.operator import PS_PROPS_BLoop
from .props.operator import PS_PROPS_Merge
from .props.operator import PS_PROPS_Operator
from .props.gizmos import PS_PROPS_HUD_Gizmo
from .props.object import PS_PROPS_Object
from .props.mesh import PS_PROPS_Mesh
from .props.addon import PS_ADDON_Prefs

########################•########################
"""                CURVE OPS                  """
########################•########################

from .ops.curve.adjust import PS_OT_AdjustCurves
from .ops.curve.mesh_to_curve import PS_OT_MeshToCurve

########################•########################
"""                  DEV OPS                  """
########################•########################

from .ops.dev.modal_test import PS_OT_ModalTesting
from .ops.dev.static_test import PS_OT_StaticTesting
from .ops.dev.write_data import PS_OT_WriteData

########################•########################
"""               HANDLE OPS                  """
########################•########################

from .ops.handles.poly_debug import PS_OT_PolyDebug

########################•########################
"""                 MESH OPS                  """
########################•########################

from .ops.mesh.bisect_loop import PS_OT_BLoop
from .ops.mesh.clean_mesh import PS_OT_CleanMesh
from .ops.mesh.dissolve import PS_OT_Dissolve
from .ops.mesh.edge_mark import PS_OT_EdgeMark
from .ops.mesh.edge_trace import PS_OT_EdgeTrace
from .ops.mesh.flatten import PS_OT_Flatten
from .ops.mesh.join import PS_OT_Join
from .ops.mesh.merge import PS_OT_Merge
from .ops.mesh.select_axis import PS_OT_SelectAxis
from .ops.mesh.select_boundary import PS_OT_SelectBoundary
from .ops.mesh.select_loops import PS_OT_LoopSelect
from .ops.mesh.select_mark import PS_OT_SelectMark
from .ops.mesh.sharp_bevel import PS_OT_SharpBevel
from .ops.mesh.slice_and_knife import PS_OT_SliceAndKnife
from .ops.mesh.vert_mark import PS_OT_VertMark

########################•########################
"""                  MOD OPS                  """
########################•########################

from .ops.mods.bevel import PS_OT_Bevel
from .ops.mods.booleans import PS_OT_BooleanDifference
from .ops.mods.booleans import PS_OT_BooleanIntersect
from .ops.mods.booleans import PS_OT_BooleanSlice
from .ops.mods.booleans import PS_OT_BooleanUnion
from .ops.mods.deform import PS_OT_Deform
from .ops.mods.mirror_and_weld import PS_OT_MirrorAndWeld
from .ops.mods.mod_apply import PS_OT_ModApply
from .ops.mods.mod_sort import PS_OT_ModSort
from .ops.mods.obj_shade import PS_OT_ObjectShading
from .ops.mods.select_booleans import PS_OT_SelectBooleans
from .ops.mods.solidify import PS_OT_Solidify

########################•########################
"""               OBJECT OPS                  """
########################•########################

from .ops.object.object_display import PS_OT_ObjectDisplay
from .ops.object.select_objects import PS_OT_SelectObjects

########################•########################
"""               RENDER OPS                  """
########################•########################

from .ops.render.cycles import PS_OT_Cycles
from .ops.render.eevee import PS_OT_EEVEE
from .ops.render.workbench import PS_OT_Workbench

########################•########################
"""                   GIZMOS                  """
########################•########################

from .gizmos.hud_gizmos_editor import PS_OT_HudGizmosEditor
from .gizmos.hud_gizmos_toggle import PS_OT_HudGizmosToggle
from .gizmos.hud_gizmos import PS_GIZMO_HUD

########################•########################
"""                 INTERFACES                """
########################•########################

from .interfaces.booleans import PS_MT_BooleansMenu
from .interfaces.curve import PS_MT_CurveOpsMenu
from .interfaces.main import PS_MT_MainMenu
from .interfaces.mesh import PS_MT_MeshOpsMenu
from .interfaces.mods import PS_MT_ModsMenu
from .interfaces.scene import PS_MT_SceneMenu
from .interfaces.select import PS_MT_SelectMenu
from .interfaces.settings import PS_OT_SettingsPopup
from .interfaces.shading import PS_MT_ShadingMenu

########################•########################
"""                  REGISTER                 """
########################•########################

classes = (
    # --- PROPS --- #
    PS_PROPS_Settings,
    PS_PROPS_Sort,
    PS_PROPS_Dev,
    PS_PROPS_Drawing,
    PS_PROPS_EEVEE,
    PS_PROPS_Cycles,
    PS_PROPS_Workbench,
    PS_PROPS_SliceAndKnife,
    PS_PROPS_MirrorAndWeld,
    PS_PROPS_LoopSelect,
    PS_PROPS_BLoop,
    PS_PROPS_Merge,
    PS_PROPS_Operator,
    PS_PROPS_HUD_Gizmo,
    PS_PROPS_Object,
    PS_PROPS_Mesh,
    PS_ADDON_Prefs,
    # --- CURVE OPS --- #
    PS_OT_AdjustCurves,
    PS_OT_MeshToCurve,
    # --- DEV OPS --- #
    PS_OT_ModalTesting,
    PS_OT_StaticTesting,
    PS_OT_WriteData,
    # --- HANDLE OPS --- #
    PS_OT_PolyDebug,
    # --- MESH OPS --- #
    PS_OT_BLoop,
    PS_OT_CleanMesh,
    PS_OT_Dissolve,
    PS_OT_EdgeMark,
    PS_OT_EdgeTrace,
    PS_OT_Flatten,
    PS_OT_Join,
    PS_OT_Merge,
    PS_OT_SelectAxis,
    PS_OT_SelectBoundary,
    PS_OT_LoopSelect,
    PS_OT_SelectMark,
    PS_OT_SharpBevel,
    PS_OT_SliceAndKnife,
    PS_OT_VertMark,
    # --- MOD OPS --- #
    PS_OT_Bevel,
    PS_OT_BooleanDifference,
    PS_OT_BooleanIntersect,
    PS_OT_BooleanSlice,
    PS_OT_BooleanUnion,
    PS_OT_Deform,
    PS_OT_ObjectShading,
    PS_OT_MirrorAndWeld,
    PS_OT_ModApply,
    PS_OT_ModSort,
    PS_OT_SelectBooleans,
    PS_OT_Solidify,
    # --- OBJECT OPS --- #
    PS_OT_ObjectDisplay,
    PS_OT_SelectObjects,
    # --- RENDER OPS --- #
    PS_OT_Cycles,
    PS_OT_EEVEE,
    PS_OT_Workbench,
    # --- GIZMOS --- #
    PS_OT_HudGizmosEditor,
    PS_OT_HudGizmosToggle,
    PS_GIZMO_HUD,
    # --- INTERFACES --- #
    PS_MT_BooleansMenu,
    PS_MT_CurveOpsMenu,
    PS_MT_MainMenu,
    PS_MT_MeshOpsMenu,
    PS_MT_ModsMenu,
    PS_MT_SceneMenu,
    PS_MT_SelectMenu,
    PS_OT_SettingsPopup,
    PS_MT_ShadingMenu,
)

def register_addon():

    # BPY Types
    for cls in classes:
        register_class(cls)

    # Post Handles
    load_post_append()

    # Mesh Editor
    from .utils.mesh import remove_backup_meshes
    bpy.app.handlers.undo_post.append(remove_backup_meshes)

    # Pointers
    bpy.types.Object.ps = PointerProperty(name="PolyOps Props", type=PS_PROPS_Object)
    bpy.types.Mesh.ps = PointerProperty(name="PolyOps Props", type=PS_PROPS_Mesh)

    # Keymaps
    register_keymaps()

    # Utils
    from .utils.context import object_mode_toggle_reset
    object_mode_toggle_reset()

    # Resources
    from .resources.icon import register_icons_collection
    register_icons_collection()


def unregister_addon():

    # Handles
    load_post_remove()

    # BPY Types
    for cls in reversed(classes):
        unregister_class(cls)

    # Mesh Editor
    from .utils.mesh import remove_backup_meshes
    if remove_backup_meshes in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(remove_backup_meshes)

    # Pointers
    del bpy.types.Object.ps
    del bpy.types.Mesh.ps

    # Keymaps
    unregister_keymaps()

    # Resources
    from .resources.icon import unregister_icons_collection
    unregister_icons_collection()


def load_post_append():
    # Notify
    from .utils.notifications import remove_notify_handle
    # Debug
    from .utils.debug import remove_debug_handle
    # Poly Fade
    from .utils.poly_fade import remove_poly_fade_handle
    # Vec Fade
    from .utils.vec_fade import remove_vec_fade_handle
    # Label Fade
    from .utils.modal_labels import remove_label_fade_handle
    # Ops Poly Display
    from .ops.handles.poly_debug import remove_poly_debug_handle

    functions = (
        remove_notify_handle,
        remove_debug_handle,
        remove_poly_fade_handle,
        remove_vec_fade_handle,
        remove_label_fade_handle,
        remove_poly_debug_handle,
    )

    for function in functions:
        bpy.app.handlers.load_post.append(function)


def load_post_remove():
    # Notify
    from .utils.notifications import remove_notify_handle
    # Debug
    from .utils.debug import remove_debug_handle
    # Poly Fade
    from .utils.poly_fade import remove_poly_fade_handle
    # Vec Fade
    from .utils.vec_fade import remove_vec_fade_handle
    # Label Fade
    from .utils.modal_labels import remove_label_fade_handle
    # Ops Poly Display
    from .ops.handles.poly_debug import remove_poly_debug_handle

    functions = (
        remove_notify_handle,
        remove_debug_handle,
        remove_poly_fade_handle,
        remove_vec_fade_handle,
        remove_label_fade_handle,
        remove_poly_debug_handle,
    )

    for function in functions:
        function()
        if function in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(function)

########################•########################
"""                   KEYMAP                  """
########################•########################

KEYS = []

def register_keymaps():
    global KEYS
    from .utils.addon import user_prefs
    settings = user_prefs().settings

    kc = bpy.context.window_manager.keyconfigs.addon
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

    kmi = km.keymap_items.new("ps.mirror_and_weld", 'X', 'PRESS', ctrl=False, shift=False, alt=True)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("ps.slice_and_knife", 'X', 'PRESS', ctrl=False, shift=True, alt=True)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("ps.hud_gizmos_toggle", 'D', 'PRESS', ctrl=False, shift=True, alt=True)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("wm.call_menu", settings.main_menu_hot_key, "PRESS", ctrl=False, shift=False, alt=False)
    kmi.properties.name = "PS_MT_MainMenu"
    KEYS.append((km, kmi))

    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')

    kmi = km.keymap_items.new("ps.boolean_difference", 'NUMPAD_MINUS', 'PRESS', ctrl=True, shift=False, alt=False)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("ps.boolean_slice", 'NUMPAD_SLASH', 'PRESS', ctrl=True, shift=False, alt=False)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("ps.boolean_union", 'NUMPAD_PLUS', 'PRESS', ctrl=True, shift=False, alt=False)
    KEYS.append((km, kmi))

    kmi = km.keymap_items.new("ps.boolean_intersect", 'NUMPAD_ASTERIX', 'PRESS', ctrl=True, shift=False, alt=False)
    KEYS.append((km, kmi))


def unregister_keymaps():
    global KEYS
    for km, kmi in KEYS:
        km.keymap_items.remove(kmi)
    KEYS.clear()

