########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..resources.icon import icon_id
from ..utils.addon import user_prefs


class PS_MT_CurveOpsMenu(bpy.types.Menu):
    bl_idname = "PS_MT_CurveOpsMenu"
    bl_label = "Curve Ops"


    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        active_object = context.active_object
        layout.operator("ps.mesh_to_curve", text="Mesh To Curve", icon="OUTLINER_OB_CURVE")
        layout.operator("ps.adjust_curves", text="Adjust Curve", icon="NORMALIZE_FCURVES")
