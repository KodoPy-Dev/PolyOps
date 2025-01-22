########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import bmesh
import math
import gpu
from math import radians
from mathutils import Vector, Matrix, Quaternion
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils.geometry import intersect_point_line
from .addon import user_prefs
from .bme import OPTIONS, HitInfo, BmeshController
from .bmu import ops_trace_edges
from .context import set_component_selection, object_mode_toggle_reset, object_mode_toggle_start, object_mode_toggle_end
from .event import LMB_press, RMB_press, reset_mouse_drag, pass_through, confirmed, cancelled
from .graphics import Label2D, draw_circle_2d, draw_label, draw_line, draw_arrow_3d, draw_point, draw_text, label_dims, max_text_height, draw_action_line_3d
from .modal_status import OPS_STATUS, MODAL_STATUS
from .mesh import shade_polygons, any_polygons_smooth
from .modifiers import last_auto_smooth_mod, last_auto_smooth_angle, last_weighted_normal_mod, setup_shading, referenced_booleans
from .object import apply_scale, scale_obj, get_visible_mesh_obj_by_name
from .ray import cast_onto_plane, cast_to_view_plane_pick_side, cast_onto_view_plane_with_angle_from_point, cast_onto_view_plane
from .screen import screen_factor, pixels_per_unit_at_depth
from .notifications import init as notify
from .notifications import remove_notify_handle
from .poly_fade import remove_poly_fade_handle
from .vec_fade import remove_vec_fade_handle
from .debug import remove_debug_handle

########################•########################
"""                  GLOBALS                  """
########################•########################

UNIFORM_COLOR = gpu.shader.from_builtin('UNIFORM_COLOR')
SMOOTH_COLOR = gpu.shader.from_builtin('SMOOTH_COLOR')

########################•########################
"""             STANDARD OPS                  """
########################•########################

def reset_and_clear_handles():
    object_mode_toggle_reset()
    reset_mouse_drag()
    remove_notify_handle()
    remove_poly_fade_handle()
    remove_vec_fade_handle()
    remove_debug_handle()


def standard_modal_setup(self, context, event, utils):
    # Globals
    reset_and_clear_handles()
    # Modal
    self.modal_status = MODAL_STATUS.RUNNING
    # Prefs
    prefs = utils.addon.user_prefs().hud_gizmos
    self.show_gizmos = prefs.show_gizmos
    prefs.show_gizmos = False
    # Component Selection
    utils.context.save_current_select_mode(context)
    # Side Panels
    utils.context.hide_3d_panels(context)
    # Shader Handles
    self.handle_post_view = None
    self.handle_post_pixel = None
    # Assign Shader Handles
    except_guard_prop_set = utils.guards.except_guard_prop_set
    call_args = (self.draw_post_view, (context,), self, 'modal_status', MODAL_STATUS.ERROR)
    self.handle_post_view = bpy.types.SpaceView3D.draw_handler_add(except_guard_prop_set, call_args, 'WINDOW', 'POST_VIEW')
    call_args = (self.draw_post_pixel, (context,), self, 'modal_status', MODAL_STATUS.ERROR)
    self.handle_post_pixel = bpy.types.SpaceView3D.draw_handler_add(except_guard_prop_set, call_args, 'WINDOW', 'POST_PIXEL')
    # Modal
    context.window_manager.modal_handler_add(self)
    context.area.tag_redraw()


def standard_modal_shutdown(self, context, utils, restore_select_mode=True):
    def shut_down():
        # Shader Handles
        if self.handle_post_view:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_post_view, "WINDOW")
        if self.handle_post_pixel:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle_post_pixel, "WINDOW")
        self.handle_post_view, self.handle_post_pixel = None, None
        # Prefs
        prefs = utils.addon.user_prefs().hud_gizmos
        prefs.show_gizmos = self.show_gizmos
        # Component Selection
        if restore_select_mode:
            utils.context.restore_to_last_select_mode(context)
        # Side Panels
        utils.context.restore_3d_panels(context)
        # Exit Notify
        if self.modal_status == MODAL_STATUS.ERROR:
            utils.notifications.init(context, messages=[("Operation", "Error")])
        elif self.modal_status == MODAL_STATUS.CANCEL:
            utils.notifications.init(context, messages=[("Operation", "Cancelled")])
        elif self.modal_status == MODAL_STATUS.CONFIRM:
            utils.notifications.init(context, messages=[("Operation", "Completed")])
        context.area.tag_redraw()
    utils.guards.except_guard(try_func=shut_down, try_args=None)


