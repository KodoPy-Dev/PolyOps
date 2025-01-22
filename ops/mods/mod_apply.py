########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from math import radians
from ... import utils
from ...utils.addon import user_prefs
from ...utils.context import get_mesh_objs

DESC = """Modifier Quick Apply\n
• Apply modifiers on selected mesh objects\n
• (LMB)
\t\t→ Apply all except (First Bevel | Last Auto-Smooth | Last Weighted-Normal)\n
• (SHIFT)
\t\t→ Apply all Booleans\n
• (CTRL)
\t\t→ Apply all except (Last Auto-Smooth | Last Weighted-Normal)\n
• (SHIFT + CTRL)
\t\t→ Apply all using Vertex Groups and First Mirror
"""

class PS_OT_ModApply(bpy.types.Operator):
    bl_idname      = "ps.mod_apply"
    bl_label       = "Modifier Apply"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)


    def invoke(self, context, event):
        self.apply_mode = 'BEVEL_AUTO_WEIGHTED'
        if event.shift and not event.ctrl:
            self.apply_mode = 'BOOLEANS'
        elif not event.shift and event.ctrl:
            self.apply_mode = 'AUTO_WEIGHTED'
        elif event.shift and event.ctrl:
            self.apply_mode = 'VGROUPS_MIR'

        utils.context.object_mode_toggle_reset()
        return self.execute(context)


    def execute(self, context):
        objs = get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        toggle = utils.context.object_mode_toggle_start(context)

        for obj in objs:
            if self.apply_mode == 'BEVEL_AUTO_WEIGHTED':
                utils.modifiers.apply_mods_with_leave_opts(context, obj, leave_first_bevel=True, leave_last_auto_smooth=True, leave_last_weighted_normal=True)
            elif self.apply_mode == 'AUTO_WEIGHTED':
                utils.modifiers.apply_mods_with_leave_opts(context, obj, leave_first_bevel=False, leave_last_auto_smooth=True, leave_last_weighted_normal=True)
            elif self.apply_mode == 'VGROUPS_MIR':
                utils.modifiers.apply_first_mirror(context, obj)
                utils.modifiers.apply_mods_with_vgroups(context, obj)
            elif self.apply_mode == 'BOOLEANS':
                utils.modifiers.apply_all_booleans(context, obj)

        if toggle: utils.context.object_mode_toggle_end(context)
        msgs = [
            ("Operation", "Modifier Quick Apply"),
            ("Objects", str(len(objs)))]
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}
