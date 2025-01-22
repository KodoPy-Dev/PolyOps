########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Solidify\n
• Object Mode
\t\t→ (LMB) Adjust last or create new
\t\t→ (CTRL) New\n
• Edit Mode
\t\t→ (LMB)(With Selection) Adjust best matching from Vertex Group or New
\t\t→ (CTRL) New with vertex group if selection else standard\n
(SHIFT)
\t\t→ Bypass Sync Mode"""

class PS_OT_Solidify(bpy.types.Operator):
    bl_idname      = "ps.solidify"
    bl_label       = "Solidify"
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
            ("Solidify",),
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
        # Indexes
        i1 = self.obj_names.index(self.obj.name)
        i2 = self.mod_names.index(self.mod.name)
        # Tips
        t0 = "(LMB) Pick Modifier (SHIFT) Move Modifier Up (CTRL) Move Modifier Down"
        t1 = "Show modifier in viewport"
        t2 = "Sync the current modifier settings to the other objects"
        t3 = "Set to 0"
        t4 = "Set to 0.125"
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
            SlideProp(as_slider=True , label="Offset"      , label_len=6, label_tip=t3, instance=self.mod, prop_type=float, prop_name='offset'             , prop_len=4, callback=callback, increment=1/16, min_val=-1, soft_min=True, max_val=1, soft_max=True, label_callback=self.offset_label_callback),
            SlideProp(as_slider=True , label="Thickness"   , label_len=6, label_tip=t4, instance=self.mod, prop_type=float, prop_name='thickness'          , prop_len=4, callback=callback, increment=1/16, min_val=-1, soft_min=True, max_val=1, soft_max=True, label_callback=self.thickness_label_callback),
            SlideProp(as_slider=False, label="Object"      , label_len=7, label_tip="", instance=self    , prop_type=list , prop_name='obj_names'          , prop_len=7, callback=callback, index=i1, invalid_list_opts=iv1, preview_callback=self.obj_preview_callback),
            SlideProp(as_slider=False, label="Modifier"    , label_len=7, label_tip=t0, instance=self    , prop_type=list , prop_name='mod_names'          , prop_len=7, callback=callback, index=i2, invalid_list_opts=iv2, panel_box_shift_callback=self.mods_panel_shift_callback, panel_box_ctrl_callback=self.mods_panel_ctrl_callback),
            SlideProp(as_slider=False, label="Show VP"     , label_len=7, label_tip=t1, instance=self.mod, prop_type=bool , prop_name='show_viewport'      , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Sync Mode"   , label_len=7, label_tip=t2, instance=self    , prop_type=bool , prop_name='sync_mode'          , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Even Mode"   , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='use_even_offset'    , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Use Rim"     , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='use_rim'            , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Only Rim"    , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='use_rim_only'       , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Flip Normals", label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='use_flip_normals'   , prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="HQ Normals"  , label_len=7, label_tip="", instance=self.mod, prop_type=bool , prop_name='use_quality_normals', prop_len=7, callback=callback),
            SlideProp(as_slider=False, label="Mat Body"    , label_len=7, label_tip="", instance=self.mod, prop_type=int  , prop_name='material_offset'    , prop_len=7, callback=callback, increment=1, min_val=-1, soft_min=True, max_val=1, soft_max=True),
            SlideProp(as_slider=False, label="Mat Rim"     , label_len=7, label_tip="", instance=self.mod, prop_type=int  , prop_name='material_offset_rim', prop_len=7, callback=callback, increment=1, min_val=-1, soft_min=True, max_val=1, soft_max=True),
            SlideProp(as_slider=False, label="Crease-In"   , label_len=7, label_tip="", instance=self.mod, prop_type=float, prop_name='edge_crease_inner'  , prop_len=7, callback=callback, increment=1/16, min_val=0, max_val=1),
            SlideProp(as_slider=False, label="Crease-Out"  , label_len=7, label_tip="", instance=self.mod, prop_type=float, prop_name='edge_crease_outer'  , prop_len=7, callback=callback, increment=1/16, min_val=0, max_val=1),
            SlideProp(as_slider=False, label="Crease-Rim"  , label_len=7, label_tip="", instance=self.mod, prop_type=float, prop_name='edge_crease_rim'    , prop_len=7, callback=callback, increment=1/16, min_val=0, max_val=1),
            SlideProp(as_slider=False, label="Bevel Convex", label_len=7, label_tip="", instance=self.mod, prop_type=float, prop_name='bevel_convex'       , prop_len=7, callback=callback, increment=1/16, min_val=0, max_val=1),
            SlideProp(as_slider=False, label="Clamp"       , label_len=7, label_tip="", instance=self.mod, prop_type=float, prop_name='thickness_clamp'    , prop_len=7, callback=callback, increment=1/16, min_val=0, max_val=1, soft_max=True),
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
        # SOLIDIFY
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


    def offset_label_callback(self, context, event, slide_prop):
        self.mod.offset = 0
        self.sync_settings()


    def thickness_label_callback(self, context, event, slide_prop):
        self.mod.thickness = 0.125
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
        mod_type = utils.modifiers.TYPES.SOLIDIFY
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
            mod.solidify_mode = self.mod.solidify_mode
            mod.thickness = self.mod.thickness
            mod.offset = self.mod.offset
            mod.use_even_offset = self.mod.use_even_offset
            mod.use_rim = self.mod.use_rim
            mod.use_rim_only = self.mod.use_rim_only
            mod.use_flip_normals = self.mod.use_flip_normals
            mod.use_quality_normals = self.mod.use_quality_normals
            mod.material_offset = self.mod.material_offset
            mod.material_offset_rim = self.mod.material_offset_rim
            mod.edge_crease_inner = self.mod.edge_crease_inner
            mod.edge_crease_outer = self.mod.edge_crease_outer
            mod.edge_crease_rim = self.mod.edge_crease_rim
            mod.bevel_convex = self.mod.bevel_convex
            mod.thickness_clamp = self.mod.thickness_clamp


