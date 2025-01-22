########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import gc
from mathutils import Vector, Matrix, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS, OPS_STATUS
from ...utils.event import RMB_press
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Slice & Knife\n
• (LMB)
\t\t→ Slice or Knife Cut\n
• (CTRL)
\t\t→ Set to Knife Cut"""

class PS_OT_SliceAndKnife(bpy.types.Operator):
    bl_idname      = "ps.slice_and_knife"
    bl_label       = "Slice & Knife"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return utils.context.get_mesh_from_edit_or_mesh_from_active(context)


    def invoke(self, context, event):
        # Data
        self.prefs = utils.addon.user_prefs()
        self.op_prefs = self.prefs.operator.slice_and_knife
        self.obj = utils.context.get_mesh_from_edit_or_mesh_from_active(context)

        # BME
        self.bmeCON = utils.bme.BmeshController()
        objs = utils.context.get_meshes_from_edit_or_from_selected(context)
        for obj in objs:
            options = utils.bme.mesh_add_options(context, obj, eval_obm=True, eval_edm=True)
            self.bmeCON.add_obj(context, obj, options)
        self.objs = self.bmeCON.available_objs(ensure_bmeditor=True, ensure_ray=True)

        # Validate
        if (not self.obj) or (not self.objs) or (self.obj not in self.objs):
            utils.notifications.init(context, messages=[("$Error", "Are the mesh objects visible?")])
            self.bmeCON.close(context, revert=True)
            return {'CANCELLED'}

        # Mods
        self.show_mods = True
        self.mod_vp_vis_map = {obj : utils.modifiers.vp_visibility_map(obj) for obj in self.objs}

        # Object Wire Display
        self.show_wire = all([obj.show_wire for obj in self.objs])
        self.wire_display_map = {obj: obj.show_wire for obj in self.objs}

        # Events
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.running_circle_select = False
        self.circle_select_radius = round(25 * utils.screen.screen_factor())
        self.circle_color = COLORS.ACT_ONE

        # Pick Line
        self.pick_line_op = utils.modal_ops.PickLineFromV3D(context)
        self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')

        # Menus
        self.setup_help_panel(context)
        self.setup_status_panel(context)
        self.setup_menu(context, event)

        # Setups
        utils.modal_ops.standard_modal_setup(self, context, event, utils)
        if context.mode == 'EDIT_MESH':
            utils.context.append_face_select_mode(context)
        if event.ctrl:
            self.op_prefs.cut_mode = 'Knife'
            if context.mode != 'EDIT_MESH':
                self.show_wire = True
        self.set_wire_display()
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
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))

        # Menu
        self.menu.update(context, event)
        if self.modal_status in {MODAL_STATUS.CONFIRM, MODAL_STATUS.CANCEL}: return
        if self.menu.status == UX_STATUS.ACTIVE: return

        # Select  / Deselect All
        if event.type == 'A' and event.value == 'PRESS':
            if context.mode == 'EDIT_MESH':
                bpy.ops.mesh.select_all(action='TOGGLE')
        # Toggle Help
        elif event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_help_panel(context)

        # CIRCLE SELECT
        if self.running_circle_select:
            if utils.event.pass_through(event, with_scoll=True, with_numpad=True, with_shading=True):
                self.modal_status = MODAL_STATUS.PASS
                return
            mode = 'SUB' if event.shift else 'ADD'
            self.circle_color = COLORS.RED if event.shift else COLORS.BLUE
            # SELECT
            if utils.event.is_mouse_dragging(event) or event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                bpy.ops.view3d.select_circle(x=int(self.mouse.x), y=int(self.mouse.y), radius=self.circle_select_radius, wait_for_input=True, mode=mode)
            # FINISH
            elif event.type in {'C', 'SPACE', 'RET', 'NUMPAD_ENTER', 'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
                self.running_circle_select = False
                self.setup_status_panel(context)
            return

        # Restart Line
        if self.pick_line_op.status == OPS_STATUS.INACTIVE:
            self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')

        # Undo
        if event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            self.undo(context)
        # Wire Display
        elif event.type == 'W' and event.value == 'PRESS':
            if context.mode != 'EDIT_MESH':
                self.show_wire = not self.show_wire
                self.set_wire_display()
        # Confirm
        elif event.type in {'RET', 'NUMPAD_ENTER', 'SPACE'} and event.value == 'PRESS':
            self.modal_status = MODAL_STATUS.CONFIRM
            return
        # Circle Select
        elif event.type == 'C' and event.value == 'PRESS':
            if context.mode == 'EDIT_MESH':
                utils.event.is_mouse_dragging(event)
                self.running_circle_select = True
            self.setup_status_panel(context)
        # Cut Mode
        elif event.type == 'S' and event.value == 'PRESS':
            # Toggle
            if self.op_prefs.cut_mode == 'Knife':
                self.op_prefs.cut_mode = 'Slice'
            elif self.op_prefs.cut_mode == 'Slice':
                self.op_prefs.cut_mode = 'Knife'
            # Wire Display
            if self.op_prefs.cut_mode == 'Knife' and context.mode != 'EDIT_MESH':
                self.show_wire = True
                self.set_wire_display()
            self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')
            self.setup_status_panel(context)
        # Multi Mode
        elif event.type == 'D' and event.value == 'PRESS':
            self.op_prefs.multi_mode = not self.op_prefs.multi_mode
            objs = self.objs if self.op_prefs.multi_mode else [self.obj]
            for obj in objs:
                utils.poly_fade.init(obj=obj, bounding_box_only=True, color_a=COLORS.YELLOW, color_b=COLORS.BLACK)
            self.setup_status_panel(context)
        # Create Faces
        elif event.type == 'F' and event.value == 'PRESS':
            self.op_prefs.create_faces = not self.op_prefs.create_faces
            self.setup_status_panel(context)
        # Only Selected
        elif event.type == 'G' and event.value == 'PRESS':
            if context.mode == 'EDIT_MESH':
                self.op_prefs.only_selected = not self.op_prefs.only_selected
                self.setup_status_panel(context)
        # Pick
        self.pick_line_op.update(context, event, self.bmeCON)
        # Passthrough
        if self.pick_line_op.status == OPS_STATUS.PASS:
            self.modal_status = MODAL_STATUS.PASS
        # Cancelled
        elif event.type in {'ESC'} or self.pick_line_op.status == OPS_STATUS.CANCELLED:
            self.modal_status = MODAL_STATUS.CANCEL
        # Ops
        elif self.pick_line_op.status == OPS_STATUS.COMPLETED:
            self.ops_view_slice(context)
            self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')


    def exit_modal(self, context):
        def shut_down():
            for obj, vis_map in self.mod_vp_vis_map.items():
                utils.modifiers.set_vp_visibility_from_map(obj, vis_map=vis_map)
            # Revert
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                self.bmeCON.close(context, revert=True)
            # Keep
            else:
                self.bmeCON.close(context, revert=False)
            self.menu.close(context)
            for obj, show_wire in self.wire_display_map.items():
                obj.show_wire = show_wire
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)
        self.bmeCON = None
        del self.bmeCON
        gc.collect()
        toggle = utils.context.object_mode_toggle_start(context)
        if toggle: utils.context.object_mode_toggle_end(context)

    # --- MENUS --- #

    def setup_help_panel(self, context):
        help_msgs = [("H", "Toggle Help")]
        append = help_msgs.append
        if self.prefs.settings.show_modal_help:
            append(("RET / SPACE", "Confirm"))
            append(("RMB"        , "Cancel"))
            append(("CTRL + Z"   , "Undo"))
            append(("SHIFT + Z"  , "Shading"))
            if context.mode == 'EDIT_MESH':
                append(("A", "Toggle Select All"))
                append(("C", "Start Circle Select"))
            else:
                append(("W", "Wire Display"))
        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def setup_status_panel(self, context):
        status_msgs = [("Slice & Knife",),]
        append = status_msgs.append
        if self.running_circle_select:
            append(("(A)", "Toggle Select All"))
            append(("(LMB)", "Select"))
            append(("(LMB + SHIFT)", "Subtract"))
            append(("(C / RET / ESC / RMB / SPACE)", "Finish Circle Select"))
        else:
            append(("(S) Cut Mode", str(self.op_prefs.cut_mode)))
            append(("(D) Multi Mode", "On" if self.op_prefs.multi_mode else "Off"))
            append(("(F) Create Faces", "On" if self.op_prefs.create_faces else "Off"))
            if context.mode == 'EDIT_MESH':
                append(("(G) Only Selected", "On" if self.op_prefs.only_selected else "Off"))
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_menu(self, context, event):
        PropMap = utils.modal_ux.PropMap
        Row = utils.modal_ux.Row
        Container = utils.modal_ux.Container
        Menu = utils.modal_ux.Menu

        map_1 = PropMap(label="Cancel" , instance=self, prop_name='menu_callback', box_len=5)
        map_2 = PropMap(label="Undo"   , instance=self, prop_name='menu_callback', box_len=4)
        map_3 = PropMap(label="Confirm", instance=self, prop_name='menu_callback', box_len=6)
        row_1 = Row(label="", prop_maps=[map_1, map_2, map_3], min_borders=True)
        cont_1 = Container(label="", rows=[row_1])

        prefs = self.op_prefs
        map_1 = PropMap(label="Flip", instance=prefs, prop_name='flip'    , box_len=3, call_back=self.menu_callback)
        map_2 = PropMap(label="X"   , instance=prefs, prop_name='mirror_x', box_len=3, call_back=self.menu_callback)
        map_3 = PropMap(label="Y"   , instance=prefs, prop_name='mirror_y', box_len=3, call_back=self.menu_callback)
        map_4 = PropMap(label="Z"   , instance=prefs, prop_name='mirror_z', box_len=3, call_back=self.menu_callback)
        row_1 = Row(prop_maps=[map_1, map_2, map_3, map_4], min_borders=True)
        cont_2 = Container(label="Auto Mirror", rows=[row_1])

        map_1 = PropMap(label="P1", instance=self.pick_line_op, prop_name='p1', label_len=4, box_len=6, align_vec="Vertical", call_back=self.menu_callback, increment_value=0.125)
        map_2 = PropMap(label="P2", instance=self.pick_line_op, prop_name='p2', label_len=4, box_len=6, align_vec="Vertical", call_back=self.menu_callback, increment_value=0.125)
        row_1 = Row(label="", prop_maps=[map_1, map_2])
        cont_3 = Container(label="Points", rows=[row_1])

        rows = []
        if context.mode == 'EDIT_MESH':
            t1 = "Slice all mesh objects in Edit Mode"
            cut_modes = ['Slice', 'Knife']
            i1 = cut_modes.index(prefs.cut_mode)
            map_1 = PropMap(label="Multi Mode", tip=t1, instance=prefs, prop_name='multi_mode', box_len=7, call_back=self.menu_callback)
            map_2 = PropMap(label="Cut Mode"  , tip="", instance=prefs, prop_name='cut_mode'  , box_len=7, call_back=self.menu_callback, list_items=cut_modes, list_index=i1)
            row = Row(label="", prop_maps=[map_1, map_2], min_borders=True)
            rows.append(row)
            map_1 = PropMap(label="Mods", tip="Show / Hide all the modifiers", instance=self, prop_name='show_mods', box_len=7, call_back=self.menu_callback)
            map_2 = PropMap(label="Fill", tip="Create faces after cutting", instance=prefs, prop_name='create_faces' , box_len=7, call_back=self.menu_callback)
            row = Row(label="", prop_maps=[map_1, map_2], min_borders=True)
            rows.append(row)
            map_1 = PropMap(label="Circle Sel", tip="Start / Stop Circle Selection Tool", instance=self, prop_name='running_circle_select', box_len=7, call_back=self.menu_callback)
            map_2 = PropMap(label="Only Sel" , tip="Only cut the selected geo", instance=prefs, prop_name='only_selected', box_len=7, call_back=self.menu_callback)
            row = Row(label="", prop_maps=[map_1, map_2], min_borders=True)
            rows.append(row)
        else:
            t1 = "Slice all selected mesh objects"
            cut_modes = ['Slice', 'Knife']
            i1 = cut_modes.index(prefs.cut_mode)
            map_1 = PropMap(label="Multi Mode", tip=t1, instance=prefs, prop_name='multi_mode', box_len=7, call_back=self.menu_callback)
            map_2 = PropMap(label="Cut Mode"  , tip="", instance=prefs, prop_name='cut_mode'  , box_len=7, call_back=self.menu_callback, list_items=cut_modes, list_index=i1)
            row = Row(label="", prop_maps=[map_1, map_2], min_borders=True)
            rows.append(row)
            map_1 = PropMap(label="Wire", tip="Toggle wire display", instance=self, prop_name='show_wire', box_len=5, call_back=self.menu_callback)
            map_2 = PropMap(label="Mods", tip="Show / Hide all the modifiers", instance=self, prop_name='show_mods', box_len=5, call_back=self.menu_callback)
            map_3 = PropMap(label="Fill", tip="Create faces after cutting", instance=prefs, prop_name='create_faces' , box_len=5, call_back=self.menu_callback)
            row = Row(label="", prop_maps=[map_1, map_2, map_3], min_borders=True)
            rows.append(row)

        cont_4 = Container(label="", rows=rows)
        self.menu = Menu(context, event, containers=[cont_1, cont_2, cont_3, cont_4])


    def menu_callback(self, context, event, prop_map):
        label = prop_map.label
        if label == "Confirm":
            self.modal_status = MODAL_STATUS.CONFIRM
        elif label == "Cancel":
            self.modal_status = MODAL_STATUS.CANCEL
        elif label == "Undo":
            self.undo(context)
        elif label == "P1":
            if self.pick_line_op.step == 1:
                self.pick_line_op.step = 2
        elif label == "P2":
            self.pick_line_op.step = 3
        elif label == "Mods":
            # Turn On
            if self.show_mods == True:
                for obj, vis_map in self.mod_vp_vis_map.items():
                    utils.modifiers.set_vp_visibility_from_map(obj, vis_map=vis_map)
                    self.bmeCON.rebuild_ray(context, obj)
            # Turn Off
            else:
                for obj in self.objs:
                    for mod in obj.modifiers:
                        mod.show_viewport = False
                    self.bmeCON.rebuild_ray(context, obj)
        elif label == "Multi Mode":
            objs = self.objs if self.op_prefs.multi_mode else [self.obj]
            for obj in objs:
                utils.poly_fade.init(obj=obj, bounding_box_only=True, color_a=COLORS.YELLOW, color_b=COLORS.BLACK)
            self.setup_status_panel(context)
        elif label == "Wire":
            self.set_wire_display()
        elif label == "Cut Mode":
            if self.op_prefs.cut_mode == 'Knife' and context.mode != 'EDIT_MESH':
                self.show_wire = True
                self.set_wire_display()
            self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')
            self.setup_status_panel(context)
        elif label == "Circle Sel":
            if self.running_circle_select:
                utils.event.is_mouse_dragging(event)
            self.setup_status_panel(context)

    # --- SHADERS --- #

    def draw_post_view(self, context):
        if not self.running_circle_select:
            self.pick_line_op.draw_3d(context)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        if self.running_circle_select:
            utils.graphics.draw_circle_2d(radius=self.circle_select_radius, res=32, line_width=2, center=self.mouse, color=self.circle_color)
        else:
            self.pick_line_op.draw_2d(context)
        self.menu.draw()

    # --- UTILS --- #

    def ops_view_slice(self, context):

        if self.op_prefs.multi_mode:
            self.bmeCON.clear_specified_objs()
        else:
            self.bmeCON.set_specified_objs(objs=[self.obj])

        push_undo_pool = False
        for bmed in self.bmeCON.iter_bmeditors():
            obj = bmed.obj
            bm = bmed.BM

            plane_co = bmed.mat_ws_inv @ self.pick_line_op.side_co
            plane_no = (bmed.mat_ws_trs @ self.pick_line_op.side_no).normalized()

            # Line Slice
            if self.op_prefs.cut_mode == 'Slice':
                utils.bmu.ops_slice_mesh(obj, bm, plane_co=plane_co, plane_no=plane_no, clear_outer=True, fill_cut_with_faces=self.op_prefs.create_faces, cut_sel_geo=self.op_prefs.only_selected, sel_cut_geo=True)
            # Line Slice
            elif self.op_prefs.cut_mode == 'Knife':
                utils.bmu.ops_slice_mesh(obj, bm, plane_co=plane_co, plane_no=plane_no, clear_inner=False, clear_outer=False, cut_sel_geo=self.op_prefs.only_selected, sel_cut_geo=True)
            # Mirror -> Slice & Mirror
            if self.op_prefs.mirror_x:
                if self.op_prefs.flip:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((-1,0,0)), clear_inner=True)
                else:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((1,0,0)), clear_inner=True)
                utils.bmu.ops_mirror_and_weld(obj, bm, axis='X', flip=self.op_prefs.flip, show_poly_fade=False)
            if self.op_prefs.mirror_y:
                if self.op_prefs.flip:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((0,1,0)), clear_inner=True)
                else:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((0,-1,0)), clear_inner=True)
                utils.bmu.ops_mirror_and_weld(obj, bm, axis='Y', flip=self.op_prefs.flip, show_poly_fade=False)
            if self.op_prefs.mirror_z:
                if self.op_prefs.flip:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((0,0,-1)), clear_inner=True)
                else:
                    utils.bmu.ops_slice_mesh(obj, bm, plane_no=Vector((0,0,1)), clear_inner=True)
                utils.bmu.ops_mirror_and_weld(obj, bm, axis='Z', flip=self.op_prefs.flip, show_poly_fade=False)

            # Save
            if self.bmeCON.save_in_pool(context, obj, update_ray=True):
                push_undo_pool = True
        # Save Push
        if push_undo_pool:
            self.bmeCON.save_pool_push()


    def set_wire_display(self):
        for obj in self.objs:
            obj.show_wire = self.show_wire


    def undo(self, context):
        self.bmeCON.save_pool_undo(context, update_ray=True)
        self.pick_line_op.start(pick_side=self.op_prefs.cut_mode=='Slice')
