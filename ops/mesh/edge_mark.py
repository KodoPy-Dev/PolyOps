########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from math import radians
from ... import utils

DESC = """Edge Mark\n
• Object Mode
\t\t→ (LMB) Recalculate
\t\t→ (SHIFT) Clears all\n
• Edit Mode
\t\t→ (LMB) Append if selection or Recalculate if none
\t\t→ (SHIFT) Clears selection or all if none"""

class PS_OT_EdgeMark(bpy.types.Operator):
    bl_idname      = "ps.edge_mark"
    bl_label       = "Edge Mark"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    remove_seam: BoolProperty(name="Remove Seam", description="Remove Seam", default=True)
    remove_sharp: BoolProperty(name="Remove Sharp", description="Remove Sharp", default=True)
    remove_bevel_weight: BoolProperty(name="Remove Bevel Weight", description="Remove Bevel Weight", default=True)
    remove_crease_weight: BoolProperty(name="Remove Crease Weight", description="Remove Crease Weight", default=True)

    mark_seam: BoolProperty(name="Mark Seam", description="Mark Edges as Seam", default=True)
    mark_sharp: BoolProperty(name="Mark Sharp", description="Mark Edges as Sharp", default=True)
    crease_weight: FloatProperty(name="Edge Crease", description="Edge Crease Amount", default=1, min=0, max=1)
    bevel_weight: FloatProperty(name="Edge Bevel Weight", description="Edge Bevel Weight", default=1, min=0, max=1)
    omit_x_axis: BoolProperty(name="Omit X Axis", description="Omit X Axis Boundary Edges", default=False)
    omit_y_axis: BoolProperty(name="Omit Y Axis", description="Omit Y Axis Boundary Edges", default=False)
    omit_z_axis: BoolProperty(name="Omit Z Axis", description="Omit Z Axis Boundary Edges", default=False)
    mark_boundary: BoolProperty(name="Mark Boundary", description="Mark Boundary Edges", default=False)
    recalc_angle: FloatProperty(name="Recalculate Angle", description="Edge angel to use as Recalculate Basis", default=radians(30), min=0, max=180, subtype='ANGLE')
    append_on_recalc: BoolProperty(name="Append on Recalculate", description="Append on Recalculate", default=False)

    @classmethod
    def poll(cls, context):
        return utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)


    def invoke(self, context, event):
        self.shift = event.shift
        self.show_poly_fade = True
        utils.context.set_component_selection(context, values=(False, True, False))
        return self.execute(context)


    def execute(self, context):
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)

        # Remove
        if self.shift:
            selected_only = False
            if context.mode == 'EDIT_MESH' and utils.bmu.query_any_sel_edges(objs):
                selected_only = True
            for obj in objs:
                utils.bmu.remove_edge_marks(context, obj,
                    selected_only=selected_only,
                    seam=self.remove_seam,
                    sharp=self.remove_sharp,
                    e_crease=self.remove_bevel_weight,
                    b_weight=self.remove_crease_weight)
            msgs = [
                ("Operation"      , "All Removed" if selected_only else "Selected Removed"),
                ("Objects"        , str(len(objs))),
                ("Remove Seam"    , "True" if self.remove_seam else "False"),
                ("Remove Sharp"   , "True" if self.remove_sharp else "False"),
                ("Remove B-Weight", "True" if self.remove_bevel_weight else "False"),
                ("Remove Crease"  , "True" if self.remove_crease_weight else "False")]
            utils.notifications.init(context, messages=msgs)
        # Assign
        else:
            recalc = False
            if context.mode != 'EDIT_MESH':
                recalc = True
            elif utils.bmu.query_any_sel_edges(objs) == False:
                recalc = True
            for obj in objs:
                utils.bmu.assign_edge_marks(context, obj,
                    recalc=recalc,
                    recalc_angle=self.recalc_angle,
                    recalc_append=self.append_on_recalc,
                    mark_boundary=self.mark_boundary,
                    omit_x_axis=self.omit_x_axis,
                    omit_y_axis=self.omit_y_axis,
                    omit_z_axis=self.omit_z_axis,
                    seam=self.mark_seam,
                    sharp=self.mark_sharp,
                    e_crease=self.crease_weight,
                    b_weight=self.bevel_weight,
                    show_poly_fade=self.show_poly_fade)
            self.show_poly_fade = False
            msgs = [
                ("Operation"    , "Auto Marked" if recalc else "Manually Marked"),
                ("Objects"      , str(len(objs))),
                ("Mark Sharp"   , "True" if self.mark_sharp else "False"),
                ("Mark Seam"    , "True" if self.mark_seam else "False"),
                ("Crease Weight", f"{self.crease_weight:.2f}"),
                ("Bevel Weight" , f"{self.bevel_weight:.2f}")]
            utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        # Remove
        if self.shift:
            row = box.row()
            row.prop(self, 'remove_seam')
            row = box.row()
            row.prop(self, 'remove_sharp')
            row = box.row()
            row.prop(self, 'remove_bevel_weight')
            row = box.row()
            row.prop(self, 'remove_crease_weight')
        # Append
        else:
            row = box.row()
            row.prop(self, 'mark_seam')
            row = box.row()
            row.prop(self, 'mark_sharp')
            row = box.row()
            row.prop(self, 'crease_weight')
            row = box.row()
            row.prop(self, 'bevel_weight')
            row = box.row()
            row.prop(self, 'omit_x_axis')
            row = box.row()
            row.prop(self, 'omit_y_axis')
            row = box.row()
            row.prop(self, 'omit_z_axis')
            row = box.row()
            row.prop(self, 'mark_boundary')
            row = box.row()
            row.prop(self, 'recalc_angle')
            row = box.row()
            row.prop(self, 'append_on_recalc')


