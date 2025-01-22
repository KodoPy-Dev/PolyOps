########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import math
import gc
from mathutils import Vector, Matrix, Euler, Quaternion
from ... import utils
from ...utils.modal_status import MODAL_STATUS, UX_STATUS
from ...utils.graphics import COLORS, draw_action_line_3d
except_guard_prop_set = utils.guards.except_guard_prop_set

DESC = """Dissolve\n
• Edit Mode
\t\t→ Dissolve Elements"""

class PS_OT_Dissolve(bpy.types.Operator):
    bl_idname      = "ps.dissolve"
    bl_label       = "Dissolve"
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

        # Ops
        self.angle_limit = 35
        self.planar_limit = 2
        # Graphics
        self.mode = 'None'
        self.p1 = Vector((0,0,0))
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
        # Operations
        self.ops_dissolve(context, event)
        # Possible Errors Occured
        if self.modal_status != MODAL_STATUS.RUNNING:
            return
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
                ("LMB"        , "Vert"),
                ("CTRL"       , "Edge"),
                ("ALT"        , "Face"),
                ("SHIFT + ALT", "Planar"),
            ]
        utils.modal_labels.info_panel_init(context, messages=help_msgs)


    def setup_status_panel(self, context):
        status_msgs = [
            ("Dissolve",),
            ("(LMB)", "$Vert" if self.mode == "Vert" else "Vert"),
            ("(CTRL)", "$Edge" if self.mode == "Edge" else "Edge"),
            ("(ALT)", "$Face" if self.mode == "Face" else "Face"),
            ("(SHIFT + ALT)", "$Planar" if self.mode == "Planar" else "Planar"),
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

        rows = []
        tip = "Preserve edges with angles greater than or equal to the limit"
        map_1 = PropMap(label="Angle Limit", tip=tip, as_degrees=True, min_val=0, max_val=180, show_label=False, instance=self, prop_name='angle_limit', box_len=7)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        cont_2 = Container(label="Angle Limit", center_label=True, rows=rows, force_no_scroll_bar=True)

        rows = []
        tip = "Planar angle limit"
        map_1 = PropMap(label="Planar Limit", tip=tip, as_degrees=True, min_val=0, max_val=180, show_label=False, instance=self, prop_name='planar_limit', box_len=7)
        rows.append(Row(label="", prop_maps=[map_1], min_label_height=True, min_borders=True))
        cont_3 = Container(label="Planar Limit", center_label=True, rows=rows, force_no_scroll_bar=True)

        self.menu = Menu(context, event, containers=[cont_1, cont_2, cont_3])


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
        if self.mode != "None":
            draw_action_line_3d(context, p1=self.p1, p2=None)
        self.bmeCON.mesh_graphics.draw_3d(verts=True, edges=True, faces=True)


    def draw_post_pixel(self, context):
        utils.modal_labels.draw_info_panel()
        utils.modal_labels.draw_status_panel()
        self.menu.draw()

    # --- OPS --- #

    def ops_dissolve(self, context, event):
        self.reset(context)
        # Planar Face Cast
        if event.shift and event.alt:
            self.ops_dissolve_planar(context, event)
        # Face Cast
        elif event.alt:
            self.ops_dissolve_face(context, event)
        # Edge Cast
        elif event.ctrl:
            self.ops_dissolve_edge(context, event)
        # Vert Cast
        else:
            self.ops_dissolve_vert(context, event)


    def ops_dissolve_planar(self, context, event):
        hit_info = self.bmeCON.ray_to_face(context, event, self.bme_ray_options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        face = bmed.get_bm_elem(index=hit_info.face_index, elem_type='FACE')
        if face is None: return

        faces = utils.bmu.connected_faces_to_face_by_angle(face, angle=math.radians(self.planar_limit))
        if not faces: return
        perimeter_edges = utils.bmu.perimeter_edges_from_faces(faces, convert_to_list=False)
        if not perimeter_edges: return

        # Graphics
        self.mode = "Planar"
        self.p1 = hit_info.face_co_ws
        if perimeter_edges:
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=perimeter_edges, use_depth_test=False, line_width=3, edge_color=COLORS.RED)
        if face:
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[face], use_depth_test=False, edge_color=COLORS.FACE)
        if faces:
            self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=faces, use_depth_test=False, edge_color=COLORS.EDGE)

        # No Confirm
        if not (event.type == 'LEFTMOUSE' and event.value == 'PRESS'):
            return

        angle_lim = math.radians(self.angle_limit)
        edges = {e for f in faces for e in f.edges if e not in perimeter_edges and e.calc_face_angle(math.inf) <= angle_lim}

        if len(edges) == len(bm.edges):
            utils.notifications.init(context, messages=[("$Error", "All geometry would be dissolved")])
            return

        if edges:
            bmesh.ops.dissolve_edges(bm, edges=list(edges), use_verts=False, use_face_split=False)

        if perimeter_edges:
            perimeter_verts = {v for e in perimeter_edges if e.is_valid for v in e.verts if v.is_valid}
            verts = {v for v in perimeter_verts if len(v.link_edges) == 2 and v.calc_edge_angle(math.inf) <= angle_lim}
            if verts and len(verts) != len(perimeter_verts):
                bmesh.ops.dissolve_verts(bm, verts=list(verts), use_face_split=False, use_boundary_tear=False)

        self.save(context, obj)
        del hit_info


    def ops_dissolve_face(self, context, event):
        hit_info = self.bmeCON.ray_to_face(context, event, self.bme_ray_options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        face = bmed.get_bm_elem(index=hit_info.face_index, elem_type='FACE')
        if face is None: return

        # Graphics
        self.mode = "Face"
        self.p1 = hit_info.face_co_ws
        self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[face], use_depth_test=False, face_color=COLORS.FACE)

        # Confirm
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            edges = [edge for edge in face.edges if edge.calc_face_angle(0) <= math.radians(self.angle_limit)]
            if edges:
                bmesh.ops.dissolve_edges(bm, edges=edges, use_verts=False, use_face_split=False)
                self.save(context, obj)
        del hit_info


    def ops_dissolve_edge(self, context, event):
        hit_info = self.bmeCON.ray_to_edge(context, event, self.bme_ray_options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        edge = bmed.get_bm_elem(index=hit_info.edge_index, elem_type='EDGE')
        if edge is None: return

        # Graphics
        self.mode = "Edge"
        self.p1 = hit_info.edge_co_ws_nearest
        self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[edge], use_depth_test=False, line_width=3, edge_color=COLORS.EDGE)

        # Confirm
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            angle = edge.calc_face_angle(0)
            if angle <= math.radians(self.angle_limit):
                bmesh.ops.dissolve_edges(bm, edges=[edge], use_verts=False, use_face_split=False)
                self.save(context, obj)
        del hit_info


    def ops_dissolve_vert(self, context, event):
        hit_info = self.bmeCON.ray_to_vert(context, event, self.bme_ray_options)
        if hit_info is None: return
        bmed = hit_info.bmed
        if bmed is None: return
        obj = bmed.obj
        bm = bmed.BM
        vert = bmed.get_bm_elem(index=hit_info.vert_index, elem_type='VERT')
        if vert is None: return

        # Graphics
        self.mode = "Vert"
        self.p1 = hit_info.vert_co_ws
        self.bmeCON.mesh_graphics.batch_for_geo(obj, bm, geo=[vert], use_depth_test=False, point_size=6, vert_color=COLORS.VERT)

        # Confirm
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Single Vert on edge
            if len(vert.link_edges) == 2:
                bmesh.ops.dissolve_verts(bm, verts=[vert], use_face_split=False, use_boundary_tear=False)
                self.save(context, obj)
            else:
                # Edges within limit (Idea is to leave edges that hold the shape)
                edges = []
                for edge in vert.link_edges:
                    angle = edge.calc_face_angle(0)
                    if angle <= math.radians(self.angle_limit):
                        edges.append(edge)
                if edges:
                    bmesh.ops.dissolve_edges(bm, edges=edges, use_verts=False, use_face_split=False)
                    if vert and vert.is_valid:
                        # Remove remaining isolated vert
                        if len(vert.link_edges) == 2:
                            bmesh.ops.dissolve_verts(bm, verts=[vert], use_face_split=False, use_boundary_tear=False)
                    self.save(context, obj)
        del hit_info

    # --- UTILS --- #

    def undo(self, context):
        self.bmeCON.save_pool_undo(context, update_ray=True)
        self.reset(context)


    def save(self, context, obj):
        if self.bmeCON.save_in_pool(context, obj, update_ray=True):
            self.bmeCON.save_pool_push()


    def reset(self, context):
        self.mode = "None"
        self.bmeCON.mesh_graphics.clear_batches(verts=True, edges=True, faces=True)
        OPTIONS = utils.bme.OPTIONS
        self.bme_ray_options = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
