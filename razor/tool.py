########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import os
from bpy.types import WorkSpaceTool
from .. resources.icon import get_icon_directory
from .. import utils


DESC = """Razor\n
• Mesh Drawing System
"""

class PS_WT_RazorTool(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "ps.razor_tool"
    bl_label = "Razor"
    bl_description = DESC
    bl_icon = os.path.join(get_icon_directory(), 'razor')
    bl_widget = "PS_GGT_Razor_Workplane"
    bl_keymap = (("ps.razor_ops", {'type': 'LEFTMOUSE', 'value': 'CLICK_DRAG'}, {'properties': []}),)


    def draw_settings(context, layout, tool):
        formcraft_label = utils.addon.version(opt='POLY_OPS', as_label=True)
        razor_label = utils.addon.version(opt='RAZOR', as_label=True)
        info = f"{formcraft_label} • {razor_label}"
        layout.label(text=info)

