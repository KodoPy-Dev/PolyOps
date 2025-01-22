########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from math import degrees, radians
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Deform\n
• Object Mode
\t\t→ (LMB) Adjust last or create new
\t\t→ (CTRL) New\n
• Edit Mode
\t\t→ (LMB)(With Selection) Adjust best matching from Vertex Group or New
\t\t→ (CTRL) New with vertex group if selection else standard\n
(SHIFT)
\t\t→ Bypass Sync Mode"""

class PS_OT_Deform(bpy.types.Operator):
    bl_idname      = "ps.deform"
    bl_label       = "Deform"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)


    def invoke(self, context, event):
        # Common Data
        self.prefs = utils.addon.user_prefs()
        self.obj = utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)
        self.objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        self.mod = None
        self.mod_controllers = []
        self.sync_mode = False if event.shift else True
        self.obj_names = []
        self.mod_names = []
        # Mod Data
        self.deform_methods = ['TWIST', 'BEND', 'TAPER', 'STRETCH']
        self.axes = ['X', 'Y', 'Z']
        self.factor = 0
        self.limit_0 = 0
        self.limit_1 = 0
        self.lock_x = False
        self.lock_y = False
        self.lock_z = False
        # Error
        if (not self.obj) or (not self.objs) or (self.obj not in self.objs):
            utils.notifications.init(context, messages=[("$Error", "Setup Invalid (Step 1)")])
            return {'CANCELLED'}
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.objs, track_vgroups=True)
        # Data : Setup
        self.setup_data(context, event)
        # Error
        if (not self.mod) or (not all([controller.status() == 'OK' for controller in self.mod_controllers])):
            utils.notifications.init(context, messages=[("$Error", "Setup Invalid (Step 2)")])
            return {'CANCELLED'}
        # Sync to Init
        self.sync_settings()
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
            ("Deform",),
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
        self.factor = self.mod.factor if self.mod.deform_method == 'TAPER' else self.mod.angle
        self.limit_0 = self.mod.limits[0]
        self.limit_1 = self.mod.limits[1]
        # Switches
        as_degrees = False if self.mod.deform_method == 'TAPER' else True
        # Min Values
        mi1 = -2 if self.mod.deform_method == 'TAPER' else radians(-180)
        # Max Values
        ma1 = 2 if self.mod.deform_method == 'TAPER' else radians(180)
        # Increments
        inc1 = 1/8 if self.mod.deform_method == 'TAPER' else radians(5)
        # Indexes
        i1 = self.obj_names.index(self.obj.name)
        i2 = self.mod_names.index(self.mod.name)
        i3 = 0
        if self.mod.deform_method in self.deform_methods:
            i3 = self.deform_methods.index(self.mod.deform_method)
        else:
            self.deform_methods.append(self.mod.deform_method)
            i3 = len(self.deform_methods) - 1
        i4 = 0
        if self.mod.deform_axis in self.axes:
            i4 = self.axes.index(self.mod.deform_axis)
        else:
            self.axes.append(self.mod.deform_axis)
            i4 = len(self.axes) - 1
        # Tips
        t0 = "(LMB) Pick Modifier (SHIFT) Move Modifier Up (CTRL) Move Modifier Down"
        t1 = "Show modifier in viewport"
        t2 = "Sync the current modifier settings to the other objects"
        t3 = self.tip_for_factor_prop()
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
            SlideProp(as_slider=True , label="Method"   , label_len=6, label_tip="", instance=self    , prop_type=list , prop_name='deform_methods', prop_len=4, callback=callback, index=i3),
            SlideProp(as_slider=True , label="Axis"     , label_len=6, label_tip="", instance=self    , prop_type=list , prop_name='axes'          , prop_len=4, callback=callback, index=i4),
            SlideProp(as_slider=True , label="Factor"   , label_len=6, label_tip=t3, instance=self    , prop_type=float, prop_name='factor'        , prop_len=4, callback=callback, as_degrees=as_degrees, min_val=mi1, soft_min=True, max_val=ma1, soft_max=True, increment=inc1, label_callback=self.factor_label_callback),
            SlideProp(as_slider=False, label="Object"   , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='obj_names'     , prop_len=8, callback=callback, index=i1, invalid_list_opts=iv1, preview_callback=self.obj_preview_callback),
            SlideProp(as_slider=False, label="Modifier" , label_len=7, label_tip=t0, instance=self    , prop_type=list , prop_name='mod_names'     , prop_len=8, callback=callback, index=i2, invalid_list_opts=iv2, panel_box_shift_callback=self.mods_panel_shift_callback, panel_box_ctrl_callback=self.mods_panel_ctrl_callback),
            SlideProp(as_slider=False, label="Show VP"  , label_len=7, label_tip=t1, instance=self.mod, prop_type=bool , prop_name='show_viewport' , prop_len=8, callback=callback),
            SlideProp(as_slider=False, label="Sync Mode", label_len=7, label_tip=t2, instance=self    , prop_type=bool , prop_name='sync_mode'     , prop_len=8, callback=callback),
            SlideProp(as_slider=False, label="Limit 0"  , label_len=7, label_tip="", instance=self    , prop_type=float, prop_name='limit_0'       , prop_len=8, callback=callback, min_val=0, max_val=1, increment=1/32),
            SlideProp(as_slider=False, label="Limit 1"  , label_len=7, label_tip="", instance=self    , prop_type=float, prop_name='limit_1'       , prop_len=8, callback=callback, min_val=0, max_val=1, increment=1/32),
            SlideProp(as_slider=False, label="Lock X"   , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='lock_x'        , prop_len=8, callback=callback),
            SlideProp(as_slider=False, label="Lock Y"   , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='lock_y'        , prop_len=8, callback=callback),
            SlideProp(as_slider=False, label="Lock Z"   , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='lock_z'        , prop_len=8, callback=callback),
        ]
        # Menu
        self.slide_menu = SlideMenu(context, event, slide_props=props)


    def slide_menu_callback(self, context, event, slide_prop):
        label = slide_prop.label
        # COMMON
        if label == "Object":
            self.rebuild_slides_menu_if_valid(context, event, slide_prop)
            return
        elif label == "Modifier":
            self.rebuild_slides_menu_if_valid(context, event, slide_prop)
            return
        # SIMPLE DEFORM
        elif label == "Method":
            index = slide_prop.index
            if index >= 0 and index < len(self.deform_methods):
                method = self.deform_methods[index]
                self.mod.deform_method = method
                self.rebuild_factor_prop(method)
        elif label == "Axis":
            index = slide_prop.index
            if index >= 0 and index < len(self.axes):
                axis = self.axes[index]
                self.mod.deform_axis = axis
        elif label == "Factor":
            self.mod.factor = self.factor
            self.mod.angle = self.factor
        elif label == "Limit 0":
            self.mod.limits[0] = self.limit_0
        elif label == "Limit 1":
            self.mod.limits[1] = self.limit_1

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


    def obj_preview_callback(self, context, event, slide_prop, index=0, initialized=False):
        if initialized == False:
            obj_name = self.objs[index].name
            for obj in self.objs:
                if obj.name == obj_name:
                    utils.poly_fade.init(obj=obj, bounding_box_only=True)
                    utils.modal_labels.fade_label_init(context, text=obj.name, coord_ws=obj.matrix_world.translation)
                    return


    def factor_label_callback(self, context, event, slide_prop):
        value = 0
        if event.shift:
            value = 2 if self.mod.deform_method == 'TAPER' else radians(90)
        elif event.ctrl:
            value = -2 if self.mod.deform_method == 'TAPER' else radians(180)
        elif event.alt:
            value = 1 if self.mod.deform_method == 'TAPER' else radians(360)
        self.factor = value
        self.mod.factor = value
        self.mod.angle = value
        self.sync_settings()


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


    def rebuild_factor_prop(self, method=''):
        factor_prop = self.slide_menu.get_slide_prop_by_label(label="Factor")
        if not factor_prop:
            return
        factor_prop.label_tip = self.tip_for_factor_prop()
        # Switch from Degrees
        if method == 'TAPER':
            factor_prop.as_degrees = False
        # Switch To Degrees
        else:
            factor_prop.as_degrees = True
        self.slide_menu.rebuild_slide_prop(factor_prop)


    def tip_for_factor_prop(self):
        if self.mod.deform_method == 'TAPER':
            return (("LMB", "0"), ("SHIFT", "2"), ("CTRL", "-2"), ("ALT", "1"))
        return (("LMB", "0º"), ("SHIFT", "90º"), ("CTRL", "180º"), ("ALT", "360º"))

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
        mod_type = utils.modifiers.TYPES.SIMPLE_DEFORM
        
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
            # Object Mode New
            elif event.ctrl or not controller.mods:
                controller.new_mod()
            # Object Mode Set Current
            else:
                controller.mod = None
                for mod in reversed(controller.mods):
                    controller.set_current_mod(mod)
                    break
            # Backup
            if controller.mod is None:
                controller.new_mod()
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
            mod.deform_method = self.mod.deform_method
            mod.deform_axis = self.mod.deform_axis
            mod.factor = self.mod.factor
            mod.angle = self.mod.angle
            mod.limits[0] = self.mod.limits[0]
            mod.limits[1] = self.mod.limits[1]

