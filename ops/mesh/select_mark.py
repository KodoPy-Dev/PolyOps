########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from ... import utils

DESC = """Select Mark\n
• Edit Mode
\t\t→ Append if selection"""

class PS_OT_SelectMark(bpy.types.Operator):
    bl_idname      = "ps.select_mark"
    bl_label       = "Select Mark"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    select_seam: BoolProperty(name="Select Seam", description="Select Seam", default=True)
    select_sharp: BoolProperty(name="Select Sharp", description="Select Sharp", default=True)
    select_bevel_weight: BoolProperty(name="Select Bevel Weight", description="Select Bevel Weight", default=True)
    select_edge_crease: BoolProperty(name="Select Edge Crease", description="Select Edge Crease", default=True)
    select_vert_crease: BoolProperty(name="Select Vert Crease", description="Select Vert Crease", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        for obj in objs:
            utils.bmu.select_marks(context, obj,
                sharp_edges=self.select_sharp,
                seamed_edges=self.select_seam,
                bevel_edges=self.select_bevel_weight,
                crease_edges=self.select_edge_crease,
                creased_verts=self.select_vert_crease)
        msgs = [
            ("Operation"  , "Select Marks"),
            ("Objects"    , str(len(objs))),
            ("Sharps"     , "True" if self.select_sharp else "False"),
            ("Seams"      , "True" if self.select_seam else "False"),
            ("B-Weight"   , "True" if self.select_bevel_weight else "False"),
            ("Edge Crease", "True" if self.select_edge_crease else "False"),
            ("Vert Crease", "True" if self.select_vert_crease else "False"),
            ]
        utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'select_seam')
        row = box.row()
        row.prop(self, 'select_sharp')
        row = box.row()
        row.prop(self, 'select_bevel_weight')
        row = box.row()
        row.prop(self, 'select_edge_crease')
        row = box.row()
        row.prop(self, 'select_vert_crease')