class StandardOps:
    def __init__(self, context, event, objs=[], track_scale=False, track_shading_mods=False, track_vgroups=False, track_polygon_shading=False, track_spline_shading=False):
        self.status = MODAL_STATUS.RUNNING
        self.objs = [obj for obj in objs if isinstance(obj, bpy.types.Object)]
        # Objects
        self.show_wire = any([obj.show_wire for obj in objs])
        self.scale_map = {obj: obj.scale.copy() for obj in self.objs} if track_scale else {}
        self.wire_display_map = {obj: obj.show_wire for obj in self.objs}
        self.obj_shading_mods_map = {obj:{'USE_SMOOTH':any_polygons_smooth(obj), 'USE_AUTO_SMOOTH':bool(last_auto_smooth_mod(obj)), 'ANGLE':last_auto_smooth_angle(obj), 'USE_WEIGHTED_NORMAL':bool(last_weighted_normal_mod(obj))} for obj in self.objs} if track_shading_mods else {}
        # Meshes
        mesh_objs = [obj for obj in self.objs if obj.type == 'MESH']
        self.vgroup_map = {obj : {vgroup for vgroup in obj.vertex_groups} for obj in mesh_objs} if track_vgroups else {}
        self.mesh_poly_shading_map = {obj.data.name : {polygon.index : polygon.use_smooth for polygon in obj.data.polygons} for obj in mesh_objs} if track_polygon_shading else {}
        # Curves
        curve_objs = [obj for obj in self.objs if obj.type == 'CURVE']
        self.spline_shading_map = {obj : {index : spline.use_smooth for index, spline in enumerate(obj.data.splines)} for obj in curve_objs} if track_spline_shading else {}


    def update(self, context, event, ops_press_value='PRESS', cancel_press_value='PRESS', wire_display_key='W', pass_with_scoll=False, pass_with_numpad=False, pass_with_shading=False):
        self.status = MODAL_STATUS.RUNNING
        # Wire Display
        if event.type == wire_display_key and event.value == ops_press_value:
            self.show_wire = not self.show_wire
            for obj in self.objs:
                if obj and isinstance(obj, bpy.types.Object):
                    obj.show_wire = self.show_wire
        # View Movement
        elif pass_through(event, with_scoll=pass_with_scoll, with_numpad=pass_with_numpad, with_shading=pass_with_shading):
            self.status = MODAL_STATUS.PASS
        # Finished
        elif confirmed(event):
            self.status = MODAL_STATUS.CONFIRM
        # Cancelled
        elif cancelled(event, value=cancel_press_value):
            self.status = MODAL_STATUS.CANCEL


    def close(self, context, revert=False):
        for obj, show_wire in self.wire_display_map.items():
            if obj and isinstance(obj, bpy.types.Object):
                obj.show_wire = show_wire
        if revert:
            self.revert_object_scale()
            self.revert_shading()
            self.revert_vgroups()


    def set_object_scale(self):
        for obj in self.objs:
            apply_scale(obj)


    def set_shading(self, specified_objs=[], use_smooth=True, use_weighted_normal=True, angle=radians(30), smooth_boolean_objs=True):
        objs = [obj for obj in specified_objs if isinstance(obj, bpy.types.Object)] if specified_objs else self.objs
        for obj in objs:
            setup_shading(obj, use_smooth=use_smooth, auto_smooth=use_smooth, weighted_normal=use_weighted_normal, angle=angle)
            if smooth_boolean_objs:
                for boolean in referenced_booleans(obj):
                    # Track the shading when its not empty : meaning polygon shading was initialized to be tracked
                    if self.mesh_poly_shading_map:
                        mesh = boolean.data
                        if mesh.name not in self.mesh_poly_shading_map:
                            self.mesh_poly_shading_map[mesh.name] = {polygon.index : polygon.use_smooth for polygon in mesh.polygons}
                    shade_polygons(boolean, use_smooth=use_smooth)


    def revert_object_scale(self):
        for obj, scale in self.scale_map.items():
            if obj and isinstance(obj, bpy.types.Object):
                if obj.scale != scale:
                    scale_obj(obj, scale)


    def revert_shading(self):
        # Objects
        for obj, shade_settings in self.obj_shading_mods_map.items():
            if obj and isinstance(obj, bpy.types.Object):
                setup_shading(obj, use_smooth=shade_settings['USE_SMOOTH'], auto_smooth=shade_settings['USE_AUTO_SMOOTH'], weighted_normal=shade_settings['USE_WEIGHTED_NORMAL'], angle=shade_settings['ANGLE'])
        # Meshes
        for mesh_name, poly_shading_map in self.mesh_poly_shading_map.items():
            if mesh_name in bpy.data.meshes:
                mesh = bpy.data.meshes[mesh_name]
                polygons = mesh.polygons
                for polygon in polygons:
                    if polygon.index in poly_shading_map:
                        polygon.use_smooth = poly_shading_map[polygon.index]
        # Curves
        for obj, spline_shading_map in self.spline_shading_map.items():
            if obj and isinstance(obj, bpy.types.Object):
                for index, spline in enumerate(obj.data.splines):
                    if index in spline_shading_map:
                        spline.use_smooth = spline_shading_map[index]


    def revert_vgroups(self):
        for obj, og_vgroups_set in self.vgroup_map.items():
            if obj and isinstance(obj, bpy.types.Object):
                for vgroup in obj.vertex_groups[:]:
                    if vgroup not in og_vgroups_set:
                        obj.vertex_groups.remove(vgroup)

