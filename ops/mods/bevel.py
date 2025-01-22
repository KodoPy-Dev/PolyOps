########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from mathutils import Vector
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Bevel\n
• Object Mode
\t\t→ (LMB) Adjust last or create new
\t\t→ (CTRL) New\n
• Edit Mode
\t\t→ (LMB)(With Selection) Adjust best matching from Vertex Group or New
\t\t→ (CTRL) New with vertex group if selection else standard\n
(SHIFT)
\t\t→ Bypass Sync Mode
\t\t→ Bypass Apply Scale"""

class PS_OT_Bevel(bpy.types.Operator):
    bl_idname      = "ps.bevel"
    bl_label       = "Bevel"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, single_resolve=True, types={'MESH', 'CURVE'}, selected_only=False)


    def invoke(self, context, event):
        # Common Data
        self.prefs = utils.addon.user_prefs()
        self.obj = utils.context.get_objects(context, single_resolve=True, types={'MESH', 'CURVE'}, selected_only=False)
        self.objs = utils.context.get_objects_selected_or_in_mode(context, types={'MESH', 'CURVE'})
        self.mod = None
        self.mod_controllers = []
        self.sync_mode = False if event.shift else True
        self.apply_scale = False if event.shift else True
        self.smooth = True
        self.weighted_nor = bool(utils.modifiers.last_weighted_normal_mod(self.obj))
        self.obj_names = []
        self.mod_names = []
        # Slide Menu Data
        self.offset_type = ['OFFSET', 'WIDTH', 'DEPTH', 'PERCENT', 'ABSOLUTE']
        self.miter_outer = ['MITER_SHARP', 'MITER_PATCH', 'MITER_ARC']
        self.miter_inner = ['MITER_ARC', 'MITER_SHARP']
        self.affect_types = ['EDGES', 'VERTICES']
        self.smooth_angles = [0, 15, 30, 35, 45, 60]
        self.smooth_angle = math.radians(35)
        # Error
        if (not self.obj) or (not self.objs) or (self.obj not in self.objs):
            msgs = [("$Error", "Setup Invalid (Step 1)"), ("Tip", "Are the objects selected?")]
            utils.notifications.init(context, messages=msgs)
            return {'CANCELLED'}
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.objs, track_scale=True, track_shading_mods=True, track_vgroups=True, track_polygon_shading=True, track_spline_shading=True)
        if self.apply_scale:
            self.std_ops.set_object_scale()
        # Data : Setup
        self.setup_data(context, event)
        # Error
        if (not self.mod) or (not all([controller.status() == 'OK' for controller in self.mod_controllers])):
            utils.notifications.init(context, messages=[("$Error", "Setup Invalid (Step 2)")])
            return {'CANCELLED'}
        # Sync to Init
        self.sync_settings()
        # Shading : Setup
        self.smooth_angle_setup()
        self.std_ops.set_shading(use_smooth=self.smooth, use_weighted_normal=self.weighted_nor, angle=self.smooth_angle)
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
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        self.modal_status = self.std_ops.status

        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_status_and_help_panels(context)


    def exit_modal(self, context):
        def shut_down():
            self.slide_menu.close(context)
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                for controller in self.mod_controllers:
                    controller.reset(revert_props=True, remove_created=True, reset_stack_order=True)
                self.std_ops.close(context, revert=True)
            else:
                self.std_ops.close(context, revert=False)
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)

    # --- MENU --- #

    def setup_status_and_help_panels(self, context):
        help_msgs = [("H", "Toggle Help")]
        if self.prefs.settings.show_modal_help:
            help_msgs = [
                ("H"        , "Toggle Help"),
                ("LMB"      , "Finish"),
                ("RMB"      , "Cancel"),
                ("W"        , "Wire Display"),
                ("SHIFT + Z", "VP Display"),]
        status_msgs = [
            ("Bevel",),
            ("Object"  , str(self.obj.name)),
            ("Modifier", str(self.mod.name)),
            ("Objects" , str(len(self.objs))),
        ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_slide_menu(self, context, event):
        SlideProp = utils.modal_ux.SlideProp
        SlideMenu = utils.modal_ux.SlideMenu
        # Setup
        self.obj_names = [obj.name for obj in self.objs]
        self.mod_names = [mod.name for mod in self.obj.modifiers]
        # Max Values
        ma1 = max([controller.mod.segments for controller in self.mod_controllers]) + 3
        ma2 = max([len(controller.obj.material_slots) for controller in self.mod_controllers])
        # Indexes
        i1 = self.obj_names.index(self.obj.name)
        i2 = self.mod_names.index(self.mod.name)
        i3 = self.offset_type.index(self.mod.offset_type)
        i4 = self.miter_outer.index(self.mod.miter_outer)
        i5 = self.miter_inner.index(self.mod.miter_inner)
        i6 = self.smooth_angle_setup()
        i7 = self.affect_types.index(self.mod.affect)
        # Tips
        t0 = "(LMB) Pick Modifier (SHIFT) Move Modifier Up (CTRL) Move Modifier Down"
        t1 = "Show modifier in viewport"
        t2 = "Sync the current modifier settings to the other objects"
        t3 = "Auto-Smoothing angles"
        t4 = "Assign / Remove weighted normal modifier"
        t5 = "Clamp the width to avoid overlap"
        t6 = "Match normals of new faces to adjacent faces"
        t7 = "Mark seams along beveled edges"
        t8 = "Mark beveled edges as sharp"
        t9 = "Apply scale to objects"
        t10 = "Set to 0.5"
        t11 = "Does not sync to other bevels."
        t12 = "Set the 30º"
        # Invalid List Items
        iv1 = [self.obj.name]
        iv2 = []
        for controller in self.mod_controllers:
            if controller.obj == self.obj:
                iv2 = [mod.name for mod in self.obj.modifiers if mod not in controller.mods or mod == self.mod]
                break
        # Slides
        callback = self.slide_menu_callback
        props = [
            SlideProp(as_slider=True , label="Angle"       , label_len=6, label_tip=t12,instance=self.mod, prop_type=float, prop_name='angle_limit'      , prop_len=4, callback=callback, increment=math.radians(1.0), min_val=0, max_val=math.pi, as_degrees=True, label_callback=self.angle_label_callback),
            SlideProp(as_slider=True , label="Profile"     , label_len=6, label_tip=t10,instance=self.mod, prop_type=float, prop_name='profile'          , prop_len=4, callback=callback, increment=1/16, min_val=0, max_val=1, label_callback=self.profile_label_callback),
            SlideProp(as_slider=True , label="Segments"    , label_len=6, label_tip="", instance=self.mod, prop_type=int  , prop_name='segments'         , prop_len=4, callback=callback, increment=1, min_val=1, max_val=ma1, soft_max=True),
            SlideProp(as_slider=True , label="Width"       , label_len=6, label_tip="", instance=self.mod, prop_type=float, prop_name='width'            , prop_len=4, callback=callback, increment=1/16, min_val=0, max_val=1, soft_max=True),
            SlideProp(as_slider=False, label="Object"      , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='obj_names'        , prop_len=7, callback=callback, index=i1, invalid_list_opts=iv1, preview_callback=self.obj_preview_callback),
            SlideProp(as_slider=False, label="Modifier"    , label_len=7, label_tip=t0, instance=self    , prop_type=list , prop_name='mod_names'        , prop_len=7, callback=callback, index=i2, invalid_list_opts=iv2, panel_box_shift_callback=self.mods_panel_shift_callback, panel_box_ctrl_callback=self.mods_panel_ctrl_callback),
            SlideProp(as_slider=False, label="Show VP"     , label_len=7, label_tip=t1, instance=self.mod, prop_type=bool , prop_name='show_viewport'    , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Sync Mode"   , label_len=7, label_tip=t2, instance=self    , prop_type=bool , prop_name='sync_mode'        , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Material"    , label_len=7, label_tip="", instance=self.mod, prop_type=int  , prop_name='material'         , prop_len=7, callback=callback, min_val=-1, max_val=ma2),
            SlideProp(as_slider=False, label="Offset Type" , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='offset_type'      , prop_len=7, callback=callback, index=i3),
            SlideProp(as_slider=False, label="Miter Outer" , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='miter_outer'      , prop_len=7, callback=callback, index=i4),
            SlideProp(as_slider=False, label="Miter Inner" , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='miter_inner'      , prop_len=7, callback=callback, index=i5),
            SlideProp(as_slider=False, label="Smoothing"   , label_len=7, label_tip=t3, instance=self    , prop_type=list , prop_name='smooth_angles'    , prop_len=7, callback=callback, as_degrees=True, index=i6),
            SlideProp(as_slider=False, label="Weighted N"  , label_len=7, label_tip=t4, instance=self    , prop_type=bool , prop_name='weighted_nor'     , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Clamp"       , label_len=7, label_tip=t5, instance=self.mod, prop_type=bool , prop_name='use_clamp_overlap', prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Harden"      , label_len=7, label_tip=t6, instance=self.mod, prop_type=bool , prop_name='harden_normals'   , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Mark Seam"   , label_len=7, label_tip=t7, instance=self.mod, prop_type=bool , prop_name='mark_seam'        , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Mark Sharp"  , label_len=7, label_tip=t8, instance=self.mod, prop_type=bool , prop_name='mark_sharp'       , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Apply Scale" , label_len=7, label_tip=t9, instance=self    , prop_type=bool , prop_name='apply_scale'      , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Affect Type" , label_len=7, label_tip=t11,instance=self    , prop_type=list , prop_name='affect_types'     , prop_len=7, callback=callback, index=i7),
        ]
        # Menu
        self.slide_menu = SlideMenu(context, event, slide_props=props)


    def slide_menu_callback(self, context, event, slide_prop):
        label = slide_prop.label
        # COMMON
        if label == "Object":
            self.rebuild_slides_menu_if_valid(context, event, slide_prop)
        elif label == "Modifier":
            self.rebuild_slides_menu_if_valid(context, event, slide_prop)
        # BEVEL
        elif label == "Offset Type":
            self.mod.offset_type = self.offset_type[slide_prop.index]
            self.sync_settings()
        elif label == "Miter Outer":
            self.mod.miter_outer = self.miter_outer[slide_prop.index]
            self.sync_settings()
        elif label == "Miter Inner":
            self.mod.miter_inner = self.miter_inner[slide_prop.index]
            self.sync_settings()
        elif label == "Apply Scale":
            if self.apply_scale:
                self.std_ops.set_object_scale()
            else:
                self.std_ops.revert_object_scale()
        elif label == "Smoothing":
            value = self.smooth_angles[slide_prop.index]
            if value == 0:
                self.smooth = False
                self.smooth_angle = 0
            else:
                self.smooth = True
                self.smooth_angle = math.radians(float(value))
            if self.sync_mode:
                self.std_ops.set_shading(use_smooth=self.smooth, use_weighted_normal=self.weighted_nor, angle=self.smooth_angle)
            else:
                self.std_ops.set_shading(specified_objs=[self.obj], use_smooth=self.smooth, use_weighted_normal=self.weighted_nor, angle=self.smooth_angle)
        elif label == "Weighted N":
            if self.sync_mode:
                self.std_ops.set_shading(use_smooth=self.smooth, use_weighted_normal=self.weighted_nor, angle=self.smooth_angle)
            else:
                self.std_ops.set_shading(specified_objs=[self.obj], use_smooth=self.smooth, use_weighted_normal=self.weighted_nor, angle=self.smooth_angle)
        elif label == "Affect Type":
            self.mod.affect = self.affect_types[slide_prop.index]
        else:
            self.sync_settings()


    def mods_panel_shift_callback(self, context, event, slide_prop):
        for controller in self.mod_controllers:
            if controller.obj == self.obj and controller.mod == self.mod:
                controller.move_curent_mod(move_up=True)
                self.mod_names = [mod.name for mod in self.obj.modifiers]
                if self.mod.name in self.mod_names:
                    slide_prop.index = self.mod_names.index(self.mod.name)
                    slide_prop.invalid_list_opts = [mod.name for mod in self.obj.modifiers if mod not in controller.mods or mod == self.mod]
                break


    def mods_panel_ctrl_callback(self, context, event, slide_prop):
        for controller in self.mod_controllers:
            if controller.obj == self.obj and controller.mod == self.mod:
                controller.move_curent_mod(move_up=False)
                self.mod_names = [mod.name for mod in self.obj.modifiers]
                if self.mod.name in self.mod_names:
                    slide_prop.index = self.mod_names.index(self.mod.name)
                    slide_prop.invalid_list_opts = [mod.name for mod in self.obj.modifiers if mod not in controller.mods or mod == self.mod]
                break


    def angle_label_callback(self, context, event, slide_prop):
        self.mod.angle_limit = math.radians(30)
        self.sync_settings()


    def profile_label_callback(self, context, event, slide_prop):
        self.mod.profile = 0.5
        self.sync_settings()


    def obj_preview_callback(self, context, event, slide_prop, index=0, initialized=False):
        if initialized == False:
            obj_name = self.objs[index].name
            for obj in self.objs:
                if obj.name == obj_name:
                    utils.poly_fade.init(obj=obj, bounding_box_only=True)
                    utils.modal_labels.fade_label_init(context, text=obj.name, coord_ws=obj.matrix_world.translation)
                    return


    def rebuild_slides_menu_if_valid(self, context, event, slide_prop):
        rebuild = False
        if slide_prop.label == "Object":
            sel_obj_name = self.obj_names[slide_prop.index]
            if self.obj.name != sel_obj_name:
                for obj in self.objs:
                    if obj.name == sel_obj_name:
                        self.obj = obj
                        rebuild = True
                        break
            if rebuild:
                for controller in self.mod_controllers:
                    if controller.obj == self.obj:
                        if controller.status() == 'OK':
                            self.mod = controller.mod
        elif slide_prop.label == "Modifier":
            sel_mod_name = self.mod_names[slide_prop.index]
            if self.mod.name != sel_mod_name:
                for controller in self.mod_controllers:
                    if rebuild:
                        break
                    if controller.obj == self.obj:
                        for mod in controller.mods:
                            if mod.name == sel_mod_name:
                                controller.set_current_mod(mod)
                                self.mod = controller.mod
                                rebuild = True
                                break
        if rebuild:
            self.sync_mode = False
            if self.obj:
                utils.object.select_obj(context, self.obj, make_active=True)
            self.mod_names = [mod.name for mod in self.obj.modifiers]
            self.setup_slide_menu(context, event)
            self.setup_status_and_help_panels(context)

    # --- SHADER --- #

    def draw_post_view(self, context):
        pass


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()

        self.slide_menu.draw()

    # --- UTILS --- #

    def setup_data(self, context, event):
        ModController = utils.modifiers.ModController
        mod_type = utils.modifiers.TYPES.BEVEL
        mode = context.mode
        if mode != 'OBJECT':
            utils.context.object_mode_toggle_start(context)
        for obj in self.objs:
            controller = ModController(obj, mod_type=mod_type)
            self.mod_controllers.append(controller)
            # Edit Mode Setup
            if mode == 'EDIT_MESH':
                vgroup, vgroup_created, mod, mod_created = utils.modifiers.mod_from_edit_mode(context, obj, mod_type=mod_type, sort_when_new=True, only_new=event.ctrl)
                controller.add_mod(mod)
                finalize_mod_settings(context, mode, obj, mod)
            # Object Mode New
            elif event.ctrl or not controller.mods:
                mod = controller.new_mod()
                finalize_mod_settings(context, mode, obj, mod)
            # Object Mode Set Current
            else:
                controller.mod = None
                for mod in reversed(controller.mods):
                    controller.set_current_mod(mod)
                    break
            # Backup
            if controller.mod is None:
                mod = controller.new_mod()
                finalize_mod_settings(context, mode, obj, mod)
            # Sort Modifiers
            controller.sort()
            # Active Mod
            if obj == self.obj:
                self.mod = controller.mod
        if mode != 'OBJECT':
            utils.context.object_mode_toggle_end(context)
        if self.obj:
            utils.object.select_obj(context, self.obj, make_active=True)


    def sync_settings(self):
        if self.sync_mode == False:
            return
        for controller in self.mod_controllers:
            if controller.mod == self.mod:
                continue
            mod = controller.mod
            mod.show_viewport = self.mod.show_viewport
            mod.angle_limit = self.mod.angle_limit
            mod.material = self.mod.material
            mod.profile = self.mod.profile
            mod.width = self.mod.width
            mod.use_clamp_overlap = self.mod.use_clamp_overlap
            mod.harden_normals = self.mod.harden_normals
            mod.mark_seam = self.mod.mark_seam
            mod.mark_sharp = self.mod.mark_sharp
            # Possibly Slower to Set
            if mod.width != self.mod.width:
                mod.width = self.mod.width
            if mod.segments != self.mod.segments:
                mod.segments = self.mod.segments


    def smooth_angle_setup(self):
        angle = utils.modifiers.last_auto_smooth_angle(self.obj)
        if angle != None:
            self.smooth_angle = angle
            angle = round(math.degrees(angle))
            if angle not in self.smooth_angles:
                self.smooth_angles.append(angle)
            return self.smooth_angles.index(angle)
        return 0


def finalize_mod_settings(context, mode, obj, mod):
    if not utils.object.obj_has_flat_dim(obj):
        return
    # if mod.vertex_group:
    #     return
    if mode == 'EDIT_MESH':
        if not any([v.select for v in obj.data.vertices]):
            return
    indices = utils.bmu.query_vert_indices_from_boundary_or_wire(context, obj)
    if not indices:
        return
    mod.affect = 'VERTICES'
    if not mod.vertex_group:
        vgroup = utils.mesh.create_vgroup(context, obj, name=mod.name, vertex_indices=indices)
        utils.modifiers.assign_vgroup_to_mod(obj, mod, vgroup, mod_type=utils.modifiers.TYPES.BEVEL)
