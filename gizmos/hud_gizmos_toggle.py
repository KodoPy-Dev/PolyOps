########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from .. import utils

DESC = """Gizmos Display Toggle"""

class PS_OT_HudGizmosToggle(bpy.types.Operator):
    bl_idname      = "ps.hud_gizmos_toggle"
    bl_label       = "HUD Gizmos Toggle"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True


    def invoke(self, context, event):
        # Gizmo Prefs
        prefs = utils.addon.user_prefs().hud_gizmos
        # Turn Off
        if prefs.show_gizmos:
            prefs.show_gizmos = False
        # Turn On
        else:
            bpy.context.space_data.show_gizmo = True
            prefs.show_gizmos = True
        msgs = [("Hot Bar", "Activated" if prefs.show_gizmos else "Deactivated")]
        utils.notifications.init(context, messages=msgs)
        context.area.tag_redraw()
        return {'FINISHED'}
