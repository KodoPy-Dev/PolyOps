########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import gc
import numpy as np
from math import cos, sin, radians, degrees
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ... import utils

DESC = """Select Axis\n
• Edit Mode
\t\t→ Select geometry about an axis"""

class PS_OT_SelectAxis(bpy.types.Operator):
    bl_idname      = "ps.select_axis"
    bl_label       = "Select Axis"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    x_axis: BoolProperty(name="X Axis", description="Select Verts on the X Axis", default=True)
    y_axis: BoolProperty(name="Y Axis", description="Select Verts on the Y Axis", default=False)
    z_axis: BoolProperty(name="Z Axis", description="Select Verts on the Z Axis", default=False)
    center_line: BoolProperty(name="Center Line", description="Only select center line", default=False)
    invert_sel: BoolProperty(name="Invert Selection", description="Invert the selection", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.bmu.select_axis_verts(context, obj,
                x=self.x_axis,
                y=self.y_axis,
                z=self.z_axis,
                only_center_line=self.center_line,
                invert=self.invert_sel)

        msgs = [
            ("Operation", "Select Axis Verts"),
            ("Objects", str(len(objs))),
            ("X Axis", "True" if self.x_axis else "False"),
            ("Y Axis", "True" if self.y_axis else "False"),
            ("Z Axis", "True" if self.z_axis else "False"),
            ("Center", "True" if self.center_line else "False"),
            ("Invert", "True" if self.invert_sel else "False"),
            ]
        utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row(align=True)
        row.prop(self, 'x_axis', text="X Axis")
        row = box.row(align=True)
        row.prop(self, 'y_axis', text="Y Axis")
        row = box.row(align=True)
        row.prop(self, 'z_axis', text="Z Axis")
        row = box.row(align=True)
        row.prop(self, 'center_line', text="Center Line Only")
        row = box.row(align=True)
        row.prop(self, 'invert_sel', text="Invert Selection")