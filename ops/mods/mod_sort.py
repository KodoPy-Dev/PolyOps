########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from math import radians
from ... import utils
from ...utils.addon import user_prefs
from ...utils.context import get_mesh_objs

DESC = """Modifier Quick Sort\n
• Sort modifiers on selected objects"""

class PS_OT_ModSort(bpy.types.Operator):
    bl_idname      = "ps.mod_sort"
    bl_label       = "Modifier Sort"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return user_prefs().sort.sort_enabled and get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.modifiers.sort_all_mods(obj)
        msgs = [
            ("Operation", "Modifier Quick Sort"),
            ("Objects", str(len(objs)))]
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}
