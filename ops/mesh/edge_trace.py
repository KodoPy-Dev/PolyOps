########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import gc
from math import pi, cos, sin, radians, degrees
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from bpy.props import IntProperty, FloatProperty
from ... import utils

DESC = """Edge Trace\n
• Edit Mode
\t\t→ Trace selected edges by angle and step limit"""

class PS_OT_EdgeTrace(bpy.types.Operator):
    bl_idname      = "ps.edge_trace"
    bl_label       = "Edge Trace"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    step_limit: IntProperty(name="Step Limit", description="Max Iterations", default=70, min=0, max=10_000)
    angle_limit: FloatProperty(name="Angle Limit", description="Max Angle", default=radians(30), min=0, max=pi, subtype='ANGLE')

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.bmu.ops_trace_edges(context, obj, step_limit=self.step_limit, angle_limit=self.angle_limit, select_traced=True, from_selected=True)
        msgs = [
            ("Operation", "Edge Trace"),
            ("Objects", str(len(objs)))]
        utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row(align=True)
        row.prop(self, 'step_limit', text="Step Limit")
        row = box.row(align=True)
        row.prop(self, 'angle_limit', text="Angle Limit")


