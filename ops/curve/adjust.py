########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Adjust Curves\n
• Adjust the selected curves"""

class PS_OT_AdjustCurves(bpy.types.Operator):
    bl_idname      = "ps.adjust_curves"
    bl_label       = "Adjust Curves"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects_selected_or_in_mode(context, types={'CURVE'})


    def invoke(self, context, event):
        self.prefs = utils.addon.user_prefs()
        # Edit Mode Objects : With selected edges
        self.curves = utils.context.get_objects_selected_or_in_mode(context, types={'CURVE'})
        if not self.curves:
            utils.notifications.init(context, messages=[("$Error", "No curves found")])
            return {'CANCELLED'}
        # Backup Data
        self.revert_data = dict()
        for curve in self.curves:
            copied_curve_data = utils.curve.create_copy(curve)
            if isinstance(copied_curve_data, bpy.types.Curve):
                self.revert_data[curve.name] = copied_curve_data
        # Props
        self.spline_types = ['BEZIER', 'POLY', 'NURBS']
        self.spline_type = self.spline_types[0]
        self.use_smooth = True
        self.fill_end_caps = True
        self.resolution = 3
        self.radius = 0.05
        # Setup
        active_object = None
        if context.mode == 'EDIT_CURVE':
            if context.edit_object in self.curves:
                active_object = context.edit_object
        if not active_object:
            if context.active_object in self.curves:
                active_object = context.active_object
        if not active_object:
            active_object = self.curves[0]
        if isinstance(active_object, bpy.types.Object):
            self.fill_end_caps = active_object.data.use_fill_caps
            self.resolution = active_object.data.bevel_resolution
            self.radius = active_object.data.bevel_depth
            for spline in active_object.data.splines:
                self.use_smooth = spline.use_smooth
                if spline.type in self.spline_types:
                    self.spline_type = spline.type
                break
        self.sync_curve_settings()
        # Graphics
        self.obj_count_str = str(len(self.curves))
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.curves)
        # Menus
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
                for curve in self.curves:
                    if curve.name in self.revert_data:
                        copied_curve_data = self.revert_data[curve.name]
                        if isinstance(copied_curve_data, bpy.types.Curve):
                            utils.curve.swap_curve_data_and_remove_current(context, curve, copied_curve_data)
            else:
                self.std_ops.close(context, revert=False)
                for curve in self.curves:
                    if curve.name in self.revert_data:
                        copied_curve_data = self.revert_data[curve.name]
                        if isinstance(copied_curve_data, bpy.types.Curve):
                            utils.curve.delete_curve_data(copied_curve_data)
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
            SlideProp(as_slider=True , label="Resolution", label_len=6, label_tip="", instance=self, prop_type=int  , prop_name='resolution', prop_len=4, min_val=0, max_val=6, soft_max=True, callback=callback),
            SlideProp(as_slider=True , label="Radius"    , label_len=6, label_tip="", instance=self, prop_type=float, prop_name='radius'    , prop_len=4, min_val=0, max_val=1, soft_max=True, callback=callback),
            SlideProp(as_slider=False, label="Type"          , label_len=7, label_tip="", instance=self, prop_type=list, prop_name='spline_types'  , prop_len=7, index=self.spline_types.index(self.spline_type), callback=callback),
            SlideProp(as_slider=False, label="Smooth"        , label_len=7, label_tip="", instance=self, prop_type=bool, prop_name='use_smooth'    , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="End Caps"      , label_len=7, label_tip="", instance=self, prop_type=bool, prop_name='fill_end_caps' , prop_len=7, callback=callback),
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
        elif label == "Type":
            self.spline_type = self.spline_types[slide_prop.index]
            self.update_curves_to_copy(context)
            self.sync_curve_settings()
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

    def update_curves_to_copy(self, context):
        utils.context.object_mode_toggle_start(context)
        for curve in self.curves:
            if curve.name in self.revert_data:
                copied_curve_data = self.revert_data[curve.name]
                if isinstance(copied_curve_data, bpy.types.Curve):
                    utils.curve.swap_curve_data_and_remove_current(context, curve, copied_curve_data)
                copied_curve_data = utils.curve.create_copy(curve)
                if isinstance(copied_curve_data, bpy.types.Curve):
                    self.revert_data[curve.name] = copied_curve_data
        utils.context.object_mode_toggle_end(context)


    def sync_curve_settings(self):
        for curve in self.curves:
            utils.curve.set_smooth(curve, smooth=self.use_smooth)
            utils.curve.set_radius(curve, radius=self.radius)
            utils.curve.set_fill_end_caps(curve, fill_end_caps=self.fill_end_caps)
            utils.curve.set_bevel_resolution(curve, resolution=self.resolution)
            utils.curve.set_spline_type(curve, spline_type=self.spline_type)