########################•########################
"""                  SYSTEMS                  """
########################•########################

class PickLineFromV3D:
    def __init__(self, context, reset_key='R'):
        # Screen
        self.screen_width = context.area.width
        self.screen_height = context.area.height
        self.screen_factor = screen_factor()
        self.screen_padding = round(user_prefs().drawing.screen_padding * self.screen_factor)
        # States
        self.status = OPS_STATUS.INACTIVE
        self.step = 1
        self.pick_side = True
        # Line Data
        self.p1 = Vector((0,0,0))
        self.p2 = Vector((0,0,0))
        self.side_co = Vector((0,0,0))
        self.side_no = Vector((0,0,0))
        # Event Data
        self.reset_key = reset_key
        # Drawing
        self.step_1_label = Label2D()
        self.step_2_label = Label2D()
        self.step_3_label = Label2D()
        self.angle_snap = ""
        self.mouse = Vector((0,0))
        self.__build(context)


    def __build(self, context):
        x = round(self.screen_width - self.screen_padding)
        y = self.screen_padding
        step_1_msgs = [
            ("LMB", "Pick 1st Point"),
            ("CTRL", "Vertex"),
            ("CTRL + SHIFT", "Edge"),
            ("ALT", "Edge Center")]
        step_2_msgs = [
            ("LMB", "Pick 2nd Point"),
            (f"{self.reset_key}", "Restart"),
            ("Shift", "Angle"),
            ("Ctrl", "Vertex"),
            ("CTRL + SHIFT", "Edge"),
            ("ALT", "Edge Center")]
        step_3_msgs = [
            ("LMB", "Pick Side" if self.pick_side else "Confirm"),
            ("R", "Restart")]
        self.step_1_label.build_from_msgs(pos_x=x, pos_y=y, messages=step_1_msgs, pos='BOTTOM_RIGHT')
        self.step_2_label.build_from_msgs(pos_x=x, pos_y=y, messages=step_2_msgs, pos='BOTTOM_RIGHT')
        self.step_3_label.build_from_msgs(pos_x=x, pos_y=y, messages=step_3_msgs, pos='BOTTOM_RIGHT')


    def reset(self):
        self.status = OPS_STATUS.INACTIVE
        self.step = 1
        self.p1 = Vector((0,0,0))
        self.p2 = Vector((0,0,0))
        self.side_co = Vector((0,0,0))
        self.side_no = Vector((0,0,0))
        self.angle_snap = ""


    def start(self, pick_side=True):
        self.pick_side = pick_side
        self.reset()
        self.status = OPS_STATUS.ACTIVE


    def update(self, context, event, bmeCON:BmeshController):
        # Cancel
        if RMB_press(event):
            self.reset()
            self.status = OPS_STATUS.CANCELLED
            return
        # Completed
        if self.step > 3:
            self.status = OPS_STATUS.INACTIVE
        if self.status in {OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED}:
            return
        # View
        if pass_through(event, with_scoll=True, with_numpad=True, with_shading=True):
            self.status = OPS_STATUS.PASS
            return
        # Reset
        if event.type == self.reset_key and event.value == 'PRESS':
            self.start(self.pick_side)
            return
        self.angle_snap = ""
        self.mouse.x = event.mouse_region_x
        self.mouse.y = event.mouse_region_y
        self.status = OPS_STATUS.ACTIVE
        
        # --- CAPTURE POINT --- #
        if self.step < 3:
            point = self.__capture_point(context, event, bmeCON)
            if isinstance(point, Vector):
                if self.step == 1:
                    self.p1 = point
                else:
                    self.p2 = point
        
        # --- CAPTURE SIDE --- #
        if self.pick_side:
            if self.step == 3:
                self.side_co, self.side_no = cast_to_view_plane_pick_side(context, event, line_p1=self.p1, line_p2=self.p2)
        
        # --- LINE ONLY --- #
        else:
            if self.step == 2 and LMB_press(event):
                self.side_co, self.side_no = cast_to_view_plane_pick_side(context, event, line_p1=self.p1, line_p2=self.p2)
                # Error
                if (self.p2 - self.p1).length < 0.0001:
                    self.step = 2
                    notify(context, messages=[("$Error", "Points to close")])
                # Valid
                else:
                    self.step = 3
                    self.status = OPS_STATUS.COMPLETED

        # Step forward
        if LMB_press(event):
            self.step += 1
            # Hide the next circle to stop glitched appearence
            if self.step == 2:
                self.p2 = self.p1
        # Points to close
        if self.step == 3:
            if (self.p2 - self.p1).length < 0.0001:
                self.step = 2
                notify(context, messages=[("$Error", "Points to close")])
        # Complete
        if self.step > 3:
            self.status = OPS_STATUS.COMPLETED


    def __capture_point(self, context, event, bmeCON:BmeshController):
        if not isinstance(bmeCON, BmeshController):
            return None
        point = None
        options = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = None

        # Edge Center
        if event.alt:
            hit_info = bmeCON.ray_to_edge(context, event, options)
            if isinstance(hit_info, HitInfo):
                point = hit_info.edge_co_ws_center.copy()
        # Edge
        elif event.ctrl and event.shift:
            hit_info = bmeCON.ray_to_edge(context, event, options)
            if isinstance(hit_info, HitInfo):
                point = hit_info.edge_co_ws_nearest.copy()
        # Vert
        elif event.ctrl:
            hit_info = bmeCON.ray_to_vert(context, event, options)
            if isinstance(hit_info, HitInfo):
                point = hit_info.vert_co_ws.copy()
        # Angle
        elif event.shift and self.step == 2:
            point, angle = cast_onto_view_plane_with_angle_from_point(context, event, point=self.p1, increment_angle=15)
            if point is None or angle is None:
                return point
            deg = math.degrees(angle)
            self.angle_snap = str(int(round(deg)))
        # Face
        else:
            hit_info = bmeCON.ray_to_face(context, event, options)
            if isinstance(hit_info, HitInfo):
                point = hit_info.face_co_ws.copy()
        # Plane
        if point is None:
            point = cast_onto_view_plane(context, event)
        del hit_info
        return point


    def draw_2d(self, context):
        if self.status in {OPS_STATUS.COMPLETED, OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED}:
            return
        if self.step == 1:
            self.step_1_label.draw()
        elif self.step == 2:
            self.step_2_label.draw()
            if self.angle_snap:
                x = round(self.mouse.x + 25 * self.screen_factor)
                y = round(self.mouse.y - 25 * self.screen_factor)
                draw_label(messages=[("Angle", self.angle_snap)], left_x=x, top_y=y)
        elif self.step == 3:
            self.step_3_label.draw()


    def draw_3d(self, context):
        if self.status in {OPS_STATUS.COMPLETED, OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED}:
            return
        if self.step == 1:
            draw_action_line_3d(context, p1=self.p1, p2=None)
        elif self.step == 2:
            draw_action_line_3d(context, p1=self.p1, p2=self.p2)
        elif self.step == 3:
            draw_action_line_3d(context, p1=self.p1, p2=self.p2)
            if self.pick_side:
                arrow_size = 150 / pixels_per_unit_at_depth(context, self.side_co)
                end = self.side_co + (self.side_no * arrow_size)
                draw_arrow_3d(context, start=self.side_co, end=end, fill_color=(0,1,0,0.5), border_color=(1,1,1,1), border_width=1)


