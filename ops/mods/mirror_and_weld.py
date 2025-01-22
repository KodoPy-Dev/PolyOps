########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import gc
from enum import Enum
from mathutils import Vector, Matrix, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS, OPS_STATUS
from ...utils.event import RMB_press
except_guard_prop_set = utils.guards.except_guard_prop_set
ModType = utils.modifiers.TYPES


DESC = """Mirror & Weld\n
(LMB)
\t\t→ Slice & Weld (No Modifier)\n
(SHIFT)
\t\t→ Slice & Mirror (Modifier)\n
(CTRL)
\t\t→ Mirror & Bisect (Modifier)"""

class PS_OT_MirrorAndWeld(bpy.types.Operator):
    bl_idname      = "ps.mirror_and_weld"
    bl_label       = "Mirror & Weld"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)


    def invoke(self, context, event):
        # Data
        self.ops_prefs = utils.addon.user_prefs().operator.mirror_and_weld
        self.obj = utils.context.get_objects(context, single_resolve=True, types={'MESH'}, selected_only=False)
        if self.obj is None or not utils.mesh.mesh_obj_is_valid(context, self.obj):
            return {'CANCELLED'}
        objs = utils.context.get_mesh_objs(context, object_mode_require_selection=True, edit_mesh_mode_require_selection=False, other_mesh_modes_require_selection=False)
        self.objs = [obj for obj in objs if utils.mesh.mesh_obj_is_valid(context, obj)]
        self.wire_display_map = {obj: obj.show_wire for obj in self.objs}
        self.obj_bm_map = dict()
        # State
        self.cursor_bisect = False
        self.parent_objects_to_empty = False
        self.ensure_new_mirror_mod = False
        # Entry Points
        if event.shift:
            self.ops_prefs.tool = 'SLICE_AND_MIRROR'
        elif event.ctrl:
            self.ops_prefs.tool = 'MIRROR_AND_BISECT'
        # Ensure Proper Tool
        if self.ops_prefs.tool == 'MIRROR_OVER_ACTIVE':
            if len(self.objs) < 2:
                self.ops_prefs.tool = 'SLICE_AND_MIRROR'
                utils.notifications.init(context, messages=[("Tool", "Set to Default")])
        elif self.ops_prefs.tool == 'MIRROR_SEL_GEO' and context.mode != 'EDIT_MESH':
            self.ops_prefs.tool = 'SLICE_AND_MIRROR'
            utils.notifications.init(context, messages=[("Tool", "Set to Default")])
        # Tool Change
        self.setup_tool_change_menu(context)
        # Radial Pick
        self.cursor_quat = context.scene.cursor.matrix.to_quaternion()
        self.single_mode_quat = self.obj.matrix_world.to_quaternion()
        self.multi_mode_quat = Quaternion()
        self.pick_radial_op = utils.modal_ops.PickRadialDirFromV3D()
        self.restart_radial_ops()
        # Modal
        self.setup_status_and_help_panels(context)
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

        # Tool Change Menu
        self.tool_change_menu.update(context, event, blocked_indexes=self.get_blocked_indexes(context))
        if self.tool_change_menu.status == UX_STATUS.ACTIVE:
            self.pick_radial_op.reset()
            return

        # Needs to restart
        if self.pick_radial_op.status == OPS_STATUS.INACTIVE:
            self.restart_radial_ops()

        # Update Widget
        self.pick_radial_op.update(context, event)

        # Parent
        if event.type == 'D' and event.value == 'PRESS':
            if self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
                self.parent_objects_to_empty = not self.parent_objects_to_empty
                self.setup_status_and_help_panels(context)
                if self.parent_objects_to_empty:
                    utils.notifications.init(context, messages=[("Parent to Empty", "(On)"), ("Info", "The objects will be parented to the empty")])
                else:
                    utils.notifications.init(context, messages=[("Parent to Empty", "(Off)"), ("Info", "The objects will not be parented to the empty")])

        # Multi-Object Mode
        if event.type == 'A' and event.value == 'PRESS':
            if self.ops_prefs.tool in {'SLICE_AND_WELD', 'MIRROR_OVER_CURSOR', 'SLICE_AND_MIRROR', 'MIRROR_AND_BISECT'}:
                self.ops_prefs.multi_obj_mode = not self.ops_prefs.multi_obj_mode
                self.restart_radial_ops()
                self.setup_status_and_help_panels(context)
                if self.ops_prefs.multi_obj_mode:
                    for obj in self.objs:
                        utils.poly_fade.init(obj=obj, bounding_box_only=True)
                        utils.modal_labels.fade_label_init(context, text=obj.name, coord_ws=obj.matrix_world.translation)
                    utils.notifications.init(context, messages=[("Multi-Objects", "(On)"), ("Info", "Applies operation to all selected or all in edit mode")])
                else:
                    utils.poly_fade.init(obj=self.obj, bounding_box_only=True)
                    utils.modal_labels.fade_label_init(context, text=self.obj.name, coord_ws=self.obj.matrix_world.translation)
                    utils.notifications.init(context, messages=[("Multi-Objects", "(Off)"), ("Info", "Only applies operation to the active object")])

        # Cursor Bisect
        if event.type == 'B' and event.value == 'PRESS':
            if self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
                self.cursor_bisect = not self.cursor_bisect
                self.setup_status_and_help_panels(context)
        
        # Ensure New
        if event.type == 'N' and event.value == 'PRESS':
            if self.ops_prefs.tool in {'SLICE_AND_MIRROR', 'MIRROR_AND_BISECT'}:
                self.ensure_new_mirror_mod = not self.ensure_new_mirror_mod
                self.setup_status_and_help_panels(context)

        # Passthrough
        if self.pick_radial_op.status == OPS_STATUS.PASS:
            self.modal_status = MODAL_STATUS.PASS
            self.pick_radial_op.reset()
        # Cancelled
        elif self.pick_radial_op.status == OPS_STATUS.CANCELLED:
            self.modal_status = MODAL_STATUS.CANCEL
        # Ops
        elif self.pick_radial_op.status == OPS_STATUS.COMPLETED:
            self.modal_status = MODAL_STATUS.CONFIRM
            self.radial_ops(context)


    def exit_modal(self, context):
        def shut_down():
            for obj, show_wire in self.wire_display_map.items():
                obj.show_wire = show_wire
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)
        gc.collect()

    # --- MENUS --- #

    def setup_tool_change_menu(self, context):
        labels = [
            ("Slice & Weld", "Slice mesh along axis", "No Modifier"),
            ("Slice & Mirror", "Slice mesh along axis", "With Modifier"),
            ("Mirror & Bisect", "Use Bisect on Mirror", "With Modifier"),
            ("Mirror Over Cursor", "Mirror across the 3D Cursor", "Empty + Modifier"),
            ("Mirror Over Active", "Mirror over the active object", "Modifier"),
            ("Mirror Sel Geo", "Only mirror the selected geometry", "No Modifier")]
        self.tool_change_menu = utils.modal_ux.ListPickMenu(labels=labels, call_back=self.tool_change_menu_callback, action_key='TAB')


    def get_blocked_indexes(self, context):
        blocked_indexes = []
        if self.ops_prefs.tool == 'SLICE_AND_WELD':
            blocked_indexes.append(0)
        elif self.ops_prefs.tool == 'SLICE_AND_MIRROR':
            blocked_indexes.append(1)
        elif self.ops_prefs.tool == 'MIRROR_AND_BISECT':
            blocked_indexes.append(2)
        elif self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
            blocked_indexes.append(3)
        elif self.ops_prefs.tool == 'MIRROR_OVER_ACTIVE':
            blocked_indexes.append(4)
        elif self.ops_prefs.tool == 'MIRROR_SEL_GEO':
            blocked_indexes.append(5)
        if len(self.objs) < 2:
            blocked_indexes.append(4)
        if context.mode != 'EDIT_MESH':
            blocked_indexes.append(5)
        return blocked_indexes


    def setup_status_and_help_panels(self, context):
        status_msgs = []
        help_msgs = []
        operation = self.ops_prefs.tool.replace("_", " ").title()
        status_msgs.append((operation, ""))
        if self.ops_prefs.tool in {'SLICE_AND_WELD', 'MIRROR_SEL_GEO'}:
            status_msgs.append(("(A) Multi Mode", "On" if self.ops_prefs.multi_obj_mode else "Off"))
            help_msgs = [
                ("LMB", "Finish"),
                ("RMB", "Cancel"),
                ("TAB", "Change Tool"),
                ("A"  , "Multi-Objects")]
        elif self.ops_prefs.tool in {'SLICE_AND_MIRROR', 'MIRROR_AND_BISECT'}:
            status_msgs.append(("(A) Multi Mode", "On" if self.ops_prefs.multi_obj_mode else "Off"))
            status_msgs.append(("(N) Ensure New", "On" if self.ensure_new_mirror_mod else "Off"))
            help_msgs = [
                ("LMB", "Finish"),
                ("RMB", "Cancel"),
                ("TAB", "Change Tool"),
                ("A"  , "Multi-Objects"),
                ("N"  , "Ensure New")]
        elif self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
            status_msgs.append(("(A) Multi Mode", "On" if self.ops_prefs.multi_obj_mode else "Off"))
            status_msgs.append(("(D) Parent to Empty", "On" if self.parent_objects_to_empty else "Off"))
            status_msgs.append(("(B) Bisect", "On" if self.cursor_bisect else "Off"))
            help_msgs = [
                ("LMB", "Finish"),
                ("RMB", "Cancel"),
                ("TAB", "Change Tool"),
                ("A"  , "Multi-Objects"),
                ("B"  , "Bisect"),
                ("D"  , "Parent to Empty")]
        elif self.ops_prefs.tool == 'MIRROR_OVER_ACTIVE':
            status_msgs.append(("Multi Mode", "Always on in this mode"))
            help_msgs = [
                ("LMB", "Finish"),
                ("RMB", "Cancel"),
                ("TAB", "Change Tool")]
        utils.modal_labels.status_panel_init(context, messages=status_msgs)
        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def tool_change_menu_callback(self, context, event, label=""):
        if label == "Slice & Weld":
            self.ops_prefs.tool = 'SLICE_AND_WELD'
        elif label == "Mirror Sel Geo":
            self.ops_prefs.tool = 'MIRROR_SEL_GEO'
        elif label == "Slice & Mirror":
            self.ops_prefs.tool = 'SLICE_AND_MIRROR'
        elif label == "Mirror & Bisect":
            self.ops_prefs.tool = 'MIRROR_AND_BISECT'
        elif label == "Mirror Over Cursor":
            self.ops_prefs.tool = 'MIRROR_OVER_CURSOR'
        elif label == "Mirror Over Active":
            if len(self.objs) > 1:
                self.ops_prefs.tool = 'MIRROR_OVER_ACTIVE'
                self.pick_radial_op.start(rot=self.single_mode_quat)
                utils.poly_fade.init(obj=self.obj, bounding_box_only=True)
                utils.modal_labels.fade_label_init(context, text=self.obj.name, coord_ws=self.obj.matrix_world.translation)
            else:
                utils.notifications.init(context, messages=[("Invalid", "Need more than one other object selected")])
        self.setup_status_and_help_panels(context)

    # --- SHADERS --- #

    def draw_post_view(self, context):
        # Menu
        if self.tool_change_menu.status == UX_STATUS.ACTIVE:
            return
        # Radial
        self.pick_radial_op.draw_3d(context)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        # Tool Change Menu
        if self.tool_change_menu.status == UX_STATUS.ACTIVE:
            self.tool_change_menu.draw()
            return
        # Radial
        self.pick_radial_op.draw_2d(context)

    # --- UTILS --- #

    def restart_radial_ops(self):
        if self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
            self.pick_radial_op.start(rot=self.cursor_quat)
        else:
            if self.ops_prefs.multi_obj_mode:
                self.pick_radial_op.start(rot=self.multi_mode_quat)
            else:
                self.pick_radial_op.start(rot=self.single_mode_quat)


    def radial_ops(self, context):
        # BMESH-MAP-SETUP
        close_bmesh_required = False
        if self.ops_prefs.tool in {'SLICE_AND_WELD', 'MIRROR_SEL_GEO', 'SLICE_AND_MIRROR', 'MIRROR_AND_BISECT'}:
            close_bmesh_required = True
            objs = self.objs if self.ops_prefs.multi_obj_mode else [self.obj]
            self.obj_bm_map.clear()
            for obj in objs:
                bm = utils.bmu.open_bmesh(context, obj)
                if bm is not None:
                    self.obj_bm_map[obj] = bm

        # REQUIRES-BMESH-OPS
        if self.ops_prefs.tool == 'SLICE_AND_WELD':
            self.ops_slice_mesh(context)
            self.ops_mirror_and_weld(context, only_sel_geo=False)
        elif self.ops_prefs.tool == 'MIRROR_SEL_GEO':
            self.ops_mirror_and_weld(context, only_sel_geo=True)
        elif self.ops_prefs.tool == 'SLICE_AND_MIRROR':
            self.ops_mirror_mod(context, use_bisect=False)
        elif self.ops_prefs.tool == 'MIRROR_AND_BISECT':
            self.ops_mirror_mod(context, use_bisect=True)
        # NON-BMESH-OPS
        elif self.ops_prefs.tool == 'MIRROR_OVER_CURSOR':
            self.ops_mirror_over_cursor(context)
        elif self.ops_prefs.tool == 'MIRROR_OVER_ACTIVE':
            self.ops_mirror_over_active(context)

        # UPDATE-BMESH
        if close_bmesh_required:
            for obj, bm in self.obj_bm_map.items():
                utils.bmu.close_bmesh(context, obj, bm)
                bm = None
        self.obj_bm_map = None


    def ops_slice_mesh(self, context):
        axis_name = self.pick_radial_op.best_axis_name
        plane_no = Vector((0,0,0))
        if axis_name == "+X":
            plane_no = Vector((-1,0,0))
        elif axis_name == "-X":
            plane_no =  Vector((1,0,0))
        elif axis_name == "+Y":
            plane_no = Vector((0,-1,0))
        elif axis_name == "-Y":
            plane_no = Vector((0,1,0))
        elif axis_name == "+Z":
            plane_no = Vector((0,0,-1))
        elif axis_name == "-Z":
            plane_no = Vector((0,0,1))
        # Poly fade
        flip = "-" in axis_name
        axis = axis_name[1]
        color = utils.graphics.color_from_axis(axis=axis, flip=flip)
        # Slice
        for obj, bm in self.obj_bm_map.items():
            utils.bmu.ops_slice_mesh(obj, bm, plane_co=Vector((0,0,0)), plane_no=plane_no, clear_inner=True)
            if self.ops_prefs.tool == 'SLICE_AND_MIRROR':
                utils.poly_fade.init(obj, bounding_box_only=True, color_a=utils.graphics.COLORS.WHITE, color_b=color)


    def ops_mirror_and_weld(self, context, only_sel_geo=False):
        axis_name = self.pick_radial_op.best_axis_name
        if not axis_name:
            return
        flip = "-" in axis_name
        axis = axis_name[1]
        color = utils.graphics.color_from_axis(axis=axis, flip=flip)
        for obj, bm in self.obj_bm_map.items():
            utils.bmu.ops_mirror_and_weld(obj, bm, axis=axis, flip=flip, only_sel_geo=only_sel_geo, show_poly_fade=True, color=color)


    def ops_mirror_mod(self, context, use_bisect=False):
        if not use_bisect:
            self.ops_slice_mesh(context)
        def setup(obj):
            mirror_mod = None
            # Use a mirror that does not have an object associated
            if self.ensure_new_mirror_mod == False:
                mirror_mods = utils.modifiers.get_all_of_type(obj=obj, mod_type=ModType.MIRROR)
                for mod in mirror_mods:
                    if use_bisect and any(mod.use_bisect_axis[i] == True for i in range(3)):
                        mirror_mod = mod
                        break
                    elif not use_bisect and all(mod.use_bisect_axis[i] == False for i in range(3)) and mod.mirror_object is None:
                        mirror_mod = mod
                        break
            if mirror_mod is None:
                mirror_mod = utils.modifiers.add(obj=obj, mod_type=ModType.MIRROR)
                if use_bisect:
                    mirror_mod.name += " (Bisect)"
                mirror_mod.use_axis[0] = False
                mirror_mod.use_bisect_axis[0] = False
            mirror_mod.use_clip = True
            axis_name = self.pick_radial_op.best_axis_name
            if not axis_name:
                return
            if axis_name[1] == "X":
                mirror_mod.use_axis[0] = True
                if use_bisect:
                    mirror_mod.use_bisect_axis[0] = True
                    if axis_name == "+X":
                        mirror_mod.use_bisect_flip_axis[0] = True
            elif axis_name[1] == "Y":
                mirror_mod.use_axis[1] = True
                if use_bisect:
                    mirror_mod.use_bisect_axis[1] = True
                    if axis_name == "+Y":
                        mirror_mod.use_bisect_flip_axis[1] = True
            elif axis_name[1] == "Z":
                mirror_mod.use_axis[2] = True
                if use_bisect:
                    mirror_mod.use_bisect_axis[2] = True
                    if axis_name == "+Z":
                        mirror_mod.use_bisect_flip_axis[2] = True
            utils.modifiers.sort_all_mods(obj)
        if self.ops_prefs.multi_obj_mode and self.objs:
            for obj in self.objs:
                setup(obj)
        else:
            setup(self.obj)


    def ops_mirror_over_cursor(self, context):
        def setup(empty, obj):
            if self.parent_objects_to_empty:
                utils.object.parent_object(child=obj, parent=empty)
            mirror_mod = utils.modifiers.add(obj=obj, mod_type=ModType.MIRROR)
            utils.modifiers.sort_all_mods(obj)
            mirror_mod.mirror_object = empty
            mirror_mod.use_clip = True
            axis_name = self.pick_radial_op.best_axis_name
            if not axis_name:
                return
            mirror_mod.use_axis[0] = False
            mirror_mod.use_bisect_axis[0] = False
            if axis_name[1] == "X":
                mirror_mod.use_axis[0] = True
                if self.cursor_bisect:
                    mirror_mod.use_bisect_axis[0] = True
                    if axis_name == "+X":
                        mirror_mod.use_bisect_flip_axis[0] = True
            elif axis_name[1] == "Y":
                mirror_mod.use_axis[1] = True
                if self.cursor_bisect:
                    mirror_mod.use_bisect_axis[1] = True
                    if axis_name == "+Y":
                        mirror_mod.use_bisect_flip_axis[1] = True
            elif axis_name[1] == "Z":
                mirror_mod.use_axis[2] = True
                if self.cursor_bisect:
                    mirror_mod.use_bisect_axis[2] = True
                    if axis_name == "+Z":
                        mirror_mod.use_bisect_flip_axis[2] = True
            utils.modifiers.sort_all_mods(obj)

        loc = context.scene.cursor.location.copy()
        rot = self.cursor_quat.copy()
        sca = Vector((1,1,1,))
        collection = utils.collections.utility_collection(context)
        empty = utils.object.create_obj(context, data_type='EMPTY', obj_name="Empty", data_name="", loc=loc, rot=rot, sca=sca, collection=collection, ensure_visible=True)

        if self.ops_prefs.multi_obj_mode and self.objs:
            for obj in self.objs:
                setup(empty, obj)
        else:
            setup(empty, self.obj)


    def ops_mirror_over_active(self, context):
        for obj in self.objs:
            if obj == self.obj:
                continue
            mirror_mod = utils.modifiers.add(obj, mod_type=ModType.MIRROR)
            mirror_mod.mirror_object = self.obj
            mirror_mod.use_clip = True
            axis_name = self.pick_radial_op.best_axis_name
            if not axis_name:
                return
            mirror_mod.use_axis[0] = False
            mirror_mod.use_bisect_axis[0] = False
            if axis_name[1] == "X":
                mirror_mod.use_axis[0] = True
            elif axis_name[1] == "Y":
                mirror_mod.use_axis[1] = True
            elif axis_name[1] == "Z":
                mirror_mod.use_axis[2] = True
            utils.modifiers.sort_all_mods(obj)
