########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..resources.icon import icon_id


class PS_MT_SelectMenu(bpy.types.Menu):
    bl_idname = "PS_MT_SelectMenu"
    bl_label = "Select"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.select_objects", text="Objects", icon="CON_CHILDOF")
        layout.operator("ps.select_booleans", text="Booleans", icon="MOD_BOOLEAN")
        layout.operator("ps.select_mark", text="Select Mark", icon="EDGESEL")
        layout.operator("ps.loop_select", text="Loop Select", icon_value=icon_id("loop_select"))
        layout.operator("ps.edge_trace", text="Edge Trace", icon="CON_TRACKTO")
        layout.operator("ps.select_boundary", text="Boundary Loop", icon="PIVOT_BOUNDBOX")
        layout.operator("ps.select_axis", text="By Axis", icon="AXIS_FRONT")



