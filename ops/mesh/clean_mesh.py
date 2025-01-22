########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gc
from bpy.props import BoolProperty, IntProperty, FloatProperty, FloatVectorProperty, EnumProperty, PointerProperty
from math import radians
from ... import utils

DESC = """Clean Mesh\n
• Object Mode
\t\t→ Clean Entire Mesh\n
• Edit Mode
\t\t→ (With Face Selection) Clean selected faces
\t\t→ (With No Selection) Clean Entire Mesh"""

class PS_OT_CleanMesh(bpy.types.Operator):
    bl_idname      = "ps.clean_mesh"
    bl_label       = "Clean Mesh"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO'}

    remove_interior: BoolProperty(name="Remove Interior", description="Remove Interior Faces\nFaces extruded from edges that are non-manifold", default=True)
    clean_hidden: BoolProperty(name="Clean Hidden Faces", description="Clean Hidden Faces", default=True)
    dissolve_angle: FloatProperty(name="Dissolve Angle", description="Edges under this angle are dissolved", default=radians(0.1), min=0, max=radians(1), subtype='ANGLE')
    epsilon: FloatProperty(name="Threshold", description="Threshold for doubles", default=.0001, min=0, max=1)

    @classmethod
    def poll(cls, context):
        return utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)


    def invoke(self, context, event):
        return self.execute(context)


    def execute(self, context):

        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        if not objs:
            return {'FINISHED'}

        mode = context.mode
        if context.mode != 'EDIT_MESH':
            if not context.active_object:
                context.view_layer.objects.active = objs[0]
            utils.context.set_mode(target_mode='EDIT_MESH')

        # Clean All if no verts selected
        clean_all = True
        if mode == 'EDIT_MESH':
            if utils.bmu.query_any_sel_verts(objs):
                clean_all = False

        for obj in objs:
            # Clean
            utils.bmu.ops_clean_mesh(context, obj,
                clean_all=clean_all,
                dissolve_angle=self.dissolve_angle,
                remove_interior=self.remove_interior,
                clean_hidden=self.clean_hidden,
                epsilon=self.epsilon)
            # Poly Fade
            if mode == 'EDIT_MESH' and not clean_all:
                mat_ws = obj.matrix_world
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)
                lines = [mat_ws @ vert.co.copy() for edge in bm.edges if edge.select and edge.is_valid for vert in edge.verts if vert.is_valid]
                utils.poly_fade.init(obj=obj, lines=lines)
            else:
                utils.poly_fade.init(obj=obj)

        if mode != 'EDIT_MESH':
            utils.context.set_mode(target_mode=mode)

        msgs = [
            ("Operation"      , "Clean Mesh"),
            ("Objects"        , str(len(objs))),
            ("Dissolve Angle" , f"{self.dissolve_angle:.3f}"),
            ("Remove Interior", "True" if self.remove_interior else "False"),
            ("Clean Hidden"   , "True" if self.clean_hidden else "False"),
            ]
        utils.notifications.init(context, messages=msgs)
        gc.collect()
        return {'FINISHED'}


    def draw(self, context):
        box = self.layout.box()
        row = box.row()
        row.prop(self, 'remove_interior')
        row = box.row()
        row.prop(self, 'clean_hidden')
        row = box.row()
        row.prop(self, 'dissolve_angle')
        row = box.row()
        row.prop(self, 'epsilon')
