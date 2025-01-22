########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..resources.icon import icon_id
from ..utils.addon import user_prefs


class PS_MT_MeshOpsMenu(bpy.types.Menu):
    bl_idname = "PS_MT_MeshOpsMenu"
    bl_label = "Mesh Ops"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.hud_gizmos_editor", text="HUD Hot Bar", icon_value=icon_id("hud_hot_bar"))
        layout.operator("ps.mirror_and_weld", text="Mirror & Weld", icon_value=icon_id("mirror_and_weld"))
        layout.operator("ps.slice_and_knife", text="Slice & Knife", icon_value=icon_id("slice_and_knife"))
        layout.operator("ps.clean_mesh", text="Clean", icon="MESH_GRID")
        layout.operator("ps.sharp_bevel", text="Sharp Bevel", icon="FACE_CORNER")
        layout.operator("ps.join", text="Join", icon="CON_TRACKTO")
        layout.operator("ps.merge", text="Merge", icon="POINTCLOUD_POINT")
        layout.operator("ps.bisect_loop", text="Bisect Loop", icon="MOD_SIMPLIFY")
        layout.operator("ps.flatten", text="Flatten", icon="MOD_DISPLACE")
        layout.operator("ps.dissolve", text="Dissolve", icon="CON_STRETCHTO")
        layout.menu("VIEW3D_MT_snap", text="Snap", icon="BLENDER")
        layout.menu("VIEW3D_MT_object_apply", text="Apply", icon="BLENDER")
        layout.operator_menu_enum("object.origin_set", text="Set Origin", property="type", icon="BLENDER")

