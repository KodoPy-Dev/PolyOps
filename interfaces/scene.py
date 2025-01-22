########################•########################
"""                   KodoPy                  """
########################•########################

import bpy


class PS_MT_SceneMenu(bpy.types.Menu):
    bl_idname = "PS_MT_SceneMenu"
    bl_label = "Scene"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        row = layout.row(align=True)
        layout.operator("ps.eevee_settings", text="EEVEE", icon="RESTRICT_RENDER_OFF")
        layout.operator("ps.cycles_settings", text="Cycles", icon="RESTRICT_RENDER_OFF")
        layout.operator("ps.workbench_settings", text="WorkBench", icon="RESTRICT_RENDER_OFF")
