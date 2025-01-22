########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
import math
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty
from ... import utils

DESC = """Flatten\n
• Edit Mode
\t\t→ Flatten selected geometry to active face
\t\t→ With a 3 vert selection : Flatten to triangulation"""

class PS_OT_Flatten(bpy.types.Operator):
    bl_idname      = "ps.flatten"
    bl_label       = "Flatten to Face"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    use_boundary_edges: BoolProperty(name="Use Boundary Edges", description="Use the boundary edges as the angle of projection", default=True)
    clean_surface: BoolProperty(name="Clean Surface", description="Clean the surface after projecting", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.bmu.ops_flatten_geometry(context, obj, project_boundary_verts=self.use_boundary_edges, clean_surface=self.clean_surface)

        msgs = [
            ("Operation", "Flatten"),
            ("Boundary Project", "True" if self.use_boundary_edges else "False"),
            ("Clean Surface" , "True" if self.clean_surface else "False")]
        utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'use_boundary_edges')
        row = box.row()
        row.prop(self, 'clean_surface')


