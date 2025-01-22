
########################•########################
"""               SLIDES OPS                  """
########################•########################

import bpy
import math
import gc
from math import pi, cos, sin, radians, degrees
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from bpy.props import IntProperty, FloatProperty
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS, OPS_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Loop Select\n
Interactive loop selection tool
• Edit Mode
\t\t→ (LMB) Select Edge Loops Tool
\t\t→ (SHIFT) Quick Select edges by angle (30º)
\t\t→ (CTRL) Quick Select edges by angle (60º)
\t\t→ (SHIFT + CTRL) Quick Select faces by Normal\n"""

class PS_OT_LoopSelect(bpy.types.Operator):
    bl_idname      = "ps.loop_select"
    bl_label       = "Loop Select"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):

        # Mod Keys
        if context.mode == 'EDIT_MESH':
            # Quick Select 30 Deg
            if event.shift and not event.ctrl:
                utils.context.set_component_selection(context, values=(False, True, False))
                bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(30))
                utils.notifications.init(context, messages=[("Selected Edges by Sharp Angle", "30º")])
                return {'FINISHED'}
            # Quick Select 60 Deg
            elif not event.shift and event.ctrl:
                utils.context.set_component_selection(context, values=(False, True, False))
                bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(60))
                utils.notifications.init(context, messages=[("Selected Edges by Sharp Angle", "60º")])
                return {'FINISHED'}
            # Quick Select Faces
            elif event.shift and event.ctrl:
                utils.context.set_component_selection(context, values=(False, False, True))
                bpy.ops.mesh.select_similar(type='FACE_NORMAL', threshold=0.01)
                utils.notifications.init(context, messages=[("Selected Faces by Face Normal", "Threshold 0.01")])
                return {'FINISHED'}

        self.prefs = utils.addon.user_prefs()
        self.op_prefs = self.prefs.operator.loop_select

        # BME
        OPTIONS = utils.bme.OPTIONS
        self.bme_ray_options = OPTIONS.NONE
        self.bme_add_options = OPTIONS.USE_RAY | OPTIONS.ONLY_VISIBLE | OPTIONS.IGNORE_HIDDEN_GEO
        self.bmeCON = utils.bme.BmeshController()
        objs = utils.context.get_meshes_from_edit_or_from_selected(context)
        for obj in objs:
            self.bmeCON.add_obj(context, obj, self.bme_add_options)
        self.objs = self.bmeCON.available_objs(ensure_bmeditor=True, ensure_ray=True)
        if not self.objs:
            utils.notifications.init(context, messages=[("$Error", "Are the mesh objects visible?")])
            self.bmeCON.close(context, revert=True)
            return {'CANCELLED'}

        # Modal Ops
        self.loop_sel_ops = utils.modal_ops.EdgeLoopSelectV3D()
        self.loop_sel_ops.start(context, event, step_limit=self.op_prefs.step_limit, angle_limit=self.op_prefs.angle_limit, break_at_boundary=self.op_prefs.break_at_boundary, break_at_intersections=self.op_prefs.break_at_intersections)
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.objs)
        context.tool_settings.mesh_select_mode = (False, True, False)
        self.setup_status_and_help_panels(context)
        self.setup_slide_menu(context, event)
        utils.modal_ops.standard_modal_setup(self, context, event, utils)
        return {"RUNNING_MODAL"}

    # --- MODAL --- #

    def modal(self, context, event):
        except_guard_prop_set(self.update, (context, event), self, 'modal_status', MODAL_STATUS.ERROR)
        # Catch Error / Cancelled
        if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
            self.exit_modal(context)
            return {'CANCELLED'}
        # Finished
        if self.modal_status == MODAL_STATUS.CONFIRM:
            self.exit_modal(context)
            return {'FINISHED'}
        # View Movement
        if self.modal_status == MODAL_STATUS.PASS:
            context.area.tag_redraw()
            return {'PASS_THROUGH'}
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}


    def update(self, context, event):
        # Reset
        self.modal_status = MODAL_STATUS.RUNNING
        # Menu
        self.slide_menu.update(context, event)
        if self.slide_menu.status == UX_STATUS.ACTIVE:
            return
        # Standards
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        self.modal_status = self.std_ops.status
        if self.modal_status in {MODAL_STATUS.CANCEL, MODAL_STATUS.PASS, MODAL_STATUS.ERROR}:
            return
            # Help
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_status_and_help_panels(context)
        # Finished
        if self.modal_status == MODAL_STATUS.CONFIRM:
            self.loop_sel_ops.select_mesh_geo(context)
            if event.shift:
                self.loop_sel_ops.start(context, event, step_limit=self.op_prefs.step_limit, angle_limit=self.op_prefs.angle_limit, break_at_boundary=self.op_prefs.break_at_boundary, break_at_intersections=self.op_prefs.break_at_intersections)
                self.modal_status = MODAL_STATUS.RUNNING
            else:
                return
        # Loop Select
        self.loop_sel_ops.update(context, event, self.bmeCON)
        if self.loop_sel_ops.status in {OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED}:
            self.modal_status = MODAL_STATUS.CANCEL


    def exit_modal(self, context):
        def shut_down():
            self.slide_menu.close(context)
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                self.std_ops.close(context, revert=True)
                self.bmeCON.close(context, revert=True)
            else:
                self.std_ops.close(context, revert=False)
                self.bmeCON.close(context, revert=False)
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils, restore_select_mode=False)
        self.std_ops = None
        self.bmeCON = None
        del self.bmeCON
        gc.collect()
        toggle = utils.context.object_mode_toggle_start(context)
        if toggle: utils.context.object_mode_toggle_end(context)

    # --- MENU --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [("H", "Toggle Help")]
        if self.prefs.settings.show_modal_help:
            help_msgs = [
                ("H"        , "Toggle Help"),
                ("LMB"      , "Finish"),
                ("RMB"      , "Cancel"),
                ("W"        , "Wire Display"),
                ("SHIFT + Z", "VP Display"),
                ("$LOOP-SEL",),
                ("SHIFT", "Append Select")]
        status_msgs = [("Loop Select",), ("(SHIFT)", "Append")]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_slide_menu(self, context, event):
        SlideProp = utils.modal_ux.SlideProp
        SlideMenu = utils.modal_ux.SlideMenu
        callback = self.slide_menu_callback
        props = [
            SlideProp(as_slider=True, label="Step Limit" , label_len=6, instance=self.op_prefs, prop_type=int, prop_name='step_limit', prop_len=4, min_val=0, max_val=self.op_prefs.step_limit + 10, soft_max=True, increment=1, callback=callback),
            SlideProp(as_slider=True, label="Angle Limit", label_len=6, instance=self.op_prefs, prop_type=float, prop_name='angle_limit', prop_len=4, min_val=0, max_val=pi, as_degrees=True, callback=callback),
            SlideProp(as_slider=False, label="Break at Boundary", label_len=12, instance=self.op_prefs, prop_type=bool, prop_name='break_at_boundary', prop_len=2, callback=callback),
            SlideProp(as_slider=False, label="Break at Intersection", label_len=12, instance=self.op_prefs, prop_type=bool, prop_name='break_at_intersections', prop_len=2, callback=callback),
        ]
        self.slide_menu = SlideMenu(context, event, slide_props=props)


    def slide_menu_callback(self, context, event, slide_prop):
        label = slide_prop.label
        if label == "Step Limit":
            self.loop_sel_ops.step_limit = self.op_prefs.step_limit
        elif label == "Angle Limit":
            self.loop_sel_ops.angle_limit = self.op_prefs.angle_limit
        elif label == "Break at Boundary":
            self.loop_sel_ops.break_at_boundary = self.op_prefs.break_at_boundary
        elif label == "Break at Intersection":
            self.loop_sel_ops.break_at_intersections = self.op_prefs.break_at_intersections

    # --- SHADER --- #

    def draw_post_view(self, context):
        self.loop_sel_ops.draw_3d(context)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.loop_sel_ops.draw_2d(context)
        self.slide_menu.draw()