class PickRadialDirFromV3D:
    def __init__(self):
        # State
        self.status = OPS_STATUS.INACTIVE
        self.needs_rebuild = True
        # Data
        self.rot = Quaternion()
        self.axes = {}
        self.center = Vector((0,0))
        self.center_3d = Vector((0,0,0))
        self.best_axis_name = ""
        # Event
        self.mouse = Vector((0,0))
        # Constants
        self.axis_label_offset = 12 * screen_factor()
        self.exit_radius = 120 * screen_factor()
        self.axis_names = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
        self.axis_colors = {"+X": (1,0,0,1), "-X": (.5,0,0,1), "+Y": (0,1,0,1), "-Y": (0,.5,0,1), "+Z": (0,0,1,1), "-Z": (0,0,.5,1)}


    def reset(self):
        # State
        self.status = OPS_STATUS.INACTIVE
        self.needs_rebuild = True
        # Data
        self.axes.clear()
        self.center = Vector((0,0))
        self.center_3d = Vector((0,0,0))
        self.scale_factor = 1
        self.best_axis_name = ""
        # Event
        self.mouse = Vector((0,0))


    def start(self, rot=Quaternion()):
        self.reset()
        self.rot = rot
        self.status = OPS_STATUS.ACTIVE


    def update(self, context, event):
        # Call Start to engage
        if self.status == OPS_STATUS.INACTIVE:
            return
        # Passthrough
        if pass_through(event, with_scoll=True, with_numpad=True):
            self.needs_rebuild = True
            self.status = OPS_STATUS.PASS
            return
        # Rebuild
        if self.needs_rebuild:
            self.__build_widget(context, event)
        # Cancel
        if cancelled(event):
            self.reset()
            self.status = OPS_STATUS.CANCELLED
            return 
        # View Transitions
        casted_point = location_3d_to_region_2d(context.region, context.region_data, self.center_3d)
        if type(casted_point) == Vector:
            if (casted_point - self.center).length > (5 * screen_factor()):
                self.needs_rebuild = True
                self.status = OPS_STATUS.ACTIVE
                return
        else:
            self.needs_rebuild = True
            self.status = OPS_STATUS.ACTIVE
            return
        # Error in build
        if len(self.axes) == 0:
            self.needs_rebuild = True
            self.status = OPS_STATUS.ACTIVE
            return
        # Mouse outside of region
        if event.mouse_region_x > context.region.width or event.mouse_region_x < 0:
            return
        if event.mouse_region_y > context.region.height or event.mouse_region_y < 0:
            return
        # Confirm
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.__calc_best_axis(context)
        if not self.best_axis_name:
            self.status = OPS_STATUS.ACTIVE
            return
        if (self.mouse - self.center).length > self.exit_radius:
            self.status = OPS_STATUS.COMPLETED


    def __build_widget(self, context, event):
        self.center = Vector((event.mouse_region_x, event.mouse_region_y))
        self.axes.clear()
        region = context.region
        rv3d = context.region_data
        view_nor = rv3d.view_rotation @ Vector((0,0,1))
        view_loc = rv3d.view_location
        self.center_3d = cast_onto_plane(context, event, plane_co=view_loc, plane_no=view_nor)
        unit_pixels = pixels_per_unit_at_depth(context, self.center_3d)
        self.scale_factor = 100 / unit_pixels
        vectors = [
            self.rot @ Vector((1 , 0, 0)),
            self.rot @ Vector((-1, 0, 0)),
            self.rot @ Vector((0 , 1, 0)),
            self.rot @ Vector((0 ,-1, 0)),
            self.rot @ Vector((0 , 0, 1)),
            self.rot @ Vector((0 , 0,-1))]
        epsilon = 0.01
        for i, vec in enumerate(vectors):
            if 1 - abs(vec.dot(view_nor)) < epsilon:
                continue
            line_p1 = self.center_3d
            line_p2 = self.center_3d + (vec * self.scale_factor)
            name = self.axis_names[i]
            self.axes[name] = (line_p1, line_p2, self.axis_colors[name])
        self.needs_rebuild = False


    def __calc_best_axis(self, context):
        self.best_axis_name = ""
        mouse_vec = self.mouse - self.center
        if mouse_vec.x == 0 and mouse_vec.y == 0:
            return
        mouse_dir = mouse_vec.normalized()
        delta_angle = math.pi
        for axis_name, data in self.axes.items():
            p1, p2, col = data
            p2_casted = location_3d_to_region_2d(context.region, context.region_data, p2)
            if not p2_casted:
                continue
            line_dir = (p2_casted - self.center).normalized()
            angle = mouse_dir.angle(line_dir)
            if angle < delta_angle:
                delta_angle = angle
                self.best_axis_name = axis_name


    def draw_2d(self, context):
        if self.status in {OPS_STATUS.COMPLETED, OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED} or self.needs_rebuild:
            return
        for axis_name, data in self.axes.items():
            p1, p2, col = data
            p2_casted = location_3d_to_region_2d(context.region, context.region_data, p2)
            if p2_casted:
                draw_point(point=p2_casted, point_size=8, color=col)
        circle_col = (1,1,1,1)
        if self.best_axis_name in self.axes:
            circle_col = self.axes[self.best_axis_name][2]
        draw_circle_2d(radius=self.exit_radius, res=32, line_width=3, center=self.center, color=circle_col)
        draw_circle_2d(radius=(self.mouse - self.center).length, res=32, line_width=1, center=self.center, color=(1,1,1,.125))
        if self.best_axis_name:
            draw_text(text=self.best_axis_name, x=self.mouse.x + self.axis_label_offset, y=self.mouse.y + self.axis_label_offset, size=12, color=(1,1,1,1))


    def draw_3d(self, context):
        if self.status in {OPS_STATUS.COMPLETED, OPS_STATUS.INACTIVE, OPS_STATUS.CANCELLED} or self.needs_rebuild:
            return
        for axis_name, data in self.axes.items():
            p1, p2, col = data
            draw_line(p1, p2, width=2, color=col)


