########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from math import cos, sin, radians, degrees
from bpy.props import FloatProperty, BoolProperty
from ... import utils

DESC = """Object Shading\n
• Add / Remove Shading from (Mesh | Curve)\n
• (LMB) Add
\t\t→ Smooth + AutoSmooth\n
• (CTRL) Add
\t\t→ Smooth + AutoSmooth + Weighted Normal\n
• (SHIFT) Remove
\t\t→ Shade Flat
\t\t→ Remove Last AutoSmooth
\t\t→ Remove Last Weighted Normal\n
• *Optionally Shades Booleans from Modifiers*"""

class PS_OT_ObjectShading(bpy.types.Operator):
    bl_idname      = "ps.obj_shade"
    bl_label       = "Object Shading"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    shade_booleans : BoolProperty(name="Shade Booleans", default=True)
    auto_smooth_angle : FloatProperty(name="Auto Smooth Angle", description="Auto Smooth Geo-Nodes Angle", default=radians(35), min=0, max=math.pi, subtype='ANGLE')

    @classmethod
    def poll(cls, context):
        return [obj for obj in context.selected_editable_objects if obj and obj.type in {'MESH', 'CURVE'}]


    def invoke(self, context, event):
        self.smooth = not event.shift
        self.weighted_normal = event.ctrl
        return self.execute(context)


    def execute(self, context):
        objs = [obj for obj in context.selected_editable_objects if obj and obj.type in {'MESH', 'CURVE'}]
        shaded_booleans_count = 0
        for obj in objs:
            utils.modifiers.setup_shading(
                obj,
                use_smooth=self.smooth,
                auto_smooth=self.smooth,
                weighted_normal=self.weighted_normal,
                angle=self.auto_smooth_angle)
            if self.shade_booleans and obj.type == 'MESH':
                boolean_objs = utils.modifiers.referenced_booleans(obj)
                for boolean_obj in boolean_objs:
                    shaded_booleans_count += 1
                    utils.mesh.shade_polygons(boolean_obj, use_smooth=self.smooth)
        msgs = [
            ("Shading", "Smooth" if self.smooth else "Flat"),
            ("Objects", str(len(objs)))]
        if shaded_booleans_count:
            msgs.append(("Booleans Shaded", str(shaded_booleans_count)))
        utils.notifications.init(context, messages=msgs)
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'auto_smooth_angle')
        row = box.row()
        row.prop(self, 'shade_booleans')

