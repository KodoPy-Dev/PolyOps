########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Mesh to Curve\n
• Edit Mode
\t\t→ Create curve from selected edges"""

class PS_OT_MeshToCurve(bpy.types.Operator):
    bl_idname      = "ps.mesh_to_curve"
    bl_label       = "Mesh to Curve"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        self.prefs = utils.addon.user_prefs()
        # Edit Mode Objects : With selected edges
        objs = utils.context.get_mesh_objs_from_edit_mode_if_edges_selected(context)
        if not objs:
            utils.notifications.init(context, messages=[("$Error", "No edges selected")])
            return {'CANCELLED'}
        # Props
        self.simplify = True
        self.use_smooth = True
        self.fill_end_caps = True
        self.resolution = 3
        self.radius = 0.05
        self.exit_to_curves = False
        self.objs = objs
        self.active_curve = None
        self.curves = []
        # Setup
        self.create_curves(context)
        if not self.curves or not self.active_curve:
            utils.notifications.init(context, messages=[("$Error", "No no curves created")])
            return {'CANCELLED'}
        # Graphics
        self.obj_count_str = str(len(objs))
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.curves)
        self.setup_status_and_help_panels(context)
        self.setup_slide_menu(context, event)
        utils.modal_ops.standard_modal_setup(self, context, event, utils)
        return {"RUNNING_MODAL"}


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
        self.modal_status = MODAL_STATUS.RUNNING
        self.slide_menu.update(context, event)
        if self.slide_menu.status == UX_STATUS.ACTIVE:
            return
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_status_and_help_panels(context)
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        self.modal_status = self.std_ops.status


    def exit_modal(self, context):
        def shut_down():
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                self.std_ops.close(context, revert=True)
                for curve in self.curves[:]:
                    utils.curve.delete_curve(curve)
            else:
                self.std_ops.close(context, revert=False)
                if self.exit_to_curves and self.curves:
                    utils.context.set_mode(target_mode='OBJECT')
                    utils.object.select_none(context)
                    for curve in self.curves:
                        utils.object.select_obj(context, obj=curve)
                    utils.object.select_obj(context, obj=self.active_curve, make_active=True)
                    utils.context.set_mode(target_mode='EDIT_CURVE')
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)

    # --- MENU --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [("H", "Toggle Help")]
        if self.prefs.settings.show_modal_help:
            help_msgs = [
                ("H"        , "Toggle Help"),
                ("LMB"      , "Confirm"),
                ("RMB / ESC", "Cancel"),
                ("SHIFT + Z", "VP Display"),
                ("W"        , "Wire Display"),
            ]
        status_msgs = [
            ("Ops",),
            ("Objects" , self.obj_count_str),
        ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_slide_menu(self, context, event):
        SlideProp = utils.modal_ux.SlideProp
        SlideMenu = utils.modal_ux.SlideMenu
        # Slides
        callback = self.slide_menu_callback
        props = [
            SlideProp(as_slider=True , label="Resolution", label_len=6, label_tip="", instance=self, prop_type=int  , prop_name='resolution'  , prop_len=4, min_val=0, max_val=6, soft_max=True, callback=callback),
            SlideProp(as_slider=True , label="Radius"    , label_len=6, label_tip="", instance=self, prop_type=float, prop_name='radius', prop_len=4, min_val=0, max_val=1, soft_max=True, callback=callback),
            SlideProp(as_slider=False, label="Smooth"        , label_len=7, label_tip="", instance=self, prop_type=bool, prop_name='use_smooth'    , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="End Caps"      , label_len=7, label_tip="", instance=self, prop_type=bool, prop_name='fill_end_caps' , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Exit to Curves", label_len=9, label_tip="", instance=self, prop_type=bool, prop_name='exit_to_curves', prop_len=5, callback=callback),
        ]
        # Menu
        self.slide_menu = SlideMenu(context, event, slide_props=props)


    def slide_menu_callback(self, context, event, slide_prop):
        label = slide_prop.label
        if label == "Resolution":
            for curve in self.curves:
                utils.curve.set_bevel_resolution(curve, resolution=self.resolution)
        elif label == "Radius":
            for curve in self.curves:
                utils.curve.set_radius(curve, radius=self.radius)
        elif label == "Smooth":
            for curve in self.curves:
                utils.curve.set_smooth(curve, smooth=self.use_smooth)
        elif label == "End Caps":
            for curve in self.curves:
                utils.curve.set_fill_end_caps(curve, fill_end_caps=self.fill_end_caps)

    # --- SHADER --- #

    def draw_post_view(self, context):
        pass


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.slide_menu.draw()

    # --- UTILS --- #

    def create_curves(self, context):
        for obj in self.objs:
            curve = utils.bmu.ops_selections_to_curves(context, obj, simplify=self.simplify)
            if curve is None:
                continue
            if obj == context.edit_object:
                self.active_curve = curve
            self.curves.append(curve)
            utils.curve.set_smooth(curve, smooth=self.use_smooth)
            utils.curve.set_radius(curve, radius=self.radius)
            utils.curve.set_spline_type(curve=curve, spline_type='BEZIER')
            utils.curve.set_bevel_resolution(curve, resolution=self.resolution)
            utils.curve.set_fill_end_caps(curve, fill_end_caps=self.fill_end_caps)
        if not self.active_curve and self.curves:
            self.active_curve = self.curves[0]

