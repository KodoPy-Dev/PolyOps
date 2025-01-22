########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
import bmesh
import time
import gc
from mathutils import Vector, Matrix, Euler, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Merge\n
• Edit Mode
\t\t→ (LMB) Radial
\t\t→ (SHIFT) Edge
\t\t→ (CTRL) Vert to Vert"""

class PS_OT_Merge(bpy.types.Operator):
    bl_idname      = "ps.merge"
    bl_label       = "Merge"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        # Prefs
        self.prefs = utils.addon.user_prefs()
        self.op_prefs = self.prefs.operator.merge

        # BME
        OPTIONS = utils.bme.OPTIONS
        self.bme_ray_options = OPTIONS.NONE
        self.bme_add_options = OPTIONS.USE_RAY | OPTIONS.USE_BME | OPTIONS.ONLY_VISIBLE | OPTIONS.IGNORE_HIDDEN_GEO
        self.bmeCON = utils.bme.BmeshController()
        objs = utils.context.get_meshes_from_edit_or_from_selected(context)
        for obj in objs:
            self.bmeCON.add_obj(context, obj, self.bme_add_options)
        self.objs = self.bmeCON.available_objs(ensure_bmeditor=True, ensure_ray=True)
        if not self.objs:
            utils.notifications.init(context, messages=[("$Error", "Are the mesh objects visible?")])
            self.bmeCON.close(context, revert=True)
            return {'CANCELLED'}

        # Operation
        self.step = 1
        self.obj = None
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.all_islands = False
        self.modes = ['Radial', 'Edge', 'Vert-Vert']
        self.mode = self.op_prefs.merge_mode
        if event.shift:
            self.mode = 'Edge'
        elif event.ctrl:
            self.mode = 'Vert-Vert'
        self.rebuild_menu = False
        self.merge_co_ws = Vector((0,0,0))
        self.merge_radius = 0
        self.vert_island = set()
        self.vert_ref = None

        # Graphics
        self.snapped_element_type = ""
        self.vert_count = 0
        self.graphics_p1 = None
        self.graphics_p2 = None
        from ...resources.shapes.quad_sphere_mid import gen_poly_batch_flat, draw_poly_batch_flat
        self.gen_quad_sphere_batch = gen_poly_batch_flat
        self.draw_quad_sphere_batch = draw_poly_batch_flat
        self.quad_sphere_batch = None
        self.quad_sphere_color_front = COLORS.LIGHT_BLUE.copy()
        self.quad_sphere_color_front[3] = 0.25
        self.quad_sphere_color_back = COLORS.DARK_BLUE.copy()
        self.quad_sphere_color_back[3] = 0.375

        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=objs)
        utils.context.set_component_selection(context, values=(True, False, False))
        self.setup_help_panel(context)
        self.setup_status_panel(context)
        self.setup_menu(context, event)
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
        self.menu.update(context, event)
        # Rebuild
        if self.rebuild_menu:
            self.rebuild_menu = False
            self.reset(context)
            self.setup_help_panel(context)
            self.setup_status_panel(context)
            self.setup_menu(context, event)
        # Set from callback
        if self.modal_status in {MODAL_STATUS.CONFIRM, MODAL_STATUS.CANCEL}:
            return
        if self.menu.status == UX_STATUS.ACTIVE:
            self.modal_status = MODAL_STATUS.RUNNING
            return
        self.modal_status = MODAL_STATUS.RUNNING
        # Event Data
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        # Help
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_help_panel(context)
        # Undo
        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            self.undo(context)
        # Reset
        elif event.type == 'R' and event.value == 'PRESS':
            self.reset(context, restore_last_bmeditor=True)
        # Toggle Modes
        elif event.type == 'E' and event.value == 'PRESS':
            if self.mode == 'Radial':
                self.mode = 'Edge'
            elif self.mode == 'Edge':
                self.mode = 'Vert-Vert'
            elif self.mode == 'Vert-Vert':
                self.mode = 'Radial'
            self.reset(context, restore_last_bmeditor=True)
            self.setup_help_panel(context)
            self.setup_status_panel(context)
            self.setup_menu(context, event)
            return
        # Merge Radius Mode
        if self.mode == 'Radial':
            # Merge All Toggle
            if event.type == 'A' and event.value == 'PRESS':
                self.all_islands = not self.all_islands
                self.reset(context, restore_last_bmeditor=True)
            # Raycast
            if self.step == 1:
                self.radial_merge_step_1(context, event)
            # Merge
            elif self.step == 2:
                self.radial_merge_step_2(context, event)
        # Edge Click Collapse
        elif self.mode == 'Edge':
            self.edge_merge(context, event)
        # Vert to Vert
        elif self.mode == 'Vert-Vert':
            self.vert_vert_merge(context, event)
        # Update Status
        self.setup_status_panel(context)
        # Passthrough / Cancel / Confirm
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        if event.type != 'LEFTMOUSE':
            self.modal_status = self.std_ops.status


    def exit_modal(self, context):
        def shut_down():
            if self.mode in self.modes:
                self.op_prefs.merge_mode = self.mode
            self.menu.close(context)
            self.reset(context, restore_last_bmeditor=False)
            if self.modal_status in {MODAL_STATUS.ERROR, MODAL_STATUS.CANCEL}:
                self.std_ops.close(context, revert=True)
                self.bmeCON.close(context, revert=True)
            else:
                self.std_ops.close(context, revert=False)
                self.bmeCON.close(context, revert=False)
        utils.guards.except_guard(try_func=shut_down, try_args=None)
        utils.modal_ops.standard_modal_shutdown(self, context, utils)
        self.std_ops = None
        self.bmeCON = None
        del self.std_ops
        del self.bmeCON
        gc.collect()
        toggle = utils.context.object_mode_toggle_start(context)
        if toggle: utils.context.object_mode_toggle_end(context)

    # --- MENU --- #

    def setup_help_panel(self, context):
        help_msgs = [("H", "Toggle Help")]
        if self.prefs.settings.show_modal_help:
            help_msgs = [
                ("H"          , "Toggle Help"),
                ("RET / SPACE", "Confirm"),
                ("RMB / ESC"  , "Cancel"),
                ("CTRL + Z"   , "Undo"),
                ("SHIFT + Z"  , "VP Display"),
                ("E"          , "Modes"),
                ("R"          , "Reset"),]
            if self.mode == 'Radial':
                help_msgs.extend([
                    ("A"    , "Islands"),
                    ("SHIFT", "Edge Center"),
                    ("CTRL" , "Edge"),
                    ("ALT"  , "Face"),])
            elif self.mode == 'Edge':
                help_msgs.extend([
                    ("LMB"  , "Collapse Edge"),
                    ("SHIFT", "Edge Center"),])
        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def setup_status_panel(self, context):
        status_msgs = []
        append = status_msgs.append
        if self.mode == 'Edge':
            append(("(E) Mode", "Edge"))
            append(("(SHIFT)", "Edge Center"))
        elif self.mode == 'Radial':
            append(("(E) Mode", "Radius"))
            append(("(A) All Islands", "On" if self.all_islands else "Off"))
            if self.step == 1:
                append(("(SHIFT)", "$Edge_Center" if self.snapped_element_type == "Edge_Center" else "Edge_Center"))
                append(("(CTRL)", "$Edge_Point" if self.snapped_element_type == "Edge_Point" else "Edge_Point"))
                append(("(ALT)", "$Face" if self.snapped_element_type == "Face" else "Face"))
            elif self.step == 2:
                append(("(R) Reset", "Merge"))
                append(("Verts", str(self.vert_count)))
        utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_menu(self, context, event):
        PropMap = utils.modal_ux.PropMap
        Row = utils.modal_ux.Row
        Container = utils.modal_ux.Container
        Menu = utils.modal_ux.Menu
        rows = []
        map_1 = PropMap(label="Confirm", instance=self, prop_name='menu_callback', box_len=7)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Cancel", instance=self, prop_name='menu_callback', box_len=7)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Undo", instance=self, prop_name='menu_callback', box_len=7)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Wireframe", instance=self, prop_name='menu_callback', box_len=7, highlight_callback=self.menu_highlight_wireframe)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        cont_1 = Container(label="", rows=rows, force_no_scroll_bar=True)

        rows = []
        tip = "Collapse mode"
        map_1 = PropMap(label="Mode", tip=tip, instance=self, prop_name='mode', list_items=self.modes, list_index=self.modes.index(self.mode), box_len=7, call_back=self.menu_callback)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        if self.mode == 'Radial':
            map_1 = PropMap(label="All Islands", instance=self, prop_name='all_islands', box_len=7, call_back=self.menu_callback)
            rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        cont_2 = Container(label="", rows=rows, force_no_scroll_bar=True)

        self.menu = Menu(context, event, containers=[cont_1, cont_2])


    def menu_callback(self, context, event, prop_map):
        label = prop_map.label
        if label == "Confirm":
            self.modal_status = MODAL_STATUS.CONFIRM
        elif label == "Cancel":
            self.modal_status = MODAL_STATUS.CANCEL
        elif label == "Undo":
            self.undo(context)
        elif label == "Wireframe":
            if context.space_data.shading.type == 'WIREFRAME':
                context.space_data.shading.type = 'SOLID'
            else:
                context.space_data.shading.type = 'WIREFRAME'
        elif label == "Islands":
            self.reset(context, restore_last_bmeditor=True)
            self.setup_status_panel(context)
        elif label == "Mode":
            self.rebuild_menu = True
            self.reset(context, restore_last_bmeditor=True)
            self.setup_status_panel(context)


    def menu_highlight_wireframe(self, context, event, prop_map):
        return context.space_data.shading.type == 'WIREFRAME'

    # --- SHADER --- #

    def draw_post_view(self, context):
        if self.mode == 'Radial':
            if self.step == 1:
                if self.snapped_element_type in {"Edge Point", "Edge Center"}:
                    if isinstance(self.graphics_p1, Vector) and isinstance(self.merge_co_ws, Vector) and isinstance(self.graphics_p2, Vector):
                        utils.graphics.draw_line_segments_smooth_colors(points=[self.graphics_p1, self.merge_co_ws, self.graphics_p2], width=3, colors=[COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK])
            elif self.step == 2:
                self.draw_quad_sphere_batch(self.quad_sphere_batch, color_front=self.quad_sphere_color_front, color_back=self.quad_sphere_color_back)
            if isinstance(self.merge_co_ws, Vector):
                utils.graphics.draw_action_line_3d(context, p1=self.merge_co_ws, p2=None)

        elif self.mode == 'Edge':
            if isinstance(self.graphics_p1, Vector) and isinstance(self.merge_co_ws, Vector) and isinstance(self.graphics_p2, Vector):
                utils.graphics.draw_line_segments_smooth_colors(points=[self.graphics_p1, self.merge_co_ws, self.graphics_p2], width=3, colors=[COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK])
            if isinstance(self.merge_co_ws, Vector):
                utils.graphics.draw_action_line_3d(context, p1=self.merge_co_ws, p2=None)

        elif self.mode == 'Vert-Vert':
            if self.obj is None:
                if isinstance(self.graphics_p1, Vector):
                    utils.graphics.draw_action_line_3d(context, p1=self.graphics_p1, p2=None)
            else:
                if isinstance(self.graphics_p1, Vector) and isinstance(self.graphics_p2, Vector):
                    utils.graphics.draw_action_line_3d(context, p1=self.graphics_p1, p2=self.graphics_p2)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.menu.draw()

    # --- OPS --- #

    def radial_merge_step_1(self, context, event):
        self.reset(context, restore_last_bmeditor=False)
        OPTIONS = utils.bme.OPTIONS
        ray_opts = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = None
        sampled_vert_index = -1

        # Edge Cast
        if event.ctrl or event.shift:
            hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
            if edge is None: return
            bm = bmed.BM
            self.obj = bmed.obj

            mat_ws = hit_info.mat_ws
            vert_1 = edge.verts[0]
            vert_2 = edge.verts[1]
            sampled_vert_index = vert_1.index
            self.snapped_element_type = "Edge_Center" if event.shift else "Edge_Point"
            self.graphics_p1 = mat_ws @ vert_1.co
            self.graphics_p2 = mat_ws @ vert_2.co
            self.merge_co_ws = ((self.graphics_p1 + self.graphics_p2)  / 2) if event.shift else hit_info.edge_co_ws_nearest.copy()

        # Face Cast
        elif event.alt:
            hit_info = self.bmeCON.ray_to_face(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            face = bmed.get_bm_elem(index=hit_info.face_index, elem_type='FACE')
            if face is None: return
            bm = bmed.BM
            self.obj = bmed.obj

            sampled_vert_index = face.verts[0].index
            self.snapped_element_type = "Face"
            self.merge_co_ws = hit_info.face_co_ws

        # Vert Cast
        else:
            hit_info = self.bmeCON.ray_to_vert(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            vert = bmed.get_bm_elem(index=hit_info.vert_index, elem_type='VERT')
            if vert is None: return
            bm = bmed.BM
            self.obj = bmed.obj

            sampled_vert_index = hit_info.vert_index
            self.snapped_element_type = "Vert"
            self.merge_co_ws = hit_info.vert_co_ws

        # Step 2
        if utils.event.is_mouse_dragging(event) and (self.obj is not None) and (sampled_vert_index >= 0):
            bmed = self.bmeCON.get_bmeditor(self.obj)
            if bmed is None: return
            self.step = 2
            if not self.all_islands:
                vert = bmed.get_bm_elem(index=sampled_vert_index, elem_type='VERT')
                if vert is None: return
                bm = bmed.BM
                vert_islands = utils.bmu.vert_islands_from_seperation(bm)
                for vert_island in vert_islands:
                    if vert in vert_island:
                        self.vert_island = {vert : vert.co.copy() for vert in vert_island}
                        break

        del hit_info


    def radial_merge_step_2(self, context, event):

        # View Plane Distance Point
        hit_point = utils.ray.cast_onto_view_plane_at_depth(context, event, plane_co=self.merge_co_ws, fallback=self.merge_co_ws)
        self.merge_radius = (hit_point - self.merge_co_ws).length
        # Graphics
        merge_scale = Vector((self.merge_radius, self.merge_radius, self.merge_radius)) * 2
        self.quad_sphere_batch = self.gen_quad_sphere_batch(center=self.merge_co_ws, scale=merge_scale)

        # Merge All
        if self.all_islands:
            self.vert_count = 0
            push_save = False
            for bmed in self.bmeCON.iter_bmeditors():
                bmed.restore()
                bmed.update()
                obj = bmed.obj
                bm = bmed.BM
                mat_ws = bmed.mat_ws
                merge_point_ls = bmed.mat_ws_inv @ self.merge_co_ws
                verts = [vert for vert in bm.verts if not vert.hide and (mat_ws @ vert.co - self.merge_co_ws).length <= self.merge_radius]
                self.vert_count += len(verts)
                # Merge
                if not utils.event.is_mouse_dragging(event):
                    if verts:
                        push_save = True
                        bmesh.ops.pointmerge(bm, verts=verts, merge_co=merge_point_ls)
                        self.bmeCON.save_in_pool(context, obj, update_ray=True)
                else:
                    for vert in verts:
                        vert.co = merge_point_ls
                    bmed.update()
            if push_save:
                self.bmeCON.save_pool_push()

        # Merge Single Island
        else:
            bmed = self.bmeCON.get_bmeditor(self.obj)
            if bmed is None:
                self.reset(context, restore_last_bmeditor=False)
                return
            bm = bmed.BM
            mat_ws = bmed.mat_ws
            merge_point_ls = bmed.mat_ws_inv @ self.merge_co_ws
            verts = []
            for vert, vert_co_ls in self.vert_island.items():
                if vert.is_valid:
                    if (mat_ws @ vert_co_ls - self.merge_co_ws).length <= self.merge_radius:
                        vert.co = merge_point_ls
                        verts.append(vert)
                    else:
                        vert.co = vert_co_ls
            self.vert_count = len(verts)
            # Merge
            update = True
            if not utils.event.is_mouse_dragging(event):
                if verts:
                    update = False
                    bmesh.ops.pointmerge(bm, verts=verts, merge_co=merge_point_ls)
                    self.bmeCON.save_in_pool(context, self.obj, update_ray=True)
                    self.bmeCON.save_pool_push()
            if update:
                bmed.update()

        # Resest
        if not utils.event.is_mouse_dragging(event):
            self.reset(context)


    def edge_merge(self, context, event):
        self.reset(context, restore_last_bmeditor=False)
        OPTIONS = utils.bme.OPTIONS
        ray_opts = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE

        hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
        if edge is None: return
        bm = bmed.BM
        obj = bmed.obj

        mat_ws = hit_info.mat_ws
        mat_ws_inv = hit_info.mat_ws_inv
        vert_1 = edge.verts[0]
        vert_2 = edge.verts[1]
        self.graphics_p1 = mat_ws @ vert_1.co
        self.graphics_p2 = mat_ws @ vert_2.co
        if event.shift:
            self.merge_co_ws = (self.graphics_p1 + self.graphics_p2)  / 2
        else:
            self.merge_co_ws = hit_info.edge_co_ws_nearest
        # Complete
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            merge_co_ls = mat_ws_inv @ self.merge_co_ws
            bmesh.ops.pointmerge(bm, verts=[vert_1, vert_2], merge_co=merge_co_ls)
            self.bmeCON.save_in_pool(context, obj, update_ray=True)
            self.bmeCON.save_pool_push()
            self.reset(context)
        del hit_info


    def vert_vert_merge(self, context, event):
        OPTIONS = utils.bme.OPTIONS
        ray_opts = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = None

        # Step 1
        if self.obj is None:
            self.reset(context)
            hit_info = self.bmeCON.ray_to_vert(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            vert = bmed.get_bm_elem(index=hit_info.vert_index, elem_type='VERT')
            if vert is None: return
            bm = bmed.BM
            self.graphics_p1 = hit_info.vert_co_ws
            # STEP 1 : COMPLETE
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self.obj = hit_info.obj
                self.vert_ref = vert
                self.bmeCON.set_specified_objs(objs=[self.obj])
        
        # Step 2
        else:
            valid = False
            if isinstance(self.obj, bpy.types.Object):
                if isinstance(self.vert_ref, bmesh.types.BMVert):
                    if self.vert_ref.is_valid:
                        valid = True
            if not valid:
                utils.notifications.init(context, messages=[("$Error", "Bad References")])
                self.reset(context)
                return

            ray_opts = ray_opts | OPTIONS.ONLY_SPECIFIED
            hit_info = self.bmeCON.ray_to_vert(context, event, ray_opts)
            if hit_info is None: return

            if hit_info.obj != self.obj:
                utils.notifications.init(context, messages=[("$Error", "Bad References")])
                self.reset(context)
                return

            bmed = hit_info.bmed
            if bmed is None: return
            vert = bmed.get_bm_elem(index=hit_info.vert_index, elem_type='VERT')
            if vert is None: return
            bm = bmed.BM

            self.graphics_p2 = hit_info.vert_co_ws

            # STEP 2 : COMPLETE
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                if self.vert_ref != vert:
                    bmesh.ops.pointmerge(bm, verts=[self.vert_ref, vert], merge_co=vert.co)
                    self.bmeCON.save_in_pool(context, self.obj, update_ray=True)
                    self.bmeCON.save_pool_push()
                    self.reset(context)
        del hit_info

    # --- UTILS --- #

    def save(self, context, obj, pool_push=False):
        self.bmeCON.save_in_pool(context, obj, update_ray=True)
        if pool_push:
            self.bmeCON.save_pool_push(context)


    def undo(self, context):
        self.bmeCON.save_pool_undo(context, update_ray=True)
        self.reset(context, restore_last_bmeditor=False)


    def reset(self, context, restore_last_bmeditor=False):
        # BME
        self.bmeCON.clear_specified_objs()
        if restore_last_bmeditor:
            bmed = self.bmeCON.get_bmeditor_from_last_ray()
            if bmed is not None:
                bmed.restore()
                bmed.update()
                self.bmeCON.rebuild_ray(context, bmed.obj)
        # Operation
        self.step = 1
        self.obj = None
        self.show_merge_radial_edge = False
        self.merge_co_ws.zero()
        self.merge_radius = 0
        self.vert_island = set()
        self.vert_ref = None
        # Graphics
        self.vert_count = 0
        self.graphics_p1 = None
        self.graphics_p2 = None
        self.quad_sphere_batch = None
