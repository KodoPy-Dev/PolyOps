########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import math
import gc
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS, draw_action_line_3d
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Bisect-Loop\n
• Edit Mode
\t\t→ Bisect mesh from edges or verts"""

class PS_OT_BLoop(bpy.types.Operator):
    bl_idname      = "ps.bisect_loop"
    bl_label       = "BLoop"
    bl_description = DESC
    bl_options     = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'


    def invoke(self, context, event):
        # Prefs
        self.prefs = utils.addon.user_prefs()
        self.op_prefs = self.prefs.operator.bloop

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

        # Operations
        self.rebuild_menu = False
        self.ray_modes = ['Edge', 'Vert']
        self.cut_through_modes = ['Island', 'Mesh', 'All', 'Selected']
        self.edge_angle_modes = ['Perpendicular', 'Aligned', 'View X', 'View Y', 'World X', 'World Y', 'World Z']
        self.vert_angle_modes = ['Adjacent-V', 'Center-F', 'View X', 'View Y', 'World X', 'World Y', 'World Z']
        self.sel_second_vert = False

        # Graphics
        self.p1 = Vector((0,0,0))
        self.p2 = Vector((0,0,0))

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
        # Help
        if event.type == 'H' and event.value == 'PRESS':
            self.prefs.settings.show_modal_help = not self.prefs.settings.show_modal_help
            self.setup_help_panel(context)
        # Undo
        elif event.type == 'Z' and event.value == 'PRESS' and event.ctrl:
            self.undo(context)
        # Ray Mode
        elif event.type == 'A' and event.value == 'PRESS':
            self.op_prefs.ray_mode = utils.algos.wrap_to_next(item=self.op_prefs.ray_mode, sequence=self.ray_modes)
            self.setup_help_panel(context)
            self.setup_status_panel(context)
            self.setup_menu(context, event)
        # Cut Through Mode
        elif event.type == 'S' and event.value == 'PRESS':
            self.op_prefs.cut_through_mode = utils.algos.wrap_to_next(item=self.op_prefs.cut_through_mode, sequence=self.cut_through_modes)
            self.setup_status_panel(context)
        # Angle Mode
        elif event.type == 'D' and event.value == 'PRESS':
            if self.op_prefs.ray_mode == 'Edge':
                self.op_prefs.edge_angle_mode = utils.algos.wrap_to_next(item=self.op_prefs.edge_angle_mode, sequence=self.edge_angle_modes)
            elif self.op_prefs.ray_mode == 'Vert':
                self.op_prefs.vert_angle_mode = utils.algos.wrap_to_next(item=self.op_prefs.vert_angle_mode, sequence=self.vert_angle_modes)
            self.setup_status_panel(context)
        # Operations
        self.operations(context, event)
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
                ("A"          , "Ray Modes"),
                ("S"          , "Cut Modes"),
                ("D"          , "Angle Modes"),
                ]
            if self.op_prefs.ray_mode == 'Edge':
                help_msgs.append(("$Edge-Mode",))
                help_msgs.append(("SHIFT", "Snap Center"))

        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def setup_status_panel(self, context):
        if self.op_prefs.ray_mode == 'Edge':
            status_msgs = [
                ("(A) Ray Mode", "Edge"),
                ("(S) Through", f"{self.op_prefs.cut_through_mode}"),
                ("(D) Angle", f"{self.op_prefs.edge_angle_mode}"),
                ("(LMB)", "Confirm Loop"),
                ("(SHIFT)", "Center Snap"),
            ]
            utils.modal_labels.status_panel_init(context, messages=status_msgs)
        elif self.op_prefs.ray_mode == 'Vert':
            status_msgs = [
                ("(A) Ray Mode", "Vert"),
                ("(S) Through", f"{self.op_prefs.cut_through_mode}"),
                ("(D) Angle", f"{self.op_prefs.vert_angle_mode}"),
                ("(LMB)", "Confirm Loop"),
            ]
            utils.modal_labels.status_panel_init(context, messages=status_msgs)


    def setup_menu(self, context, event):
        PropMap = utils.modal_ux.PropMap
        Row = utils.modal_ux.Row
        Container = utils.modal_ux.Container
        Menu = utils.modal_ux.Menu
        rows = []
        box_len = 8
        map_1 = PropMap(label="Confirm", instance=self, prop_name='menu_callback', box_len=box_len)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Cancel", instance=self, prop_name='menu_callback', box_len=box_len)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Undo", instance=self, prop_name='menu_callback', box_len=box_len)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        map_1 = PropMap(label="Wireframe", instance=self, prop_name='menu_callback', box_len=box_len, highlight_callback=self.menu_highlight_wireframe)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        cont_1 = Container(label="", rows=rows, force_no_scroll_bar=True)

        rows = []
        tip = "Ray Mode"
        map_1 = PropMap(label="Ray Mode", tip=tip, instance=self.op_prefs, prop_name='ray_mode', list_items=self.ray_modes, list_index=self.ray_modes.index(self.op_prefs.ray_mode), box_len=box_len, call_back=self.menu_callback)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        tip = "Cut Through Mode"
        map_1 = PropMap(label="Cut Mode", tip=tip, instance=self.op_prefs, prop_name='cut_through_mode', list_items=self.cut_through_modes, list_index=self.cut_through_modes.index(self.op_prefs.cut_through_mode), box_len=box_len, call_back=self.menu_callback)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        if self.op_prefs.ray_mode == 'Edge':
            tip = "Angle Mode"
            map_1 = PropMap(label="Edge Angle", tip=tip, instance=self.op_prefs, prop_name='edge_angle_mode', list_items=self.edge_angle_modes, list_index=self.edge_angle_modes.index(self.op_prefs.edge_angle_mode), box_len=box_len, call_back=self.menu_callback)
            rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        elif self.op_prefs.ray_mode == 'Vert':
            tip = "Angle Mode"
            map_1 = PropMap(label="Vert Angle", tip=tip, instance=self.op_prefs, prop_name='vert_angle_mode', list_items=self.vert_angle_modes, list_index=self.vert_angle_modes.index(self.op_prefs.vert_angle_mode), box_len=box_len, call_back=self.menu_callback)
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
        elif label == "Ray Mode":
            self.rebuild_menu = True
        elif label == "Cut Mode":
            self.setup_status_panel(context)
        elif label == "Edge Angle":
            self.setup_status_panel(context)
        elif label == "Vert Angle":
            self.setup_status_panel(context)


    def menu_highlight_wireframe(self, context, event, prop_map):
        return context.space_data.shading.type == 'WIREFRAME'

    # --- SHADER --- #

    def draw_post_view(self, context):
        draw_faces = False
        if self.op_prefs.ray_mode == 'Vert':
            if self.op_prefs.vert_angle_mode in {'Adjacent-V', 'Center-F'}:
                draw_faces = True
                draw_action_line_3d(context, p1=self.p1, p2=self.p2)
            else:
                draw_action_line_3d(context, p1=self.p1, p2=None)
        elif self.op_prefs.ray_mode == 'Edge':
            if self.op_prefs.edge_angle_mode == 'Aligned':
                draw_faces = True
        self.bmeCON.mesh_graphics.draw_3d(verts=True, edges=True, faces=draw_faces)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.menu.draw()

    # --- OPS --- #

    def operations(self, context, event):
        # Graphics
        self.p1.zero()
        self.p2.zero()
        self.bmeCON.mesh_graphics.clear_batches(verts=True, edges=True, faces=True)
        # Edge
        if self.op_prefs.ray_mode == 'Edge':
            self.ops_edge_mode(context, event)
        # Vert
        elif self.op_prefs.ray_mode == 'Vert':
            self.ops_vert_mode(context, event)


    def ops_vert_mode(self, context, event):
        # Ray
        OPTIONS = utils.bme.OPTIONS
        options = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = self.bmeCON.ray_to_vert(context, event, options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        vert = bmed.get_bm_elem(index=hit_info.vert_index, elem_type='VERT')
        if vert is None: return
        face = bmed.get_bm_elem(index=hit_info.face_index, elem_type='FACE')
        if face is None: return
        mat_ws = bmed.mat_ws
        mat_ws_trs = bmed.mat_ws_trs
        vert_co_ws = hit_info.vert_co_ws

        # Graphics
        self.p1 = vert_co_ws

        # Plane Coord
        plane_co_ls = vert.co.copy()

        # Plane Normal
        plane_no = Vector((1,0,0))
        if self.op_prefs.vert_angle_mode == 'Adjacent-V':
            vert_2 = utils.bmu.farthest_vert_to_vert_on_face(face, vert)
            if not vert_2: return
            vert_2_co_ws = mat_ws @ vert_2.co
            edge_no = (vert_co_ws - vert_2_co_ws).normalized()
            face_no = face.normal
            plane_no = mat_ws_trs @ face_no.cross(edge_no)
            # Graphics
            self.p2 = vert_2_co_ws
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[face], use_depth_test=False, point_size=1, line_width=1, face_cull=False)
        elif self.op_prefs.vert_angle_mode == 'Center-F':
            face_center_ws = mat_ws @ face.calc_center_median()
            vert_to_face_no = (vert_co_ws - face_center_ws).normalized()
            face_no = face.normal
            plane_no = mat_ws_trs @ face_no.cross(vert_to_face_no)
            # Graphics
            self.p2 = face_center_ws
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[face], use_depth_test=False, point_size=1, line_width=1, face_cull=False)
        elif self.op_prefs.vert_angle_mode == 'View X':
            plane_no = utils.math3.perp_norm_from_view_with_coord_and_object(context, event, obj, direction=Vector((1,0,0)), plane_co_ls=plane_co_ls)
        elif self.op_prefs.vert_angle_mode == 'View Y':
            plane_no = utils.math3.perp_norm_from_view_with_coord_and_object(context, event, obj, direction=Vector((0,1,0)), plane_co_ls=plane_co_ls)
        elif self.op_prefs.vert_angle_mode == 'World X':
            plane_no = mat_ws_trs @ Vector((0,1,0))
        elif self.op_prefs.vert_angle_mode == 'World Y':
            plane_no = mat_ws_trs @ Vector((1,0,0))
        elif self.op_prefs.vert_angle_mode == 'World Z':
            plane_no = mat_ws_trs @ Vector((0,0,1))
        plane_no.normalize()

        # Bisect
        self.ops_bisect(context, event, obj, plane_co_ls=plane_co_ls, plane_no=plane_no, vert_sample_for_island=vert.index)
        del hit_info


    def ops_edge_mode(self, context, event):
        # Reset
        self.arrow_batch = None

        # Ray
        OPTIONS = utils.bme.OPTIONS
        options = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = self.bmeCON.ray_to_edge(context, event, options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
        if edge is None: return
        face = bmed.get_bm_elem(index=hit_info.face_index, elem_type='FACE')
        if face is None: return
        mat_ws = bmed.mat_ws
        mat_ws_inv = bmed.mat_ws_inv
        mat_ws_trs = bmed.mat_ws_trs
        vert_co_ws = hit_info.vert_co_ws
        vert_1 = edge.verts[0]
        vert_2 = edge.verts[1]
        vert_1_co_ls = vert_1.co.copy()
        vert_2_co_ls = vert_2.co.copy()
        vert_1_co_ws = mat_ws @ vert_1_co_ls
        vert_2_co_ws = mat_ws @ vert_2_co_ls

        # Plane Coord
        plane_co_ls = (vert_1_co_ls + vert_2_co_ls) / 2 if event.shift else mat_ws_inv @ hit_info.edge_co_ws_nearest

        # Plane Normal
        plane_no = Vector((1,0,0))
        if self.op_prefs.edge_angle_mode == 'Perpendicular':
            plane_no = mat_ws_trs @ (vert_1_co_ws - vert_2_co_ws)
        elif self.op_prefs.edge_angle_mode == 'Aligned':
            edge_no = (vert_1_co_ls - vert_2_co_ls).normalized()
            plane_no = face.normal.cross(edge_no)
            # Graphics
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[face], use_depth_test=False, point_size=1, line_width=1, face_cull=False)
        elif self.op_prefs.edge_angle_mode == 'View X':
            plane_no = utils.math3.perp_norm_from_view_with_coord_and_object(context, event, obj, direction=Vector((1,0,0)), plane_co_ls=plane_co_ls)
        elif self.op_prefs.edge_angle_mode == 'View Y':
            plane_no = utils.math3.perp_norm_from_view_with_coord_and_object(context, event, obj, direction=Vector((0,1,0)), plane_co_ls=plane_co_ls)
        elif self.op_prefs.edge_angle_mode == 'World X':
            plane_no = mat_ws_trs @ Vector((0,1,0))
        elif self.op_prefs.edge_angle_mode == 'World Y':
            plane_no = mat_ws_trs @ Vector((1,0,0))
        elif self.op_prefs.edge_angle_mode == 'World Z':
            plane_no = mat_ws_trs @ Vector((0,0,1))
        plane_no.normalize()

        # Graphics
        self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[edge, vert_1, vert_2], use_depth_test=False, point_size=6, line_width=2, face_cull=False, vert_color=COLORS.WHITE, edge_color=COLORS.ACT_ONE)

        # Bisect
        self.ops_bisect(context, event, obj, plane_co_ls=plane_co_ls, plane_no=plane_no, vert_sample_for_island=vert_1.index)
        del hit_info


    def ops_bisect(self, context, event, from_obj, plane_co_ls=Vector((0,0,0)), plane_no=Vector((0,0,1)), vert_sample_for_island=None):
        ''' Cut Through Modes | Bisect | Mesh Graphics | LMB Save'''
        # Refs
        edge_verts_are_in_plane = utils.bmu.edge_verts_are_in_plane

        # Multi Object Cut Type
        if self.op_prefs.cut_through_mode in {'All', 'Selected'}:
            from_mat_ws = from_obj.matrix_world
            from_mat_ws_inv = from_mat_ws.inverted_safe()
            from_mat_ws_inv_ts = from_mat_ws_inv.transposed()

            only_sel_geo = self.op_prefs.cut_through_mode == 'Selected'

            # Bmesh Editors
            push_pool = False
            for bmed in self.bmeCON.iter_bmeditors():
                obj = bmed.obj
                bm = bmed.BM

                # Graphics : Original Edges
                ori_edges = set(bm.edges[:])

                # Coords
                plane_coord = plane_co_ls.copy()
                plane_normal = plane_no.copy()

                # Cut
                ret = None
                if from_obj != obj:
                    mat_ws = obj.matrix_world
                    mat_ws_inv = mat_ws.inverted_safe()
                    mat_ws_trs = mat_ws.transposed()
                    plane_coord = mat_ws_inv @ (from_mat_ws @ plane_coord)
                    plane_normal = mat_ws_trs @ (from_mat_ws_inv_ts @ plane_normal)
                    ret = utils.bmu.bisect_mesh(bm, plane_co=plane_coord, plane_no=plane_normal, cut_hidden=False, vert_sample_for_island=None, only_sel_geo=only_sel_geo)
                else:
                    ret = utils.bmu.bisect_mesh(bm, plane_co=plane_coord, plane_no=plane_normal, cut_hidden=False, vert_sample_for_island=None, only_sel_geo=only_sel_geo)

                # No Cut
                if isinstance(ret, dict):
                    if len(ret['geom_cut']) == 0:
                        continue

                # Graphics : New Edges
                edges = set(bm.edges[:]).difference(ori_edges)
                edges = [e for e in edges if edge_verts_are_in_plane(e, plane_coord, plane_normal)]
                if edges:
                    self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=edges, use_depth_test=False, point_size=1, line_width=1, face_cull=False, edge_color=COLORS.ACT_TWO)

                # Save
                if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                    if self.bmeCON.save_in_pool(context, obj, update_ray=True):
                        push_pool = True
                # Restore
                else:
                    bmed.restore()
                    bmed.update()
                    self.bmeCON.rebuild_ray(context, obj)

            # Push Saves
            if push_pool:
                self.bmeCON.save_pool_push()

        # Single Mesh Cut Types
        else:
            bmed = self.bmeCON.get_bmeditor_from_last_ray()
            if bmed is None: return
            obj = bmed.obj
            bm = bmed.BM

            # Graphics : Original Edges
            ori_edges = set(bm.edges[:])

            # Cut
            ret = None
            if self.op_prefs.cut_through_mode == 'Island':
                vert_sample = None
                if vert_sample_for_island is not None:
                    if vert_sample_for_island < len(bm.verts) and vert_sample_for_island >= 0:
                        bm.verts.ensure_lookup_table()
                        vert_sample = bm.verts[vert_sample_for_island]
                ret = utils.bmu.bisect_mesh(bm, plane_co=plane_co_ls, plane_no=plane_no, cut_hidden=False, vert_sample_for_island=vert_sample, only_sel_geo=False)
            elif self.op_prefs.cut_through_mode == 'Mesh':
                ret = utils.bmu.bisect_mesh(bm, plane_co=plane_co_ls, plane_no=plane_no, cut_hidden=False, vert_sample_for_island=None, only_sel_geo=False)

            # No Cut
            if isinstance(ret, dict):
                if len(ret['geom_cut']) == 0:
                    return

            # New Edges
            edges = set(bm.edges[:]).difference(ori_edges)
            edges = [e for e in edges if edge_verts_are_in_plane(e, plane_co_ls, plane_no)]
            if edges:
                self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=edges, use_depth_test=False, point_size=1, line_width=1, face_cull=False, edge_color=COLORS.ACT_TWO)

            # Save
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                if self.bmeCON.save_in_pool(context, obj, update_ray=True):
                    self.bmeCON.save_pool_push()
            # Restore
            else:
                bmed.restore()
                bmed.update()
                self.bmeCON.rebuild_ray(context, obj)

    # --- UTILS --- #

    def undo(self, context):
        self.bmeCON.save_pool_undo(context, update_ray=True)
