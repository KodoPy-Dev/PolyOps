########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from ..utils.addon import version, user_prefs


class PS_MT_MainMenu(bpy.types.Menu):
    bl_idname = "PS_MT_MainMenu"
    bl_label = version(opt='POLY_OPS', as_label=True)


    def draw(self, context):
        prefs = user_prefs()
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.menu("PS_MT_MeshOpsMenu", text="Mesh Ops", icon="EXPERIMENTAL")
        layout.menu("PS_MT_CurveOpsMenu", text="Curve Ops", icon="OUTLINER_DATA_CURVE")
        layout.menu("PS_MT_ModsMenu", text="Modifiers", icon="MODIFIER_ON")
        layout.menu("PS_MT_ShadingMenu", text="Shading", icon="NODE_MATERIAL")
        layout.menu("PS_MT_SelectMenu", text="Select", icon="RESTRICT_SELECT_OFF")
        layout.menu("PS_MT_SceneMenu", text="Scene", icon="SCENE")
        layout.operator("ps.settings_popup", text="Settings", icon="TOOL_SETTINGS")
        layout.separator()
        layout.menu("SCREEN_MT_user_menu", text="Quick Favorites", icon="BLENDER")

        # Developer
        dev = prefs.dev
        if dev.debug_mode:
            draw_dev_ops(context, layout, dev)


def draw_dev_ops(context, layout, dev):
    layout.separator()
    layout.operator("ps.modal_testing", text="Modal Testing")
    layout.operator("ps.static_testing", text="Static Testing")
    layout.operator("ps.write_data", text="Write Data")

