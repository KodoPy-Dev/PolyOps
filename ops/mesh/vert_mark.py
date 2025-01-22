########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from math import radians
from ... import utils

DESC = """Vert Mark\n
• Object Mode
\t\t→ (LMB) Recalculate
\t\t→ (SHIFT) Clears all\n
• Edit Mode
\t\t→ (LMB) Append if selection or Recalculate if none
\t\t→ (SHIFT) Clears selection or all if none"""

class PS_OT_VertMark(bpy.types.Operator):
    bl_idname      = "ps.vert_mark"
    bl_label       = "Vert Mark"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    vert_crease: FloatProperty(name="Vert Crease", description="Vert Crease", default=1, min=0, max=1)
    mark_boundary: BoolProperty(name="Mark Boundary", description="Mark Boundary Edges", default=False)
    omit_x_axis: BoolProperty(name="Omit X Axis", description="Omit X Axis Boundary Edges", default=False)
    omit_y_axis: BoolProperty(name="Omit Y Axis", description="Omit Y Axis Boundary Edges", default=False)
    omit_z_axis: BoolProperty(name="Omit Z Axis", description="Omit Z Axis Boundary Edges", default=False)

    @classmethod
    def poll(cls, context):
        return utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)


    def invoke(self, context, event):
        self.shift = event.shift
        utils.context.set_component_selection(context, values=(True, False, False))
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        recalc = False
        if context.mode != 'EDIT_MESH':
            recalc = True
        if utils.bmu.query_any_sel_verts(objs) == False:
            recalc = True
        # Remove
        if self.shift:
            for obj in objs:
                utils.bmu.remove_vert_marks(context, obj, remove_all=recalc)
            msgs = [
                ("Operation", "All Removed" if recalc else "Selected Removed"),
                ("Objects"  , str(len(objs)))]
            utils.notifications.init(context, messages=msgs)
        # Assign
        else:
            for obj in objs:
                utils.bmu.assign_vert_marks(context, obj,
                    v_crease=self.vert_crease,
                    mark_boundary=self.mark_boundary,
                    omit_x_axis=self.omit_x_axis,
                    omit_y_axis=self.omit_y_axis,
                    omit_z_axis=self.omit_z_axis)
            msgs = [
                ("Operation"    , "Auto Marked" if recalc else "Manually Marked"),
                ("Objects"      , str(len(objs))),
                ("v-Crease"     , f"{self.vert_crease:.2f}"),
                ("Mark Boundary", "True" if self.mark_boundary else "False")]
            utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        # Remove
        if self.shift:
            row = box.row()
            row.label(text="Removed")
        # Append
        else:
            row = box.row()
            row.prop(self, 'vert_crease')
            row = box.row()
            row.prop(self, 'mark_boundary')
            row = box.row()
            row.prop(self, 'omit_x_axis')
            row = box.row()
            row.prop(self, 'omit_y_axis')
            row = box.row()
            row.prop(self, 'omit_z_axis')
