########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..utils.addon import version


class PS_MT_BooleansMenu(bpy.types.Menu):
    bl_idname = "PS_MT_BooleansMenu"
    bl_label = "Booleans"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.boolean_difference", text="Difference", icon="SELECT_SUBTRACT")
        layout.operator("ps.boolean_slice", text="Slice", icon="SELECT_INTERSECT")
        layout.operator("ps.boolean_union", text="Union", icon="SELECT_EXTEND")
        layout.operator("ps.boolean_intersect", text="Intersect", icon="SELECT_DIFFERENCE")
