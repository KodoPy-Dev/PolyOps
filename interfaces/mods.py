########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..resources.icon import icon_id


class PS_MT_ModsMenu(bpy.types.Menu):
    bl_idname = "PS_MT_ModsMenu"
    bl_label = "Modifiers"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.mod_apply", text="Apply", icon="CHECKMARK")
        layout.operator("ps.mod_sort", text="Sort", icon="SORTSIZE")
        layout.operator("ps.obj_shade", text="Object Shading", icon="MESH_CUBE")
        layout.operator("ps.mirror_and_weld", text="Mirror & Weld", icon_value=icon_id("mirror_and_weld"))
        layout.operator("ps.bevel", text="Bevel", icon="MOD_BEVEL")
        layout.operator("ps.solidify", text="Solidify", icon="MOD_SOLIDIFY")
        layout.operator("ps.deform", text="Deform", icon="MOD_SIMPLEDEFORM")
        layout.menu("PS_MT_BooleansMenu", text="Booleans", icon="MOD_BOOLEAN")

