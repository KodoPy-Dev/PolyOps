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

DESC = """Select Boundary\n
• Edit Mode
\t\t→ Select edges that are boundary edges
\t\t→ Or boundary of selection set"""

class PS_OT_SelectBoundary(bpy.types.Operator):
    bl_idname      = "ps.select_boundary"
    bl_label       = "Select Boundary"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    omit_x_axis: BoolProperty(name="Omit X Axis", description="Omit verts on the X Axis", default=False)
    flip_x_axis: BoolProperty(name="Flip X Axis", default=False)
    omit_y_axis: BoolProperty(name="Omit Y Axis", description="Omit verts on the Y Axis", default=False)
    flip_y_axis: BoolProperty(name="Flip Y Axis", default=False)
    omit_z_axis: BoolProperty(name="Omit Z Axis", description="Omit verts on the Z Axis", default=False)
    flip_z_axis: BoolProperty(name="Flip Z Axis", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.bmu.select_boundary(context, obj,
                omit_axis_x=self.omit_x_axis,
                omit_axis_y=self.omit_y_axis,
                omit_axis_z=self.omit_z_axis,
                flip_axis_x=self.flip_x_axis,
                flip_axis_y=self.flip_y_axis,
                flip_axis_z=self.flip_z_axis)
        messages = [
            ("Selected"   , "Boundary"),
            ("Objects"    , str(len(objs))),
            ("Omit X Axis", "True" if self.omit_x_axis else "False"),
            ("Omit X Axis", "True" if self.omit_y_axis else "False"),
            ("Omit X Axis", "True" if self.omit_z_axis else "False")]
        utils.notifications.init(context, messages)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row = box.row(align=True)
        row.prop(self, 'omit_x_axis')
        row = box.row(align=True)
        row.prop(self, 'flip_x_axis')
        row = box.row(align=True)
        row.prop(self, 'omit_y_axis')
        row = box.row(align=True)
        row.prop(self, 'flip_y_axis')
        row = box.row(align=True)
        row.prop(self, 'omit_z_axis')
        row = box.row(align=True)
        row.prop(self, 'flip_z_axis')
