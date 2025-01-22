########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import time
import gpu
import gc
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix, Euler, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS
except_guard_prop_set = utils.guards.except_guard_prop_set

SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')

DESC = """Join\n
• Edit Mode
\t\t→ Click two verts to create and edge between them"""

class PS_OT_Join(bpy.types.Operator):
    bl_idname      = "ps.join"
    bl_label       = "Join"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        self.prefs = utils.addon.user_prefs()

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
        self.s1_index = None
        self.s1_co_ls = None
        self.s1_co_ws = None
        self.s1_edge_batch = None
        self.s1_elem_type = ""
        self.s2_index = None
        self.s2_co_ls = None
        self.s2_co_ws = None
        self.s2_edge_batch = None
        self.s2_elem_type = ""
        # Standard Ops
        self.std_ops = utils.modal_ops.StandardOps(context, event, objs=self.objs)
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
        # Set from callback
        if self.modal_status in {MODAL_STATUS.CONFIRM, MODAL_STATUS.CANCEL}:
            return
        if self.menu.status == UX_STATUS.ACTIVE:
            self.modal_status = MODAL_STATUS.RUNNING
            return
        self.modal_status = MODAL_STATUS.RUNNING
        # Help
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_help_panel(context)
        # Undo
        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            self.undo(context)
        # Reset
        elif event.type == 'R' and event.value == 'PRESS':
            self.reset(context)
        # Operations
        if self.step == 1:
            if self.step_prep(context):
                self.ops_join_step_1(context, event)
        elif self.step == 2:
            if self.step_prep(context):
                self.ops_join_step_2(context, event)
            else:
                self.reset(context)
        if self.step == 3:
            if self.step_prep(context):
                self.ops_join_step_3(context, event)
            else:
                self.reset(context)
        # Update Status
        self.setup_status_panel(context)
        # Passthrough / Cancel / Confirm
        self.std_ops.update(context, event, pass_with_scoll=True, pass_with_numpad=True, pass_with_shading=True)
        if event.type != 'LEFTMOUSE':
            self.modal_status = self.std_ops.status


    def exit_modal(self, context):
        def shut_down():
            self.menu.close(context)
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
                ("R"          , "Reset"),
            ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def setup_status_panel(self, context):
        elem_type = self.s1_elem_type if self.step == 1 else self.s2_elem_type
        status_msgs = [
            ("(R)", "Reset Join"),
            ("(LMB)", "$Vert" if elem_type == "Vert" else "Vert"),
            ("(CTRL)", "$Edge_Point" if elem_type == "Edge Point" else "Edge_Point"),
            ("(SHIFT)", "$Edge_Center" if elem_type == "Edge Center" else "Edge_Center")
            ]
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
        self.menu = Menu(context, event, containers=[cont_1])


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


    def menu_highlight_wireframe(self, context, event, prop_map):
        return context.space_data.shading.type == 'WIREFRAME'

    # --- SHADER --- #

    def draw_post_view(self, context):
        if self.step == 1:
            utils.graphics.draw_action_line_3d(context, p1=self.s1_co_ws, p2=None)
        elif self.step == 2:
            utils.graphics.draw_action_line_3d(context, p1=self.s1_co_ws, p2=self.s2_co_ws)
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(3)
        if self.s1_edge_batch:
            self.s1_edge_batch.draw(SMOOTH_COLOR)
        if self.s2_edge_batch:
            self.s2_edge_batch.draw(SMOOTH_COLOR)
        gpu.state.line_width_set(1)
        gpu.state.blend_set('NONE')


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.menu.draw()

    # --- OPS --- #

    def ops_join_step_1(self, context, event):
        CONFIRMED = event.type == 'LEFTMOUSE' and event.value == 'PRESS'
        OPTIONS = utils.bme.OPTIONS
        ray_opts = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = None

        # EDGE CENTER
        if event.shift:
            hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
            if edge is None: return
            bm = bmed.BM

            vert_1_co_ws = hit_info.mat_ws @ edge.verts[0].co
            vert_2_co_ws = hit_info.mat_ws @ edge.verts[1].co
            self.obj = hit_info.obj
            self.s1_index = hit_info.edge_index
            self.s1_co_ls = hit_info.mat_ws_inv @ hit_info.edge_co_ws_center
            self.s1_co_ws = hit_info.edge_co_ws_center.copy()
            self.s1_edge_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (vert_1_co_ws, self.s1_co_ws, vert_2_co_ws), "color": (COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK)})
            self.s1_elem_type = "Edge Center"
            if CONFIRMED:
                self.bmeCON.set_specified_objs(objs=[self.obj])
                self.step = 2

        # EDGE NEAREST
        elif event.ctrl:
            hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
            if edge is None: return
            bm = bmed.BM

            vert_1_co_ls = edge.verts[0].co
            vert_2_co_ls = edge.verts[1].co
            vert_1_co_ws = hit_info.mat_ws @ vert_1_co_ls
            vert_2_co_ws = hit_info.mat_ws @ vert_2_co_ls
            point = hit_info.mat_ws_inv @ hit_info.edge_co_ws_nearest
            factor = utils.math3.projected_point_line_factor(point, line_p1=vert_1_co_ls, line_p2=vert_2_co_ls, clamp_factor=True)
            self.obj = hit_info.obj
            self.s1_index = hit_info.edge_index
            self.s1_co_ls = vert_1_co_ls.lerp(vert_2_co_ls, factor)
            self.s1_co_ws = hit_info.mat_ws @ self.s1_co_ls
            self.s1_elem_type = "Edge Point"
            self.s1_edge_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (vert_1_co_ws, self.s1_co_ws, vert_2_co_ws), "color": (COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK)})
            if CONFIRMED:
                self.bmeCON.set_specified_objs(objs=[self.obj])
                self.step = 2

        # VERT
        else:
            hit_info = self.bmeCON.ray_to_vert(context, event, ray_opts)
            if hit_info is None: return

            self.obj = hit_info.obj
            self.s1_index = hit_info.vert_index
            self.s1_co_ls = hit_info.mat_ws_inv @ hit_info.vert_co_ws
            self.s1_co_ws = hit_info.vert_co_ws.copy()
            self.s1_elem_type = "Vert"
            if CONFIRMED:
                self.bmeCON.set_specified_objs(objs=[self.obj])
                self.step = 2

        del hit_info


    def ops_join_step_2(self, context, event):
        CONFIRMED = event.type == 'LEFTMOUSE' and event.value == 'PRESS'
        OPTIONS = utils.bme.OPTIONS
        ray_opts = OPTIONS.CHECK_OBSTRUCTIONS | OPTIONS.ONLY_SPECIFIED if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.ONLY_SPECIFIED
        hit_info = None

        # EDGE CENTER
        if event.shift:
            hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
            if edge is None: return
            bm = bmed.BM

            vert_1_co_ws = hit_info.mat_ws @ edge.verts[0].co
            vert_2_co_ws = hit_info.mat_ws @ edge.verts[1].co
            self.s2_index = hit_info.edge_index
            self.s2_co_ls = hit_info.mat_ws_inv @ hit_info.edge_co_ws_center
            self.s2_co_ws = hit_info.edge_co_ws_center
            self.s2_edge_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (vert_1_co_ws, self.s2_co_ws, vert_2_co_ws), "color": (COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK)})
            self.s2_elem_type = "Edge Center"
            if CONFIRMED:
                self.step = 3

        # EDGE NEAREST
        elif event.ctrl:
            hit_info = self.bmeCON.ray_to_edge(context, event, ray_opts)
            if hit_info is None: return
            bmed = hit_info.bmed
            if bmed is None: return
            edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
            if edge is None: return
            bm = bmed.BM

            vert_1_co_ls = edge.verts[0].co
            vert_2_co_ls = edge.verts[1].co
            vert_1_co_ws = hit_info.mat_ws @ vert_1_co_ls
            vert_2_co_ws = hit_info.mat_ws @ vert_2_co_ls
            point = hit_info.mat_ws_inv @ hit_info.edge_co_ws_nearest
            factor = utils.math3.projected_point_line_factor(point, line_p1=vert_1_co_ls, line_p2=vert_2_co_ls, clamp_factor=True)
            self.s2_index = hit_info.edge_index
            self.s2_co_ls = vert_1_co_ls.lerp(vert_2_co_ls, factor)
            self.s2_co_ws = hit_info.mat_ws @ self.s2_co_ls
            self.s2_elem_type = "Edge Point"
            self.s2_edge_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (vert_1_co_ws, self.s2_co_ws, vert_2_co_ws), "color": (COLORS.BLACK, COLORS.ACT_ONE, COLORS.BLACK)})
            if CONFIRMED:
                self.step = 3

        # VERT
        else:
            hit_info = self.bmeCON.ray_to_vert(context, event, ray_opts)
            if hit_info is None: return

            self.s2_index = hit_info.vert_index
            self.s2_co_ls = hit_info.mat_ws_inv @ hit_info.vert_co_ws
            self.s2_co_ws = hit_info.vert_co_ws.copy()
            self.s2_elem_type = "Vert"
            if CONFIRMED:
                self.step = 3

        del hit_info


    def ops_join_step_3(self, context, event):

        bmed = self.bmeCON.get_bmeditor(self.obj)
        bm = bmed.BM
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        vert_1 = None
        vert_2 = None
        edge_1 = None
        edge_2 = None

        # REFS S1
        if self.s1_elem_type in {'Edge Point', 'Edge Center'}:
            edge_1 = bm.edges[self.s1_index]
        else:
            vert_1 = bm.verts[self.s1_index]
        # REFS S2
        if self.s2_elem_type in {'Edge Point', 'Edge Center'}:
            edge_2 = bm.edges[self.s2_index]
        else:
            vert_2 = bm.verts[self.s2_index]
        # EDGE 1 SPLIT
        if self.s1_elem_type == 'Edge Point':
            vert_1 = utils.bmu.split_edge_at_point(edge_1, self.s1_co_ls)
        elif self.s1_elem_type == 'Edge Center':
            vert_1 = utils.bmu.split_edge_at_center(edge_1)
        # EDGE 2 SPLIT
        if self.s2_elem_type == 'Edge Point':
            vert_2 = utils.bmu.split_edge_at_point(edge_2, self.s2_co_ls)
        elif self.s2_elem_type == 'Edge Center':
            vert_2 = utils.bmu.split_edge_at_center(edge_2)
        # VALIDATE : VERT 1
        if not isinstance(vert_1, bmesh.types.BMVert) or not vert_1.is_valid:
            bmed.update(context)
            self.bmeCON.rebuild_ray(context, self.obj)
            self.reset(context)
            return
        # VALIDATE : VERT 2
        if not isinstance(vert_2, bmesh.types.BMVert) or not vert_2.is_valid:
            bmed.update(context)
            self.bmeCON.rebuild_ray(context, self.obj)
            self.reset(context)
            return
        # VALIDATE : UNIQUE
        if vert_1 == vert_2:
            bmed.update(context)
            self.bmeCON.rebuild_ray(context, self.obj)
            self.reset(context)
            return
        # CONNECT VERTS
        geo_is_local = any([(face in vert_1.link_faces) for face in vert_2.link_faces])
        if geo_is_local:
            bmesh.ops.connect_verts(bm, verts=[vert_1, vert_2], faces_exclude=[], check_degenerate=False)
        else:
            bmesh.ops.connect_vert_pair(bm, verts=[vert_1, vert_2])
        # SAVE
        self.bmeCON.save_in_pool(context, self.obj, update_ray=True)
        self.bmeCON.save_pool_push()
        self.reset(context)

    # --- UTILS --- #

    def step_prep(self, context):
        if self.step == 1:
            self.reset(context)
        elif self.step == 2:
            self.s2_edge_batch = None
            if not isinstance(self.obj, bpy.types.Object): return False
            if not isinstance(self.obj.data, bpy.types.Mesh): return False
            if not self.bmeCON.is_obj_in_specified(self.obj): return False
            if not isinstance(self.s1_co_ls, Vector): return False
            if not isinstance(self.s1_co_ws, Vector): return False
            if self.s1_elem_type not in {'Vert', 'Edge Point', 'Edge Center'}: return False
            if not isinstance(self.s1_index, int): return False
            bmed = self.bmeCON.get_bmeditor(self.obj)
            if bmed is None: return False
            bm = bmed.BM
            if self.s1_elem_type == 'Vert':
                if len(bm.verts) == 0 or self.s1_index >= len(bm.verts) or self.s1_index < 0: return False
                if not bm.verts[self.s1_index].is_valid: return False
            elif self.s1_elem_type in {'Edge Point', 'Edge Center'}:
                if len(bm.edges) == 0 or self.s1_index >= len(bm.edges) or self.s1_index < 0: return False
                if not bm.edges[self.s1_index].is_valid: return False
        elif self.step == 3:
            if not isinstance(self.obj, bpy.types.Object): return False
            if not isinstance(self.obj.data, bpy.types.Mesh): return False
            if not self.bmeCON.is_obj_in_specified(self.obj): return False
            if not isinstance(self.s1_index, int): return False
            if not isinstance(self.s2_index, int): return False
            if not isinstance(self.s1_co_ls, Vector): return False
            if not isinstance(self.s2_co_ls, Vector): return False
            if not isinstance(self.s1_co_ws, Vector): return False
            if not isinstance(self.s2_co_ws, Vector): return False
            if self.s1_elem_type not in {'Vert', 'Edge Point', 'Edge Center'}: return False
            if self.s2_elem_type not in {'Vert', 'Edge Point', 'Edge Center'}: return False
            bmed = self.bmeCON.get_bmeditor(self.obj)
            if bmed is None: return False
            bm = bmed.BM
            if self.s1_elem_type == 'Vert':
                if len(bm.verts) == 0 or self.s1_index >= len(bm.verts) or self.s1_index < 0: return False
                if not bm.verts[self.s1_index].is_valid: return False
            elif self.s1_elem_type in {'Edge Point', 'Edge Center'}:
                if len(bm.edges) == 0 or self.s1_index >= len(bm.edges) or self.s1_index < 0: return False
                if not bm.edges[self.s1_index].is_valid: return False
            if self.s2_elem_type == 'Vert':
                if len(bm.verts) == 0 or self.s2_index >= len(bm.verts) or self.s2_index < 0: return False
                if not bm.verts[self.s2_index].is_valid: return False
            elif self.s2_elem_type in {'Edge Point', 'Edge Center'}:
                if len(bm.edges) == 0 or self.s2_index >= len(bm.edges) or self.s2_index < 0: return False
                if not bm.edges[self.s2_index].is_valid: return False
            # UNIQUE ELEMENTS
            if self.s1_index == self.s2_index:
                if (self.s1_elem_type == self.s2_elem_type) or (self.s1_elem_type in {'Edge Point', 'Edge Center'} and self.s2_elem_type in {'Edge Point', 'Edge Center'}):
                    self.step = 2
                    self.s2_co_ls = None
                    self.s2_co_ws = None
                    self.s2_index = None
                    self.s2_elem_type = ""
                    return False
        return True


    def undo(self, context):
        self.bmeCON.save_pool_undo(context, update_ray=True)
        self.reset(context)


    def reset(self, context):
        self.bmeCON.clear_specified_objs()
        self.step = 1
        self.obj = None
        self.s1_index = None
        self.s1_co_ls = None
        self.s1_co_ws = None
        self.s1_edge_batch = None
        self.s1_elem_type = ""
        self.s2_index = None
        self.s2_co_ls = None
        self.s2_co_ws = None
        self.s2_edge_batch = None
        self.s2_elem_type = ""