class EdgeLoopSelectV3D:
    def __init__(self):
        self.reset()
        # --- Edge Sel Colors --- #
        self.color_L = Vector((0.0, 1.0, 0.3, 1.0))
        self.color_C = Vector((0.0, 1.0, 1.0, 1.0))
        self.color_R = Vector((0.0, 0.3, 1.0, 1.0))
        self.color_A = Vector((0.0, 0.0, 0.0, 1.0))


    def reset(self):
        # State
        self.status = OPS_STATUS.INACTIVE
        # User Data
        self.step_limit = 0
        self.angle_limit = 0
        self.break_at_boundary = True
        self.break_at_intersections = True
        # Event
        self.mouse = Vector((0,0))
        self.clear_mesh_data()


    def clear_mesh_data(self):
        # Selection
        self.obj_name = ""
        self.mesh_name = ""
        self.edge_indices = []
        self.face_indices = []
        # --- Edge Loop Sel --- #
        self.edge_batch = None
        self.edge_cast_point_batch = None
        self.edges_L_batch = None
        self.edges_C_batch = None
        self.edges_R_batch = None
        self.edge_p1_batch = None
        self.edge_p2_batch = None


    def start(self, context, event, step_limit=0, angle_limit=0, break_at_boundary=True, break_at_intersections=True):
        self.reset()
        self.step_limit = step_limit
        self.angle_limit = angle_limit
        self.break_at_boundary = break_at_boundary
        self.break_at_intersections = break_at_intersections
        self.status = OPS_STATUS.ACTIVE


    def stop(self):
        self.status = OPS_STATUS.INACTIVE


    def update(self, context, event, bmeCON:BmeshController):
        # Call Start to engage
        if self.status == OPS_STATUS.INACTIVE:
            return
        # Passthrough
        if pass_through(event, with_scoll=True, with_numpad=True):
            self.status = OPS_STATUS.PASS
            return
        # Casting
        self.status = OPS_STATUS.ACTIVE
        self.mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.__edge_loop_sel(context, event, bmeCON)


    def __edge_loop_sel(self, context, event, bmeCON:BmeshController):
        self.clear_mesh_data()
        if not isinstance(bmeCON, BmeshController):
            return None
        point = None
        options = OPTIONS.CHECK_OBSTRUCTIONS if context.space_data.shading.type != 'WIREFRAME' else OPTIONS.NONE
        hit_info = bmeCON.ray_to_edge(context, event, options)
        if hit_info is None: return

        # References
        obj = hit_info.obj
        mesh = obj.data
        edge_index = hit_info.edge_index
        if edge_index >= len(mesh.edges) or edge_index < 0:
            return
        hit_co_ws = hit_info.edge_co_ws_nearest
        mat_ws = hit_info.mat_ws

        # Casted Edge Data
        index_direction = -1
        edge = mesh.edges[edge_index]
        v1 = mat_ws @ mesh.vertices[edge.vertices[0]].co
        v2 = mat_ws @ mesh.vertices[edge.vertices[1]].co

        # Directional Vert
        ret = intersect_point_line(hit_co_ws, v1, v2)
        if ret and len(ret) == 2:
            point, factor = ret
            if factor <= 1/3:
                index_direction = 0
            elif factor >= 2/3:
                index_direction = 1

        # TRACE || Capture
        self.edge_indices = ops_trace_edges(context, obj,
            step_limit=self.step_limit,
            angle_limit=self.angle_limit,
            select_traced=False,
            from_selected=False,
            from_index=edge_index,
            vert_dir_index=index_direction,
            break_at_intersections=self.break_at_intersections,
            break_at_boundary=self.break_at_boundary)
        self.obj_name = obj.name
        self.mesh_name = obj.data.name
        if not self.edge_indices:
            return
        # BATCH || Casted Point
        self.edge_cast_point_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [hit_co_ws]})
        if index_direction < 0:
            self.color_A = self.color_C
        elif index_direction < 1:
            self.color_A = self.color_L
        elif index_direction > 0:
            self.color_A = self.color_R
        # BATCH || Active Edge Line
        center = (v1 + v2) / 2
        self.edge_batch = batch_for_shader(SMOOTH_COLOR, 'LINE_STRIP', {"pos": (v1, center, v2), "color": (self.color_L, self.color_C, self.color_R)})
        # BATCH || Active Edge Points
        self.edge_p1_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [v1]})
        self.edge_p2_batch = batch_for_shader(UNIFORM_COLOR, 'POINTS', {"pos": [v2]})
        # BATCH || Traced Edges
        lines = []
        for index in self.edge_indices:
            if index == edge_index:
                continue
            edge = mesh.edges[index]
            v1 = mat_ws @ mesh.vertices[edge.vertices[0]].co
            lines.append(v1)
            v2 = mat_ws @ mesh.vertices[edge.vertices[1]].co
            lines.append(v2)
        self.edges_L_batch = None
        self.edges_C_batch = None
        self.edges_R_batch = None
        if index_direction < 0:
            self.edges_C_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": lines})
        elif index_direction < 1:
            self.edges_L_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": lines})        
        elif index_direction > 0:
            self.edges_R_batch = batch_for_shader(UNIFORM_COLOR, 'LINES', {"pos": lines})


    def select_mesh_geo(self, context):
        if not self.edge_indices: return
        obj = get_visible_mesh_obj_by_name(context, obj_name=self.obj_name, update=True)
        if not obj: return
        toggle = object_mode_toggle_start(context)
        bm = bmesh.new(use_operators=True)
        bm.from_mesh(obj.data, face_normals=True, vertex_normals=True, use_shape_key=False, shape_key_index=0)
        bm.edges.ensure_lookup_table()
        for edge_index in self.edge_indices:
            if edge_index < len(bm.edges) and edge_index >= 0:
                edge = bm.edges[edge_index]
                if edge.is_valid:
                    edge.select = True
        bm.to_mesh(obj.data)
        obj.data.calc_loop_triangles()
        if toggle: object_mode_toggle_end(context)


    def draw_2d(self, context):
        if self.status == OPS_STATUS.INACTIVE:
            return


    def draw_3d(self, context):
        if self.status in {OPS_STATUS.INACTIVE, OPS_STATUS.PASS}:
            return
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(3)
        if self.edges_L_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_L)
            self.edges_L_batch.draw(UNIFORM_COLOR)
        if self.edges_C_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_C)
            self.edges_C_batch.draw(UNIFORM_COLOR)
        if self.edges_R_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_R)
            self.edges_R_batch.draw(UNIFORM_COLOR)
        gpu.state.line_width_set(2)
        if self.edge_batch:
            self.edge_batch.draw(SMOOTH_COLOR)
        gpu.state.line_width_set(1)
        gpu.state.point_size_set(6)
        if self.edge_p1_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_L)
            self.edge_p1_batch.draw(UNIFORM_COLOR)
        if self.edge_p2_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_R)
            self.edge_p2_batch.draw(UNIFORM_COLOR)
        gpu.state.blend_set('NONE')
        gpu.state.point_size_set(8)
        if self.edge_cast_point_batch:
            UNIFORM_COLOR.uniform_float("color", self.color_A)
            self.edge_cast_point_batch.draw(UNIFORM_COLOR)
        gpu.state.point_size_set(1)
