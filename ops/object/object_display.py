########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from math import cos, sin, radians, degrees
from bpy.props import IntProperty, FloatProperty
from ... import utils

DESC = """Object Display\n
• (LMB)
\t\t→ Wire Only\n
• (SHIFT)
\t\t→ Solid Only\n
• (CTRL)
\t\t→ Solid + Wire"""

class PS_OT_ObjectDisplay(bpy.types.Operator):
    bl_idname      = "ps.object_display"
    bl_label       = "Object Display"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects_selected_or_in_mode(context)


    def invoke(self, context, event):
        self.display = 'WIRE'
        if event.shift:
            self.display = 'SOLID'
        elif event.ctrl:
            self.display = 'WIREFRAME'
        return self.execute(context)


    def execute(self, context):
        objs = [obj for obj in utils.context.get_objects_selected_or_in_mode(context) if hasattr(obj, 'display_type')]
        for obj in objs:
            if self.display == 'WIREFRAME':
                obj.show_wire = True
                obj.display_type = 'SOLID'
            elif self.display in {'SOLID', 'WIRE'}:
                obj.display_type = self.display
                obj.show_wire = False
        msgs = [
            ("Display", self.display),
            ("Objects", str(len(objs)))]
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}

